"""Record an authorized command executed in the actual target repository."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path('/home/kingderman/Documents/ME5412-github-latest')
OUT=ROOT/'results/user_protected_correction_20261031_001'
label,*argv=sys.argv[1:]
log=OUT/(label+'.log')
record=OUT/(label+'.command.json')
assert not log.exists() and not record.exists()
log.parent.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',MUJOCO_GL='egl')
keys=('PYTHONDONTWRITEBYTECODE','MUJOCO_GL','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')
for k in keys[2:]:
    env[k]='1'
started=time.monotonic()
with log.open('w') as stream:
    result=subprocess.run(argv,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
data={'argv':argv,'cwd':str(ROOT),'environment_overrides':{k:env[k] for k in keys},
    'exit_code':result.returncode,'elapsed_s':time.monotonic()-started,'log':str(log)}
record.write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(data,indent=2))
print(log.read_text()[-6000:])
raise SystemExit(result.returncode)
