from copy import deepcopy
from pathlib import Path

import pytest

from sign_robot.motion import ROOT
from sign_robot.pair_contract import (atomic_json,file_hash,json_hash,load_policy,save_pair_trajectory)
from sign_robot.pair_routes import build_pair_context_v2,iter_deterministic_attempts_v2
from sign_robot.pair_verification_v2 import verify_saved_pair_v2


@pytest.fixture(scope='module')
def actual():
    p=load_policy(ROOT/'config/transition_policy_user_protected_v1.json',supported_versions=(1,2))
    context=build_pair_context_v2(ROOT,p)
    stream=iter_deterministic_attempts_v2(context,'COME','COME',seed=5412)
    attempt=next(a for a in stream if a.timing_trajectories)
    return p,attempt.trajectory or attempt.timing_trajectories[0]


def save(tmp_path,t):
    path=tmp_path/'saved.json'
    save_pair_trajectory(path,t)
    return path


def test_real_saved_auto_self_pair_is_independently_reconstructed(actual,tmp_path):
    p,t=actual
    e=verify_saved_pair_v2(ROOT,save(tmp_path,t),p)
    assert e['artifact_contract_passed'] and e['input_checks_passed']
    assert e['approval_checks_passed'] is False and e['window_provenance']=='algorithm'
    assert e['validation_complete'] and e['word_occurrences']==2
    assert e['protected_core_preserved'] and e['original_word_slices_preserved']
    assert len(e['protected_instance_checks'])==2
    assert all(x['protected_frame_count']==115 and x['poses_bitwise_equal'] for x in e['protected_instance_checks'])
    assert len({x['instance_id'] for x in e['protected_instance_checks']})==2
    assert e['status']!='PASS_SIM' and e['playback_eligible'] is False
    assert len(e['dense_recheck_result'])>=9


def test_changed_protection_reference_is_rejected_even_with_resigned_curve(actual,tmp_path):
    p,t=actual
    t=deepcopy(t)
    t['word_instances'][0]['protection_sha256']='0'*64
    e=verify_saved_pair_v2(ROOT,save(tmp_path,t),p)
    assert e['numerical_checks_passed'] is not True
    assert e['status']=='ERROR'


@pytest.mark.parametrize('mutation',[
    lambda t:t['word_instances'].pop(),
    lambda t:t['word_instances'][0]['source_frames'].__setitem__(1,140),
    lambda t:t['word_instances'][0].update(approval_id='fake-review'),
    lambda t:t['word_instances'][0].update(window_provenance='user_approved'),
    lambda t:t['segments'][0].update(time_scale=.9),
])
def test_independent_reader_rejects_lost_repeat_deleted_core_forged_approval_and_retiming(actual,tmp_path,mutation):
    p,t=actual
    t=deepcopy(t)
    mutation(t)
    path=tmp_path/'forged.json'
    atomic_json(path,{'schema_version':2,'trajectory':t,'trajectory_hash':json_hash(t)})
    e=verify_saved_pair_v2(ROOT,path,p)
    assert not e['artifact_contract_passed'] and e['numerical_checks_passed'] is not True


def test_new_runner_rejects_human_approval_claim_in_auto_evidence(actual,tmp_path):
    from sign_robot.pair_runner_v2 import V2RunStore,RunIntegrityError
    p,t=actual
    path=save(tmp_path,t)
    store=V2RunStore(ROOT,tmp_path,p,{'identity':t['identity']})
    e={'schema_version':2,'pair_id':t['pair_id'],'status':'FAILED_QUALITY','reason_codes':[],
       'playback_eligible':False,'numerical_checks_passed':True,'validation_complete':True,
       'artifact_contract_passed':True,'input_checks_passed':True,'approval_checks_passed':False,
       'window_provenance':'algorithm','protected_core_preserved':True,'original_word_slices_preserved':True,
       'word_occurrences':2,'identity':t['identity'],
       'metrics':{'peak_jerk_rad_s3':100.,'peak_acceleration_rad_s2':10.,'analytic_connector_jerk_integral_rad2_s5':50.}}
    store._validate_evidence(e,t['pair_id'])
    e['approval_checks_passed']=True
    with pytest.raises(RunIntegrityError,match='cannot claim human'):
        store._validate_evidence(e,t['pair_id'])


def test_independent_selection_prefers_smoother_verified_candidate_before_shorter_duration(actual,tmp_path):
    from sign_robot.pair_runner_v2 import V2RunStore
    p,t=actual
    store=V2RunStore(ROOT,tmp_path,p,{})
    attempts=[]
    reviews=[]
    # Evidence values stand in for completed independent measurements in this ranking-only test.
    for i,(duration,jerk) in enumerate(((.3,200.),(.6,100.))):
        from test_pair_contract_v2 import _trajectory
        curve=_trajectory()
        curve['segments'][1]['end_time_s']=.1+duration
        curve['segments'][2]['start_time_s']=.1+duration
        curve['segments'][2]['end_time_s']=.2+duration
        name=f'candidate-{i}.json'
        save_pair_trajectory(tmp_path/name,curve)
        review=f'review-{i}.json'
        atomic_json(tmp_path/review,{'evidence':{'metrics':{'peak_jerk_rad_s3':jerk,
            'peak_acceleration_rad_s2':10.,'analytic_connector_jerk_integral_rad2_s5':5.}}})
        attempts.append({'attempt_id':str(i),'candidate_file':name})
        reviews.append({'attempt_id':str(i),'numerical_checks_passed':True,'path':review})
    assert store._selection_winner(reviews,attempts)=='1'
