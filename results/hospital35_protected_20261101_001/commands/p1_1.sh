#!/bin/bash
# P1-1: official four-pair regression under the frozen hospital35 policy, then a fresh recheck of each selection.
set -u
cd /home/kingderman/Documents/ME5412-github-latest
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
R=results/hospital35_protected_20261101_001
P=.venv/bin/python
step() { echo "== $*"; "$@"; echo "exit $?"; }
step $P scripts/run_hospital35_batches.py pairs --batch-manifest $R/batches/manifest.json \
  --batch-manifest-sha256 fb7c56187f6a1edded67b3c701fde6746a3c87d49eeff62af303ca19231ebf19 \
  --batch regression_001 --run-id hospital35_protected_20261101_001 --results-root $R/pair_runs --control-dir $R/batch_control
step $P scripts/run_hospital35_batches.py recheck-pairs --run-dir $R/pair_runs/hospital35_protected_20261101_001 \
  --output $R/P1-1/selected_recheck
echo "== done"
