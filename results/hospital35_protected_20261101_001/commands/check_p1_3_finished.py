"""Exit 0 only when no pairs driver is running and every frozen P1-3 batch's latest invocation log ended BATCH_COMPLETE."""
import json
from pathlib import Path
import subprocess
import sys

R = Path("/home/kingderman/Documents/ME5412-github-latest/results/hospital35_protected_20261101_001")

running = subprocess.run(["pgrep", "-f", r"^[^ ]*python[^ ]* scripts/run_hospital35_batches\.py pairs --batch-manifest results/hospital35_protected_20261101_001/batches/manifest\.json"], capture_output=True, text=True).stdout.split()
if running:
    sys.exit(f"P1-3 driver still running (pid {' '.join(running)}); refusing")
batches = json.loads((R / "batches/manifest.json").read_text(encoding="utf-8"))["batches"]
open_batches = []
for batch in batches:
    logs = sorted((R / "batch_control/pair_batches" / batch["batch_id"]).glob("invocation_*.json"))
    if not logs or json.loads(logs[-1].read_text(encoding="utf-8"))["stop_reason"] != "BATCH_COMPLETE":
        open_batches.append(batch["batch_id"])
if open_batches:
    sys.exit(f"P1-3 not finished: {len(open_batches)}/{len(batches)} batches open, first {open_batches[0]}; refusing")
print(f"P1-3 finished: {len(batches)}/{len(batches)} batches BATCH_COMPLETE")
