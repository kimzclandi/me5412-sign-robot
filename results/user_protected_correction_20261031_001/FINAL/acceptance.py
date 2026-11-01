"""Read-only final acceptance of corrected inputs, saved run and media."""
import argparse
import json
from pathlib import Path
import re
import sys
import numpy as np


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[3])
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    root=args.root.resolve()
    sys.path.insert(0,str(root/'src'))
    from sign_robot.pair_contract import (file_hash,freeze_library,json_hash,load_policy,read_json,
        read_motion,read_pair_trajectory,run_identity)
    from sign_robot.pair_runner_v2 import V2RunStore
    out=root/'results/user_protected_correction_20261031_001'
    checks=[]
    def check(name,passed,details=None):
        checks.append({'check':name,'passed':bool(passed),'details':details})
    baseline=read_json(out/'R1/baseline_inventory.json')
    preservation=read_json(out/'R1/preservation.json')
    check('current_installed_baseline_fully_preserved',preservation['entries']==8726
        and preservation['source_unchanged'] and preservation['restore_matches'])
    frozen=read_json(out/'R2/engineering_freeze.json')
    policy=load_policy(root/frozen['policy_file'],supported_versions=(1,2))
    old=load_policy(root/'config/transition_policy_user_protected_v1.json',supported_versions=(1,2))
    development=load_policy(root/'config/transition_policy_v2.json',supported_versions=(1,2))
    check('engineering_policy_file_hash_frozen_before_pilot',file_hash(root/frozen['policy_file'])==frozen['policy_file_sha256'])
    check('all_engineering_thresholds_and_budgets_unchanged',all(policy[k]==old[k]==development[k] for k in frozen['unchanged_fields']))
    check('contract_semantics_unchanged',policy['contract']==old['contract'])
    check('formal_acceptance_remains_disabled',policy['formal_acceptance_enabled'] is False
        and policy['endpoints']['review_status']=='pending')
    check('algorithm_windows_do_not_claim_human_approval',policy['endpoints']['approval_file'] is None
        and policy['endpoints']['approval_bundle_sha256'] is None)
    binding=read_json(out/'R2/correction_binding.json')
    bundle=read_json(root/policy['endpoints']['protection_file'])
    check('exact_user_correction_recorded',binding['user_correction_verbatim']=='我要更正一下，COME是0.93～4.40s，NOW是0.13～2.53s'
        and binding['user_correction_verbatim'] in bundle['source_instruction'])
    check('new_policy_and_protection_version_distinct',binding['new_policy_sha256']!=binding['previous_policy_sha256']
        and binding['new_bundle_sha256']!=binding['previous_bundle_sha256']
        and policy['endpoints']['window_version']==bundle['window_version']=='come-now-user-protection-20261031-v2')
    expected={'COME':([.93,4.40],[27,132],106),'NOW':([.13,2.53],[3,76],74)}
    records={r['gloss']:r for r in bundle['records']}
    check('corrected_inclusive_outward_protection',set(records)==set(expected) and all(
        r['user_interval_s']==expected[g][0] and r['protected_core_frames']==expected[g][1]
        and r['retiming_allowed'] is False and file_hash(root/r['motion'])==r['motion_sha256'] for g,r in records.items()))
    legacy_files=('config/user_protected_come_now_v1.json','config/transition_policy_user_protected_v1.json',
        'contracts/all_pairs_user_protected_v1.json','PLAN.md')
    check('legacy_config_contract_and_plan_preserved',all(file_hash(root/p)==baseline[p]['sha256'] for p in legacy_files))
    run=out/'runs/user_protected_corrected_pilot_20261031_001'
    store=V2RunStore.load(root,run)
    library,_=freeze_library(root,policy)
    check('fresh_installed_code_model_input_environment_identity',run_identity(library,policy)==store.manifest['identity'])
    summary=read_json(run/'summary.json')
    check('fixed_full_library_denominators',[summary['groups'][k]['denominator'] for k in ('all','non_self','self')]==[1225,1190,35])
    pairs={'COME__NOW','NOW__COME','COME__COME','NOW__NOW'}
    check('exact_four_real_pairs_executed',set(store.manifest['heads'])==pairs)
    heads={p:store._head_record(p) for p in pairs}
    check('all_six_families_attempted_per_pair',all(set(r['method_coverage'])==set(policy['planner']['methods'])
        and all(v['attempted'] for v in r['method_coverage'].values()) for r in heads.values()))
    expected_candidates={'COME__NOW':0,'NOW__COME':20,'COME__COME':64,'NOW__NOW':0}
    check('actual_candidate_inventory',{p:r['candidate_count'] for p,r in heads.items()}==expected_candidates)
    check('all_eligible_candidates_independently_reviewed',all(len(r['verifications'])==r['candidate_count'] for r in heads.values()))
    proofs=[read_json(run/v['path'])['evidence'] for r in heads.values() for v in r['verifications']]
    check('all_84_candidate_verifications_complete',len(proofs)==84 and all(e['validation_complete'] for e in proofs))
    check('candidate_inputs_protection_and_two_instances_preserved',all(e['input_checks_passed']
        and e['artifact_contract_passed'] and e['protected_core_preserved'] and e['original_word_slices_preserved']
        and e['word_occurrences']==2 and len(e['protected_instance_checks'])==2
        and all(w['protected_frame_count']==expected[w['gloss']][2] and w['poses_bitwise_equal']
            and w['max_relative_timing_error_s']<=1e-10 for w in e['protected_instance_checks']) for e in proofs))
    check('algorithm_evidence_never_fabricates_approval',all(e['window_provenance']=='algorithm'
        and e['approval_checks_passed'] is False for e in proofs))
    check('candidate_dense_geometry_checks_pass',all(e['min_clearance_mm']>=1000*policy['constraints']['min_clearance_m'] for e in proofs),
        {'minimum_mm':min(e['min_clearance_mm'] for e in proofs)})
    check('failed_numerical_results_reported_honestly',all(e['numerical_checks_passed'] is False for e in proofs)
        and summary['executed_development_scope']['numerical_pass_count']==0
        and all(r['selected_candidate_id'] is None for r in heads.values())
        and summary['groups']['all']['status_counts']['PASS_SIM']==0)
    check('full_library_not_misrepresented_as_complete',summary['groups']['all']['status_counts']['NOT_RUN']==1221
        and summary['groups']['all']['status_counts']['FAILED_QUALITY']==2
        and summary['groups']['all']['status_counts']['TIMEOUT']==2 and summary['L2_complete'] is False)
    check('zero_candidate_pairs_have_only_diagnosis',all(
        r['verification_state']=='DIAGNOSIS_ONLY' and read_json(run/r['diagnosis_file'])['evidence']['validation_complete'] is False
        for p,r in heads.items() if expected_candidates[p]==0))
    intrinsic=read_json(out/'R5/protected_source_quality.json')
    check('source_quality_recomputed_for_corrected_ranges',all(w['protected_core_frames']==expected[g][1]
        and w['exceeds_frozen_limit'] for g,w in intrinsic['words'].items()),
        {g:w['squared_jerk_integral_rad2_s5'] for g,w in intrinsic['words'].items()})
    lower=read_json(out/'R5/protected_source_lower_bound.json')
    check('four_pair_protected_interior_lower_bounds_exceed_limit',all(
        p['full_motion_lower_bound_rad2_s5']>p['frozen_full_motion_limit_rad2_s5'] for p in lower['pairs'].values()))
    check('saved_curve_version_isolation_negative_checks',read_json(out/'R5/version_isolation.json')['passed'])
    resume=read_json(out/'R5/completed_resume.json')
    actual_run={str(p.relative_to(run)):file_hash(p) for p in run.rglob('*') if p.is_file()}
    check('completed_resume_preserves_all_run_bytes',resume['passed'] and resume['before']==resume['after']==actual_run,
        {'file_count':len(actual_run)})
    import imageio.v2 as imageio
    video_summary=read_json(out/'videos/summary.json')
    check('four_comparison_videos_exported',len(video_summary['pairs'])==4)
    for pair in sorted(pairs):
        folder=out/'videos'/pair
        report=read_json(folder/'report.json')
        curve=read_pair_trajectory(folder/'trajectory.json',schema_version=2)
        replay=read_motion(folder/'replay.npz')
        check(pair+':failure_algorithm_labels',report['diagnostic_only'] is True
            and report['numerical_checks_passed'] is False and report['window_provenance']=='algorithm'
            and report['playback_eligible'] is False)
        check(pair+':export_hashes_match',all(file_hash(folder/name)==value for name,value in report['files'].items()))
        original_curve=run/report['source_curve']
        check(pair+':video_matches_saved_run_curve',file_hash(original_curve)==report['source_curve_sha256']
            and read_pair_trajectory(original_curve,schema_version=2)==curve)
        reader=imageio.get_reader(folder/'comparison.mp4')
        count=reader.count_frames()
        metadata=reader.get_meta_data()
        reader.close()
        check(pair+':video_decodes_at_30hz',count==report['video_frames'] and metadata['fps']==30,
            {'decoded_frames':count,'expected_frames':report['video_frames']})
        instance_results=[]
        valid=True
        for word,segment in zip(curve['word_instances'],(curve['segments'][0],curve['segments'][-1])):
            original=read_motion(root/records[word['gloss']]['motion'])
            c0,c1=word['protected_core_frames']
            valid &= [c0,c1]==expected[word['gloss']][1]
            mapped=segment['start_time_s']+original['timestamps_s'][c0:c1+1]-original['timestamps_s'][word['source_frames'][0]]
            indices=np.rint(mapped*30).astype(int)
            equal=np.array_equal(replay['positions'][indices],original['positions'][c0:c1+1])
            relative_error=float(abs((replay['timestamps_s'][indices]-replay['timestamps_s'][indices[0]])-
                (original['timestamps_s'][c0:c1+1]-original['timestamps_s'][c0])).max())
            valid &= equal and relative_error<=1e-10
            instance_results.append({'instance_id':word['instance_id'],'protected_frames':c1-c0+1,
                'poses_bitwise_equal':bool(equal),'relative_time_error_s':relative_error})
        check(pair+':protected_poses_and_timing_exported',valid,instance_results)
        check(pair+':two_distinct_word_instances',len(curve['word_instances'])==2 and len({w['instance_id'] for w in curve['word_instances']})==2)
        evidence=read_json(folder/'independent_verification.json')
        check(pair+':displayed_curve_fully_independently_verified',evidence['validation_complete']
            and evidence['numerical_checks_passed'] is False
            and evidence['trajectory_file_sha256']==report['source_curve_sha256'])
    media=read_json(out/'R6/media_checks.json')
    check('image_tool_checks_never_called_human_approval',media['passed'] and media['human_approval_supplied'] is False)
    test_command=read_json(out/'R7/full_tests.command.json')
    test_log=(out/'R7/full_tests.log').read_text()
    test_count=re.search(r'(\d+) passed in ([\d.]+)s',test_log)
    check('full_regression_passed',test_command['exit_code']==0 and test_count is not None,
        {'test_count':int(test_count[1]) if test_count else None,'exit_code':test_command['exit_code']})
    assets=[]
    history=[]
    mismatch=[]
    for relative,entry in baseline.items():
        if entry['kind']!='file':
            continue
        if relative.startswith(('assets/','motions/','models/')):
            assets.append(relative)
            if not (root/relative).is_file() or file_hash(root/relative)!=entry['sha256']:
                mismatch.append(relative)
        if relative.startswith('results/') and not relative.startswith('results/session_logs/'):
            if not (root/relative).is_file() or file_hash(root/relative)!=entry['sha256']:
                history.append(relative)
    check('all_original_motion_and_model_files_preserved',not mismatch,{'count':len(assets),'mismatches':mismatch})
    check('all_historical_results_preserved',not history,history)
    check('bilingual_report_state_handoff_and_index',all((root/p).is_file() for p in (
        'TASK-22.md','TASK-22.en.md','STATE.md','STATE.en.md','HANDOFF.md','HANDOFF.en.md','docs/README.md','docs/README.en.md'))
        and all('TASK-22' in (root/p).read_text() for p in ('docs/README.md','docs/README.en.md')))
    before=(out/'R2/before/src/sign_robot/project_overview.py').read_text()
    for rel in ('docs/README.md','docs/README.en.md'):
        before=before.replace(baseline[rel]['sha256'],file_hash(root/rel))
    check('only_two_required_download_sha_literals_changed',before==(root/'src/sign_robot/project_overview.py').read_text())
    result={'engineering_delivery_checks_passed':all(c['passed'] for c in checks),'checks':checks,
        'pilot_numerical_pass_count':0,'pilot_denominator':4,'formal_pass_sim_count':0,
        'full_library_denominator':1225,'full_library_acceptance_complete':False,'goal_complete':False,
        'identity':store.manifest['identity'],'blocking_cause':'corrected protected-source quality exceeds unchanged engineering limits'}
    assert not args.output.exists(),args.output
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'passed':result['engineering_delivery_checks_passed'],'checks':len(checks),
        'failed_checks':[c for c in checks if not c['passed']],'goal_complete':False},ensure_ascii=False))
    return 0 if result['engineering_delivery_checks_passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
