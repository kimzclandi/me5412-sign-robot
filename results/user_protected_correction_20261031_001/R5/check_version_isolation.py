"""Saved trajectories from either interval version cannot be rebound to the other."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from sign_robot.pair_contract import atomic_json, file_hash, load_policy
from sign_robot.pair_verification_v2 import verify_saved_pair_v2

old_run = ROOT/'results/user_protected_auto_20261031_001/runs/user_protected_pilot_20261031_001'
new_run = ROOT/'results/user_protected_correction_20261031_001/runs/user_protected_corrected_pilot_20261031_001'
old_curve = sorted((old_run/'candidates/COME__COME').glob('*.json'))[0]
new_curve = sorted((new_run/'candidates/COME__COME').glob('*.json'))[0]
results = []
for path, version in ((old_curve, 2), (new_curve, 1)):
    before = file_hash(path)
    policy = load_policy(ROOT/f'config/transition_policy_user_protected_v{version}.json',supported_versions=(1,2))
    evidence = verify_saved_pair_v2(ROOT,path,policy)
    assert evidence['status'] == 'ERROR' and evidence.get('numerical_checks_passed') is not True
    assert file_hash(path) == before
    results.append({'trajectory':str(path.relative_to(ROOT)), 'trajectory_sha256':before,
        'attempted_policy_version':version, 'evidence':evidence, 'source_file_unchanged':True})
output = Path(__file__).with_name('version_isolation.json')
assert not output.exists()
atomic_json(output,{'passed':True,'checks':results})
print(json.dumps({'passed':True,'checks':[{'file':x['trajectory'],'policy_version':x['attempted_policy_version'],
    'status':x['evidence']['status'],'details':x['evidence'].get('diagnostic_details')} for x in results]},indent=2))
