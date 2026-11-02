#!/usr/bin/env python3
"""Single-writer, soft-budget driver for frozen hospital35 pair batches and sequence sub-batches.

pairs          plan then independently review frozen pair batches (<=16 pairs) in one run
recheck-pairs  fresh verify_saved_pair_v2 of every selected candidate into a new directory
sequences      plan and recheck one frozen sequence sub-batch (<=8 cases) into its registered output
aggregate      merge registered sequence outputs into a fixed-denominator table

Budgets are checked only at saved breakpoints, so a stop is soft. Creating
<control-dir>/<run-id>.stop (or sequences.stop), or sending SIGTERM, requests a
graceful stop at the next breakpoint. Every invocation appends a new log with
command, limits, resources and exit code.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

from sign_robot.batch_control import (
    GIB, BatchControlError, SingleWriterLock, SoftBudget, load_batch_manifest, resource_record, run_pair_batch,
    write_new_log,
)
from sign_robot.pair_contract import freeze_library, inside, load_policy, pair_universe, run_directory, run_identity
from sign_robot.sequence_batches import SequenceBatchError, aggregate, load_case_manifest, next_output


def pairs_command(args):
    policy = load_policy(inside(ROOT, args.policy), supported_versions=(2,))
    universe = [p["pair_id"] for p in pair_universe(policy["scope"]["expected_glosses"])]
    manifest, batches = load_batch_manifest(ROOT, args.batch_manifest, args.batch_manifest_sha256, universe, args.policy)
    requested = args.batches or manifest["order"]
    if any(batch not in batches for batch in requested):
        raise BatchControlError("UNKNOWN_BATCH", [b for b in requested if b not in batches])
    limits = manifest["limits"]
    wall = args.soft_wall_time_s or limits["soft_wall_time_s"]
    floor = (args.min_free_gib if args.min_free_gib is not None else limits["min_free_gib"]) * GIB
    control = inside(ROOT, args.control_dir)
    results_root = inside(ROOT, args.results_root)
    from sign_robot.pair_routes import build_pair_context_v2
    from sign_robot.pair_runner_v2 import V2RunStore
    stop_signal = []
    signal.signal(signal.SIGTERM, lambda *_: stop_signal.append(True))
    with SingleWriterLock(control / f"{args.run_id}.lock"):
        context = build_pair_context_v2(ROOT, policy)
        if context.input_blockers:
            write_new_log(control / "pair_global_blockers", {"command": sys.argv, "blockers": context.input_blockers,
                                                             "exit_code": 4})
            print(json.dumps({"status": "GLOBAL_INPUT_BLOCKED", "blockers": context.input_blockers}), flush=True)
            return 4
        run_dir = run_directory(results_root, args.run_id)
        store = V2RunStore.create(ROOT, policy, context, results_root, args.run_id, resume=run_dir.exists())

        def drift():
            library, _ = freeze_library(ROOT, policy)
            return None if run_identity(library, policy) == store.manifest["identity"] else "IDENTITY_CHANGED_DURING_RUN"

        exit_code = 0
        for batch_id in requested:
            # The soft wall clock and disk floor apply to each batch separately.
            budget = SoftBudget(wall, floor, ROOT, stop_file=control / f"{args.run_id}.stop",
                                requested=lambda: bool(stop_signal), drift=drift)
            started, before = time.monotonic(), resource_record(ROOT)
            result = run_pair_batch(store, context, batches[batch_id], budget=budget, seed_base=policy["planner"]["seed"])
            summary = store.summarize()
            exit_code = 0 if result["stop_reason"] == "BATCH_COMPLETE" else 3
            log = {"schema_version": 1, "batch_id": batch_id, "group": batches[batch_id]["group"], "run_id": args.run_id,
                   "identity": store.manifest["identity"], "command": sys.argv, "limits": budget.record(),
                   "batch_manifest_sha256": args.batch_manifest_sha256, "resources_before": before,
                   "resources_after": resource_record(ROOT), "wall_time_s": time.monotonic() - started, **result,
                   "run_scanned": summary["groups"]["all"]["scanned"], "run_verified_records": summary["verified_records"],
                   "run_numerical_pass_count": summary.get("executed_development_scope", {}).get("numerical_pass_count"),
                   "formal_acceptance_enabled": False, "playback_eligible": False, "exit_code": exit_code}
            path = write_new_log(control / "pair_batches" / batch_id, log)
            print(json.dumps({"batch": batch_id, "stop_reason": result["stop_reason"], "log": str(path.relative_to(ROOT)),
                              "selected": sum(s.get("selected_candidate_id") is not None for s in result["pairs"]),
                              "pairs": len(result["pairs"])}), flush=True)
            if exit_code:
                break
        return exit_code


def sequences_command(args):
    from sign_robot.sequence_contract import load_sequence_policy
    import importlib.util
    policy, _ = load_sequence_policy(ROOT, args.sequence_policy)
    manifest = load_case_manifest(ROOT, args.case_manifest, args.case_manifest_sha256, policy["cases"])
    if manifest["sequence_policy"]["path"] != args.sequence_policy:
        raise BatchControlError("CASE_MANIFEST_POLICY_MISMATCH", manifest["sequence_policy"])
    subbatch = next((s for s in manifest["subbatches"] if s["subbatch_id"] == args.subbatch), None)
    if subbatch is None:
        raise BatchControlError("UNKNOWN_SUBBATCH", args.subbatch)
    limits = manifest["limits"]
    control = inside(ROOT, args.control_dir)
    with SingleWriterLock(control / f"sequences_{Path(args.case_manifest).stem}.lock"):
        chain, output = next_output(ROOT, subbatch)
        started, before = time.monotonic(), resource_record(ROOT)
        command = ["--sequence-policy", args.sequence_policy, "--pair-run-dir", manifest["pair_run_dir"],
                   "--output", str(output.relative_to(ROOT)), "--case-budget-s", str(limits["case_budget_s"]),
                   "--soft-wall-time-s", str(limits["soft_wall_time_s"]), "--min-free-gib", str(limits["min_free_gib"]),
                   "--stop-file", str((control / "sequences.stop").relative_to(ROOT))]
        for case in subbatch["cases"]:
            command += ["--case", case]
        for earlier in chain:
            command += ["--resume-from", str(earlier.relative_to(ROOT))]

        def script(name):
            spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

        planned = script("plan_sequences").main(command)
        rechecked = script("verify_sequences").main(["--run-dir", str(output.relative_to(ROOT))])
        exit_code = planned or rechecked
        log = {"schema_version": 1, "subbatch_id": args.subbatch, "output": str(output.relative_to(ROOT)),
               "resume_from": [str(p.relative_to(ROOT)) for p in chain], "command": sys.argv, "plan_arguments": command,
               "limits": limits, "resources_before": before, "resources_after": resource_record(ROOT),
               "wall_time_s": time.monotonic() - started, "plan_exit_code": planned, "recheck_exit_code": rechecked,
               "exit_code": exit_code, "formal_acceptance_enabled": False}
        write_new_log(control / "sequence_subbatches" / args.subbatch, log)
        return exit_code


def recheck_pairs_command(args):
    """Fresh verify_saved_pair_v2 of each selected candidate into a new directory; saved reviews are not reused."""
    from sign_robot.pair_contract import atomic_json, file_hash, json_hash, read_json
    from sign_robot.pair_runner_v2 import V2RunStore
    from sign_robot.pair_verification_v2 import verify_saved_pair_v2
    run_dir = inside(ROOT, args.run_dir)
    output = inside(ROOT, args.output)
    if output.exists():
        raise BatchControlError("OUTPUT_EXISTS", args.output)
    store = V2RunStore.load(ROOT, run_dir)
    pairs = args.pairs or sorted(store.manifest["heads"])
    output.mkdir(parents=True)
    rows = []
    for pair_id in pairs:
        record = store._head_record(pair_id)
        selected = None if record is None else record["selected_candidate_id"]
        row = {"pair_id": pair_id, "selected_candidate_id": selected,
               "verification_state": None if record is None else record["verification_state"]}
        if selected is not None:
            entry = next(a for a in record["attempts"] if a["attempt_id"] == selected)
            path = inside(run_dir, entry["candidate_file"])
            evidence = verify_saved_pair_v2(ROOT, path, store.policy)
            saved = read_json(run_dir / "verification" / pair_id / f"{selected}.json")["evidence"]
            atomic_json(output / f"{pair_id}.json", {"schema_version": 1, "identity": store.manifest["identity"],
                        "candidate_file": entry["candidate_file"], "candidate_hash": file_hash(path),
                        "evidence": evidence, "evidence_hash": json_hash(evidence)})
            row.update(candidate_hash=file_hash(path), fresh_numerical_checks_passed=evidence["numerical_checks_passed"],
                       fresh_validation_complete=evidence["validation_complete"],
                       saved_numerical_checks_passed=saved["numerical_checks_passed"],
                       agrees_with_saved_review=evidence["numerical_checks_passed"] is saved["numerical_checks_passed"]
                       and evidence.get("metrics") == saved.get("metrics"),
                       protected_instances=[{k: c[k] for k in ("instance_id", "source_frames", "poses_bitwise_equal",
                                                                "max_relative_timing_error_s")}
                                            for c in evidence.get("protected_instance_checks", [])],
                       min_clearance_mm=evidence.get("min_clearance_mm"), metrics=evidence.get("metrics"))
        rows.append(row)
        print(json.dumps({k: row.get(k) for k in ("pair_id", "selected_candidate_id", "fresh_numerical_checks_passed",
                                                  "agrees_with_saved_review")}), flush=True)
    summary = {"schema_version": 1, "run_id": store.manifest["run_id"], "identity": store.manifest["identity"], "rows": rows,
               "selected": sum(r["selected_candidate_id"] is not None for r in rows),
               "fresh_numerical_pass": sum(r.get("fresh_numerical_checks_passed") is True for r in rows),
               "all_selected_agree": all(r.get("agrees_with_saved_review", True) for r in rows),
               "formal_pass_count": 0, "formal_acceptance_enabled": False}
    atomic_json(output / "summary.json", summary)
    return 0 if summary["all_selected_agree"] else 1


def aggregate_command(args):
    from sign_robot.sequence_contract import load_sequence_policy
    policy, _ = load_sequence_policy(ROOT, args.sequence_policy)
    manifest = load_case_manifest(ROOT, args.case_manifest, args.case_manifest_sha256, policy["cases"])
    result = aggregate(ROOT, manifest)
    result["case_manifest_sha256"] = args.case_manifest_sha256
    path = write_new_log(inside(ROOT, manifest["aggregate_directory"]), result)
    print(json.dumps({"aggregate": str(path.relative_to(ROOT)), "totals": {k: {"denominator": v["denominator"],
                      "independently_rechecked_pass": v["independently_rechecked_pass"], "status_counts": v["status_counts"]}
                      for k, v in result["totals"].items()}}, ensure_ascii=False), flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    pairs = commands.add_parser("pairs", help="Frozen pair batches in one single-writer run")
    pairs.add_argument("--policy", default="config/transition_policy_user_protected_hospital35_v1.json")
    pairs.add_argument("--batch-manifest", required=True)
    pairs.add_argument("--batch-manifest-sha256", required=True)
    pairs.add_argument("--batch", action="append", dest="batches", help="Batch id in manifest order; may repeat")
    pairs.add_argument("--run-id", required=True)
    pairs.add_argument("--results-root", required=True)
    pairs.add_argument("--control-dir", required=True, help="Locks and invocation logs, outside the run directory")
    pairs.add_argument("--soft-wall-time-s", type=float)
    pairs.add_argument("--min-free-gib", type=float)
    recheck = commands.add_parser("recheck-pairs", help="Fresh independent recheck of selected pair candidates")
    recheck.add_argument("--run-dir", required=True)
    recheck.add_argument("--output", required=True, help="New directory; never reused")
    recheck.add_argument("--pair", action="append", dest="pairs")
    for name in ("sequences", "aggregate"):
        sub = commands.add_parser(name)
        sub.add_argument("--sequence-policy", required=True)
        sub.add_argument("--case-manifest", required=True)
        sub.add_argument("--case-manifest-sha256", required=True)
        if name == "sequences":
            sub.add_argument("--subbatch", required=True)
            sub.add_argument("--control-dir", required=True)
    args = parser.parse_args(argv)
    try:
        return {"pairs": pairs_command, "recheck-pairs": recheck_pairs_command, "sequences": sequences_command,
                "aggregate": aggregate_command}[args.command](args)
    except (BatchControlError, SequenceBatchError) as exc:
        print(json.dumps({"status": "REFUSED", "code": exc.code, "details": str(exc.details)}, ensure_ascii=False), flush=True)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
