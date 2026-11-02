#!/bin/bash
# P1-3: frozen batches in manifest order in the same run (regression is already complete and is skipped quickly).
# Stops at the first batch that does not complete; a graceful stop is `touch $R/batch_control/hospital35_protected_20261101_001.stop`.
set -u
cd /home/kingderman/Documents/ME5412-github-latest
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
R=results/hospital35_protected_20261101_001
echo "== start $(date -Is)"
.venv/bin/python scripts/run_hospital35_batches.py pairs --batch-manifest $R/batches/manifest.json \
  --batch-manifest-sha256 fb7c56187f6a1edded67b3c701fde6746a3c87d49eeff62af303ca19231ebf19 \
  --run-id hospital35_protected_20261101_001 --results-root $R/pair_runs --control-dir $R/batch_control
echo "exit $?"
echo "== end $(date -Is)"
