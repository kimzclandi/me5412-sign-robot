"""Stop-free connector timing (smooth_route_timing_v1), fewest-stops selection and sign-level limits."""
import copy
import json
from types import SimpleNamespace

import numpy as np
import pytest

from sign_robot import pair_runner_v2
from sign_robot.motion import ROOT
from sign_robot.pair_contract import (
    CORNER_BLEND_V1, FEWEST_STOPS_SELECTION_V1, MIN_JERK_SPLINE_V1, connector_interior_stops, load_policy,
    polynomial_boundary_v2, read_motion, validate_policy_v2,
)
from sign_robot.pair_timing import (
    connector_quality_v2, corner_blend_pieces, min_jerk_spline_states, quintic_coefficients_v2, time_route_v2,
)

OLD, NEW = 'transition_policy_hospital_sentences_fast_v4.json', 'transition_policy_hospital_sentences_fast_v5.json'
NAMES = np.array(['left_shoulder_pitch_joint', 'right_shoulder_pitch_joint'])  # arm joints: 15 rad/s
BOUNDS = np.array([[-3.0, 3.0], [-3.0, 3.0]])


def _load(name):
    return load_policy(ROOT/'config'/name, supported_versions=(1, 2))


def _state(p, v=(0.0, 0.0), a=(0.0, 0.0)):
    return {'position': list(p), 'velocity': list(v), 'acceleration': list(a)}


def _segments(pieces):
    out, cursor = [], 0.0
    for duration, first, last in pieces:
        out.append({'kind': 'polynomial_v2', 'start_time_s': cursor, 'end_time_s': cursor + duration,
                    'coefficients': quintic_coefficients_v2(first, last, float(duration)).tolist()})
        cursor += duration
    return out


def _continuous(segments):
    for left, right in zip(segments, segments[1:]):
        a, b = polynomial_boundary_v2(left, 'end'), polynomial_boundary_v2(right, 'start')
        for key in a:
            np.testing.assert_allclose(a[key], b[key], atol=1e-7)


def _jerk_integral(segments):
    policy = _load(NEW)
    metrics, _ = connector_quality_v2(segments, BOUNDS, NAMES, policy)
    return metrics['jerk_integral_rad2_s5']


def test_new_policy_changes_only_timing_selection_and_three_limits():
    old, new = _load(OLD), _load(NEW)
    assert {k for k in old if old[k] != new[k]} == {'policy_id', 'planner', 'selection_rule', 'quality'}
    assert {k for k in new['planner'] if new['planner'].get(k) != old['planner'].get(k)} == {'smooth_timing', 'budget', 'rrt'}
    assert new['planner']['budget'] == {**old['planner']['budget'], 'wall_time_s': 720.0}
    assert new['planner']['rrt'] == {**old['planner']['rrt'], 'wall_time_s': 240.0}
    assert new['selection_rule'] == FEWEST_STOPS_SELECTION_V1
    changed = {k for k in new['quality']['limits'] if new['quality']['limits'][k] != old['quality']['limits'][k]}
    assert changed == {'peak_acceleration_rad_s2', 'peak_jerk_rad_s3', 'jerk_integral_rad2_s5'}
    assert new['constraints'] == old['constraints']  # speed caps unchanged
    for change in ({'growth': 1.0}, {'growth': 3.0}, {'minimum_total_frames': 6}, {'version': 'x'}, {'extra': 1}):
        bad = copy.deepcopy(new)
        bad['planner']['smooth_timing'].update(change)
        with pytest.raises(ValueError):
            validate_policy_v2(bad)


