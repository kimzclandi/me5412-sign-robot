#!/usr/bin/env python3
"""Assemble frozen multi-word cases from one independently verified pair run, then verify each saved chain.

Each case first checks its pair dependencies (not planned, planning or review
unfinished, no numerical candidate) and is recorded as BLOCKED_DEPENDENCY
instead of stopping the run; a stale or corrupt pair run still stops
everything. Soft budgets (per case including verification, per invocation wall
clock, free disk), an operator stop file or SIGTERM, and a fresh identity
check are consulted before each attempt: unstarted cases stay NOT_RUN and an
interrupted attempt is never selected. --resume-from reads
earlier outputs of the same identity: their passing selections are retained,
their completely verified attempts are not repeated and all files stay.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import shutil
import signal
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

GIB = 1024 ** 3


def _relative(path):
    return str(Path(path).resolve().relative_to(ROOT))


def prior_attempts(prior_outputs, case):
    """Completely verified attempts of one case in earlier outputs, keyed by combination index."""
    found = {}
    for directory in prior_outputs:
        folder = directory / "sequences" / case
        for path in sorted(folder.glob("attempt_*.verification.json")) if folder.is_dir() else []:
            envelope = read_json(path)
            sequence_path = folder / envelope["sequence_file"]
            if (file_hash(sequence_path) != envelope["sequence_file_sha256"]
                    or json_hash(envelope["evidence"]) != envelope["evidence_hash"]):
                raise ValueError(f"Earlier attempt evidence changed: {path}")
            if envelope["evidence"]["validation_complete"] is not True:
                continue  # Incomplete reviews are retried; the earlier files stay as history.
            index = int(path.name.split(".")[0].split("_")[1])
            if index in found:
                raise ValueError(f"Attempt {index} of {case} was completed twice; refusing to choose one")
            found[index] = {"output": _relative(directory), "attempt": f"attempt_{index:04d}",
                            "numerical_checks_passed": envelope["evidence"]["numerical_checks_passed"],
                            "sequence_file_sha256": envelope["sequence_file_sha256"],
                            "verification_sha256": file_hash(path)}
    return found


def run_case(case, *, policy, policy_path, pools, states, implementation, folder, prior, budget, case_budget_s,
             clock=time.monotonic):
    glosses = sequence_glosses(case, policy)
    edges = [f"{a}__{b}" for a, b in zip(glosses, glosses[1:])]
    record = {"sequence_id": case, "word_count": len(glosses), "attempts": [], "selected_attempt": None,
              "selected_output": None, "status": "NOT_RUN", "numerical_checks_passed": None,
              "formal_status": "NOT_ENABLED", "dependencies": {edge: states[edge] for edge in edges}}
    blocked = sorted({states[edge] for edge in edges if states[edge] != "READY"})
    if blocked:
        record.update(status="BLOCKED_DEPENDENCY", blocking_reasons=blocked)
        return record, None
    passed = sorted(index for index, entry in prior.items() if entry["numerical_checks_passed"] is True)
    if passed:
        entry = prior[passed[0]]
        record.update(status="NUMERICAL_PASS", numerical_checks_passed=True, selected_attempt=entry["attempt"],
                      selected_output=entry["output"], retained_from_prior_output=True)
        return record, None
    started = clock()
    stop = None
    for number, ranks in enumerate(combinations(pools, edges, policy["assembly"]["max_combinations_per_case"]), 1):
        name = f"attempt_{number:04d}"
        entry = {"attempt": name, "ranks": list(ranks),
                 "pair_attempts": [pools[e][r]["attempt_id"] for e, r in zip(edges, ranks)]}
        if number in prior:
            entry.update(status="PRIOR_VERIFIED_NO_PASS", processed_in=prior[number]["output"])
            record["attempts"].append(entry)
            continue
        stop = budget.stop_reason()
        if stop:
            record.update(status="INCOMPLETE_SOFT_BUDGET", stop_reason=stop)
            break
        if clock() - started >= case_budget_s:
            record.update(status="INCOMPLETE_CASE_BUDGET", stop_reason="CASE_BUDGET_REACHED")
            break
        try:
            sequence = assemble_sequence(case, [pools[e][r] for e, r in zip(edges, ranks)],
                                         policy=policy, sequence_identity=implementation)
        except SequenceAssemblyError as exc:
            entry.update(status="ASSEMBLY_REJECTED", reason_codes=[exc.code], details=str(exc.details))
            record["attempts"].append(entry)
            continue
        folder.mkdir(parents=True, exist_ok=True)
        save_sequence(folder / f"{name}.json", sequence, policy)
        evidence = verify_saved_sequence_v1(ROOT, folder / f"{name}.json", policy_path)
        atomic_json(folder / f"{name}.verification.json", {"schema_version": 1, "sequence_file": f"{name}.json",
                    "sequence_file_sha256": file_hash(folder / f"{name}.json"), "evidence": evidence,
                    "evidence_hash": json_hash(evidence)})
        entry.update(status=evidence["status"], numerical_checks_passed=evidence["numerical_checks_passed"],
                     validation_complete=evidence["validation_complete"], reason_codes=evidence["reason_codes"])
        record["attempts"].append(entry)
        if evidence["numerical_checks_passed"] is True:
            record.update(selected_attempt=name, selected_output=_relative(folder.parents[1]), status="NUMERICAL_PASS",
                          numerical_checks_passed=True)
            break
        if not evidence["validation_complete"]:
            record.update(status="INCOMPLETE_" + evidence["status"], numerical_checks_passed=None)
            break
    else:
        record.update(status="NO_NUMERICAL_PASS_WITHIN_COMBINATION_BUDGET", numerical_checks_passed=False)
    record["wall_time_s"] = clock() - started
    return record, stop


class Budget:
    """Invocation wall clock, free-disk floor and operator stop, checked before each attempt only."""

    def __init__(self, wall_time_s, min_free_bytes, path, stop_file=None, drift=None, clock=time.monotonic):
        self.wall_time_s, self.min_free_bytes, self.path, self.clock = wall_time_s, min_free_bytes, path, clock
        self.stop_file = None if stop_file is None else Path(stop_file)
        self.drift = drift or (lambda: None)
        self.requested = False
        self.started = clock()

    def stop_reason(self):
        if self.requested or (self.stop_file is not None and self.stop_file.exists()):
            return "STOP_REQUESTED"
        if self.clock() - self.started >= self.wall_time_s:
            return "SOFT_WALL_TIME_REACHED"
        if shutil.disk_usage(self.path).free < self.min_free_bytes:
            return "DISK_FREE_BELOW_FLOOR"
        return self.drift()


def summarize(records, stop, budgets):
    counts = Counter(r["status"] for r in records)
    blocked = Counter(reason for r in records for reason in r.get("blocking_reasons", []))
    return {"schema_version": 1, "cases": records, "denominator": len(records),
            "numerical_pass_count": sum(r["numerical_checks_passed"] is True for r in records),
            "status_counts": dict(sorted(counts.items())), "blocked_reason_counts": dict(sorted(blocked.items())),
            "not_run_count": counts["NOT_RUN"], "stop_reason": stop, "budgets": budgets,
            "formal_pass_count": 0, "formal_acceptance_enabled": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sequence-policy", default="config/sequence_policy_user_protected_v1.json")
    parser.add_argument("--pair-run-dir", type=Path, action="append", required=True,
                        help="Pair run of the same identity; may repeat when the pairs were split over runs "
                             "(each pair is read from the one run that planned it)")
    parser.add_argument("--output", type=Path, required=True, help="New directory; never reused")
    parser.add_argument("--case", action="append", dest="cases", help="Sequence id from the frozen policy; may repeat")
    parser.add_argument("--case-budget-s", type=float, default=600.0, help="Soft per-case budget, planning plus verification")
    parser.add_argument("--soft-wall-time-s", type=float, default=7200.0)
    parser.add_argument("--min-free-gib", type=float, default=5.0)
    parser.add_argument("--stop-file", type=Path, help="Graceful stop at the next attempt once this file exists")
    parser.add_argument("--resume-from", type=Path, action="append", default=[],
                        help="Earlier output of the same identity, in order; read only")
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
    run_dirs = [path.resolve() for path in args.pair_run_dir]
    if len(set(run_dirs)) != len(run_dirs):
        parser.error("Each pair run may be given once")
    heads = {}
    for run_dir in run_dirs:
        manifest = read_json(run_dir / "manifest.json")
        if manifest["identity"] != identity:
            raise SystemExit("Pair run identity differs from current code/inputs; use a fresh pair run")
        heads[run_dir] = set(manifest["heads"])
    implementation = sequence_identity(ROOT, policy, library, identity)
    pair_ids = sorted({f"{a}__{b}" for case in cases for a, b in zip(sequence_glosses(case, policy), sequence_glosses(case, policy)[1:])})
    if len(run_dirs) == 1:
        run_dir = run_dirs[0]
        pools, states = load_candidate_pools(ROOT, run_dir, pair_ids, require_all=False)
    else:
        owners = {p: [r for r in run_dirs if p in heads[r]] for p in pair_ids}
        if any(len(found) > 1 for found in owners.values()):
            raise SystemExit("A pair was planned in more than one run: " + ", ".join(p for p, f in owners.items() if len(f) > 1))
        pools, states = {}, {}
        for owner in run_dirs:
            mine = [p for p in pair_ids if owners[p] == [owner]]
            if mine:
                found, found_states = load_candidate_pools(ROOT, owner, mine, require_all=False)
                pools.update(found)
                states.update(found_states)
        states.update({p: "PAIR_NOT_PLANNED" for p in pair_ids if not owners[p]})
        run_dir = None
    pool_summary = {p: [{k: c[k] for k in ("attempt_id", "candidate_file", "candidate_file_sha256")} for c in pool]
                    for p, pool in pools.items()}
    run_label = _relative(run_dir) if run_dir is not None else [_relative(r) for r in run_dirs]
    priors = [path.resolve() for path in args.resume_from]
    for prior in priors:
        earlier = read_json(prior / "manifest.json")
        if (earlier["sequence_policy_sha256"] != file_hash(ROOT / args.sequence_policy) or earlier["pair_identity"] != identity
                or earlier["sequence_identity"] != implementation or earlier["pair_run_dir"] != run_label
                or any(earlier["candidate_pools"].get(p, pool) != pool for p, pool in pool_summary.items())):
            raise SystemExit(f"Resume source differs in identity or candidate pools: {prior}")
    budgets = {"case_budget_s": args.case_budget_s, "soft_wall_time_s": args.soft_wall_time_s,
               "min_free_bytes": int(args.min_free_gib * GIB), "hard_real_time_abort": False,
               "max_combinations_per_case": policy["assembly"]["max_combinations_per_case"]}
    output.mkdir(parents=True)
    checkpoint = {case: prior_attempts(priors, case) for case in cases}
    atomic_json(output / "manifest.json", {
        "schema_version": 1, "sequence_policy": args.sequence_policy,
        "sequence_policy_sha256": file_hash(ROOT / args.sequence_policy), "pair_policy_sha256": policy["pair_policy"]["sha256"],
        "pair_run_dir": run_label, "pair_identity": identity, "sequence_identity": implementation,
        "environment": library["environment"], "cases": cases, "pair_dependency_states": states,
        "candidate_pools": pool_summary, "budgets": budgets,
        "resume_from": [{"output": _relative(p), "manifest_sha256": file_hash(p / "manifest.json")} for p in priors],
        "checkpoint_processed_attempts": {c: {str(i): e for i, e in v.items()} for c, v in checkpoint.items() if v}})
    def drift():
        current, _ = freeze_library(ROOT, pair_policy)
        fresh = run_identity(current, pair_policy)
        if fresh != identity or sequence_identity(ROOT, policy, current, fresh) != implementation:
            return "IDENTITY_CHANGED_DURING_RUN"
        return None

    budget = Budget(args.soft_wall_time_s, budgets["min_free_bytes"], output, stop_file=args.stop_file, drift=drift)
    signal.signal(signal.SIGTERM, lambda *_: setattr(budget, "requested", True))
    records, stop = [], None
    for case in cases:
        if stop:
            glosses = sequence_glosses(case, policy)
            records.append({"sequence_id": case, "word_count": len(glosses), "attempts": [], "selected_attempt": None,
                            "selected_output": None, "status": "NOT_RUN", "numerical_checks_passed": None,
                            "formal_status": "NOT_ENABLED", "not_run_reason": stop})
            continue
        record, stop = run_case(case, policy=policy, policy_path=args.sequence_policy, pools=pools, states=states,
                                implementation=implementation, folder=output / "sequences" / case,
                                prior=checkpoint[case], budget=budget, case_budget_s=args.case_budget_s)
        records.append(record)
        print(json.dumps({k: record[k] for k in ("sequence_id", "status", "selected_attempt")}
                         | {"attempts": len(record["attempts"])}), flush=True)
    summary = summarize(records, stop, budgets)
    atomic_json(output / "summary.json", summary)
    print(json.dumps({"denominator": summary["denominator"], "numerical_pass_count": summary["numerical_pass_count"],
                      "status_counts": summary["status_counts"], "stop_reason": stop}), flush=True)
    return 0 if stop is None else 3


if __name__ == "__main__":
    raise SystemExit(main())
