"""Map source failures to both video rows and check exported protected poses."""
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from sign_robot.pair_contract import atomic_json,read_json,read_motion,read_pair_trajectory

out=ROOT/'results/user_protected_correction_20261031_001'
intrinsic=read_json(out/'R5/protected_source_quality.json')['words']
binding=read_json(out/'R2/correction_binding.json')
records={r['gloss']:r for r in binding['records']}
plan=read_json(out/'R4/planning_analysis.json')
verification=read_json(out/'R5/verification_analysis.json')
pairs={}
for pair in ('COME__NOW','NOW__COME','COME__COME','NOW__NOW'):
    folder=out/'videos'/pair
    report=read_json(folder/'report.json')
    evidence=read_json(folder/'independent_verification.json')
    curve=read_pair_trajectory(folder/'trajectory.json',schema_version=2)
    replay=read_motion(folder/'replay.npz')
    assert evidence['validation_complete'] and evidence['numerical_checks_passed'] is False
    assert report['diagnostic_only'] and report['window_provenance']=='algorithm'
    instances=[]
    events=[]
    original_offset=0
    for word,segment in zip(curve['word_instances'],(curve['segments'][0],curve['segments'][-1])):
        gloss=word['gloss']
        clip=read_motion(ROOT/records[gloss]['motion'])
        c0,c1=word['protected_core_frames']
        assert [c0,c1]==records[gloss]['protected_core_frames']
        mapped=segment['start_time_s']+clip['timestamps_s'][c0:c1+1]-clip['timestamps_s'][word['source_frames'][0]]
        indices=np.rint(mapped*30).astype(int)
        expected=clip['positions'][c0:c1+1]
        actual=replay['positions'][indices]
        exact=np.array_equal(actual,expected)
        error=float(abs(actual-expected).max())
        timing_error=float(abs((replay['timestamps_s'][indices]-replay['timestamps_s'][indices[0]])-
            (clip['timestamps_s'][c0:c1+1]-clip['timestamps_s'][c0])).max())
        assert exact and timing_error<=1e-10
        instances.append({'instance_id':word['instance_id'],'gloss':gloss,'protected_source_frames':[c0,c1],
            'protected_frame_count':c1-c0+1,'poses_bitwise_equal':bool(exact),'max_position_error_rad':error,
            'max_relative_timing_error_s':timing_error,'curve_time_range_s':[float(mapped[0]),float(mapped[-1])]})
        audit=intrinsic[gloss]
        items=[{'metric':'largest original squared-jerk power','source_frame':audit['top_power_frames'][0]['source_frame'],
                'value':audit['top_power_frames'][0]['sum_squared_jerk']}]
        items += [m for m in audit['peak_metrics'] if m['value']>m['limit']]
        for event in items:
            frame=event['source_frame']
            events.append({**event,'instance_id':word['instance_id'],'gloss':gloss,
                'original_time_s':float(clip['timestamps_s'][frame]),
                'comparison_original_row_time_s':float(original_offset+clip['timestamps_s'][frame]),
                'comparison_algorithm_row_time_s':float(segment['start_time_s']+clip['timestamps_s'][frame]-
                    clip['timestamps_s'][word['source_frames'][0]])})
        original_offset+=len(clip['positions'])/30
    assert len({w['instance_id'] for w in instances})==2
    pairs[pair]={'planning_status':plan['pairs'][pair]['planning_status'],
        'eligible_candidates':plan['pairs'][pair]['candidate_count'],
        'independently_verified_candidates':verification['pairs'][pair]['independently_verified_candidates'],
        'diagnostic_curve_full_verification_complete':True,'diagnostic_curve_numerical_checks_passed':False,
        'diagnostic_curve_metrics':evidence['metrics'],'min_clearance_mm':evidence['min_clearance_mm'],
        'reason_codes':evidence['reason_codes'],'protected_instance_checks':instances,
        'word_instances':report['word_instances'],'transition_time_s':report['transition_time_s'],
        'video':str((folder/'comparison.mp4').relative_to(ROOT)),
        'video_frames':report['video_frames'],'video_duration_s':report['video_duration_s'],
        'failure_video_locations':events,'selection':report['selection'],'diagnostic_only':True}
path=out/'R6/run_analysis.json'
assert not path.exists()
atomic_json(path,{'pairs':pairs,'pilot_numerical_pass_count':0,'pilot_denominator':4,
    'protected_instances_bitwise_equal':sum(len(x['protected_instance_checks']) for x in pairs.values()),
    'formal_acceptance_enabled':False,'human_visual_review_supplied':False})
print(json.dumps({p:{'status':x['planning_status'],'candidates':x['eligible_candidates'],
    'full_jerk_integral':x['diagnostic_curve_metrics']['jerk_integral_rad2_s5'],
    'acceleration':x['diagnostic_curve_metrics']['peak_acceleration_rad_s2'],
    'jerk':x['diagnostic_curve_metrics']['peak_jerk_rad_s3'],'min_clearance_mm':x['min_clearance_mm'],
    'video':x['video']} for p,x in pairs.items()},indent=2))
