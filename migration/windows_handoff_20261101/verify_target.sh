#!/bin/bash
# On the target (WSL2 Ubuntu 24.04, repo at the SAME path): environment, file hashes and frozen identity must match.
set -u
cd /home/kingderman/Documents/ME5412-github-latest
M=migration/windows_handoff_20261101
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
fail=0
[ "$(.venv/bin/python -c 'import platform; print(platform.python_version(), platform.system(), platform.machine())')" = "3.12.3 Linux x86_64" ] || { echo "FAIL python/system/machine"; fail=1; }
.venv/bin/python - "$M/requirements-lock.txt" <<'PY' || fail=1
import sys
from importlib import metadata
bad = []
for line in open(sys.argv[1]):
    name, version = line.strip().split("==")
    try:
        if metadata.version(name) != version: bad.append((name, metadata.version(name), version))
    except metadata.PackageNotFoundError: bad.append((name, None, version))
print("packages OK" if not bad else f"FAIL packages {bad}"); sys.exit(1 if bad else 0)
PY
sha256sum --quiet -c $M/SHA256SUMS.txt && echo "file hashes OK" || { echo "FAIL file hashes (CRLF conversion or edits?)"; fail=1; }
[ "$(git rev-parse HEAD)" = "$(.venv/bin/python -c "import json; print(json.load(open('$M/state_snapshot.json'))['git']['head'])")" ] && echo "git HEAD OK" || { echo "FAIL git HEAD"; fail=1; }
.venv/bin/python - <<'PY' || fail=1
import json, sys
sys.path.insert(0, "src")
from pathlib import Path
from sign_robot.pair_contract import freeze_library, load_policy, run_identity
policy = load_policy(Path("config/transition_policy_user_protected_hospital35_v1.json"), supported_versions=(2,))
current = run_identity(freeze_library(Path(".").resolve(), policy)[0], policy)
frozen = json.load(open("results/hospital35_protected_20261101_001/freeze/freeze.json"))["pair_identity"]
diff = {k for k in frozen if frozen[k] != current.get(k)}
print("frozen identity reproduces" if not diff else f"FAIL identity differs in {sorted(diff)}"); sys.exit(1 if diff else 0)
PY
[ $fail -eq 0 ] && echo "TARGET READY: resume with migration/windows_handoff_20261101/resume.sh" || { echo "TARGET NOT READY: do not resume the frozen runs"; exit 1; }
