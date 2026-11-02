from pathlib import Path
import json
import math
import numpy as np
from execution_support import SOURCE, STAGE, EVIDENCE_REL, json_write, sha
from sign_robot.pair_contract import read_motion, boundary_derivatives, load_policy
from sign_robot.pair_verification import trajectory_metrics

policy = load_policy(SOURCE/'config/transition_policy.json')
library = json.loads((SOURCE/'library_manifest.json').read_text())
words = {w['gloss']:w for w in library['words']}
clips = {g:read_motion(SOURCE/w['motion']) for g,w in words.items()}
run = SOURCE/'results/all_pairs/all_pairs_dev_20261031_v2'
rows=[]
for path in sorted((run/'checkpoints').glob('*.json')):
    record=json.loads(path.read_text())['record']
    if not record.get('trajectory_file'): continue
    trajectory=run/record['trajectory_file']
    assert sha(trajectory)==record['trajectory_file_hash']
    motion=read_motion(trajectory)
    first,second=clips[record['source_gloss']],clips[record['target_gloss']]
    connector=motion['positions'][record['transition_start_frame']:record['transition_end_frame']+1]
    metrics=trajectory_metrics(motion,connector,first,second,record['exit_frame'],record['entry_frame'],policy)
    for key in ['peak_arm_speed','peak_finger_speed','peak_acceleration','peak_jerk',
                'velocity_jump','acceleration_jump','jerk_integral']:
        assert np.isclose(metrics[key],record[key],atol=1e-7,rtol=1e-10),(record['pair_id'],key)
    rows.append({'pair_id':record['pair_id'],'trajectory_sha256':record['trajectory_file_hash'],
                 'transition_duration_s':record['transition_duration_s'],
                 'metrics':{k:v for k,v in metrics.items() if isinstance(v,(int,float))}})
assert len(rows)==899
statistics={}
for key in rows[0]['metrics']:
    values=np.asarray([r['metrics'][key] for r in rows])
    assert np.isfinite(values).all()
    statistics[key]={'n':len(values),**{f'p{p}':float(np.percentile(values,p)) for p in (50,95,99)},'max':float(values.max())}
durations=np.asarray([r['transition_duration_s'] for r in rows])
statistics['transition_duration_s']={'n':len(durations),**{f'p{p}':float(np.percentile(durations,p)) for p in (50,95,99)},'max':float(durations.max())}
historical=json.loads((SOURCE/'results/group3_all_pairs_startup/quality_development_metrics.json').read_text())
for name,summary in historical['metrics'].items():
    for key in ('p50','p95','p99','max'):
        assert np.isclose(statistics[name][key],summary[key],atol=1e-7,rtol=1e-10),(name,key)

analytic=[]
for side in ('source','target'):
    t=np.arange(-4,1)/30 if side=='source' else np.arange(5)/30
    q=(2+3*t+4*t*t)[:,None]
    clip={'timestamps_s':t,'positions':q,'joint_names':np.array(['right_elbow_joint'])}
    fitted=boundary_derivatives(clip,4 if side=='source' else 0,side,5)
    assert np.allclose(fitted['velocity'],[3],atol=1e-10)
    assert np.allclose(fitted['acceleration'],[8],atol=1e-9)
    analytic.append({'case':f'quadratic_{side}','expected_velocity_rad_s':3,'expected_acceleration_rad_s2':8,
                     'actual_velocity':fitted['velocity'],'actual_acceleration':fitted['acceleration']})
u=np.arange(31)/30
connector=(10*u**3-15*u**4+6*u**5)[:,None]
names=np.array(['right_elbow_joint'])
first={'positions':np.zeros((5,1)),'timestamps_s':np.arange(5)/30,'joint_names':names}
second={'positions':np.ones((5,1)),'timestamps_s':np.arange(5)/30,'joint_names':names}
full=np.vstack([first['positions'],connector[1:-1],second['positions']])
motion={'positions':full,'timestamps_s':np.arange(len(full))/30,'joint_names':names}
measured=trajectory_metrics(motion,connector,first,second,4,0,policy)
expected={'analytic_connector_peak_speed_rad_s':15/8,
          'analytic_connector_peak_acceleration_rad_s2':10/math.sqrt(3),
          'analytic_connector_peak_jerk_rad_s3':60,
          'analytic_connector_jerk_integral_rad2_s5':720}
