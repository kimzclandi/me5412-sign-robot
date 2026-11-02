"""Per-case dependency blocking, soft sequence budgets, resume checkpoints and fixed-denominator aggregation."""
import importlib.util
import json

import pytest

from sign_robot.motion import ROOT
from sign_robot.pair_contract import file_hash, json_hash
from sign_robot.sequence_assembly import dependency_state
from sign_robot.sequence_batches import SequenceBatchError, aggregate, load_case_manifest, next_output, output_chain
from sign_robot.sequence_contract import load_sequence_policy


def script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


plan = script("plan_sequences")
POLICY_PATH = "config/sequence_policy_user_protected_v1.json"


@pytest.mark.parametrize("record,state", [
    (None, "PAIR_NOT_PLANNED"),
    ({"completed": False, "verification_state": "NOT_RUN", "selected_candidate_id": None}, "PAIR_PLANNING_INCOMPLETE"),
    ({"completed": True, "verification_state": "NOT_RUN", "selected_candidate_id": None}, "PAIR_VERIFICATION_INCOMPLETE"),
    ({"completed": True, "verification_state": "COMPLETE", "selected_candidate_id": None}, "PAIR_NO_NUMERICAL_CANDIDATE"),
    ({"completed": True, "verification_state": "DIAGNOSIS_ONLY", "selected_candidate_id": None}, "PAIR_NO_NUMERICAL_CANDIDATE"),
    ({"completed": True, "verification_state": "COMPLETE", "selected_candidate_id": "attempt_00003"}, "READY"),
])
def test_dependency_states_distinguish_missing_unfinished_and_failed_pairs(record, state):
    assert dependency_state(record) == state


class Stop:
    def __init__(self, reason=None):
        self.reason = reason

    def stop_reason(self):
        return self.reason


def _case(case, states, tmp_path, *, budget=None, prior=None, case_budget_s=600, clock=None):
    policy, _ = load_sequence_policy(ROOT, POLICY_PATH)
    pools = {pair: [{"attempt_id": "attempt_00001"}] for pair, state in states.items() if state == "READY"}
    return plan.run_case(case, policy=policy, policy_path=POLICY_PATH, pools=pools, states=states, implementation={},
                         folder=tmp_path / "sequences" / case, prior=prior or {}, budget=budget or Stop(),
                         case_budget_s=case_budget_s, **({"clock": clock} if clock else {}))


def test_blocked_edge_records_reasons_without_attempts_or_files(tmp_path):
    record, stop = _case("COME__NOW__COME", {"COME__NOW": "READY", "NOW__COME": "PAIR_NO_NUMERICAL_CANDIDATE"}, tmp_path)
    assert stop is None and record["status"] == "BLOCKED_DEPENDENCY"
    assert record["blocking_reasons"] == ["PAIR_NO_NUMERICAL_CANDIDATE"] and record["attempts"] == []
    assert record["numerical_checks_passed"] is None and not (tmp_path / "sequences").exists()


def test_soft_and_case_budgets_stop_before_an_attempt_and_select_nothing(tmp_path):
    ready = {"COME__NOW": "READY", "NOW__COME": "READY"}
    record, stop = _case("COME__NOW__COME", ready, tmp_path, budget=Stop("DISK_FREE_BELOW_FLOOR"))
    assert stop == "DISK_FREE_BELOW_FLOOR" and record["status"] == "INCOMPLETE_SOFT_BUDGET"
    assert record["selected_attempt"] is None and not (tmp_path / "sequences").exists()
    ticks = iter([0.0, 700.0, 700.0])
    record, stop = _case("COME__NOW__COME", ready, tmp_path, case_budget_s=600, clock=lambda: next(ticks))
    assert stop is None and record["status"] == "INCOMPLETE_CASE_BUDGET" and record["selected_attempt"] is None


def test_prior_pass_is_retained_and_prior_failures_are_not_repeated(tmp_path):
    ready = {"COME__NOW": "READY", "NOW__COME": "READY"}
    prior = {1: {"output": "results/x", "attempt": "attempt_0001", "numerical_checks_passed": True}}
    record, _ = _case("COME__NOW__COME", ready, tmp_path, prior=prior)
    assert record["status"] == "NUMERICAL_PASS" and record["retained_from_prior_output"] is True
    assert record["selected_output"] == "results/x" and record["selected_attempt"] == "attempt_0001"
    failed = {1: {"output": "results/x", "attempt": "attempt_0001", "numerical_checks_passed": False}}
    record, _ = _case("COME__NOW__COME", ready, tmp_path, prior=failed)
    assert record["attempts"][0]["status"] == "PRIOR_VERIFIED_NO_PASS"
    assert record["status"] == "NO_NUMERICAL_PASS_WITHIN_COMBINATION_BUDGET"


