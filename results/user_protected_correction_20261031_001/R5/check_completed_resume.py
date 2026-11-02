"""A completed resume must preserve every existing run-file byte."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from sign_robot.pair_contract import atomic_json

out=ROOT/'results/user_protected_correction_20261031_001'
run_id='user_protected_corrected_pilot_20261031_001'
run=out/'runs'/run_id
def inventory():
    return {str(p.relative_to(run)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(run.rglob('*')) if p.is_file()}
before=inventory()
commands=[['.venv/bin/python','scripts/plan_all_pairs.py','--library','hospital_v1','--include-self',
    '--policy','config/transition_policy_user_protected_v2.json','--run-id',run_id,
    '--results-root',str(out/'runs'),'--pair','COME__NOW','--pair','NOW__COME','--pair','COME__COME','--pair','NOW__NOW','--resume'],
    ['.venv/bin/python','scripts/verify_all_pairs.py','--run-id',run_id,'--results-root',str(out/'runs')]]
for label,argv in zip(('resume_plan','resume_verify'),commands):
    log=out/'R5'/(label+'.log')
    assert not log.exists()
    started=time.monotonic()
    with log.open('w') as stream:
        result=subprocess.run(argv,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
    atomic_json(log.with_suffix('.command.json'),{'argv':argv,'cwd':str(ROOT),'exit_code':result.returncode,
        'elapsed_s':time.monotonic()-started,'log':str(log),'environment':'inherits frozen command wrapper overrides'})
    assert result.returncode==0,(argv,result.returncode)
after=inventory()
assert before==after,sorted(k for k in before.keys()|after.keys() if before.get(k)!=after.get(k))
path=out/'R5/completed_resume.json'
assert not path.exists()
atomic_json(path,{'passed':True,'run_id':run_id,'file_count':len(before),
    'before':before,'after':after,'all_run_files_bitwise_unchanged':True})
print(json.dumps({'passed':True,'run_files_unchanged':len(before)}))