for key,value in expected.items(): assert np.isclose(measured[key],value,atol=1e-10,rtol=0)
assert measured['velocity_jump']<1e-10 and measured['acceleration_jump']<1e-9
integration_grid=np.linspace(0,1,100001)
jerk=60-360*integration_grid+360*integration_grid**2
integral=float(np.trapezoid(jerk*jerk,x=integration_grid))
assert abs(integral-720)<1e-5
analytic.append({'case':'one_rad_one_second_quintic','expected':expected,
                 'actual':{k:measured[k] for k in expected},'independent_quadrature_jerk_integral_rad2_s5':integral})

word_metrics=[]
for gloss,clip in clips.items():
    q,t=clip['positions'],clip['timestamps_s']
    a=np.gradient(np.gradient(q,t,axis=0,edge_order=2),t,axis=0,edge_order=2)
    j=np.gradient(a,t,axis=0,edge_order=2)
    word_metrics.append({'gloss':gloss,'motion_sha256':words[gloss]['motion_sha256'],
                         'full_word_finite_difference_peak_acceleration_rad_s2':float(np.abs(a).max()),
                         'full_word_finite_difference_peak_jerk_rad_s3':float(np.abs(j).max()),
                         'full_word_finite_difference_jerk_integral_rad2_s5':float(np.trapezoid(np.sum(j*j,axis=1),x=t))})
proposal={'schema_version':2,'proposal_id':'quality-v2-proposal-20261031','freeze_status':'pending',
          'approval_evidence':None,
          'boundary_derivative_method':'exact one-sided linear replay secant velocity; one-sided interval acceleration zero; analytic connector derivatives',
          'limits':{'velocity_jump_arm_rad_s':1e-5,'velocity_jump_finger_rad_s':1e-5,
                    'acceleration_jump_arm_rad_s2':1e-4,'acceleration_jump_finger_rad_s2':1e-4,
                    'peak_acceleration_rad_s2':120.0,'peak_jerk_rad_s3':3000.0,
                    'jerk_integral_rad2_s5':1e6,'maximum_transition_duration_s':6.0},
          'reference_curve':{'distance_rad':1.0,'duration_s':0.3,
              'peak_acceleration_rad_s2':10/math.sqrt(3)/0.3**2,
              'peak_jerk_rad_s3':60/0.3**3,'jerk_integral_rad2_s5':720/0.3**5},
          'basis':'finite numerical matching tolerances; rounded development engineering caps above a one-joint 1 rad/0.3 s reference; not hardware or human-smoothness limits and not chosen to pass observed candidates',
          'full_clip_method':'unfiltered 30 Hz np.gradient edge_order=2 twice for acceleration and once more for jerk; trapezoidal squared-jerk integral',
          'analytic_connector_method':'per-piece derivative extrema and exact squared-polynomial jerk integral; check separately under the same finite caps',
          'source_replay_limitation':'linear replay has undefined impulsive acceleration/jerk at internal knots; finite difference caps do not certify globally continuous derivatives',
          'pending_decisions':['actual protected core and windows','source continuous-derivative versus finite-difference acceptance','source retiming/continuousization permission','formal numerical caps and hardware limits','collision coverage approval']}
folder=STAGE/EVIDENCE_REL/'P0-4'
json_write(folder/'quality_metrics_recomputed.json',{'scope':'899 observed development candidates; not held-out acceptance data',
           'metrics':statistics,'candidates':rows,'word_finite_difference_metrics':word_metrics})
json_write(folder/'analytic_metric_checks.json',{'passed':True,'cases':analytic})
json_write(folder/'quality_threshold_proposal.json',proposal)
print(json.dumps({'recomputed_candidates':len(rows),'historical_statistics_match':True,
                  'analytic_checks_passed':len(analytic),'word_count':len(word_metrics),
                  'metrics':statistics,'freeze_status':'pending'},indent=2))
