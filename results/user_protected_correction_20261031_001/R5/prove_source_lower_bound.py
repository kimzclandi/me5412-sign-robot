"""Record a numerical lower bound from immutable interior source samples."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from sign_robot.pair_contract import atomic_json,file_hash,load_policy

folder=Path(__file__).resolve().parent
audit=json.loads((folder/'protected_source_quality.json').read_text())
policy_path=ROOT/'config/transition_policy_user_protected_v2.json'
policy=load_policy(policy_path,supported_versions=(1,2))
assert audit['policy_file_sha256']==file_hash(policy_path)
cap=policy['quality']['limits']['jerk_integral_rad2_s5']
pairs={}
for pair in ('COME__NOW','NOW__COME','COME__COME','NOW__NOW'):
    words=pair.split('__')
    values=[audit['words'][w]['squared_jerk_integral_rad2_s5'] for w in words]
    lower=sum(values)
    assert lower>cap
    pairs[pair]={'per_instance_interior_contributions':values,'full_motion_lower_bound_rad2_s5':lower,
        'frozen_full_motion_limit_rad2_s5':cap,'lower_bound_exceeds_limit':True}
path=folder/'protected_source_lower_bound.json'
assert not path.exists()
atomic_json(path,{'policy_file_sha256':file_hash(policy_path),'script_sha256':file_hash(__file__),
    'source_audit_sha256':file_hash(folder/'protected_source_quality.json'),'pairs':pairs,
    'scope':'frozen 30-Hz full-replay finite-difference squared-jerk integral; no word retiming',
    'basis':'Sum of nonnegative contributions strictly inside each protected instance, with three-frame stencils independent of new connectors.',
    'does_not_prove':'search completeness, human comprehension, or safety under another quality definition',
    'action':'report incompatibility; preserve poses/timing and frozen limits'})
print(json.dumps(pairs,indent=2))
