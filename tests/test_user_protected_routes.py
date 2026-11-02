import itertools

import numpy as np
import pytest

from sign_robot.motion import ROOT
from sign_robot.pair_contract import load_policy, polynomial_boundary_v2, validate_trajectory_v2
from sign_robot.pair_routes import (PairWorkBudget, build_pair_context_v2, endpoint_pairs_v1,
    iter_deterministic_attempts_v2, valid_endpoint_choices_v2)


@pytest.fixture(scope='module')
def actual():
    p = load_policy(ROOT/'config/transition_policy_user_protected_v1.json',supported_versions=(1,2))
    context = build_pair_context_v2(ROOT,p)
    assert not context.input_blockers
    return context


@pytest.mark.parametrize('source,target',[('COME','NOW'),('NOW','COME'),('COME','COME'),('NOW','NOW')])
def test_real_direct_saved_curve_matches_boundary_even_when_limits_reject_it(actual,source,target):
    stream = iter_deterministic_attempts_v2(actual,source,target,seed=5412)
    screen = next(stream)
    assert screen.diagnostic['event'] == 'algorithm_window_screen'
    attempt = next((a for a in itertools.islice(stream,24) if a.timing_trajectories),None)
    assert attempt is not None
    trajectory = attempt.trajectory or attempt.timing_trajectories[0]
    assert validate_trajectory_v2(trajectory)
    assert trajectory['planner']['method'] == 'direct'
    if attempt.trajectory is None:
        assert attempt.diagnostic['reason_codes']
        assert attempt.diagnostic['candidate_available'] is False
    assert len(trajectory['word_instances'])==2
    assert len({w['instance_id'] for w in trajectory['word_instances']})==2
    for index,word in enumerate(trajectory['word_instances']):
        core=word['protected_core_frames']
        assert word['source_frames'][0]<=core[0]<=core[1]<=word['source_frames'][1]
        assert 'approval_id' not in word and word['window_provenance']=='algorithm'
        endpoint='start' if index==0 else 'end'
        polynomial=trajectory['segments'][1 if index==0 else -2]
        for key,value in polynomial_boundary_v2(polynomial,endpoint).items():
            assert np.allclose(value,trajectory['boundary'][endpoint][key],atol=1e-7,rtol=0)


def test_real_shortlist_is_finite_and_still_obeys_protection(actual):
    selection=valid_endpoint_choices_v2(actual,'COME','COME',PairWorkBudget(actual.policy))
    pairs=endpoint_pairs_v1(actual,selection)
    assert len(pairs)==8
    assert all(a>=141 and b<=27 for a,b in pairs)
