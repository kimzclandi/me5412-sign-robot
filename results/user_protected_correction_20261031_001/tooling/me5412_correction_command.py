import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('/tmp/me5412_corrected_intervals_20261031_001/repository')
OUT = ROOT/'results/user_protected_correction_20261031_001'
label, *argv = sys.argv[1:]
log = OUT/(label+'.log')
log.parent.mkdir(parents=True, exist_ok=True)
record_path = OUT/(label+'.command.json')
assert not log.exists() and not record_path.exists(), label
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', MUJOCO_GL='egl')
keys = ('PYTHONDONTWRITEBYTECODE','MUJOCO_GL','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')
for key in keys[2:]:
    env[key] = '1'
started = time.time()
with log.open('w') as stream:
    result = subprocess.run(argv, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT)
record = {'argv': argv, 'cwd': str(ROOT), 'environment_overrides': {k: env[k] for k in keys},
          'exit_code': result.returncode, 'elapsed_s': time.time()-started, 'log': str(log)}
record_path.write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps(record, indent=2))
print(log.read_text()[-7000:])
raise SystemExit(result.returncode)
