#!/bin/bash
# After P1-3: the final read-only progress table and a fresh independent recheck of every selected candidate.
# Refuses (exit 4) unless every frozen batch ended BATCH_COMPLETE and no pairs driver is running.
set -u
cd /home/kingderman/Documents/ME5412-github-latest
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
R=results/hospital35_protected_20261101_001
echo "== start $(date -Is)"
.venv/bin/python $R/commands/check_p1_3_finished.py || exit 4
# Runs 002-004 exist when the open batches were split in parallel (commands/p1_3_parallel.sh); same identity.
RUNS=$(ls -d $R/pair_runs/hospital35_protected_20261101_00[1-4] | paste -sd, -)
.venv/bin/python $R/P1-3/scan_progress_multi.py $RUNS $R/batches/manifest.json $R/preflight_final/preflight.json $R/P1-3/progress_final.json
echo "progress exit $?"
for run in ${RUNS//,/ }; do
  .venv/bin/python scripts/run_hospital35_batches.py recheck-pairs --run-dir $run --output $R/P1-3/selected_recheck_final_$(basename $run)
  echo "recheck $(basename $run) exit $?"
done
echo "== end $(date -Is)"
