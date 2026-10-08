"""Read-only analysis must not conceal model errors or mutate protected inputs."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("analysis_module", ROOT / "scripts/analyze_evaluation.py")
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def row(method="exact", case_id="synthetic-1", expected="HELLO", status="execute", actual="HELLO"):
    result = {"method": method, "case_id": case_id, "text": "synthetic example",
              "expected_action_id": expected, "expected_status": "execute" if expected else "unsupported",
              "category": "synthetic", "label_status": "agent_draft_unreviewed",
              "prediction": {"status": status, "action_id": actual, "method": method, "reason_code": "synthetic"},
              "execution_path": method + "_backend", "wall_latency_ms": 1.0}
    result["correct"] = analysis.correctness(result)
    return result


def test_outcomes_separate_wrong_id_rejection_error_and_false_execution():
    rows = [row(), row(case_id="b", status="clarify", actual=None),
            row(case_id="c", actual="THANK_YOU"), row(case_id="d", status="error", actual=None),
            row(case_id="e", expected=None), row(case_id="f", expected=None, status="error", actual=None),
            row(case_id="g", expected=None, status="unsupported", actual=None)]
    metrics = analysis.aggregate(rows)
    assert metrics["supported"] == {"correct_selection": 1, "wrong_rejection": 1, "wrong_action_id": 1, "error": 1}
    assert metrics["out_of_scope"] == {"correct_rejection": 1, "false_execution": 1, "error": 1}
    assert metrics["accuracy"] == {"numerator": 2, "denominator": 7, "value": 2 / 7}
    assert metrics["execution_precision"]["value"] == 1 / 3


def test_duplicate_or_changed_labels_are_rejected():
    rows = [row(method=m) for m in analysis.METHODS]
    with pytest.raises(ValueError, match="Duplicate"):
        analysis.validate_rows(rows + [rows[0]])
    rows[1]["text"] = "changed"
    with pytest.raises(ValueError, match="Different labels/text"):
        analysis.validate_rows(rows)


def test_stale_correctness_and_unproven_http_are_rejected():
    rows = [row(method=m) for m in analysis.METHODS]
    rows[0]["correct"] = False
    with pytest.raises(ValueError, match="Saved correctness"):
        analysis.validate_rows(rows)
    rows[0]["correct"] = True
    rows[2]["execution_path"] = "llm_http_response"
    with pytest.raises(ValueError, match="lacks per-call evidence"):
        analysis.validate_rows(rows)


def test_summary_mismatch_cannot_be_silently_accepted():
    methods = {m: analysis.aggregate([row(method=m)]) for m in analysis.METHODS}
    summary = {"methods": {m: {"status": "completed", "metrics": {
        k: v for k, v in deepcopy(methods[m]).items() if k not in {"supported", "out_of_scope"}}}
        for m in analysis.METHODS}}
    assert analysis.verify_summary(methods, summary)["all_recomputed_fields_match"]
    summary["methods"]["llm"]["metrics"]["accuracy"]["numerator"] = 0
    with pytest.raises(ValueError, match="Raw/summary mismatch"):
        analysis.verify_summary(methods, summary)


def test_current_frozen_evidence_recomputes_and_remains_byte_identical():
    run = analysis.DEFAULT_RUN
    before = analysis.protected_hashes(run)
    rows = [json.loads(x) for x in (run / "raw.jsonl").read_text(encoding="utf-8").splitlines()]
    analysis.validate_rows(rows)
    metrics = {m: analysis.aggregate([r for r in rows if r["method"] == m]) for m in analysis.METHODS}
    assert len(rows) == 180
    assert analysis.verify_summary(metrics, analysis.read_json(run / "summary.json"))["all_recomputed_fields_match"]
    assert metrics["llm"]["execution_path_counts"] == {"llm_http_response": 35, "shared_guard": 25}
    assert analysis.protected_hashes(run) == before
