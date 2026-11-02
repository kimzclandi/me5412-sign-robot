import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path('/home/kingderman/Documents/ME5412-github-latest')
OUT=ROOT/'results/user_protected_auto_20261031_001'
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',MUJOCO_GL='egl')
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    env[key]='1'
argv=[str(ROOT/'.venv/bin/python'),'results/user_protected_auto_20261031_001/FINAL/acceptance.py',
      '--root',str(ROOT),'--output','results/user_protected_auto_20261031_001/FINAL/final_acceptance_checklist.json']
started=time.time()
log=OUT/'R7/installed_acceptance.log'
assert not log.exists()
with log.open('w') as f:
    result=subprocess.run(argv,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
record={'argv':argv,'cwd':str(ROOT),'exit_code':result.returncode,'elapsed_s':time.time()-started,'log':str(log)}
(OUT/'R7/installed_acceptance.command.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
print(log.read_text())
raise SystemExit(result.returncode)
