#!/bin/bash
# P1-3 resume on WSL2 (2026-11-01) for selected workers only, in the frozen partition order (each run first finishes the
# batch it was in when the 12:35 crash hit; the driver refuses other batches until that backlog is cleared).
# Usage: p1_3_parallel_wsl.sh 1 2 3   (worker indices into P1-3/parallel_partition.json; worker w is pinned to cpu w).
# Written after p1_3_parallel_priority.sh was refused with BACKLOG_NOT_CLEARED (runs 002-004) and run 001 stopped with
# "In-progress deterministic replay differs" on NEED__PLEASE (rest_037). Does not start the after_p1_3.sh chain.
set -u
cd /home/kingderman/Documents/ME5412-github-latest
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
R=results/hospital35_protected_20261101_001
P=$R/P1-3/parallel_partition.json
[ $# -ge 1 ] || { echo "usage: $0 worker..."; exit 2; }
echo "== start $(date -Is) workers $*"
pids=()
for w in "$@"; do
  run=$(.venv/bin/python -c "import json; print(json.load(open('$P'))['workers'][$w]['run_id'])")
  if pgrep -f "scripts/run_hospital35_batches\.py pairs .*--run-id $run" >/dev/null; then echo "$run already has a driver; refusing"; exit 4; fi
  # Order: the batch holding this run's backlog (unfinished planning or review) first, then the partition's batches
  # whose latest invocation log is not BATCH_COMPLETE. The driver checks the backlog before skipping completed pairs,
  # so passing an already complete batch while a backlog exists only adds a BACKLOG_NOT_CLEARED log.
  args=$(.venv/bin/python - "$P" "$w" "$R" <<'EOF'
import json, sys
from pathlib import Path
partition, w, R = json.load(open(sys.argv[1])), int(sys.argv[2]), Path(sys.argv[3])
worker = partition["workers"][w]
batch_of = {}
for b in json.load(open(R / "batches/manifest.json"))["batches"]:
    for p in json.load(open(b["file"]))["pair_ids"]:
        batch_of[p] = b["batch_id"]
run = R / "pair_runs" / worker["run_id"]
backlog = set()
for pair_id, head in json.load(open(run / "manifest.json"))["heads"].items():
    record = json.load(open(run / head["path"]))["record"]
    if not record["completed"] or record["verification_state"] == "NOT_RUN":
        backlog.add(batch_of[pair_id])
def complete(batch_id):
    logs = sorted((R / "batch_control/pair_batches" / batch_id).glob("invocation_*.json"))
    return bool(logs) and json.loads(logs[-1].read_text(encoding="utf-8"))["stop_reason"] == "BATCH_COMPLETE"
if len(backlog) > 1 or not backlog <= set(worker["batches"]):
    sys.exit(f"unexpected backlog {sorted(backlog)}")
order = sorted(backlog) + [b for b in worker["batches"] if b not in backlog and not complete(b)]
print(" ".join("--batch " + b for b in order))
EOF
) || exit 4
  echo "worker $w $run order: $args"
  rm -f $R/batch_control/$run.stop
  taskset -c $w .venv/bin/python scripts/run_hospital35_batches.py pairs --batch-manifest $R/batches/manifest.json \
    --batch-manifest-sha256 fb7c56187f6a1edded67b3c701fde6746a3c87d49eeff62af303ca19231ebf19 $args \
    --run-id $run --results-root $R/pair_runs --control-dir $R/batch_control >> $R/P1-3_parallel_$run.log 2>&1 &
  pids+=($!); echo "worker $w $run cpu$w pid $!"
done
status=0
for p in "${pids[@]}"; do wait $p; code=$?; echo "pid $p exit $code $(date -Is)"; [ $code -eq 0 ] || status=$code; done
echo "== end $(date -Is) status $status"
exit $status
