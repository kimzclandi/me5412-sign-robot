"""Corrected user intervals bind a new input version; preserve v1 history."""
from copy import deepcopy
import json

import pytest

from sign_robot.motion import ROOT
from sign_robot.pair_contract import (atomic_json, file_hash, freeze_library, json_hash,
    load_policy, run_identity, save_pair_trajectory)
from sign_robot.pair_windows import WindowApprovalError, load_window_inputs, select_pair_windows


@pytest.fixture(scope='module')
def corrected():
    policy = load_policy(ROOT/'config/transition_policy_user_protected_v2.json', supported_versions=(1, 2))
    library, _ = freeze_library(ROOT, policy)
    assert not library['input_errors']
    records = load_window_inputs(ROOT, policy, library)
    return policy, library, records


def test_latest_user_words_round_outward_and_keep_actual_motion_binding(corrected):
    policy, library, records = corrected
    bundle = json.loads((ROOT/policy['endpoints']['protection_file']).read_text())
    assert '我要更正一下，COME是0.93～4.40s，NOW是0.13～2.53s' in bundle['source_instruction']
    expected = {'COME': ([.93, 4.40], [27, 132], 201), 'NOW': ([.13, 2.53], [3, 76], 104)}
    for record in bundle['records']:
        interval, core, count = expected[record['gloss']]
        assert record['user_interval_s'] == interval
        assert record['protected_core_frames'] == core
        assert record['frame_count'] == count
        assert file_hash(ROOT/record['motion']) == record['motion_sha256']
        assert records[record['gloss']].protected_core_frames == tuple(core)
        assert record['retiming_allowed'] is False


@pytest.mark.parametrize('source,target', [('COME','NOW'), ('NOW','COME'), ('COME','COME'), ('NOW','NOW')])
def test_corrected_windows_enumerate_new_external_cuts_without_crossing_core(corrected, source, target):
    policy, library, records = corrected
    selection = select_pair_windows(source, target, records, library)
    assert min(selection['source']['allowed_frames']) == records[source].protected_core_frames[1]
    assert max(selection['target']['allowed_frames']) == records[target].protected_core_frames[0]
    assert selection['source']['instance_id'] != selection['target']['instance_id']
    assert selection['word_occurrences'] == 2
    for role in ('source', 'target'):
        assert selection[role]['window_provenance'] == 'algorithm'
        assert selection[role]['window_version'].endswith('-v2')
        assert 'approval_id' not in selection[role]


def test_old_input_remains_loadable_and_new_run_identity_is_distinct(corrected):
    new, new_library, new_records = corrected
    old = load_policy(ROOT/'config/transition_policy_user_protected_v1.json', supported_versions=(1, 2))
    old_library, _ = freeze_library(ROOT, old)
    old_records = load_window_inputs(ROOT, old, old_library)
    assert old_records['COME'].protected_core_frames == (27, 141)
    assert old_records['NOW'].protected_core_frames == (3, 102)
    assert run_identity(new_library, new) != run_identity(old_library, old)
    assert new_records['COME'].protection_id != old_records['COME'].protection_id
    for field in ('constraints','quality','validation','planner','fps','joint_count','finger_strategies','scope','contract'):
        assert new[field] == old[field]
    assert new['formal_acceptance_enabled'] is False


@pytest.mark.parametrize('resign,code', [(False,'USER_PROTECTION_BUNDLE_HASH_MISMATCH'), (True,'INVALID_USER_PROTECTION_VERSION')])
def test_correction_rejects_old_bundle_even_if_its_file_hash_is_updated(corrected, resign, code):
    policy, library, _ = corrected
    policy = deepcopy(policy)
    old_path = ROOT/'config/user_protected_come_now_v1.json'
    policy['endpoints']['protection_file'] = str(old_path.relative_to(ROOT))
    if resign:
        policy['endpoints']['protection_bundle_sha256'] = file_hash(old_path)
    with pytest.raises(WindowApprovalError) as error:
        load_window_inputs(ROOT, policy, library)
    assert error.value.code == code


@pytest.fixture(scope='module')
def corrected_curve(corrected):
    from sign_robot.pair_routes import build_pair_context_v2, iter_deterministic_attempts_v2
    policy, _, _ = corrected
    context = build_pair_context_v2(ROOT, policy)
    stream = iter_deterministic_attempts_v2(context, 'COME', 'COME', seed=5412)
    attempt = next(a for a in stream if a.timing_trajectories)
    return policy, attempt.trajectory or attempt.timing_trajectories[0]


def test_saved_corrected_self_pair_preserves_both_106_frame_instances(corrected_curve, tmp_path):
    from sign_robot.pair_verification_v2 import verify_saved_pair_v2
    policy, curve = corrected_curve
    path = tmp_path/'corrected.json'
    save_pair_trajectory(path, curve)
    evidence = verify_saved_pair_v2(ROOT, path, policy)
    assert evidence['validation_complete'] and evidence['input_checks_passed']
    assert evidence['protected_core_preserved'] and evidence['original_word_slices_preserved']
    assert evidence['word_occurrences'] == 2
    assert all(x['protected_frame_count'] == 106 and x['poses_bitwise_equal'] for x in evidence['protected_instance_checks'])
    assert evidence['approval_checks_passed'] is False
    assert evidence['window_provenance'] == 'algorithm'


@pytest.mark.parametrize('mutation', [
    lambda t: t['word_instances'].pop(),
    lambda t: t['word_instances'][0]['source_frames'].__setitem__(1, 131),
    lambda t: t['word_instances'][0].update(approval_id='forged'),
    lambda t: t['word_instances'][0].update(window_provenance='user_approved'),
    lambda t: t['word_instances'][0].update(protection_sha256='0'*64),
    lambda t: t['segments'][0].update(time_scale=.9),
])
def test_corrected_saved_reader_rejects_deletion_forged_review_stale_binding_or_retiming(corrected_curve, tmp_path, mutation):
    from sign_robot.pair_verification_v2 import verify_saved_pair_v2
    policy, original = corrected_curve
    curve = deepcopy(original)
    mutation(curve)
    path = tmp_path/'invalid.json'
    atomic_json(path, {'schema_version': 2, 'trajectory': curve, 'trajectory_hash': json_hash(curve)})
    evidence = verify_saved_pair_v2(ROOT, path, policy)
    assert evidence['numerical_checks_passed'] is not True
    assert evidence['status'] == 'ERROR'
