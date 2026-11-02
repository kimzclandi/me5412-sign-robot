from copy import deepcopy
import json

import pytest

from sign_robot.motion import ROOT
from sign_robot.pair_contract import file_hash, freeze_library, load_policy, validate_policy_v2, validate_trajectory_v2
from sign_robot.pair_windows import (ApprovedWindow, UserProtectedWindow, WindowApprovalError,
    load_user_protections, load_window_inputs, select_pair_windows)


def policy():
    return load_policy(ROOT / 'config/transition_policy_user_protected_v1.json', supported_versions=(1, 2))


def test_real_protection_inputs_are_independent_of_legacy_human_approval():
    p = policy()
    library, _ = freeze_library(ROOT, p)
    assert not library['input_errors']
    records = load_window_inputs(ROOT, p, library)
    assert set(records) == {'COME', 'NOW'}
    assert all(isinstance(x, UserProtectedWindow) and not isinstance(x, ApprovedWindow) for x in records.values())
    selected = select_pair_windows('COME', 'NOW', records, library)
    assert min(selected['source']['allowed_frames']) == 141
    assert max(selected['target']['allowed_frames']) == 3
    assert selected['source']['window_provenance'] == 'algorithm'
    assert 'approval_id' not in selected['source']
    repeat = select_pair_windows('COME', 'COME', records, library)
    assert repeat['word_occurrences'] == 2
    assert repeat['source']['instance_id'] != repeat['target']['instance_id']


@pytest.mark.parametrize('mutation', [
    lambda p: p['endpoints'].update(review_status='approved'),
    lambda p: p['endpoints'].update(approval_file='fake.json', approval_bundle_sha256='0'*64),
    lambda p: p['endpoints'].update(generator_version='unknown'),
    lambda p: p.update(formal_acceptance_enabled=True),
])
def test_algorithm_policy_cannot_claim_human_approval(mutation):
    p = policy()
    mutation(p)
    with pytest.raises(ValueError):
        validate_policy_v2(p)


@pytest.mark.parametrize('mutation,code', [
    (lambda r: r.update(motion_sha256='0'*64), 'STALE_USER_PROTECTION_MOTION'),
    (lambda r: r.update(protected_core_frames=[28,141]), 'USER_PROTECTION_NOT_CONSERVATIVE'),
    (lambda r: r.update(frame_count=200), 'USER_PROTECTION_FRAME_COUNT_MISMATCH'),
    (lambda r: r.update(retiming_allowed=True), 'INVALID_USER_PROTECTION_SEMANTICS'),
    (lambda r: r.update(approval_id='forged', status='approved'), 'INVALID_USER_PROTECTION_INPUT'),
])
def test_invalid_or_forged_protection_bundle_is_rejected(tmp_path, mutation, code):
    p = policy()
    library, _ = freeze_library(ROOT, p)
    bundle = json.loads((ROOT / p['endpoints']['protection_file']).read_text())
    mutation(bundle['records'][0])
    path = tmp_path/'protection.json'
    path.write_text(json.dumps(bundle))
    # Only the bundle is relocated; real motion reads stay bound to ROOT.
    import sign_robot.pair_windows as windows
    original = windows.inside
    from unittest.mock import patch
    with patch.object(windows, 'inside', lambda root, rel: path if rel == 'test-bundle.json' else original(root, rel)):
        p['endpoints'].update(protection_file='test-bundle.json', protection_bundle_sha256=file_hash(path))
        with pytest.raises(WindowApprovalError) as error:
            load_user_protections(ROOT, p, library)
    assert error.value.code == code


def test_limits_are_identical_to_existing_development_policy():
    old = load_policy(ROOT/'config/transition_policy_v2.json', supported_versions=(1,2))
    new = policy()
    for field in ('constraints','quality','validation','planner','fps','joint_count','finger_strategies','scope'):
        assert old[field] == new[field]


@pytest.mark.parametrize('mutation', [
    lambda t: t['word_instances'][0]['source_frames'].__setitem__(1, 1),
    lambda t: t['word_instances'].pop(),
    lambda t: t['word_instances'][0].update(window_provenance='group2_approved'),
    lambda t: t['word_instances'][0].update(approval_id='fake'),
])
def test_saved_auto_contract_rejects_core_deletion_lost_repeat_or_forged_review(mutation):
    from test_pair_contract_v2 import _trajectory
    t = _trajectory()
    t['endpoint_mode'] = 'user_protected_auto_windows_v1'
    for word in t['word_instances']:
        word['protection_id'] = word.pop('approval_id')
        word['protection_sha256'] = word.pop('approval_sha256')
        word['window_provenance'] = 'algorithm'
    assert validate_trajectory_v2(t)
    mutation(t)
    with pytest.raises(ValueError):
        validate_trajectory_v2(t)