def _attempt(folder, index, *, complete=True, passed=False):
    folder.mkdir(parents=True, exist_ok=True)
    sequence = folder / f"attempt_{index:04d}.json"
    sequence.write_text(json.dumps({"index": index}))
    evidence = {"validation_complete": complete, "numerical_checks_passed": passed if complete else None}
    (folder / f"attempt_{index:04d}.verification.json").write_text(json.dumps({
        "sequence_file": sequence.name, "sequence_file_sha256": file_hash(sequence), "evidence": evidence,
        "evidence_hash": json_hash(evidence)}))


def test_prior_attempt_checkpoint_skips_incomplete_and_refuses_tampering_or_duplicates(tmp_path, monkeypatch):
    monkeypatch.setattr(plan, "ROOT", tmp_path)
    first = tmp_path / "results/first"
    _attempt(first / "sequences/A__B", 1)
    _attempt(first / "sequences/A__B", 2, complete=False)
    found = plan.prior_attempts([first], "A__B")
    assert sorted(found) == [1] and found[1]["numerical_checks_passed"] is False
    assert found[1]["output"] == "results/first"
    second = tmp_path / "results/second"
    _attempt(second / "sequences/A__B", 1)
    with pytest.raises(ValueError, match="twice"):
        plan.prior_attempts([first, second], "A__B")
    (first / "sequences/A__B/attempt_0001.json").write_text("{}")
    with pytest.raises(ValueError, match="changed"):
        plan.prior_attempts([first], "A__B")


def test_summary_keeps_every_case_and_counts_blocked_reasons():
    records = [{"status": "NUMERICAL_PASS", "numerical_checks_passed": True},
               {"status": "BLOCKED_DEPENDENCY", "numerical_checks_passed": None, "blocking_reasons": ["PAIR_NOT_PLANNED"]},
               {"status": "NOT_RUN", "numerical_checks_passed": None}]
    summary = plan.summarize(records, "SOFT_WALL_TIME_REACHED", {})
    assert summary["denominator"] == 3 and summary["numerical_pass_count"] == 1 and summary["not_run_count"] == 1
    assert summary["blocked_reason_counts"] == {"PAIR_NOT_PLANNED": 1} and summary["formal_pass_count"] == 0


