#!/usr/bin/env python3
"""Frozen, exploratory text-selection evaluation. No ASL or clinical claims.

Uses only the public select_action API. Results are append-only per run directory.
The default does not invoke an LLM or any remote service.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Attribution only: these are the frozen public reason codes of the shared
# guard. They do not change selection, labels, thresholds, or scoring.
GUARD_REASONS = {
    "empty_input", "input_too_long", "english_only", "negated_or_declining",
    "clinical_content_out_of_scope", "reported_or_metalinguistic",
    "multiple_or_compound_intents", "conditional_input", "waiting_role_mismatch",
    "qualified_wait_out_of_scope", "gratitude_recipient_out_of_scope",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_cases(path: Path, expected_sha256: str) -> list[dict]:
    """Read only a pre-frozen dataset; reject corruption and duplicate IDs."""
    if sha256(path) != expected_sha256:
        raise ValueError(f"Frozen dataset hash mismatch: {path.name}")
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not cases:
        raise ValueError("Empty dataset")
    if len({x["case_id"] for x in cases}) != len(cases):
        raise ValueError("Duplicate case IDs")
    for case in cases:
        if not isinstance(case["text"], str) or not case["text"].strip():
            raise ValueError("Empty or invalid text")
        if case["expected_action_id"] is None:
            if case["expected_status"] not in {"clarify", "unsupported"}:
                raise ValueError("Out-of-scope case must not expect execution")
        elif case["expected_status"] != "execute":
            raise ValueError("Supported case must expect execution")
        if case.get("label_status") != "agent_draft_unreviewed":
            raise ValueError("This protocol requires explicit draft-label provenance")
    return cases


def is_correct(case: dict, prediction: dict) -> bool:
    if case["expected_action_id"] is not None:
        return (prediction["status"] == "execute"
                and prediction["action_id"] == case["expected_action_id"])
    return prediction["status"] in {"clarify", "unsupported"}


def fraction(numerator: int, denominator: int) -> dict:
    return {"numerator": numerator, "denominator": denominator,
            "value": numerator / denominator if denominator else None}


def percentile_nearest_rank(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(p * len(ordered)) - 1)]


def execution_path(method: str, prediction: dict) -> str:
    """Use per-call HTTP evidence; a reason-code prefix is not proof of a call."""
    audit = prediction.get("metadata")
    if method == "llm" and isinstance(audit, dict):
        if audit.get("request_attempted") is True:
            return ("llm_http_response" if audit.get("response_received") is True
                    else "llm_http_attempt_without_response")
        return "llm_backend_before_http"
    if (prediction.get("reason_code") in GUARD_REASONS
            and prediction.get("status") in {"clarify", "unsupported"}):
        return "shared_guard"
    return "llm_unattributed_no_http_evidence" if method == "llm" else method + "_backend"


def latency_summary(values: list[float]) -> dict:
    return {"median": statistics.median(values) if values else None,
            "p95_nearest_rank": percentile_nearest_rank(values, .95),
            "max": max(values) if values else None}


def summarize(records: list[dict]) -> dict:
    """Count failures without treating abstention or runtime errors as success."""
    n = len(records)
    supported = [r for r in records if r["expected_action_id"] is not None]
    unsupported = [r for r in records if r["expected_action_id"] is None]
    executed = [r for r in records if r["prediction"]["status"] == "execute"]
    correct = sum(r["correct"] for r in records)
    supported_correct = sum(r["correct"] for r in supported)
    rejected_supported = sum(r["prediction"]["status"] in {"clarify", "unsupported"}
                             for r in supported)
    wrong_supported_execution = sum(r["prediction"]["status"] == "execute" and not r["correct"]
                                    for r in supported)
    wrong_out_execution = sum(r["prediction"]["status"] == "execute" for r in unsupported)
    errors = sum(r["prediction"]["status"] == "error" for r in records)
    latency = [r["wall_latency_ms"] for r in records]
    confusion: dict[str, Counter] = {}
    categories = {}
    for r in records:
        expected = r["expected_action_id"] or "REJECT"
        pred = r["prediction"]
        actual = (pred["action_id"] if pred["status"] == "execute"
                  else "ERROR" if pred["status"] == "error" else "REJECT")
        confusion.setdefault(expected, Counter())[actual] += 1
        group = categories.setdefault(r["category"], {"total": 0, "correct": 0})
        group["total"] += 1
        group["correct"] += int(r["correct"])
    return {
        "n": n, "n_supported": len(supported), "n_unsupported": len(unsupported),
        "accuracy": fraction(correct, n),
        "supported_correct_selection_rate": fraction(supported_correct, len(supported)),
        "supported_wrong_rejection_rate": fraction(rejected_supported, len(supported)),
        "supported_wrong_execution_rate": fraction(wrong_supported_execution, len(supported)),
        "unsupported_false_execution_rate": fraction(wrong_out_execution, len(unsupported)),
        "execution_coverage": fraction(len(executed), n),
        "execution_precision": fraction(sum(r["correct"] for r in executed), len(executed)),
        "runtime_error_rate": fraction(errors, n),
        "strict_status_match_rate": fraction(sum(r["prediction"]["status"] == r["expected_status"]
                                                  for r in records), n),
        "latency_ms": latency_summary(latency),
        "confusion": {key: dict(value) for key, value in confusion.items()},
        "by_category": categories,
        "reason_counts": dict(Counter(r["prediction"]["reason_code"] for r in records)),
        "execution_path_counts": dict(Counter(r.get("execution_path", "unattributed") for r in records)),
        "llm_call_audit": {
            "http_attempted": fraction(sum(r.get("execution_path") in {
                "llm_http_response", "llm_http_attempt_without_response"} for r in records), n),
            "http_response_received": fraction(sum(r.get("execution_path") == "llm_http_response"
                                                   for r in records), n),
            "response_subset_accuracy": fraction(sum(r["correct"] for r in records
                if r.get("execution_path") == "llm_http_response"),
                sum(r.get("execution_path") == "llm_http_response" for r in records)),
            "response_subset_selector_latency_ms": latency_summary([
                r["wall_latency_ms"] for r in records if r.get("execution_path") == "llm_http_response"]),
            "interpretation": "HTTP counts exclude readiness. Response subset is conditioned on passing the shared guard; not isolated or representative LLM quality.",
        },
        "method_interpretation": "Whole selector including shared heuristic guard; not isolated model quality.",
    }


def evaluate_method(cases: list[dict], method: str, catalog: list[dict], selector) -> dict:
    from sign_robot.contracts import validate_selection

    # This positive catalog alias bypasses the heuristic guard, so a missing
    # backend cannot look successful merely by rejecting negative test inputs.
    probe_text = catalog[0]["aliases"][0]
    started = time.perf_counter()
    try:
        readiness = selector(probe_text, method=method, catalog=catalog)
        validate_selection(readiness, catalog)
    except Exception as exc:
        readiness = {"status": "error", "action_id": None, "method": method,
                     "reason_code": "readiness_exception", "exception_type": type(exc).__name__}
    cold_ms = (time.perf_counter() - started) * 1000
    if readiness["status"] == "error":
        return {"status": "not_run", "reason": readiness["reason_code"],
                "readiness": readiness, "readiness_wall_ms": cold_ms,
                "records": [], "metrics": None}
    records = []
    for case in cases:
        started = time.perf_counter()
        try:
            prediction = selector(case["text"], method=method, catalog=catalog)
            validate_selection(prediction, catalog)
            if prediction.get("method") != method or not isinstance(prediction.get("reason_code"), str):
                raise ValueError("Invalid method or reason_code")
        except Exception as exc:
            prediction = {"status": "error", "action_id": None, "method": method,
                          "reason_code": "selector_exception", "exception_type": type(exc).__name__}
        wall_ms = (time.perf_counter() - started) * 1000
        records.append({**case, "method": method, "prediction": prediction,
                        "execution_path": execution_path(method, prediction),
                        "wall_latency_ms": wall_ms, "correct": is_correct(case, prediction)})
    return {"status": "completed", "readiness": readiness, "readiness_wall_ms": cold_ms,
            "metrics": summarize(records), "records": records}


def selected_llm_config() -> dict:
    override = os.environ.get("SIGN_ROBOT_LLM_CONFIG")
    path = Path(override) if override else ROOT / "config/llm.json"
    if not path.is_absolute():
        path = ROOT / path
    path = path.resolve()
    if path.suffix != ".json" or not path.is_relative_to((ROOT / "config").resolve()):
        raise ValueError("Selected LLM config must be inside project config/")
    return {"path": str(path.relative_to(ROOT.resolve())),
            "sha256": sha256(path) if path.is_file() else None,
            "explicit_research_override": override is not None}


def artifact_hashes() -> dict:
    paths = ["data/catalog.json", "data/source_manifest.json", "scripts/evaluate.py",
             "src/sign_robot/language.py", "src/sign_robot/llm.py", "src/sign_robot/contracts.py",
             "config/embedding.json", "config/llm.json", "config/embedding_download_manifest.json",
             "config/llm_local_provenance.json", "config/llm_local_feasibility_v1.json",
             "config/llm_local_feasibility_v2_label.json", "config/llm_development_audit.json",
             selected_llm_config()["path"]]
    return {p: sha256(ROOT / p) for p in paths if (ROOT / p).is_file()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("dev", "test"), default="test")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--run-reason", default="首次冻结协议的独立评价",
                        help="Record why this new evaluation is run; previous result directories stay intact.")
    parser.add_argument("--include-llm", action="store_true",
                        help="Evaluate an already configured local-only LLM; never remote APIs.")
    args = parser.parse_args(argv)
    manifest = json.loads((ROOT / "data/source_manifest.json").read_text(encoding="utf-8"))
    protocol = manifest["evaluation"]
    dataset = ROOT / f"data/eval_{args.split}.jsonl"
    cases = load_cases(dataset, protocol[f"{args.split}_sha256"])
    from sign_robot.contracts import load_catalog
    from sign_robot.language import select_action
    catalog = load_catalog()
    legal = {x["action_id"] for x in catalog}
    if any(c["expected_action_id"] is not None and c["expected_action_id"] not in legal for c in cases):
        raise ValueError("Expected action is absent from catalog")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = args.output_dir or ROOT / "results/evaluation" / f"{args.split}-{stamp}"
    output.mkdir(parents=True, exist_ok=False)
    before = artifact_hashes()
    llm_config_before = selected_llm_config()
    summary = {"schema_version": 1, "protocol": protocol, "split": args.split,
               "run_reason": args.run_reason,
               "dataset_sha256": sha256(dataset), "started_at_utc": stamp,
               "environment": {"python": platform.python_version(), "system": platform.system(),
                               "machine": platform.machine()},
               "source_hashes": before, "selected_llm_config": llm_config_before,
               "llm_enabled_for_this_run": args.include_llm, "methods": {},
               "limitations": ["Agent-written labels; not human-reviewed or population-representative.",
                               "Selection of candidate IDs only; no ASL or clinical validation.",
                               "Same heuristic guard precedes all methods; results include its behavior.",
                               "Readiness/cold loading reported separately from warm dataset calls."]}
    if llm_config_before["explicit_research_override"]:
        summary["limitations"].append(
            "Explicit research-only LLM config: " + llm_config_before["path"] +
            "; the unchanged v2 backend failed its 3/3 development enablement gate (2/3 correct). "
            "This comparison does not accept it for default use; config/llm.json remains unconfigured.")
    with (output / "raw.jsonl").open("x", encoding="utf-8") as raw, (output / "counterexamples.jsonl").open("x", encoding="utf-8") as failures:
        for method in ("exact", "embedding", "llm"):
            if method == "llm" and not args.include_llm:
                summary["methods"][method] = {"status": "not_run", "reason": "llm_not_enabled",
                                               "metrics": None}
                continue
            result = evaluate_method(cases, method, catalog, select_action)
            records = result.pop("records")
            summary["methods"][method] = result
            for record in records:
                line = json.dumps(record, ensure_ascii=False) + "\n"
                raw.write(line)
                if not record["correct"]:
                    failures.write(line)
            raw.flush()
            failures.flush()
    after = artifact_hashes()
    summary["source_hashes_after"] = after
    summary["selected_llm_config_after"] = selected_llm_config()
    summary["selected_llm_config_unchanged_during_run"] = (
        llm_config_before == summary["selected_llm_config_after"])
    summary["sources_unchanged_during_run"] = before == after
    summary["dataset_unchanged_during_run"] = sha256(dataset) == protocol[f"{args.split}_sha256"]
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output_dir": str(output), "dataset_sha256": summary["dataset_sha256"],
                      "methods": {k: {"status": v["status"], "reason": v.get("reason"),
                                       "accuracy": v["metrics"]["accuracy"] if v.get("metrics") else None}
                                  for k, v in summary["methods"].items()}}, ensure_ascii=False, indent=2))
    return 0 if (summary["sources_unchanged_during_run"] and summary["dataset_unchanged_during_run"]
                 and summary["selected_llm_config_unchanged_during_run"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