def test_relaxed_limits_stay_within_the_signs_upper_quartile():
    library = {w['gloss']: w for w in json.loads((ROOT/'motions/hospital_v1_motions.json').read_text())['glosses']}
    cores = {r['gloss']: r['protected_core_frames']
             for r in json.loads((ROOT/'config/user_protected_hospital35_v2.json').read_text())['records']}
    words = {w for s in ('HELLO YOU APPOINTMENT HAVE', 'YOU NEED INTERPRETER', 'PLEASE WAIT DOCTOR COME SOON',
                         'YOU HURT WHERE', 'NOW NURSE BLOOD-DRAW', 'MEDICINE MORNING NIGHT TAKE', 'YOU UNDERSTAND')
             for w in s.split()}
    peaks = []
    for gloss in sorted(words):
        clip = read_motion(ROOT/library[gloss]['motion'])
        q, t = clip['positions'], clip['timestamps_s']
        v = np.gradient(q, t, axis=0, edge_order=2)
        a = np.gradient(v, t, axis=0, edge_order=2)
        j = np.gradient(a, t, axis=0, edge_order=2)
        c0, c1 = cores[gloss]
        core = slice(c0, c1 + 1)
        peaks.append((np.abs(a[core]).max(), np.abs(j[core]).max(),
                      np.trapezoid(np.sum(j[core] ** 2, axis=1), t[core]) / (t[c1] - t[c0])))
    upper = np.percentile(np.array(peaks), 75, axis=0)
    limits = _load(NEW)['quality']['limits']
    assert len(words) == 21
    assert limits['peak_acceleration_rad_s2'] <= upper[0] and limits['peak_jerk_rad_s3'] <= upper[1]
    assert limits['jerk_integral_rad2_s5'] <= upper[2] * 0.4  # the per-second rate over the shortest connectors


def test_min_jerk_spline_passes_knots_without_stopping_and_beats_stop_and_go():
    knots = np.array([[0.0, 0.0], [0.6, 0.3], [1.2, 0.2], [1.5, -0.4]])
    durations = np.array([0.2, 0.25, 0.2])
    start, end = _state(knots[0], (1.0, 0.5)), _state(knots[-1], (0.0, -1.0))
    states = min_jerk_spline_states(knots, durations, start, end)
    spline = _segments([(d, states[i], states[i + 1]) for i, d in enumerate(durations)])
    _continuous(spline)
    for i, segment in enumerate(spline):
        np.testing.assert_allclose(polynomial_boundary_v2(segment, 'start')['position'], knots[i], atol=1e-12)
    assert connector_interior_stops(spline) == 0
    stops = _segments([(d, start if i == 0 else _state(knots[i]), end if i == 2 else _state(knots[i + 1]))
                       for i, d in enumerate(durations)])
    assert connector_interior_stops(stops) == 2
    assert _jerk_integral(spline) < _jerk_integral(stops)
    # one segment is exactly the old carry-the-boundary quintic
    [only] = _segments([(0.3, *min_jerk_spline_states(knots[[0, -1]], [0.3], start, end))])
    np.testing.assert_allclose(only['coefficients'], quintic_coefficients_v2(start, end, 0.3), atol=1e-12)


def test_spline_keeps_affine_couplings():
    parent = np.array([[0.0], [0.5], [0.2], [0.9]])
    knots = np.hstack([parent, 1.5 * parent + 0.1])
    start = _state(knots[0], (0.4, 0.6))
    end = _state(knots[-1], (-0.2, -0.3))
    states = min_jerk_spline_states(knots, [0.2, 0.3, 0.25], start, end)
    for s in states:
        assert s['velocity'][1] == pytest.approx(1.5 * s['velocity'][0], abs=1e-9)
        assert s['acceleration'][1] == pytest.approx(1.5 * s['acceleration'][0], abs=1e-9)


def test_corner_blend_holds_still_joints_and_overlaps_stages():
    # stage 1 moves only joint 0, stage 2 only joint 1: a stop-and-go route would halt between them
    knots = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]])
    durations = np.array([0.3, 0.3])
    pieces = corner_blend_pieces(knots, durations, _state(knots[0]), _state(knots[-1]))
    segments = _segments(pieces)
    _continuous(segments)
    assert sum(p[0] for p in pieces) == pytest.approx(0.6)
    np.testing.assert_allclose(polynomial_boundary_v2(segments[-1], 'end')['position'], knots[-1], atol=1e-12)
    assert connector_interior_stops(segments) == 0
    t = np.linspace(0, 1, 201)
    for segment in segments:
        c = np.asarray(segment['coefficients'])
        values = np.vander(t, 6, increasing=True) @ c.T
        assert values[:, 0].min() >= -1e-12 and values[:, 0].max() <= 1 + 1e-12  # no overshoot
        assert values[:, 1].min() >= -1e-12 and values[:, 1].max() <= 1 + 1e-12
    # joint 1 is still during the first quarter (before the corner blend begins), joint 0 in the last
    first = np.asarray(segments[0]['coefficients'])
    assert np.allclose(first[1], 0.0)
    last = np.asarray(segments[-1]['coefficients'])
    assert np.allclose(last[0], [1, 0, 0, 0, 0, 0])


