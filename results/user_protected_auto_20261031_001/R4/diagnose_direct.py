import json
from sign_robot.motion import ROOT
from sign_robot.pair_contract import load_policy
from sign_robot.pair_routes import build_pair_context_v2, valid_endpoint_choices_v2, PairWorkBudget, endpoint_pairs_v1
from sign_robot.pair_timing import boundary_state_v2, quintic_coefficients_v2, _extrema
import numpy as np

p=load_policy(ROOT/'config/transition_policy_user_protected_v1.json',supported_versions=(1,2))
c=build_pair_context_v2(ROOT,p)
result={}
for source,target in [('COME','NOW'),('NOW','COME'),('NOW','NOW')]:
    s=valid_endpoint_choices_v2(c,source,target,PairWorkBudget(p))
    rows=[]
    for sf,tf in endpoint_pairs_v1(c,s):
        a=boundary_state_v2(c.clips[source],sf,'source')
        b=boundary_state_v2(c.clips[target],tf,'target')
        coef=quintic_coefficients_v2(a,b,.3)
        lo,hi=_extrema(coef,.3,0)
        bad=[]
        for j,n in enumerate(c.library['joint_names']):
            bound=c.model.joint(n).range
            if lo[j]<bound[0]-1e-8 or hi[j]>bound[1]+1e-8:
                bad.append({'joint':n,'bounds':bound.tolist(),'min':float(lo[j]),'max':float(hi[j]),
                            'start':[a[k][j] for k in ('position','velocity','acceleration')],
                            'end':[b[k][j] for k in ('position','velocity','acceleration')]})
        rows.append({'source_frame':sf,'target_frame':tf,'violations':bad})
    result[source+'__'+target]=rows
print(json.dumps(result,indent=2))
