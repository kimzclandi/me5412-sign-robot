"""v5 lift-off arrival: fingers rest at an earlier target frame, then re-create its lift-off."""
import numpy as np
import pytest

from sign_robot.motion import ROOT
from sign_robot.pair_contract import (LIFT_OFF_ARRIVAL_GENERATOR, load_policy, polynomial_boundary_v2,
    save_pair_trajectory)
from sign_robot.pair_fingers import apply_finger_arrival_v1, finger_arrival_plan_v1
from sign_robot.pair_routes import build_pair_context_v2, iter_deterministic_attempts_v2, target_finger_arrival_v1
from sign_robot.pair_timing import quintic_coefficients_v2


def _load(name):
    return load_policy(ROOT/'config'/name, supported_versions=(1, 2))


@pytest.fixture(scope='module')
def contexts():
    return {name: build_pair_context_v2(ROOT, _load(f'transition_policy_user_protected_{name}.json')) for name in ('v4', 'v5')}


def test_v5_changes_only_cut_generator():
    old, new = _load('transition_policy_user_protected_v4.json'), _load('transition_policy_user_protected_v5.json')
    assert {k for k in old if old[k] != new[k]} == {'policy_id', 'endpoints'}
    assert {k for k in old['endpoints'] if old['endpoints'][k] != new['endpoints'][k]} == {'generator_version'}
    assert new['endpoints']['generator_version'] == LIFT_OFF_ARRIVAL_GENERATOR


def test_plan_targets_only_lift_off_entries_and_respects_limits(contexts):
    v4, v5 = contexts['v4'], contexts['v5']
    now, come = v5.clips['NOW'], v5.clips['COME']
    plan = target_finger_arrival_v1(v5, now, 3)
    assert plan['feasible'] and plan['staging_frame'] == 0 and plan['arrival_s'] == pytest.approx(0.1)
    limits = v5.policy['quality']['limits']
    assert plan['lift_off_peaks']['acceleration_rad_s2'] <= limits['peak_acceleration_rad_s2']
    assert plan['lift_off_peaks']['jerk_rad_s3'] <= limits['peak_jerk_rad_s3']
    infeasible = target_finger_arrival_v1(v5, now, 1)
    assert infeasible['feasible'] is False and infeasible['rejected_staging'][0]['reason_codes']
    assert target_finger_arrival_v1(v5, come, 27) is None
    assert target_finger_arrival_v1(v4, now, 3) is None


def test_arrival_keeps_arm_curve_and_endpoints_and_rests_at_staging():
    names = np.array(['left_shoulder_pitch_joint', 'L_index_proximal_joint', 'L_index_intermediate_joint'])
    couplings = [{'parent': 'L_index_proximal_joint', 'child': 'L_index_intermediate_joint', 'multiplier': 1.0, 'offset': 0.0}]
    start = {'position': [0.2, 0.8, 0.8], 'velocity': [0.1, 0.0, 0.0], 'acceleration': [0.0, 0.0, 0.0]}
    end = {'position': [0.6, 0.02, 0.02], 'velocity': [0.0, 0.3, 0.3], 'acceleration': [0.0, 0.0, 0.0]}
    base = [{'kind': 'polynomial_v2', 'start_time_s': 1.0, 'end_time_s': 1.6,
             'coefficients': quintic_coefficients_v2(start, end, 0.6).tolist()}]
    plan = {'version': 1, 'feasible': True, 'staging_frame': 0, 'target_frame': 3, 'arrival_s': 0.1,
            'staging_position': [0.0, 0.0, 0.0], 'lift_off_names': ['L_index_proximal_joint']}
    result, evidence = apply_finger_arrival_v1(base, names, couplings, plan)
    assert evidence['lift_off_start_s'] == pytest.approx(1.5)
    for key, value in polynomial_boundary_v2(result[0], 'start').items():
        assert np.allclose(value, start[key], atol=1e-9)
    for key, value in polynomial_boundary_v2(result[-1], 'end').items():
        assert np.allclose(value, end[key], atol=1e-9)
    split = next(s for s in result if abs(s['end_time_s'] - 1.5) < 1e-10)
    state = polynomial_boundary_v2(split, 'end')
    assert np.allclose([state['position'][1], state['velocity'][1], state['acceleration'][1]], 0, atol=1e-9)
    t = np.linspace(1.0, 1.6, 61)
    def sample(segments, column):
        out = []
        for moment in t:
            s = next(x for x in segments if x['start_time_s'] - 1e-10 <= moment <= x['end_time_s'] + 1e-10)
            u = (moment - s['start_time_s']) / (s['end_time_s'] - s['start_time_s'])
            out.append(np.asarray(s['coefficients'])[column] @ (u ** np.arange(6)))
        return np.array(out)
    assert np.allclose(sample(result, 0), sample(base, 0), atol=1e-12)
    assert np.allclose(sample(result, 1), sample(result, 2), atol=1e-12)
    assert sample(result, 1).min() >= -1e-9


def test_v5_come_to_now_yields_in_limit_candidate_that_verifies(contexts, tmp_path):
    from sign_robot.pair_verification_v2 import verify_saved_pair_v2
    v5 = contexts['v5']
    attempt = next(a for a in iter_deterministic_attempts_v2(v5, 'COME', 'NOW', seed=5412) if a.trajectory)
    assert attempt.trajectory['word_instances'][1]['source_frames'][0] in (2, 3)
    assert attempt.diagnostic['timing']['attempts'][-1]['finger_strategy']['arrival']['staging_frame'] == 0
    path = tmp_path/'come_now.json'
    save_pair_trajectory(path, attempt.trajectory)
    evidence = verify_saved_pair_v2(ROOT, path, v5.policy)
    assert evidence['validation_complete'] and evidence['protected_core_preserved']
    assert not any('JOINT_LIMIT' in code for code in evidence['reason_codes'])
