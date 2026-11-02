"""Compare four COME/NOW pairs between the old pilot run and a new hospital35 run (read only)."""
import json
import os
from pathlib import Path
import sys

ROOT = Path("/home/kingderman/Documents/ME5412-github-latest")
sys.path.insert(0, str(ROOT / "src"))
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

from sign_robot.pair_contract import read_json, read_pair_trajectory
from sign_robot.pair_runner_v2 import V2RunStore

PAIRS = ["COME__NOW", "NOW__COME", "COME__COME", "NOW__NOW"]


def describe(run_dir):
    store = V2RunStore.load(ROOT, run_dir)
    rows = {}
    for pair_id in PAIRS:
        record = store._head_record(pair_id)
        selected = record["selected_candidate_id"]
        row = {"attempts": len(record["attempts"]), "candidates": record["candidate_count"],
               "numerical_pass": sum(v["numerical_checks_passed"] for v in record["verifications"]),
               "selected": selected}
        if selected:
            entry = next(a for a in record["attempts"] if a["attempt_id"] == selected)
            trajectory = read_pair_trajectory(store.run_dir / entry["candidate_file"], schema_version=2)
            evidence = read_json(store.run_dir / "verification" / pair_id / f"{selected}.json")["evidence"]
            words = trajectory["word_instances"]
            row.update(method=trajectory["planner"]["method"], finger=trajectory["finger_strategy"]["name"],
                       source_frames=[w["source_frames"] for w in words],
                       protected=[w["protected_core_frames"] for w in words],
                       transition_s=[round(trajectory["segments"][1]["start_time_s"], 4), round(trajectory["segments"][-2]["end_time_s"], 4)],
                       total_s=round(trajectory["segments"][-1]["end_time_s"], 4),
                       peak_acc=round(evidence["metrics"]["peak_acceleration_rad_s2"], 2),
                       peak_jerk=round(evidence["metrics"]["peak_jerk_rad_s3"], 1),
                       region_integral=round(evidence["metrics"]["jerk_integral_rad2_s5"]),
                       analytic_integral=round(evidence["metrics"]["analytic_connector_jerk_integral_rad2_s5"]),
                       clearance_mm=round(evidence["min_clearance_mm"], 3))
        rows[pair_id] = row
    return rows


if __name__ == "__main__":
    old = describe(ROOT / sys.argv[1])
    new = describe(ROOT / sys.argv[2])
    print(json.dumps({"old": old, "new": new}, indent=1))
