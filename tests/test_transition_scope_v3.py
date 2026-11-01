"""v3 scores quality outside protected cores; cores keep pose/timing checks."""
from copy import deepcopy
import json

import numpy as np
import pytest

from sign_robot.motion import ROOT
from sign_robot.pair_contract import (TRANSITION_SCOPE_METHOD_V3, atomic_json, json_hash, load_policy,
    save_pair_trajectory, validate_policy_v2)
from sign_robot.pair_verification_v2 import _masked_trapezoid, _protected_replay_mask, verify_saved_pair_v2


def _load(name):
    return load_policy(ROOT/'config'/name, supported_versions=(1, 2))


def test_v3_changes_only_metric_scope_and_keeps_every_threshold():
    old, new = _load('transition_policy_user_protected_v2.json'), _load('transition_policy_user_protected_v3.json')
    assert new['quality']['full_clip_method'] == TRANSITION_SCOPE_METHOD_V3
    changed = {k for k in old if old[k] != new[k]}
    assert changed == {'policy_id', 'quality'}
    assert {k for k in old['quality'] if old['quality'][k] != new['quality'][k]} == {'full_clip_method'}
    assert new['formal_acceptance_enabled'] is False
    assert new['endpoints']['review_status'] == 'pending'


def test_transition_scope_requires_user_protected_cores():
    policy = deepcopy(_load('transition_policy_v2.json'))
    policy['quality']['full_clip_method'] = TRANSITION_SCOPE_METHOD_V3
    with pytest.raises(ValueError, match='user-protected'):
        validate_policy_v2(policy)


def test_mask_covers_inclusive_core_frames_and_integral_skips_mixed_intervals():
    trajectory = {'word_instances': [{'protected_core_frames': [2, 4]}, {'protected_core_frames': [0, 1]}],
                  'segments': [{'start_time_s': 0.0, 'source_frames': [0, 4]}, {},
                               {'start_time_s': 0.4, 'source_frames': [0, 3]}]}
    t = np.arange(10) / 30
    mask = _protected_replay_mask(trajectory, t)
    assert np.flatnonzero(mask).tolist() == [2, 3, 4]  # 0.4 s is 12th frame, outside t
    assert _masked_trapezoid(np.ones(10), t, ~mask) == pytest.approx(5 / 30)  # (0,1) and (5..9)
    with pytest.raises(ValueError):
        _protected_replay_mask(trajectory, t[2:5])


@pytest.fixture(scope='module')
def v3_curve():
    from sign_robot.pair_routes import build_pair_context_v2, iter_deterministic_attempts_v2
    policy = _load('transition_policy_user_protected_v3.json')
    context = build_pair_context_v2(ROOT, policy)
    attempt = next(a for a in iter_deterministic_attempts_v2(context, 'NOW', 'COME', seed=5412) if a.timing_trajectories)
    return policy, attempt.trajectory or attempt.timing_trajectories[0]


def test_v3_excludes_protected_frames_but_still_proves_cores_unchanged(v3_curve, tmp_path):
    policy, curve = v3_curve
    path = tmp_path/'v3.json'
    save_pair_trajectory(path, curve)
    evidence = verify_saved_pair_v2(ROOT, path, policy)
    assert evidence['validation_complete'] and evidence['protected_core_preserved']
    scope = evidence['quality_scope']
    assert scope['method'] == TRANSITION_SCOPE_METHOD_V3 and scope['protected_defects_gate'] == 'informational_only'
    assert scope['excluded_protected_replay_frames'] == 74 + 106
    assert all(x['poses_bitwise_equal'] for x in evidence['protected_instance_checks'])
    assert 'PROTECTED_SOURCE_QUALITY_VIOLATION' not in evidence['reason_codes']
    now_audit = next(a for i, a in evidence['protected_source_audit'].items() if a['frame_count'] == 74)
    assert {d['metric'] for d in now_audit['excluded_from_quality_gate']} == {'peak_acceleration_rad_s2', 'peak_jerk_rad_s3'}
    unscoped = evidence['full_clip_unscoped_metrics']
    for key in ('peak_acceleration_rad_s2', 'peak_jerk_rad_s3', 'jerk_integral_rad2_s5'):
        assert evidence['metrics'][key] <= unscoped[key]
    assert all(loc['origin'] != 'protected_source_clip' for loc in evidence['metric_locations'])
    assert evidence['playback_eligible'] is False


def test_v3_still_rejects_retimed_protected_source(v3_curve, tmp_path):
    policy, original = v3_curve
    curve = deepcopy(original)
    curve['segments'][0].update(time_scale=.9)
    path = tmp_path/'retimed.json'
    atomic_json(path, {'schema_version': 2, 'trajectory': curve, 'trajectory_hash': json_hash(curve)})
    evidence = verify_saved_pair_v2(ROOT, path, policy)
    assert evidence['status'] == 'ERROR' and evidence['numerical_checks_passed'] is not True
