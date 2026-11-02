"""Final read-only acceptance of installed code, preserved inputs and four videos."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[3])
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    root=args.root.resolve()
    sys.path.insert(0,str(root/'src'))
    from sign_robot.pair_contract import file_hash,freeze_library,load_policy,read_json,read_motion,read_pair_trajectory,run_identity
    from sign_robot.pair_runner_v2 import V2RunStore
    checks=[]
    def check(name,passed,details=None):
        checks.append({'check':name,'passed':bool(passed),'details':details})
    out=root/'results/user_protected_auto_20261031_001'
    policy=load_policy(root/'config/transition_policy_user_protected_v1.json',supported_versions=(1,2))
    old=load_policy(root/'config/transition_policy_v2.json',supported_versions=(1,2))
    frozen=read_json(out/'R2/engineering_freeze.json')
    check('engineering_policy_hash_unchanged',file_hash(root/frozen['policy_file'])==frozen['policy_file_sha256'])
    check('existing_numerical_limits_unchanged',all(policy[k]==old[k] for k in frozen['unchanged_fields']))
    check('formal_acceptance_disabled',policy['formal_acceptance_enabled'] is False and policy['endpoints']['review_status']=='pending')
    check('algorithm_not_human_approval',policy['endpoints']['approval_file'] is None and policy['endpoints']['approval_bundle_sha256'] is None)
    run=out/'runs/user_protected_pilot_20261031_001'
    store=V2RunStore.load(root,run)
    library,_=freeze_library(root,policy)
    check('fresh_code_model_input_environment_identity',run_identity(library,policy)==store.manifest['identity'])
    summary=read_json(run/'summary.json')
    check('full_library_denominators_preserved',[summary['groups'][k]['denominator'] for k in ('all','non_self','self')]==[1225,1190,35])
    expected={'COME__NOW','NOW__COME','COME__COME','NOW__NOW'}
    check('exact_four_real_pairs_executed',set(store.manifest['heads'])==expected)
    check('all_eligible_candidates_independently_reviewed',all(
        len(store._head_record(p)['verifications'])==store._head_record(p)['candidate_count'] for p in expected))
    check('no_false_pass_or_selected_candidate',summary['executed_development_scope']['numerical_pass_count']==0
          and summary['groups']['all']['status_counts']['PASS_SIM']==0)
    check('remaining_library_not_run',summary['groups']['all']['status_counts']['NOT_RUN']==1221)
    intrinsic=read_json(out/'R6/protected_source_quality.json')
    check('protected_source_failure_proven_without_connectors',all(w['exceeds_frozen_limit'] for w in intrinsic['words'].values()),intrinsic['words'])
    videos=out/'videos_complete'
    video_reports=read_json(videos/'summary.json')
    check('four_comparison_videos',len(video_reports['pairs'])==4)
    import imageio.v2 as imageio
    for pair in sorted(expected):
        folder=videos/pair
        report=read_json(folder/'report.json')
        curve=read_pair_trajectory(folder/'trajectory.json',schema_version=2)
        replay=read_motion(folder/'replay.npz')
        check(pair+':diagnostic_label',report['diagnostic_only'] is True and report['numerical_checks_passed'] is False and report['window_provenance']=='algorithm')
        check(pair+':all_media_hashes',all(file_hash(folder/f)==h for f,h in report['files'].items()))
        reader=imageio.get_reader(folder/'comparison.mp4')
        count=reader.count_frames()
        reader.close()
        check(pair+':video_decode_frame_count',count==report['video_frames'],{'decoded':count,'expected':report['video_frames']})
        valid=True
        exact=True
        timing=True
        instance_results=[]
        for word,segment in zip(curve['word_instances'],(curve['segments'][0],curve['segments'][-1])):
            original=read_motion(root/next(w['motion'] for w in library['words'] if w['gloss']==word['gloss']))
            c0,c1=word['protected_core_frames']
            mapped=segment['start_time_s']+original['timestamps_s'][c0:c1+1]-original['timestamps_s'][word['source_frames'][0]]
            indices=np.rint(mapped*30).astype(int)
            poses=replay['positions'][indices]
            expected_poses=original['positions'][c0:c1+1]
            error=float(abs(poses-expected_poses).max())
            valid &= error<=1e-12
            equal=np.array_equal(poses,expected_poses)
            exact &= equal
            timing &= np.allclose(replay['timestamps_s'][indices]-replay['timestamps_s'][indices[0]],
                                  original['timestamps_s'][c0:c1+1]-original['timestamps_s'][c0],atol=1e-10,rtol=0)
            instance_results.append({'instance_id':word['instance_id'],'protected_frames':c1-c0+1,'max_position_error':error,'bitwise_equal':bool(equal)})
        check(pair+':protected_poses_and_timing_in_export',valid and timing,instance_results)
        check(pair+':two_distinct_instances',len(curve['word_instances'])==2 and len({w['instance_id'] for w in curve['word_instances']})==2)
        evidence=read_json(folder/'independent_verification.json')
        check(pair+':complete_failed_saved_curve_verification',evidence.get('validation_complete') is True and evidence.get('numerical_checks_passed') is False)
    baseline=read_json(out/'R1/baseline_inventory.json')
    mismatches=[]
    assets=[]
    for relative,entry in baseline.items():
        if entry['kind']=='file' and relative.startswith(('assets/','motions/')):
            assets.append(relative)
            if not (root/relative).is_file() or file_hash(root/relative)!=entry['sha256']:
                mismatches.append(relative)
    check('all_baseline_motion_and_model_files_unchanged',not mismatches,{'count':len(assets),'mismatches':mismatches})
    history=[]
    for relative,entry in baseline.items():
        if entry['kind']=='file' and relative.startswith('results/'):
            # Existing service tests may append their own logs only in the test workspace.
            if relative.startswith('results/session_logs/'):
                continue
            if not (root/relative).is_file() or file_hash(root/relative)!=entry['sha256']:
                history.append(relative)
    check('all_baseline_historical_results_unchanged',not history,history)
    check('all_atomic_reports_bilingual',all((root/f'TASK-{n:02d}{lang}.md').is_file() for n in range(15,22) for lang in ('','.en')))
    check('project_state_bilingual',all((root/f'STATE{lang}.md').is_file() for lang in ('','.en')))
    result={'engineering_delivery_checks_passed':all(c['passed'] for c in checks),'checks':checks,
            'pilot_numerical_pass_count':0,'pilot_denominator':4,'formal_pass_sim_count':0,'full_library_denominator':1225,
            'full_library_acceptance_complete':False,'goal_complete':False,'identity':store.manifest['identity'],
            'blocking_cause':'unchanged protected-source quality exceeds unchanged engineering limits'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'passed':result['engineering_delivery_checks_passed'],'checks':len(checks),
        'failures':[c for c in checks if not c['passed']],'goal_complete':False},ensure_ascii=False))
    return 0 if result['engineering_delivery_checks_passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
