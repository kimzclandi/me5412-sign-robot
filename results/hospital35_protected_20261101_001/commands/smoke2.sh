#!/bin/bash
# Pre-freeze development smoke of the real driver path; outputs are diagnostics, not evidence.
set -u
cd /home/kingderman/Documents/ME5412-github-latest
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
R=results/hospital35_protected_20261101_001
S=$R/smoke_pre_freeze_002
P=.venv/bin/python
step() { echo "== $*"; "$@"; echo "exit $?"; }
step $P scripts/run_hospital35_batches.py pairs --batch-manifest $R/batches/manifest.json \
  --batch-manifest-sha256 fb7c56187f6a1edded67b3c701fde6746a3c87d49eeff62af303ca19231ebf19 \
  --batch regression_001 --run-id smoke_pairs_001 --results-root $S/pair_runs --control-dir $S/batch_control
step $P scripts/run_hospital35_batches.py pairs --batch-manifest $R/batches/manifest.json \
  --batch-manifest-sha256 fb7c56187f6a1edded67b3c701fde6746a3c87d49eeff62af303ca19231ebf19 \
  --batch regression_001 --run-id smoke_pairs_001 --results-root $S/pair_runs --control-dir $S/batch_control
step $P scripts/run_hospital35_batches.py recheck-pairs --run-dir $S/pair_runs/smoke_pairs_001 --output $S/recheck
step $P /tmp/claude-1000/-home-kingderman-Documents-ME5412-github-latest/19dd5746-dbff-4494-9cac-167e2ee2a16d/scratchpad/generate_case_manifest.py \
  $S/case_manifest.json $S/sequences $S/pair_runs/smoke_pairs_001 $S/aggregate
SHA=$(sha256sum $S/case_manifest.json | cut -d' ' -f1)
step $P scripts/run_hospital35_batches.py sequences --sequence-policy config/sequence_policy_hospital35_v1.json \
  --case-manifest $S/case_manifest.json --case-manifest-sha256 $SHA --subbatch s001 --control-dir $S/batch_control
step $P scripts/run_hospital35_batches.py sequences --sequence-policy config/sequence_policy_hospital35_v1.json \
  --case-manifest $S/case_manifest.json --case-manifest-sha256 $SHA --subbatch s003 --control-dir $S/batch_control
step $P scripts/run_hospital35_batches.py sequences --sequence-policy config/sequence_policy_hospital35_v1.json \
  --case-manifest $S/case_manifest.json --case-manifest-sha256 $SHA --subbatch s001 --control-dir $S/batch_control
step $P scripts/run_hospital35_batches.py aggregate --sequence-policy config/sequence_policy_hospital35_v1.json \
  --case-manifest $S/case_manifest.json --case-manifest-sha256 $SHA
step $P scripts/render_sequences.py --run-dir $S/sequences/s001 --output $S/videos --case COME__NOW__COME
echo "== done"
