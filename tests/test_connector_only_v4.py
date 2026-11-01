"""v4 gates only the added connector; source-motion findings are reported, never gated."""
from copy import deepcopy

import numpy as np
import pytest

from sign_robot.motion import ROOT
from sign_robot.pair_contract import (CONNECTOR_ONLY_METHOD_V4, CONNECTOR_STENCIL_FRAMES, load_policy,
    save_pair_trajectory, validate_policy_v2)
from sign_robot.pair_verification_v2 import connector_masks, verify_saved_pair_v2

V4_POLICY = 'transition_policy_hospital_sentences_connector_only_v1.json'


def _load(name):
    return load_policy(ROOT/'config'/name, supported_versions=(1, 2))


def test_v4_changes_only_metric_scope_and_keeps_every_threshold():
    old, new = _load('transition_policy_user_protected_hospital35_retry_budget_v1.json'), _load(V4_POLICY)
    assert new['quality']['full_clip_method'] == CONNECTOR_ONLY_METHOD_V4
    assert {k for k in old if old[k] != new[k]} == {'policy_id', 'quality'}
    assert {k for k in old['quality'] if old['quality'][k] != new['quality'][k]} == {'full_clip_method'}
    assert new['constraints'] == old['constraints'] and new['formal_acceptance_enabled'] is False


def test_connector_scope_requires_user_protected_cores():
    policy = deepcopy(_load('transition_policy_v2.json'))
    policy['quality']['full_clip_method'] = CONNECTOR_ONLY_METHOD_V4
    with pytest.raises(ValueError, match='user-protected'):
        validate_policy_v2(policy)


def test_masks_keep_whole_stencils_inside_the_connector():
    t = np.arange(30) / 30
    polynomials = [{'start_time_s': 10 / 30, 'end_time_s': 15 / 30}, {'start_time_s': 15 / 30, 'end_time_s': 20 / 30}]
    span, interior = connector_masks(polynomials, t)
    assert np.flatnonzero(span).tolist() == list(range(10, 21))
    margin = CONNECTOR_STENCIL_FRAMES
    assert np.flatnonzero(interior).tolist() == list(range(10 + margin, 21 - margin))
    with pytest.raises(ValueError, match='too short'):
        connector_masks([{'start_time_s': 10 / 30, 'end_time_s': 15 / 30}], t)


@pytest.fixture(scope='module')
def hello_you():
    # HELLO's own source slice comes within 1.1 mm of a collision (a group-2 source finding).
    from sign_robot.pair_routes import build_pair_context_v2, iter_deterministic_attempts_v2
    policy = _load(V4_POLICY)
    context = build_pair_context_v2(ROOT, policy)
    attempt = next(a for a in iter_deterministic_attempts_v2(context, 'HELLO', 'YOU', seed=5412) if a.timing_trajectories)
    return policy, attempt.trajectory or attempt.timing_trajectories[0]


def test_source_findings_are_reported_but_not_gated(hello_you, tmp_path):
    policy, curve = hello_you
    path = tmp_path/'v4.json'
    save_pair_trajectory(path, curve)
    evidence = verify_saved_pair_v2(ROOT, path, policy)
    assert evidence['validation_complete'] and evidence['protected_core_preserved']
    assert evidence['quality_scope']['scope'] == 'connector_only'
    source = evidence['source_side_findings']
    assert source['gate'] == 'informational_only' and 'ORIGINAL_WORD_SLICE_COLLISION' in source['reason_codes']
    for code in ('ORIGINAL_WORD_SLICE_COLLISION', 'PROTECTED_SOURCE_QUALITY_VIOLATION', 'FULL_CLIP_SPEED_VIOLATION'):
        assert code not in evidence['reason_codes']
    connector = [m['min_clearance_mm'] for m in evidence['dense_recheck_result'] if m['kind'] == 'polynomial_v2']
    assert evidence['min_clearance_mm'] == min(connector)
    assert source['min_clearance_mm'] < 2.0 <= evidence['min_clearance_mm']
    assert all(loc['origin'] != 'protected_source_clip' for loc in evidence['metric_locations'])
    assert evidence['playback_eligible'] is False


def test_v4_still_gates_the_connector_and_the_unchanged_cores(hello_you, tmp_path):
    policy, original = hello_you
    path = tmp_path/'v4.json'
    save_pair_trajectory(path, original)
    evidence = verify_saved_pair_v2(ROOT, path, policy)
    limits = policy['quality']['limits']
    for key in ('peak_acceleration_rad_s2', 'peak_jerk_rad_s3', 'jerk_integral_rad2_s5', 'maximum_transition_duration_s'):
        assert (evidence['metrics'][key] > limits[key]) == ('QUALITY_LIMIT_' + key.upper() in evidence['reason_codes'])
    assert evidence['quality_scope']['scored_replay_frames'] < evidence['quality_scope']['connector_replay_frames']
    assert evidence['numerical_checks_passed'] == (not [c for c in evidence['reason_codes'] if not c.endswith(
        ('NOT_ENABLED', 'NOT_FROZEN', 'NOT_APPROVED', 'NOT_HUMAN_REVIEWED'))])
    curve = deepcopy(original)
    curve['segments'][0].update(time_scale=.9)
    path = tmp_path/'retimed.json'
    try:
        save_pair_trajectory(path, curve)
    except ValueError:
        return
    assert verify_saved_pair_v2(ROOT, path, policy)['numerical_checks_passed'] is not True
