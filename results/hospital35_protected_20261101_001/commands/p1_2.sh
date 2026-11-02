#!/bin/bash
# P1-2: the original 12 cases under the new sequence policy, from the same new pair run; recheck and videos.
set -u
cd /home/kingderman/Documents/ME5412-github-latest
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
R=results/hospital35_protected_20261101_001
P=.venv/bin/python
step() { echo "== $*"; "$@"; echo "exit $?"; }
step $P scripts/plan_sequences.py --sequence-policy config/sequence_policy_hospital35_v1.json \
  --pair-run-dir $R/pair_runs/hospital35_protected_20261101_001 --output $R/sequences_regression_001 \
  --case COME__COME__COME --case COME__COME__NOW --case COME__NOW__COME --case COME__NOW__NOW \
  --case NOW__COME__COME --case NOW__COME__NOW --case NOW__NOW__COME --case NOW__NOW__NOW \
  --case COME__COME__COME__COME__COME --case NOW__NOW__NOW__NOW__NOW \
  --case COME__NOW__COME__NOW__COME --case NOW__COME__NOW__COME__NOW
step $P scripts/verify_sequences.py --run-dir $R/sequences_regression_001
step $P scripts/render_sequences.py --run-dir $R/sequences_regression_001 --output $R/videos_regression_001
echo "== done"
