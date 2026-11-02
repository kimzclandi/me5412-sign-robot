#!/usr/bin/env python3
"""Fresh independent recheck of every selected saved sequence; recounts cases, occurrences and connectors from files.

Every case of the output keeps its row. Blocked, incomplete, not-run and
unselected cases are counted separately and never as a pass or as agreement;
a selection retained from an earlier output is rechecked there, not here.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

from sign_robot.pair_contract import atomic_json, file_hash, inside, json_hash, read_json
from sign_robot.sequence_contract import load_sequence_policy, read_sequence
from sign_robot.sequence_verification import verify_saved_sequence_v1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    run_dir = args.run_dir.resolve()
    manifest = read_json(run_dir / "manifest.json")
    policy, _ = load_sequence_policy(ROOT, manifest["sequence_policy"])
    if file_hash(ROOT / manifest["sequence_policy"]) != manifest["sequence_policy_sha256"]:
        raise SystemExit("Sequence policy changed since planning")
    destination = run_dir / "independent_recheck"
    if destination.exists():
        raise SystemExit("Recheck already exists; it is never overwritten")
    summary = read_json(run_dir / "summary.json")
    destination.mkdir()
    rows = []
    for case in summary["cases"]:
        row = {"sequence_id": case["sequence_id"], "planning_status": case["status"], "selected_attempt": case["selected_attempt"],
               "recheck": "NOT_APPLICABLE"}
        local = case["selected_attempt"] and inside(ROOT, case.get("selected_output") or str(run_dir.relative_to(ROOT))) == run_dir
        if case["selected_attempt"] and not local:
            row["recheck"] = "RETAINED_FROM_PRIOR_OUTPUT"
            row["selected_output"] = case["selected_output"]
        elif case["selected_attempt"]:
            path = run_dir / "sequences" / case["sequence_id"] / f"{case['selected_attempt']}.json"
            sequence = read_sequence(path, policy)
            evidence = verify_saved_sequence_v1(ROOT, path, manifest["sequence_policy"])
            atomic_json(destination / f"{case['sequence_id']}.json", {"schema_version": 1, "sequence_file_sha256": file_hash(path),
                        "evidence": evidence, "evidence_hash": json_hash(evidence)})
            protected = evidence.get("protected_instance_checks", [])
            row.update(recheck="DONE", numerical_checks_passed=evidence["numerical_checks_passed"],
                       validation_complete=evidence["validation_complete"],
                       status=evidence["status"], reason_codes=evidence["reason_codes"],
                       word_occurrences=len(sequence["word_instances"]), connector_groups=len(sequence["edges"]),
                       protected_instances_unchanged=sum(c["poses_bitwise_equal"] and c["replay_grid_poses_bitwise_equal"]
                                                         and c["max_relative_timing_error_s"] <= policy["validation"]["protected_relative_timing_tolerance_s"]
                                                         for c in protected),
                       max_relative_timing_error_s=max((c["max_relative_timing_error_s"] for c in protected), default=None),
                       min_clearance_mm=evidence.get("min_clearance_mm"),
                       agrees_with_planning=evidence["numerical_checks_passed"] is (case["numerical_checks_passed"] is True))
        rows.append(row)
        print(json.dumps({k: row.get(k) for k in ("sequence_id", "planning_status", "recheck", "agrees_with_planning")}), flush=True)
    rechecked = [r for r in rows if r["recheck"] == "DONE"]
    planning = Counter(r["planning_status"] for r in rows)
    totals = {"cases": len(rows), "rechecked": len(rechecked),
              "numerical_pass": sum(r.get("numerical_checks_passed") is True for r in rechecked),
              "retained_from_prior_output": sum(r["recheck"] == "RETAINED_FROM_PRIOR_OUTPUT" for r in rows),
              "rechecked_agree": sum(r.get("agrees_with_planning") is True for r in rechecked),
              "planning_status_counts": dict(sorted(planning.items())),
              "word_occurrences": sum(r.get("word_occurrences", 0) for r in rechecked),
              "protected_instances_unchanged": sum(r.get("protected_instances_unchanged", 0) for r in rechecked),
              "connector_groups": sum(r.get("connector_groups", 0) for r in rechecked),
              "all_agree_with_planning": bool(rows) and len(rechecked) == len(rows)
                                         and all(r.get("agrees_with_planning") is True for r in rechecked),
              "formal_pass": 0}
    atomic_json(destination / "summary.json", {"schema_version": 1, "rows": rows, "totals": totals})
    print(json.dumps(totals), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
