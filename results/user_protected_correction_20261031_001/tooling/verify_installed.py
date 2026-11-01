"""Check installed delivery hashes and run final acceptance in the actual target."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path('/home/kingderman/Documents/ME5412-github-latest')
OUT=ROOT/'results/user_protected_correction_20261031_001'
manifest=json.loads((OUT/'FINAL/install_manifest.json').read_text())
assert all(hashlib.sha256((ROOT/e['relative']).read_bytes()).hexdigest()==e['after_sha256'] for e in manifest['files'])
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',MUJOCO_GL='egl')
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    env[k]='1'
argv=[str(ROOT/'.venv/bin/python'),'results/user_protected_correction_20261031_001/FINAL/acceptance.py',
    '--root',str(ROOT),'--output','results/user_protected_correction_20261031_001/FINAL/final_acceptance_checklist.json']
log=OUT/'R7/installed_acceptance.log'
assert not log.exists()
started=time.monotonic()
with log.open('w') as stream:
    result=subprocess.run(argv,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
record={'argv':argv,'cwd':str(ROOT),'exit_code':result.returncode,'elapsed_s':time.monotonic()-started,
    'environment_overrides':{k:env[k] for k in ('PYTHONDONTWRITEBYTECODE','MUJOCO_GL','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')},
    'log':str(log),'initial_delivery_hashes_verified':len(manifest['files'])}
(OUT/'R7/installed_acceptance.command.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
print(log.read_text())
raise SystemExit(result.returncode)