def test_verify_sequences_never_counts_blocked_or_unrun_cases(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    (run / "manifest.json").write_text(json.dumps({"sequence_policy": POLICY_PATH,
                                                   "sequence_policy_sha256": file_hash(ROOT / POLICY_PATH)}))
    (run / "summary.json").write_text(json.dumps({"cases": [
        {"sequence_id": "COME__NOW__COME", "status": "BLOCKED_DEPENDENCY", "selected_attempt": None, "numerical_checks_passed": None},
        {"sequence_id": "NOW__NOW__NOW", "status": "NOT_RUN", "selected_attempt": None, "numerical_checks_passed": None}]}))
    assert script("verify_sequences").main(["--run-dir", str(run)]) == 0
    totals = json.loads((run / "independent_recheck/summary.json").read_text())["totals"]
    assert totals["cases"] == 2 and totals["rechecked"] == 0 and totals["numerical_pass"] == 0
    assert totals["all_agree_with_planning"] is False and totals["planning_status_counts"] == {"BLOCKED_DEPENDENCY": 1, "NOT_RUN": 1}


IDENTITY = {"pair_identity_hash": "p" * 64, "sequence_identity_hash": "s" * 64}


def _case_manifest(root, subbatches, groups, policy_sha="f" * 64):
    manifest = {"schema_version": 1, "kind": "hospital35_sequence_cases_v1",
                "sequence_policy": {"path": POLICY_PATH, "sha256": policy_sha}, "pair_run_dir": "results/pairs",
                "expected_identity": IDENTITY, "denominator": sum(len(s["cases"]) for s in subbatches),
                "groups": groups, "subbatches": subbatches, "limits": {}, "aggregate_directory": "results/aggregate"}
    path = root / "case_manifest.json"
    path.write_text(json.dumps(manifest))
    return manifest, file_hash(path)


def _output(root, relative, cases, records, *, resume_from=(), pass_recheck=True, policy_sha="f" * 64):
    output = root / relative
    output.mkdir(parents=True)
    (output / "manifest.json").write_text(json.dumps({
        "sequence_policy_sha256": policy_sha, "pair_identity": {"identity_hash": IDENTITY["pair_identity_hash"]},
        "sequence_identity": {"identity_hash": IDENTITY["sequence_identity_hash"]}, "pair_run_dir": "results/pairs",
        "cases": cases, "resume_from": [{"output": r} for r in resume_from]}))
    (output / "summary.json").write_text(json.dumps({"cases": records}))
    for record in records:
        if record["status"] == "NUMERICAL_PASS" and record.get("selected_output") == relative:
            folder = output / "sequences" / record["sequence_id"]
            folder.mkdir(parents=True)
            sequence = folder / f"{record['selected_attempt']}.json"
            sequence.write_text("{}")
            if pass_recheck:
                evidence = {"numerical_checks_passed": True, "word_occurrences": record["word_count"],
                            "connector_groups": record["word_count"] - 1}
                (output / "independent_recheck").mkdir(exist_ok=True)
                (output / "independent_recheck" / f"{record['sequence_id']}.json").write_text(json.dumps({
                    "sequence_file_sha256": file_hash(sequence), "evidence": evidence, "evidence_hash": json_hash(evidence)}))
    return output


def _record(case, status, *, output=None, attempt=None, words=3):
    return {"sequence_id": case, "status": status, "word_count": words, "selected_attempt": attempt,
            "selected_output": output, "numerical_checks_passed": True if status == "NUMERICAL_PASS" else None,
            **({"blocking_reasons": ["PAIR_NOT_PLANNED"]} if status == "BLOCKED_DEPENDENCY" else {})}


def test_aggregate_fixes_denominator_and_requires_rechecks(tmp_path):
    subbatches = [{"subbatch_id": "s1", "cases": ["A__A__A", "A__B__A"], "canonical_output": "results/seq/s1"},
                  {"subbatch_id": "s2", "cases": ["B__B__B"], "canonical_output": "results/seq/s2"}]
    manifest, _ = _case_manifest(tmp_path, subbatches, {"original": ["A__A__A"], "new": ["A__B__A", "B__B__B"]})
    _output(tmp_path, "results/seq/s1", ["A__A__A", "A__B__A"], [
        _record("A__A__A", "NUMERICAL_PASS", output="results/seq/s1", attempt="attempt_0001"),
        _record("A__B__A", "BLOCKED_DEPENDENCY")])
    result = aggregate(tmp_path, manifest)
    rows = {r["sequence_id"]: r for r in result["rows"]}
    assert result["denominator"] == 3 and rows["B__B__B"]["status"] == "NOT_RUN"
    assert rows["A__A__A"]["independently_rechecked"] is True
    assert result["totals"]["all"]["independently_rechecked_pass"] == 1
    assert result["totals"]["original"]["word_occurrences_in_rechecked_passes"] == 3
    assert result["totals"]["new"]["blocked_reason_counts"] == {"PAIR_NOT_PLANNED": 1}


def test_resume_may_settle_open_cases_but_never_replace_settled_ones(tmp_path):
    subbatches = [{"subbatch_id": "s1", "cases": ["A__A__A", "A__B__A"], "canonical_output": "results/seq/s1"}]
    manifest, _ = _case_manifest(tmp_path, subbatches, {"all": ["A__A__A", "A__B__A"]})
    _output(tmp_path, "results/seq/s1", ["A__A__A", "A__B__A"], [
        _record("A__A__A", "NUMERICAL_PASS", output="results/seq/s1", attempt="attempt_0002"),
        _record("A__B__A", "INCOMPLETE_SOFT_BUDGET")])
    assert next_output(tmp_path, subbatches[0])[1].name == "s1_resume_01"
    _output(tmp_path, "results/seq/s1_resume_01", ["A__A__A", "A__B__A"], [
        _record("A__A__A", "NUMERICAL_PASS", output="results/seq/s1", attempt="attempt_0002"),
        _record("A__B__A", "NUMERICAL_PASS", output="results/seq/s1_resume_01", attempt="attempt_0005")],
        resume_from=["results/seq/s1"])
    rows = {r["sequence_id"]: r for r in aggregate(tmp_path, manifest)["rows"]}
    assert rows["A__B__A"]["source_output"] == "results/seq/s1_resume_01" and rows["A__B__A"]["independently_rechecked"]
    assert rows["A__A__A"]["selected_attempt"] == "attempt_0002"
    _output(tmp_path, "results/seq/s1_resume_02", ["A__A__A"], [
        _record("A__A__A", "NUMERICAL_PASS", output="results/seq/s1_resume_02", attempt="attempt_0009")],
        resume_from=["results/seq/s1", "results/seq/s1_resume_01"])
    with pytest.raises(SequenceBatchError) as caught:
        aggregate(tmp_path, manifest)
    assert caught.value.code == "SETTLED_CASE_CONFLICT"


def test_aggregate_rejects_foreign_identity_wrong_chain_and_gaps(tmp_path):
    subbatches = [{"subbatch_id": "s1", "cases": ["A__A__A"], "canonical_output": "results/seq/s1"}]
    manifest, _ = _case_manifest(tmp_path, subbatches, {"all": ["A__A__A"]})
    _output(tmp_path, "results/seq/s1", ["A__A__A"], [_record("A__A__A", "NOT_RUN")], policy_sha="0" * 64)
    with pytest.raises(SequenceBatchError) as caught:
        aggregate(tmp_path, manifest)
    assert caught.value.code == "OUTPUT_IDENTITY_MISMATCH"
    other = tmp_path / "other"
    other.mkdir()
    manifest, _ = _case_manifest(other, subbatches, {"all": ["A__A__A"]})
    _output(other, "results/seq/s1", ["A__A__A"], [_record("A__A__A", "NOT_RUN")])
    _output(other, "results/seq/s1_resume_01", ["A__A__A"], [_record("A__A__A", "NOT_RUN")])
    with pytest.raises(SequenceBatchError) as caught:
        aggregate(other, manifest)
    assert caught.value.code == "RESUME_SOURCES_DIFFER_FROM_CHAIN"
    (other / "results/seq/s1_resume_03").mkdir()
    with pytest.raises(SequenceBatchError) as caught:
        output_chain(other, subbatches[0])
    assert caught.value.code == "RESUME_CHAIN_HAS_GAP"


def test_case_manifest_rejects_tampering_oversize_and_overlap(tmp_path):
    cases = [f"A__{i}__A" for i in range(9)]
    manifest, sha = _case_manifest(tmp_path, [{"subbatch_id": "s1", "cases": cases[:8], "canonical_output": "results/a"},
                                              {"subbatch_id": "s2", "cases": cases[8:], "canonical_output": "results/b"}],
                                   {"all": cases})
    assert load_case_manifest(tmp_path, "case_manifest.json", sha, cases)["denominator"] == 9
    with pytest.raises(SequenceBatchError):
        load_case_manifest(tmp_path, "case_manifest.json", "0" * 64, cases)
    for subbatches in ([{"subbatch_id": "s1", "cases": cases, "canonical_output": "results/a"}],
                       [{"subbatch_id": "s1", "cases": cases[:5], "canonical_output": "results/a"},
                        {"subbatch_id": "s2", "cases": cases[4:], "canonical_output": "results/b"}]):
        _, sha = _case_manifest(tmp_path, subbatches, {"all": cases})
        with pytest.raises(SequenceBatchError):
            load_case_manifest(tmp_path, "case_manifest.json", sha, cases)


def test_sequence_budget_honours_stop_file_and_identity_drift(tmp_path):
    stop = tmp_path / "sequences.stop"
    budget = plan.Budget(100, 0, tmp_path, stop_file=stop)
    assert budget.stop_reason() is None
    stop.write_text("")
    assert budget.stop_reason() == "STOP_REQUESTED"
    drifting = plan.Budget(100, 0, tmp_path, drift=lambda: "IDENTITY_CHANGED_DURING_RUN")
    assert drifting.stop_reason() == "IDENTITY_CHANGED_DURING_RUN"
    signalled = plan.Budget(100, 0, tmp_path)
    signalled.requested = True
    assert signalled.stop_reason() == "STOP_REQUESTED"
