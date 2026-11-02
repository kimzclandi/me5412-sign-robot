#!/bin/bash
# P0-7 freeze: focused tests on the final code, final preflight, case manifest, freeze record.
set -u
cd /home/kingderman/Documents/ME5412-github-latest
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
R=results/hospital35_protected_20261101_001
F=$R/freeze
P=.venv/bin/python
SCRATCH=/tmp/claude-1000/-home-kingderman-Documents-ME5412-github-latest/19dd5746-dbff-4494-9cac-167e2ee2a16d/scratchpad
CMD="$P -m pytest -q -p no:cacheprovider tests/test_user_protected_windows.py tests/test_user_protected_correction.py tests/test_pair_runner_v2.py tests/test_lift_off_arrival_v5.py tests/test_sequence_v1.py tests/test_hospital35_protection_import.py tests/test_hospital35_preflight.py tests/test_hospital35_batches.py tests/test_sequence_combinations.py tests/test_sequence_blockers.py tests/test_hospital35_freeze.py"
echo "\$ $CMD" > $F/pytest_focused_final.log
$CMD >> $F/pytest_focused_final.log 2>&1; echo "exit $?" >> $F/pytest_focused_final.log
tail -2 $F/pytest_focused_final.log
$P scripts/preflight_hospital35.py --output $R/preflight_final > $R/preflight_final.log 2>&1; echo "exit $?" >> $R/preflight_final.log
tail -2 $R/preflight_final.log | cut -c1-300
$P $SCRATCH/generate_case_manifest.py $R/sequence_cases/case_manifest.json $R/sequences_full_001 \
  $R/pair_runs/hospital35_protected_20261101_001 $R/sequences_full_001/aggregate
cp $SCRATCH/generate_case_manifest.py $SCRATCH/write_freeze_record.py $F/
$P $SCRATCH/write_freeze_record.py $F/pytest_focused_final.log $F/pytest_full_candidate_002.log $R/preflight_final \
  $R/sequence_cases/case_manifest.json
echo "== done"
