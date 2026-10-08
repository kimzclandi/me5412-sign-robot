#!/usr/bin/env python3
"""Read-only reanalysis of saved decisions; never imports or invokes a selector.

Input: raw.jsonl [N methods x K cases] and the corresponding summary.json.
Output: independently aggregated counts, checks against the summary, hashes,
representative failures, and PNG/SVG figures. Existing output is never replaced.
Plotting only: install matplotlib==3.10.7 in a separate environment if needed.
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

ROOT = Path(__file__).resolve().parents[1]
METHODS = ("exact", "embedding", "llm")
DEFAULT_RUN = ROOT / "results/evaluation/test-20261008T142047221403Z"
SUPPORT_KEYS = ("correct_selection", "wrong_rejection", "wrong_action_id", "error")
OUTSIDE_KEYS = ("correct_rejection", "false_execution", "error")
COLORS = {"correct": "#237F73", "rejected": "#AAB4C3", "wrong_id": "#D05B50",
          "false_execution": "#D68D24", "error": "#8068B0"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def correctness(row: dict) -> bool:
    prediction = row["prediction"]
    if row["expected_action_id"] is None:
        return prediction["status"] in {"unsupported", "clarify"}
    return (prediction["status"] == "execute"
            and prediction["action_id"] == row["expected_action_id"])


def outcome(row: dict) -> str:
    status = row["prediction"]["status"]
    if status == "error":
        return "error"
    if row["expected_action_id"] is None:
        return "false_execution" if status == "execute" else "correct_rejection"
    if status in {"unsupported", "clarify"}:
        return "wrong_rejection"
    return "correct_selection" if correctness(row) else "wrong_action_id"


def validate_rows(rows: list[dict]) -> None:
    """Reject duplicates, divergent case labels, stale correctness and false HTTP claims."""
    if not rows:
        raise ValueError("No saved records")
    identities, cases = set(), {}
    by_method = {method: set() for method in METHODS}
    for row in rows:
        method, case_id, pred = row["method"], row["case_id"], row["prediction"]
        if method not in METHODS or pred.get("method") != method:
            raise ValueError("Unexpected or inconsistent method")
        identity = (method, case_id)
        if identity in identities:
            raise ValueError("Duplicate method/case record")
        identities.add(identity)
        by_method[method].add(case_id)
        case = {key: row[key] for key in ("text", "expected_action_id", "expected_status", "category", "label_status")}
        if case_id in cases and cases[case_id] != case:
            raise ValueError("Different labels/text for the same case")
        cases[case_id] = case
        status = pred["status"]
        if status not in {"execute", "unsupported", "clarify", "error"}:
            raise ValueError("Unknown prediction status")
        if (status == "execute") != (pred.get("action_id") is not None):
            raise ValueError("Prediction action/status mismatch")
        if row["correct"] is not correctness(row):
            raise ValueError("Saved correctness disagrees with raw prediction")
        if row["wall_latency_ms"] < 0 or not math.isfinite(row["wall_latency_ms"]):
            raise ValueError("Invalid saved latency")
        if method == "llm":
            audit = pred.get("metadata", {})
            path = row["execution_path"]
            if path == "llm_http_response" and not (
                audit.get("request_attempted") is True and audit.get("response_received") is True
            ):
                raise ValueError("HTTP path lacks per-call evidence")
            if path == "shared_guard" and audit.get("request_attempted"):
                raise ValueError("Guard path also claims an HTTP call")
    if not all(by_method[method] == by_method[METHODS[0]] for method in METHODS):
        raise ValueError("Methods do not contain identical case IDs")


def ratio(numerator: int, denominator: int) -> dict:
    return {"numerator": numerator, "denominator": denominator,
            "value": numerator / denominator if denominator else None}


def latencies(rows: list[dict]) -> dict:
    values = sorted(row["wall_latency_ms"] for row in rows)
    return {"median": statistics.median(values) if values else None,
            "p95_nearest_rank": values[math.ceil(.95 * len(values)) - 1] if values else None,
            "max": max(values) if values else None}


def aggregate(rows: list[dict]) -> dict:
    """Compute disjoint outcome counts directly from status/action IDs."""
    supported = [r for r in rows if r["expected_action_id"] is not None]
    outside = [r for r in rows if r["expected_action_id"] is None]
    supported_counts = {key: sum(outcome(r) == key for r in supported) for key in SUPPORT_KEYS}
    outside_counts = {key: sum(outcome(r) == key for r in outside) for key in OUTSIDE_KEYS}
    executed = [r for r in rows if r["prediction"]["status"] == "execute"]
    received = [r for r in rows if r["prediction"].get("metadata", {}).get("response_received") is True]
    attempted = [r for r in rows if r["prediction"].get("metadata", {}).get("request_attempted") is True]
    confusion, categories = {}, {}
    for row in rows:
        expected = row["expected_action_id"] or "REJECT"
        pred = row["prediction"]
        actual = pred["action_id"] if pred["status"] == "execute" else (
            "ERROR" if pred["status"] == "error" else "REJECT")
        confusion.setdefault(expected, Counter())[actual] += 1
        category = categories.setdefault(row["category"], {"total": 0, "correct": 0})
        category["total"] += 1
        category["correct"] += int(correctness(row))
    return {
        "n": len(rows), "n_supported": len(supported), "n_unsupported": len(outside),
        "supported": supported_counts, "out_of_scope": outside_counts,
        "accuracy": ratio(sum(correctness(r) for r in rows), len(rows)),
        "supported_correct_selection_rate": ratio(supported_counts["correct_selection"], len(supported)),
        "supported_wrong_rejection_rate": ratio(supported_counts["wrong_rejection"], len(supported)),
        "supported_wrong_execution_rate": ratio(supported_counts["wrong_action_id"], len(supported)),
        "unsupported_false_execution_rate": ratio(outside_counts["false_execution"], len(outside)),
        "execution_coverage": ratio(len(executed), len(rows)),
        "execution_precision": ratio(sum(correctness(r) for r in executed), len(executed)),
        "runtime_error_rate": ratio(supported_counts["error"] + outside_counts["error"], len(rows)),
        "strict_status_match_rate": ratio(sum(r["prediction"]["status"] == r["expected_status"] for r in rows), len(rows)),
        "latency_ms": latencies(rows), "confusion": {k: dict(v) for k, v in confusion.items()},
        "by_category": categories, "reason_counts": dict(Counter(r["prediction"]["reason_code"] for r in rows)),
        "execution_path_counts": dict(Counter(r["execution_path"] for r in rows)),
        "llm_call_audit": {
            "http_attempted": ratio(len(attempted), len(rows)),
            "http_response_received": ratio(len(received), len(rows)),
            "response_subset_accuracy": ratio(sum(correctness(r) for r in received), len(received)),
            "response_subset_selector_latency_ms": latencies(received),
        },
    }


def verify_summary(methods: dict, summary: dict) -> dict:
    """Check every numeric/count field reproduced here, not the source prose."""
    comparisons = 0
    def compare(actual, expected, path):
        nonlocal comparisons
        if isinstance(actual, dict):
            extra = set(expected) - set(actual) - {"interpretation"}
            if extra:
                raise ValueError(f"Unexpected summary fields: {path}: {sorted(extra)}")
            for key, value in actual.items():
                if key not in expected:
                    raise ValueError(f"Missing summary field: {path}.{key}")
                compare(value, expected[key], f"{path}.{key}")
        else:
            comparisons += 1
            equal = (math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)
                     if isinstance(actual, float) and isinstance(expected, (int, float))
                     else actual == expected)
            if not equal:
                raise ValueError(f"Raw/summary mismatch at {path}: {actual!r} != {expected!r}")
    for method, metrics in methods.items():
        if summary["methods"][method]["status"] != "completed":
            raise ValueError(f"Method {method} was not completed")
        compare({k: v for k, v in metrics.items() if k not in {"supported", "out_of_scope"}},
                {k: v for k, v in summary["methods"][method]["metrics"].items()
                 if k != "method_interpretation"}, method)
    return {"all_recomputed_fields_match": True, "leaf_comparisons": comparisons,
            "readiness_excluded_from_dataset_counts": True}


def representative_failures(rows: list[dict]) -> list[dict]:
    # Fixed rule, not best-looking examples: the lowest case ID in each failure
    # type/path, plus both out-of-scope false executions for the local LLM.
    groups = [("exact", "wrong_rejection", None), ("embedding", "wrong_rejection", None),
              ("llm", "wrong_action_id", None), ("llm", "wrong_rejection", "shared_guard"),
              ("llm", "wrong_rejection", "llm_http_response"), ("llm", "error", None),
              ("llm", "false_execution", None)]
    selected = []
    for method, failure, path in groups:
        candidates = sorted((r for r in rows if r["method"] == method and outcome(r) == failure
                             and (path is None or r["execution_path"] == path)), key=lambda r: r["case_id"])
        for row in candidates if failure == "false_execution" else candidates[:1]:
            selected.append({"selection_rule": "Lowest case ID for this method/outcome/path; all LLM out-of-scope false executions.",
                             "outcome": failure, "source_row": row})
    return selected


def protected_hashes(run: Path) -> dict:
    paths = set(p for p in (ROOT / "results/evaluation").rglob("*") if p.is_file())
    paths.update(p for p in (ROOT / "data").rglob("*") if p.is_file())
    paths.update(p for p in (ROOT / "config").glob("*.json") if p.is_file())
    paths.update([ROOT / "contracts/interfaces.json", ROOT / "scripts/evaluate.py"])
    paths.update(p for p in run.rglob("*") if p.is_file())
    return {str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p): digest(p)
            for p in sorted(paths)}


def chart_payload(methods: dict, llm_paths: dict) -> dict:
    return {
        "method_labels": ["Exact + guard", "MiniLM + guard", "Local LLM + guard"],
        "supported": {"denominator_per_method": [methods[m]["n_supported"] for m in METHODS],
                      "series": {k: [methods[m]["supported"][k] for m in METHODS] for k in SUPPORT_KEYS}},
        "out_of_scope": {"denominator_per_method": [methods[m]["n_unsupported"] for m in METHODS],
                         "series": {k: [methods[m]["out_of_scope"][k] for m in METHODS] for k in OUTSIDE_KEYS}},
        "llm_paths": llm_paths,
    }


def plot_figures(charts: dict, output: Path) -> dict:
    os.environ.setdefault("MPLCONFIGDIR", str(output / ".matplotlib-cache"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    matplotlib.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                                "svg.fonttype": "none", "savefig.facecolor": "white"})

    def stacked(filename, title, labels, series, legend, colors, denominator, note):
        fig, ax = plt.subplots(figsize=(10.8, 5.3), layout="constrained")
        left = [0] * len(labels)
        for values, label, color in zip(series, legend, colors):
            bars = ax.barh(labels, values, left=left, label=label, color=color, height=.55,
                           edgecolor="white", linewidth=.7)
            for bar, value in zip(bars, values):
                if value:
                    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_y() + bar.get_height() / 2,
                            str(value), ha="center", va="center", color="black", fontsize=11, fontweight="bold")
            left = [a + b for a, b in zip(left, values)]
        ax.invert_yaxis()
        ax.set_xlim(0, denominator)
        ax.set_xticks(range(0, denominator + 1, 5))
        ax.set_xlabel("Number of saved test cases")
        ax.set_title(title, loc="left", fontsize=15, weight="bold", pad=18)
        ax.xaxis.grid(True, color="#D7DCE2", alpha=.6)
        ax.set_axisbelow(True)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.legend(loc="upper left", bbox_to_anchor=(0, -.18), ncol=2 if len(legend) > 4 else 4,
                  frameon=False, fontsize=10)
        bottom = .11 if len(legend) > 4 else .06
        fig.get_layout_engine().set(rect=(0, bottom, 1, 1 - bottom))
        fig.text(.02, .018, note, fontsize=9, color="#46515F", va="bottom")
        for extension in ("png", "svg"):
            fig.savefig(output / f"{filename}.{extension}", dpi=200)
        plt.close(fig)

    supported = charts["supported"]["series"]
    stacked("supported_outcomes", "Supported meanings: correct choice versus missed or invalid output",
            charts["method_labels"], [supported[k] for k in SUPPORT_KEYS],
            ["Correct ID", "Wrong rejection", "Wrong ID", "Error / invalid output"],
            [COLORS[k] for k in ("correct", "rejected", "wrong_id", "error")], 30,
            "30 supported cases per method. Agent-written labels, not human reviewed. Same frozen inputs and shared guard.")
    outside = charts["out_of_scope"]["series"]
    stacked("out_of_scope_outcomes", "Out-of-scope meanings: correct rejection versus false execution",
            charts["method_labels"], [outside[k] for k in OUTSIDE_KEYS],
            ["Correct rejection", "False execution", "Error / invalid output"],
            [COLORS[k] for k in ("correct", "false_execution", "error")], 30,
            "30 out-of-scope cases per method. Zero observed errors in this small set is not evidence of zero population risk.")
    paths = charts["llm_paths"]
    groups = [paths[k] for k in ("shared_guard", "llm_http_response")]
    series = [[g["correct"] for g in groups]] + [[g["outcomes"].get(k, 0) for g in groups]
              for k in ("wrong_rejection", "wrong_action_id", "false_execution", "error")]
    stacked("llm_execution_paths", "Local LLM selector: separate rule decisions from actual model calls",
            ["Shared guard (no LLM call)", "Actual HTTP response"], series,
            ["Correct ID or rejection", "Wrong rejection", "Wrong ID", "False execution", "Error / invalid output"],
            [COLORS[k] for k in ("correct", "rejected", "wrong_id", "false_execution", "error")], 35,
            "25 guard cases; 35 actual HTTP responses. One readiness request is excluded.\nDifferent case mix: these groups do not estimate isolated or comparable model accuracy.")
    return {"matplotlib": matplotlib.__version__, "backend": "Agg", "labels": "English", "dpi": 200}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/analysis/frozen-test-final")
    args = parser.parse_args(argv)
    run, output = args.run_dir.resolve(), args.output_dir.resolve()
    if output == run or output.is_relative_to(ROOT / "results/evaluation"):
        raise ValueError("Analysis cannot be written into protected evaluation results")
    before = protected_hashes(run)
    rows = [json.loads(line) for line in (run / "raw.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    summary = read_json(run / "summary.json")
    validate_rows(rows)
    methods = {m: aggregate([r for r in rows if r["method"] == m]) for m in METHODS}
    check = verify_summary(methods, summary)
    if digest(ROOT / "data/eval_test.jsonl") != summary["dataset_sha256"]:
        raise ValueError("Current frozen test bytes differ from evaluated dataset")
    llm_rows = [r for r in rows if r["method"] == "llm"]
    llm_paths = {}
    for path in sorted({r["execution_path"] for r in llm_rows}):
        subset = [r for r in llm_rows if r["execution_path"] == path]
        llm_paths[path] = {"n": len(subset), "correct": sum(correctness(r) for r in subset),
                           "outcomes": dict(Counter(outcome(r) for r in subset)),
                           "supported": sum(r["expected_action_id"] is not None for r in subset),
                           "out_of_scope": sum(r["expected_action_id"] is None for r in subset),
                           "case_ids": [r["case_id"] for r in subset]}
    charts = chart_payload(methods, llm_paths)
    output.mkdir(parents=True, exist_ok=False)
    plotting = plot_figures(charts, output)
    after = protected_hashes(run)
    if before != after:
        raise RuntimeError("Protected input bytes changed during analysis")
    analysis = {
        "schema_version": 1, "analysis_kind": "read_only_reanalysis_without_inference",
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "source_run": str(run.relative_to(ROOT)),
        "raw_rows": len(rows), "unique_test_cases": len({r["case_id"] for r in rows}),
        "method_order": list(METHODS), "methods": methods, "llm_paths": llm_paths,
        "chart_data": charts, "summary_validation": check,
        "protected_inputs_unchanged": True, "protected_input_hashes": before,
        "analysis_script_sha256": digest(Path(__file__)),
        "representative_failures": representative_failures(rows),
        "environment": {"python": platform.python_version(), **plotting},
        "limitations": [
            "All 60 labels are agent_draft_unreviewed; no human or population validity claim.",
            "No inference rerun, new data, threshold change, prompt change, or significance test.",
            "Three selectors share heuristic guards; HTTP subset is conditioned on passing them.",
            "LLM default enablement gate remains failed; research comparison does not accept deployment.",
            "English-to-candidate selection is separate from ASL meaning, robot geometry and user comprehension.",
        ],
    }
    analysis["figure_hashes"] = {p.name: digest(p) for p in sorted(output.iterdir()) if p.suffix in {".png", ".svg"}}
    (output / "analysis.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output_dir": str(output), "raw_rows": len(rows), "summary_validation": check,
                      "protected_inputs_unchanged": True}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
