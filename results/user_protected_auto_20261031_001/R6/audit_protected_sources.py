"""Independent intrinsic-quality attribution using original protected samples."""
from pathlib import Path
import sys
import json
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from sign_robot.pair_contract import atomic_json,file_hash,load_policy,read_motion


def main():
    policy=load_policy(ROOT/'config/transition_policy_user_protected_v1.json',supported_versions=(1,2))
    bundle=json.loads((ROOT/policy['endpoints']['protection_file']).read_text())
    result={}
    for record in bundle['records']:
        path=ROOT/record['motion']
        assert file_hash(path)==record['motion_sha256']
        motion=read_motion(path)
        q,t,names=motion['positions'],motion['timestamps_s'],motion['joint_names']
        acceleration=np.gradient(np.gradient(q,t,axis=0,edge_order=2),t,axis=0,edge_order=2)
        jerk=np.gradient(acceleration,t,axis=0,edge_order=2)
        c0,c1=record['protected_core_frames']
        indices=np.arange(c0+3,c1-2)
        power=np.sum(jerk[indices]**2,axis=1)
        by_joint=np.trapezoid(jerk[indices]**2,x=t[indices],axis=0)
        integral=float(np.trapezoid(power,x=t[indices]))
        peaks=[]
        for metric,values,cap in [('peak_acceleration_rad_s2',acceleration,policy['quality']['limits']['peak_acceleration_rad_s2']),
                                 ('peak_jerk_rad_s3',jerk,policy['quality']['limits']['peak_jerk_rad_s3'])]:
            row,col=np.unravel_index(int(np.argmax(np.abs(values[indices]))),values[indices].shape)
            f=int(indices[row])
            peaks.append({'metric':metric,'value':float(abs(values[f,col])),'limit':cap,
                'source_frame':f,'original_time_s':float(t[f]),'joint':str(names[col])})
        result[record['gloss']]={'motion':record['motion'],'motion_sha256':file_hash(path),
            'protected_core_frames':[c0,c1],'evaluated_interior_frames':[int(indices[0]),int(indices[-1])],
            'squared_jerk_integral_rad2_s5':integral,'limit':policy['quality']['limits']['jerk_integral_rad2_s5'],
            'exceeds_frozen_limit':integral>policy['quality']['limits']['jerk_integral_rad2_s5'],
            'same_result_required_in_any_unretimed_preserved_instance':True,
            'stencil':'nested gradient edge_order=2; use only >=3 original frames from each protected boundary',
            'integral_basis':'nonnegative interior contribution, excluding all outer slices and added connectors',
            'peak_metrics':peaks,'top_joint_integral_contributions':[{'joint':str(names[j]),'value':float(by_joint[j])} for j in np.argsort(by_joint)[-5:][::-1]],
            'top_power_frames':[{'source_frame':int(indices[i]),'original_time_s':float(t[indices[i]]),'sum_squared_jerk':float(power[i])} for i in np.argsort(power)[-5:][::-1]]}
    output=Path(__file__).with_name('protected_source_quality.json')
    if output.exists():
        raise ValueError('Evidence already exists; do not overwrite')
    atomic_json(output,{'policy_file_sha256':file_hash(ROOT/'config/transition_policy_user_protected_v1.json'),
        'script_sha256':file_hash(__file__),'words':result,'all_four_pairs_fail_unchanged_integral_limit':all(x['exceeds_frozen_limit'] for x in result.values())})
    print(json.dumps(result,indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
