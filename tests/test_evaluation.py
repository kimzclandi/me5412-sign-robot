"""Evaluation integrity: failure denominators, freeze and backend availability."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("evaluate_module", ROOT / "scripts/evaluate.py")
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


def record(aid, status, pred_id=None):
    case = {"expected_action_id": aid, "expected_status": "execute" if aid else "unsupported",
            "category": "synthetic_test", "wall_latency_ms": 1.0}
    prediction = {"status": status, "action_id": pred_id, "reason_code": "test"}
    return {**case, "prediction": prediction, "correct": evaluation.is_correct(case, prediction)}


def test_metrics_separate_execution_rejection_and_runtime_failure():
    rows = [record("HELLO", "execute", "HELLO"), record("HELLO", "unsupported"),
            record("HELLO", "error"), record(None, "execute", "HELLO"),
            record(None, "clarify"), record(None, "error")]
    result = evaluation.summarize(rows)
    assert result["accuracy"] == {"numerator": 2, "denominator": 6, "value": 1 / 3}
    assert result["supported_wrong_rejection_rate"]["numerator"] == 1
    assert result["unsupported_false_execution_rate"]["value"] == 1 / 3
    assert result["execution_precision"]["value"] == .5
    assert result["runtime_error_rate"]["value"] == 1 / 3
    assert result["confusion"]["REJECT"]["ERROR"] == 1


def test_reject_everything_cannot_claim_perfect_coverage_or_precision():
    metrics = evaluation.summarize([record("HELLO", "unsupported"), record(None, "unsupported")])
    assert metrics["accuracy"]["value"] == .5
    assert metrics["execution_coverage"]["value"] == 0
    assert metrics["execution_precision"]["value"] is None


def test_frozen_data_rejects_any_mutation(tmp_path):
    path = tmp_path / "cases.jsonl"
    case = {"case_id": "dummy", "text": "example", "expected_action_id": None,
            "expected_status": "unsupported", "label_status": "agent_draft_unreviewed"}
    path.write_text(json.dumps(case) + "\n")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert len(evaluation.load_cases(path, digest)) == 1
    path.write_text(path.read_text() + "\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        evaluation.load_cases(path, digest)


def test_unavailable_backend_does_not_score_guarded_cases():
    calls = []
    def missing(text, method, catalog):
        calls.append(text)
        return {"status": "error", "action_id": None, "reason_code": "llm_unavailable"}
    result = evaluation.evaluate_method([{"text": "negative case"}], "llm",
                                         [{"action_id": "HELLO", "aliases": ["hello"]}], missing)
    assert calls == ["hello"]
    assert result["status"] == "not_run"
    assert result["metrics"] is None
    assert not result["records"]


def test_invalid_selector_output_is_an_error_not_a_correct_rejection():
    calls = 0
    def bad(text, method, catalog):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"status": "execute", "action_id": "HELLO", "reason_code": "ready", "method": method}
        return {"status": "unsupported", "action_id": "HELLO", "reason_code": "bad", "method": method}
    cases = [{"text": "out of scope", "expected_action_id": None,
              "expected_status": "unsupported", "category": "dummy"}]
    result = evaluation.evaluate_method(cases, "exact", [{"action_id": "HELLO", "aliases": ["hello"]}], bad)
    assert result["metrics"]["accuracy"]["value"] == 0
    assert result["metrics"]["runtime_error_rate"]["value"] == 1


def test_protocol_hashes_counts_and_normalized_split_disjointness():
    # Validate split integrity without asserting any final-set model outputs.
    import re
    manifest = json.loads((ROOT / "data/source_manifest.json").read_text())["evaluation"]
    splits = {split: evaluation.load_cases(ROOT / f"data/eval_{split}.jsonl", manifest[f"{split}_sha256"])
              for split in ("dev", "test")}
    assert len(splits["dev"]) == 18
    assert len(splits["test"]) == 60
    def key(text):
        return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()
    normalized = {split: {key(row["text"]) for row in rows} for split, rows in splits.items()}
    assert normalized["dev"].isdisjoint(normalized["test"])
    for split, rows in splits.items():
        assert len(normalized[split]) == len(rows)
    assert sum(r["expected_action_id"] is not None for r in splits["test"]) == 30


def test_http_attribution_requires_per_call_evidence_not_reason_prefix():
    assert evaluation.execution_path("llm", {
        "status": "unsupported", "reason_code": "negated_or_declining"}) == "shared_guard"
    assert evaluation.execution_path("llm", {
        "status": "error", "reason_code": "llm_unavailable"}) == "llm_unattributed_no_http_evidence"
    assert evaluation.execution_path("llm", {
        "metadata": {"request_attempted": False, "response_received": False}}) == "llm_backend_before_http"
    assert evaluation.execution_path("llm", {
        "metadata": {"request_attempted": True, "response_received": False}}) == "llm_http_attempt_without_response"
    assert evaluation.execution_path("llm", {
        "metadata": {"request_attempted": True, "response_received": True}}) == "llm_http_response"


def test_evaluation_preserves_raw_llm_output_and_excludes_guard_from_call_count():
    def selector(text, method, catalog):
        if text == "guarded":
            return {"status": "unsupported", "action_id": None, "method": method,
                    "reason_code": "negated_or_declining"}
        return {"status": "execute", "action_id": "HELLO", "method": method,
                "reason_code": "llm_selection", "metadata": {
                    "request_attempted": True, "response_received": True,
                    "raw_model_output": "HELLO", "response_sha256": "example"}}
    cases = [{"text": "positive", "expected_action_id": "HELLO", "expected_status": "execute",
              "category": "dummy"},
             {"text": "guarded", "expected_action_id": None, "expected_status": "unsupported",
              "category": "dummy"}]
    result = evaluation.evaluate_method(cases, "llm", [{"action_id": "HELLO", "aliases": ["hello"]}], selector)
    assert result["readiness"]["metadata"]["raw_model_output"] == "HELLO"
    assert result["records"][0]["prediction"]["metadata"]["response_sha256"] == "example"
    assert result["metrics"]["llm_call_audit"]["http_attempted"]["numerator"] == 1
    assert result["metrics"]["llm_call_audit"]["http_attempted"]["denominator"] == 2
    assert result["metrics"]["llm_call_audit"]["response_subset_accuracy"]["denominator"] == 1


def test_selected_research_config_is_hashed_and_confined(monkeypatch, tmp_path):
    monkeypatch.setattr(evaluation, "ROOT", tmp_path)
    config = tmp_path / "config"
    config.mkdir()
    (config / "llm.json").write_text("{}", encoding="utf-8")
    selected = config / "research.json"
    selected.write_text('{"status":"research"}', encoding="utf-8")
    monkeypatch.setenv("SIGN_ROBOT_LLM_CONFIG", "config/research.json")
    identity = evaluation.selected_llm_config()
    assert identity["path"] == "config/research.json"
    assert identity["sha256"] == evaluation.artifact_hashes()["config/research.json"]
    selected.write_text('{"status":"changed"}', encoding="utf-8")
    assert evaluation.selected_llm_config()["sha256"] != identity["sha256"]
    monkeypatch.setenv("SIGN_ROBOT_LLM_CONFIG", "../outside.json")
    with pytest.raises(ValueError, match="inside project"):
        evaluation.selected_llm_config()
