"""Read-only P1-3 progress: per frozen group and batch, with preflight predictions cross-checked.

Usage: scan_progress.py RUN_DIR BATCH_MANIFEST PREFLIGHT_JSON OUTPUT_JSON
"""
from collections import Counter
import json
import os
from pathlib import Path
import sys

ROOT = Path("/home/kingderman/Documents/ME5412-github-latest")
sys.path.insert(0, str(ROOT / "src"))
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

from sign_robot.pair_contract import read_json
from sign_robot.pair_runner_v2 import V2RunStore

PENDING = ("V2_FORMAL", "QUALITY_THRESHOLDS", "COLLISION_SCOPE", "ALGORITHM_WINDOWS", "INDEPENDENT_RECHECK", "NO_INDEPENDENT")


def main(run_dir, manifest_path, preflight_path, output):
    store = V2RunStore.load(ROOT, ROOT / run_dir)
    manifest = read_json(ROOT / manifest_path)
    preflight = read_json(ROOT / preflight_path)
    predicted = set(preflight["affected_pairs"]["any"]["pair_ids"])
    rows = {}
    for batch in manifest["batches"]:
        for pair_id in read_json(ROOT / batch["file"])["pair_ids"]:
            record = store._head_record(pair_id)
            row = {"pair_id": pair_id, "group": batch["group"], "batch": batch["batch_id"],
                   "predicted_source_blocked": pair_id in predicted}
            if record is None:
                row.update(state="NOT_RUN")
            else:
                reasons = Counter()
                for review in record.get("verifications", []):
                    evidence = read_json(store.run_dir / review["path"])["evidence"]
                    reasons.update(c for c in evidence["reason_codes"] if not c.startswith(PENDING))
                selected = record["selected_candidate_id"]
                state = ("PLANNING_INCOMPLETE" if not record["completed"] else
                         "REVIEW_INCOMPLETE" if record["verification_state"] == "NOT_RUN" else
                         "NUMERICAL_PASS" if selected else
                         "NO_CURVE_DIAGNOSIS" if record["verification_state"] == "DIAGNOSIS_ONLY" else "NUMERICAL_FAIL")
                row.update(state=state, status=record["status"], candidates=record["candidate_count"],
                           reviewed=len(record.get("verifications", [])), selected=selected,
                           failure_reasons=dict(reasons.most_common(4)))
            rows[pair_id] = row
    groups = {}
    for name in ("regression", "self", "hub", "rest", "all"):
        subset = [r for r in rows.values() if name == "all" or r["group"] == name]
        states = Counter(r["state"] for r in subset)
        done = [r for r in subset if r["state"] in ("NUMERICAL_PASS", "NUMERICAL_FAIL", "NO_CURVE_DIAGNOSIS")]
        groups[name] = {"denominator": len(subset), "states": dict(sorted(states.items())),
                        "reviewed_complete": len(done),
                        "prediction_check": {
                            "predicted_blocked_and_failed": sum(r["predicted_source_blocked"] and r["state"] != "NUMERICAL_PASS" for r in done),
                            "predicted_blocked_but_passed": sum(r["predicted_source_blocked"] and r["state"] == "NUMERICAL_PASS" for r in done),
                            "predicted_open_and_passed": sum(not r["predicted_source_blocked"] and r["state"] == "NUMERICAL_PASS" for r in done),
                            "predicted_open_but_failed": sum(not r["predicted_source_blocked"] and r["state"] != "NUMERICAL_PASS" for r in done)}}
    reasons = Counter()
    for r in rows.values():
        reasons.update(r.get("failure_reasons", {}).keys())
    result = {"schema_version": 1, "run_id": store.manifest["run_id"], "identity_hash": store.manifest["identity"]["identity_hash"],
              "groups": groups, "failure_reason_pairs": dict(reasons.most_common()), "rows": list(rows.values()),
              "formal_pass_count": 0}
    path = ROOT / output
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: v for k, v in groups.items()}, ensure_ascii=False))
    print(json.dumps(result["failure_reason_pairs"]))


if __name__ == "__main__":
    main(*sys.argv[1:5])
