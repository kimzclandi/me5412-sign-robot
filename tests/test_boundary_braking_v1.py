"""stop_and_go_v1: a fixed short stop/start segment when the boundary velocity cannot be carried into a route."""
from copy import deepcopy

import numpy as np
import pytest

from sign_robot.motion import ROOT
from sign_robot.pair_contract import BOUNDARY_BRAKING_V1, load_policy, validate_policy_v2
from sign_robot.pair_timing import _boundary_rest_v1, quintic_coefficients_v2, time_route_v2

BRAKING = 'transition_policy_hospital_sentences_braking_v1.json'
NAMES = np.array(['left_shoulder_pitch_joint', 'left_elbow_joint'])  # arm joints: 15 rad/s rate limit
BOUNDS = np.array([[-3.0, 3.0], [-3.0, 3.0]])


def _load(name):
    return load_policy(ROOT/'config'/name, supported_versions=(1, 2))


def _state(p, v):
    return {'position': list(p), 'velocity': list(v), 'acceleration': [0.0, 0.0]}


def test_braking_policy_changes_only_planner_budget_and_braking():
    old, new = _load('transition_policy_hospital_sentences_connector_only_v1.json'), _load(BRAKING)
    assert {k for k in old if old[k] != new[k]} == {'policy_id', 'planner'}
    assert new['quality'] == old['quality'] and new['constraints'] == old['constraints']
    assert new['planner']['boundary_braking']['version'] == BOUNDARY_BRAKING_V1
    bad = deepcopy(new)
    bad['planner']['boundary_braking']['limit_fraction'] = 1.5
    with pytest.raises(ValueError, match='connector limits'):
        validate_policy_v2(bad)
    bad = deepcopy(new)
    bad['planner']['boundary_braking']['extra'] = 1
    with pytest.raises(ValueError, match='fields'):
        validate_policy_v2(bad)


def test_stop_profile_is_monotone_and_travels_half_v_t():
    c = quintic_coefficients_v2(_state([0, 0], [2, -1]), _state([2 * .2 / 2, -1 * .2 / 2], [0, 0]), .2)
    assert np.allclose(c[0], [0, .4, 0, -.4, .2, 0])  # v0 T (u - u^3 + u^4 / 2)
    u = np.linspace(0, 1, 201)
    velocity = np.polynomial.polynomial.polyval(u, np.polynomial.polynomial.polyder(c[0]))
    assert velocity.min() >= -1e-12


def test_rest_is_shortest_stop_within_limits_and_none_when_slow():
    policy = _load(BRAKING)
    rest = _boundary_rest_v1(_state([0, 0], [6, -3]), 'source', NAMES, BOUNDS, policy, ())
    assert rest['feasible'] and rest['clamped_joints'] == 0
    frames = rest['frames']
    assert 1.5 * 6 / (frames / 30) <= policy['quality']['limits']['peak_acceleration_rad_s2'] + 1e-9
    assert np.allclose(rest['rest']['position'], [6 * frames / 60, -3 * frames / 60])
    shorter = (frames - 1) / 30
    assert frames == 1 or 1.5 * 6 / shorter > 120 or 6 * 6 / shorter ** 2 > 3000
    entry = _boundary_rest_v1(_state([0, 0], [6, -3]), 'target', NAMES, BOUNDS, policy, ())
    assert np.allclose(entry['rest']['position'], [-6 * entry['frames'] / 60, 3 * entry['frames'] / 60])
    assert _boundary_rest_v1(_state([0, 0], [0.01, 0]), 'source', NAMES, BOUNDS, policy, ()) is None


def test_stop_toward_a_close_limit_is_clamped_or_refused():
    policy = _load(BRAKING)
    # v = 1 needs 2 frames (jerk); the free stop would travel v T / 2 = 0.033. A clamped stop over d
    # stays monotone (no overshoot past the limit) while d >= 0.4 v T = 0.027, so 0.03 of room works.
    near = _boundary_rest_v1(_state([2.97, 0], [1, 0]), 'source', NAMES, BOUNDS, policy, ())
    assert near['feasible'] and near['clamped_joints'] == 1 and near['frames'] == 2
    assert near['rest']['position'][0] <= 3.0
    fast = _boundary_rest_v1(_state([2.9, 0], [10, 0]), 'source', NAMES, BOUNDS, policy, ())
    assert fast['feasible'] is False and fast['reason_codes']


def test_braked_fallback_keeps_fixed_stop_segments_and_exact_boundaries():
    policy = deepcopy(_load(BRAKING))
    policy['planner']['minimum_duration_s'] = 0.3
    start, end = _state([0, 0], [6, 0]), _state([0.5, 0], [-6, 0])
    calls = []

    def geometry(segments):
        # Reject any curve that carries the boundary velocity straight into the route.
        calls.append(len(segments))
        return {'passed': len(segments) > 1}
    timed = time_route_v2([[0, 0], [0.5, 0]], start, end, NAMES, BOUNDS, policy, validate_curve=geometry)
    assert timed.segments is not None and timed.diagnostics['status'] == 'TIMED_CANDIDATE'
    assert timed.diagnostics['attempts'][-1]['variant'] == BOUNDARY_BRAKING_V1
    braking = timed.diagnostics['boundary_braking']
    first, last = timed.segments[0], timed.segments[-1]
    assert np.isclose(first['end_time_s'] - first['start_time_s'], braking['source']['frames'] / 30)
    assert np.isclose(last['end_time_s'] - last['start_time_s'], braking['target']['frames'] / 30)
    for segment, state, u in ((first, start, 0.0), (last, end, 1.0)):
        c = np.asarray(segment['coefficients'])
        duration = segment['end_time_s'] - segment['start_time_s']
        values = [np.polynomial.polynomial.polyval(u, np.polynomial.polynomial.polyder(row, k)) / duration ** k
                  for row in c for k in (0, 1, 2)]
        assert np.allclose(np.asarray(values).reshape(2, 3)[:, 0], state['position'])
        assert np.allclose(np.asarray(values).reshape(2, 3)[:, 1], state['velocity'])
        assert np.allclose(np.asarray(values).reshape(2, 3)[:, 2], 0)


def test_without_braking_the_timing_diagnostics_are_unchanged():
    policy = _load('transition_policy_hospital_sentences_connector_only_v1.json')
    timed = time_route_v2([[0, 0], [0.5, 0]], _state([0, 0], [0, 0]), _state([0.5, 0], [0, 0]), NAMES, BOUNDS, policy)
    assert timed.segments is not None
    assert 'variant' not in timed.diagnostics['attempts'][0] and 'boundary_braking' not in timed.diagnostics
