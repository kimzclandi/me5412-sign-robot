#!/usr/bin/env python3
"""Assemble frozen multi-word cases from one independently verified pair run, then verify each saved chain."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

from sign_robot.pair_contract import atomic_json, file_hash, freeze_library, json_hash, read_json, run_identity
from sign_robot.sequence_assembly import SequenceAssemblyError, assemble_sequence, combinations, load_candidate_pools
from sign_robot.sequence_contract import load_sequence_policy, save_sequence, sequence_glosses, sequence_identity
from sign_robot.sequence_verification import verify_saved_sequence_v1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sequence-policy", default="config/sequence_policy_user_protected_v1.json")
    parser.add_argument("--pair-run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New directory; never reused")
    parser.add_argument("--case", action="append", dest="cases", help="Sequence id from the frozen policy; may repeat")
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if output.exists():
        parser.error("Output exists; choose a new output path")
    policy, pair_policy = load_sequence_policy(ROOT, args.sequence_policy)
    cases = args.cases or policy["cases"]
    if any(case not in policy["cases"] for case in cases) or len(set(cases)) != len(cases):
        parser.error("Cases must be unique members of the frozen policy")
    library, _ = freeze_library(ROOT, pair_policy)
    identity = run_identity(library, pair_policy)
    run_dir = args.pair_run_dir.resolve()
    if read_json(run_dir / "manifest.json")["identity"] != identity:
        raise SystemExit("Pair run identity differs from current code/inputs; use a fresh pair run")
    implementation = sequence_identity(ROOT, policy, library, identity)
    pair_ids = sorted({f"{a}__{b}" for case in cases for a, b in zip(sequence_glosses(case, policy), sequence_glosses(case, policy)[1:])})
    pools = load_candidate_pools(ROOT, run_dir, pair_ids)
    output.mkdir(parents=True)
    atomic_json(output / "manifest.json", {
        "schema_version": 1, "sequence_policy": args.sequence_policy,
        "sequence_policy_sha256": file_hash(ROOT / args.sequence_policy), "pair_policy_sha256": policy["pair_policy"]["sha256"],
        "pair_run_dir": str(run_dir.relative_to(ROOT)), "pair_identity": identity, "sequence_identity": implementation,
        "environment": library["environment"], "cases": cases,
        "candidate_pools": {p: [{k: c[k] for k in ("attempt_id", "candidate_file", "candidate_file_sha256")} for c in pool]
                            for p, pool in pools.items()}})
    records = []
    for case in cases:
        glosses = sequence_glosses(case, policy)
        edges = [f"{a}__{b}" for a, b in zip(glosses, glosses[1:])]
        folder = output / "sequences" / case
        folder.mkdir(parents=True)
        record = {"sequence_id": case, "word_count": len(glosses), "attempts": [], "selected_attempt": None,
                  "status": "NOT_RUN", "numerical_checks_passed": None, "formal_status": "NOT_ENABLED"}
        started = time.monotonic()
        for number, ranks in enumerate(combinations(pools, edges, policy["assembly"]["max_combinations_per_case"]), 1):
            name = f"attempt_{number:04d}"
            entry = {"attempt": name, "ranks": list(ranks),
                     "pair_attempts": [pools[e][r]["attempt_id"] for e, r in zip(edges, ranks)]}
            try:
                sequence = assemble_sequence(case, [pools[e][r] for e, r in zip(edges, ranks)],
                                             policy=policy, sequence_identity=implementation)
            except SequenceAssemblyError as exc:
                entry.update(status="ASSEMBLY_REJECTED", reason_codes=[exc.code], details=str(exc.details))
                record["attempts"].append(entry)
                continue
            save_sequence(folder / f"{name}.json", sequence, policy)
            evidence = verify_saved_sequence_v1(ROOT, folder / f"{name}.json", args.sequence_policy)
            atomic_json(folder / f"{name}.verification.json", {"schema_version": 1, "sequence_file": f"{name}.json",
                        "sequence_file_sha256": file_hash(folder / f"{name}.json"), "evidence": evidence,
                        "evidence_hash": json_hash(evidence)})
            entry.update(status=evidence["status"], numerical_checks_passed=evidence["numerical_checks_passed"],
                         validation_complete=evidence["validation_complete"], reason_codes=evidence["reason_codes"])
            record["attempts"].append(entry)
            if evidence["numerical_checks_passed"] is True:
                record.update(selected_attempt=name, status="NUMERICAL_PASS", numerical_checks_passed=True)
                break
            if not evidence["validation_complete"]:
                record.update(status="INCOMPLETE_" + evidence["status"], numerical_checks_passed=None)
                break
        else:
            record.update(status="NO_NUMERICAL_PASS_WITHIN_COMBINATION_BUDGET", numerical_checks_passed=False)
        record["wall_time_s"] = time.monotonic() - started
        records.append(record)
        print(json.dumps({k: record[k] for k in ("sequence_id", "status", "selected_attempt")}
                         | {"attempts": len(record["attempts"])}), flush=True)
    passed = sum(r["numerical_checks_passed"] is True for r in records)
    atomic_json(output / "summary.json", {"schema_version": 1, "cases": records, "denominator": len(records),
                                          "numerical_pass_count": passed, "formal_pass_count": 0,
                                          "formal_acceptance_enabled": False})
    print(json.dumps({"denominator": len(records), "numerical_pass_count": passed}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
