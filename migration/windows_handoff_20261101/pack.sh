#!/bin/bash
# Pack the whole working tree for transfer: .git (HEAD 2875e49 + uncommitted work), results incl. raw pair_runs,
# configs and docs. Excludes .venv and caches (rebuild from requirements-lock.txt). Run only while no driver runs.
set -eu
cd /home/kingderman/Documents/ME5412-github-latest
if pgrep -f 'scripts/run_hospital35_batches\.py' >/dev/null; then echo "a driver is running; stop it first"; exit 4; fi
OUT=${1:-$HOME/ME5412_migration_20261101.tar.zst}
tar --exclude=./.venv --exclude='*/__pycache__' --exclude=./.pytest_cache -I 'zstd -T0 -10' -cpf "$OUT" .
sha256sum "$OUT" | tee "$OUT.sha256"
ls -lh "$OUT"
