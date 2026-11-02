import numpy as np
import pytest

from sign_robot.motion import ROOT
from sign_robot.pair_contract import load_policy
from sign_robot.pair_routes import PairWorkBudget, build_pair_context_v2, valid_endpoint_choices_v2


@pytest.fixture(scope='module')
def actual():
    policy = load_policy(ROOT/'config/transition_policy_user_protected_v1.json', supported_versions=(1,2))
    context = build_pair_context_v2(ROOT,policy)
    assert not context.input_blockers
    return context


@pytest.mark.parametrize('source,target',[('COME','NOW'),('NOW','COME'),('COME','COME'),('NOW','NOW')])
def test_real_cut_screen_cannot_cross_protection_and_records_boundary_state(actual, source, target):
    selection = valid_endpoint_choices_v2(actual,source,target,PairWorkBudget(actual.policy))
    for role in ('source','target'):
        item = selection[role]
        assert item['window_provenance'] == 'algorithm'
        assert len(item['endpoint_checks']) == len(item['allowed_frames'])
        core = item['protected_core_frames']
        for check in item['endpoint_checks']:
            assert check['frame'] >= core[1] if role == 'source' else check['frame'] <= core[0]
            assert all(k in check for k in ('min_clearance_mm','joint_limit_error','coupling_error','worst_contact'))
            if not check['boundary_limit_viable']:
                assert not check['engineering_valid'] and check['outward_limit_joints']
            assert set(check['boundary_state']) == {'position','velocity','acceleration'}
            assert all(len(v)==53 and np.isfinite(v).all() for v in check['boundary_state'].values())
        assert item['retained_outer_frame'] == core[0 if role=='source' else 1]
    if source == target:
        assert selection['source']['instance_id'] != selection['target']['instance_id']
