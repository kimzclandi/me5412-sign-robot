#!/bin/bash
# P1-3 in parallel without code changes: the open frozen batches are split round-robin across 4 runs with the same
# frozen code, policy and environment, one writer each, each pinned to its own performance core (cpu0-3; planning has
# a wall-clock budget, so slow cores would yield fewer candidates). Run 001 keeps the batch it stopped in.
# Pair seeds depend only on the frozen batch position, not on the run. The partition is written once to
# P1-3/parallel_partition.json and reused; rerunning this script resumes every run (completed batches are skipped).
# Graceful stop: touch $R/batch_control/<run_id>.stop for each run (delete before resuming).
set -u
cd /home/kingderman/Documents/ME5412-github-latest
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
R=results/hospital35_protected_20261101_001
P=$R/P1-3/parallel_partition.json
echo "== start $(date -Is)"
if pgrep -f '^[^ ]*python[^ ]* scripts/run_hospital35_batches\.py pairs' >/dev/null; then echo "a pairs driver is running; refusing"; exit 4; fi
[ -f $P ] || .venv/bin/python - <<'EOF' || exit 4
import json
from datetime import datetime, timezone
from pathlib import Path
R = Path("results/hospital35_protected_20261101_001")
manifest = json.loads((R / "batches/manifest.json").read_text(encoding="utf-8"))
def complete(batch_id):
    logs = sorted((R / "batch_control/pair_batches" / batch_id).glob("invocation_*.json"))
    return bool(logs) and json.loads(logs[-1].read_text(encoding="utf-8"))["stop_reason"] == "BATCH_COMPLETE"
open_batches = [b for b in manifest["order"] if not complete(b)]
runs = [f"hospital35_protected_20261101_{n:03d}" for n in range(1, 5)]
partition = {"schema_version": 1, "kind": "hospital35_p1_3_parallel_partition_v1",
             "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "batch_manifest_sha256": "fb7c56187f6a1edded67b3c701fde6746a3c87d49eeff62af303ca19231ebf19",
             "completed_in_run_001_before_split": [b for b in manifest["order"] if complete(b)],
             "rule": "open batches in manifest order, round-robin; slice 0 (with the batch run 001 stopped in) stays in run 001",
             "workers": [{"run_id": run, "cpu": cpu, "batches": open_batches[cpu::4]} for cpu, run in enumerate(runs)]}
(R / "P1-3/parallel_partition.json").open("x", encoding="utf-8").write(json.dumps(partition, indent=2) + "\n")
print(json.dumps({"open_batches": len(open_batches), "slices": [len(w["batches"]) for w in partition["workers"]]}))
EOF
pids=()
for w in 0 1 2 3; do
  run=$(.venv/bin/python -c "import json; print(json.load(open('$P'))['workers'][$w]['run_id'])")
  args=$(.venv/bin/python -c "import json; print(' '.join('--batch ' + b for b in json.load(open('$P'))['workers'][$w]['batches']))")
  rm -f $R/batch_control/$run.stop
  taskset -c $w .venv/bin/python scripts/run_hospital35_batches.py pairs --batch-manifest $R/batches/manifest.json \
    --batch-manifest-sha256 fb7c56187f6a1edded67b3c701fde6746a3c87d49eeff62af303ca19231ebf19 $args \
    --run-id $run --results-root $R/pair_runs --control-dir $R/batch_control >> $R/P1-3_parallel_$run.log 2>&1 &
  pids+=($!); echo "worker $w $run cpu$w pid $!"
done
status=0
for i in 0 1 2 3; do wait ${pids[$i]}; code=$?; echo "worker $i exit $code"; [ $code -eq 0 ] || status=$code; done
echo "== end $(date -Is) status $status"
exit $status