def test_time_route_tries_the_stop_free_curves_first_and_keeps_the_shortest():
    policy = _load(NEW)
    knots = np.array([[0.0, 0.0], [0.6, 0.3], [1.2, 0.2], [1.5, -0.4]])
    timed = time_route_v2(knots, _state(knots[0]), _state(knots[-1]), NAMES, BOUNDS, policy)
    assert timed.segments is not None and connector_interior_stops(timed.segments) == 0
    kept = timed.diagnostics['smooth_timing']['kept']
    assert kept['curve'] in (MIN_JERK_SPLINE_V1, CORNER_BLEND_V1)
    frames = [s['frames'] for s in timed.diagnostics['smooth_timing']['schedules'] if s['frames'] is not None]
    assert kept['frames'] == min(frames)
    assert timed.attempt_segments[-1] == timed.segments
    old = time_route_v2(knots, _state(knots[0]), _state(knots[-1]), NAMES, BOUNDS, _load(OLD))
    assert 'smooth_timing' not in old.diagnostics and connector_interior_stops(old.segments) == 2
    duration = lambda s: s[-1]['end_time_s'] - s[0]['start_time_s']
    assert duration(timed.segments) < duration(old.segments)


def _store(candidates, monkeypatch):
    """(stops, retained source, connector frames, retained target, peak jerk) per attempt."""
    trajectories, evidence = {}, {}
    for attempt_id, (stops, retained_source, frames, retained_target, jerk) in candidates.items():
        pieces = [(frames / 30 / (stops + 1), _state([0.1 * k, 0.0]), _state([0.1 * (k + 1), 0.0]))
                  for k in range(stops + 1)]  # rest-to-rest pieces: a full stop at every inner boundary
        trajectories[attempt_id] = {
            'word_instances': [{'source_frames': [10, 40 + retained_source], 'protected_core_frames': [10, 40]},
                               {'source_frames': [20 - retained_target, 60], 'protected_core_frames': [20, 60]}],
            'segments': [{'end_time_s': 0.0}, *_segments(pieces), {'end_time_s': 9.0}],
            'planner': {'method': 'direct'}, 'id': attempt_id}
        evidence[attempt_id] = {'evidence': {'metrics': {'peak_jerk_rad_s3': jerk, 'peak_acceleration_rad_s2': 10.0,
                                                         'analytic_connector_jerk_integral_rad2_s5': 1.0}}}
    monkeypatch.setattr(pair_runner_v2, 'inside', lambda root, path: path)
    monkeypatch.setattr(pair_runner_v2, 'read_pair_trajectory', lambda path, schema_version: trajectories[path])
    monkeypatch.setattr(pair_runner_v2, 'read_json', lambda path: evidence[path])
    store = SimpleNamespace(policy=_load(NEW), run_dir=None)
    reviews = [{'attempt_id': a, 'path': a, 'numerical_checks_passed': True} for a in candidates]
    attempts = [{'attempt_id': a, 'candidate_file': a} for a in candidates]
    return pair_runner_v2.V2RunStore._selection_winner(store, reviews, attempts)


def test_fewest_stops_rule_prefers_a_stop_free_connector(monkeypatch):
    candidates = {'fast_but_stops': (2, 0, 12, 0, 100.0), 'stop_free': (0, 0, 20, 0, 900.0),
                  'stop_free_faster': (0, 2, 14, 1, 800.0)}
    assert _store(candidates, monkeypatch) == 'stop_free_faster'
    assert _store({'a': (1, 0, 10, 0, 1.0), 'b': (1, 0, 9, 0, 2.0)}, monkeypatch) == 'b'
