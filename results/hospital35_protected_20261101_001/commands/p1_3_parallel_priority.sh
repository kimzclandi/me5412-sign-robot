#!/bin/bash
# P1-3 resume on WSL2 (2026-11-01) with the user's nine hospital sentences first. Same frozen partition as
# p1_3_parallel.sh (each run keeps exactly its own batches, one writer each); only the order inside each run changes so
# that the open batches holding the sentences' pairs run first. Pair seeds depend only on the frozen batch position,
# so order does not change results. Completed batches are skipped by the driver. Then the usual after_p1_3.sh chain.
# Priority pairs: NEED__INTERPRETER rest_037 (001), HURT__WHERE rest_042 + MORNING__NIGHT rest_062 (002),
# WAIT__DOCTOR rest_039 (003), NIGHT__TAKE rest_064 (004).
set -u
cd /home/kingderman/Documents/ME5412-github-latest
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
R=results/hospital35_protected_20261101_001
P=$R/P1-3/parallel_partition.json
PRIORITY="rest_037 rest_039 rest_042 rest_062 rest_064"
echo "== start $(date -Is) host WSL2 $(uname -r)"
if pgrep -f 'scripts/run_hospital35_batches\.py' >/dev/null; then echo "a driver is already running; refusing"; exit 4; fi
[ -f $P ] || { echo "partition missing; refusing"; exit 4; }
rm -f $R/batch_control/hospital35_protected_20261101_00[1-4].stop
pids=()
for w in 0 1 2 3; do
  run=$(.venv/bin/python -c "import json; print(json.load(open('$P'))['workers'][$w]['run_id'])")
  args=$(.venv/bin/python -c "
import json, sys
batches = json.load(open('$P'))['workers'][$w]['batches']
first = [b for b in batches if b in sys.argv[1].split()]
print(' '.join('--batch ' + b for b in first + [b for b in batches if b not in first]))" "$PRIORITY")
  echo "worker $w $run: $args"
  taskset -c $w .venv/bin/python scripts/run_hospital35_batches.py pairs --batch-manifest $R/batches/manifest.json \
    --batch-manifest-sha256 fb7c56187f6a1edded67b3c701fde6746a3c87d49eeff62af303ca19231ebf19 $args \
    --run-id $run --results-root $R/pair_runs --control-dir $R/batch_control >> $R/P1-3_parallel_$run.log 2>&1 &
  pids+=($!)
done
bash $R/commands/after_p1_3.sh >> $R/after_p1_3.log 2>&1 &
chain=$!
status=0
for i in 0 1 2 3; do wait ${pids[$i]}; code=$?; echo "worker $i exit $code $(date -Is)"; [ $code -eq 0 ] || status=$code; done
echo "== P1-3 drivers end $(date -Is) status $status; chain (final table, P1-4, retry) continues as pid $chain"
wait $chain; echo "== chain exit $? $(date -Is)"
