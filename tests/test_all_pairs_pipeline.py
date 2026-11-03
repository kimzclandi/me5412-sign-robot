"""Failure injection, independent curve checks and interrupted-run recovery."""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

import sign_robot.all_pairs as pairs
from sign_robot.motion import ROOT, load_model
from sign_robot.pair_contract import (
    atomic_json, atomic_motion, canonical_array_hash, file_hash, freeze_library,
    json_hash, load_policy, read_json, run_identity,
)
from sign_robot.pair_verification import _dense_quintic, verify_record, verify_run
from sign_robot.transitions import ClearanceResult


def clear(q):
    return measured(q, np.full(len(q), 0.01))


def measured(q, distances):
    frame = int(np.argmin(distances))
    worst = {"frame": frame, "bodies": ["torso_link", "right_wrist_yaw_link"],
             "geoms": ["fixture_a", "fixture_b"], "distance_m": float(distances[frame])}
    return ClearanceResult(bool(np.min(distances) >= 0.002), float(np.min(distances)),
                           sampled_frames=len(q), worst_contact=worst,
                           frame_clearances_m=np.asarray(distances).tolist())


@pytest.fixture(scope="module")
def frozen_inputs():
    policy = load_policy(ROOT / "config/transition_policy.json")
    library, clips = freeze_library(ROOT, policy)
    model = load_model(ROOT)
    context = pairs.PairContext(ROOT, policy, library, clips, model, clear, {})
    context.audit = pairs.audit_words(context)
    return context


@pytest.fixture
def context(frozen_inputs):
    return pairs.PairContext(ROOT, deepcopy(frozen_inputs.policy), deepcopy(frozen_inputs.library),
                             frozen_inputs.clips, frozen_inputs.model, clear, deepcopy(frozen_inputs.audit))


def plan(context, source="HELLO", target="PLEASE"):
    return pairs.plan_pair(source, target, library_version=context.library["library_version"],
                           policy=context.policy, seed=5412, context=context)


def save_candidate(tmp_path, motion, record):
    path = tmp_path / "trajectory.npz"
    atomic_motion(path, motion)
    record.update(trajectory_file=path.name, trajectory_file_hash=file_hash(path),
                  canonical_array_hash=canonical_array_hash(motion))
    return record


@pytest.mark.parametrize("gloss", ["UNSEEN", "BUY", "BOOK"])
def test_unknown_gloss_does_not_fall_back_to_broader_demo_library(context, gloss):
    motion, record = plan(context, gloss, "HELLO")
    assert motion is None
    assert record["status"] == "BLOCKED_INPUT" and record["reason_codes"] == ["UNKNOWN_GLOSS"]


@pytest.mark.parametrize("bad", [("source",), ("target",), ("source", "target")])
def test_endpoint_blockers_are_side_specific_and_no_search_runs(context, bad):
    for role in bad:
        context.audit["words"]["HELLO" if role == "source" else "PLEASE"]["endpoints"][role]["engineering_valid"] = False
    motion, record = plan(context)
    assert motion is None and record["candidate_count"] == 0
    assert record["status"] == "BLOCKED_ENDPOINT"
    assert record["reason_codes"] == [f"{role.upper()}_ENDPOINT_INVALID" for role in bad]


def test_legacy_endpoints_are_audited_but_not_inherited(context):
    _, record = plan(context, "NURSE", "INTERPRETER")
    assert record["exit_frame"] == 88 and record["entry_frame"] == 24
    nurse = context.audit["words"]["NURSE"]
    assert {r["frame"] for r in nurse["research_endpoints"]} == {80, 81}
    # The proposals were recorded on the hospital_v1 clip; clips-v2 replaced NURSE, so they are stale.
    assert all(r["recheck_status"] == "STALE_INPUT_HASH" and not r["selected_for_scan"] for r in nurse["research_endpoints"])
    current = next(w for w in context.library["words"] if w["gloss"] == "NURSE")["motion_sha256"]
    for proposal in context.policy["endpoints"]["legacy_research_endpoints"]:
        if proposal["gloss"] == "NURSE":
            proposal["motion_sha256"] = current
    nurse = pairs.audit_words(context)["words"]["NURSE"]
    assert all(not r["selected_for_scan"] for r in nurse["research_endpoints"])
    f80 = next(r for r in nurse["research_endpoints"] if r["frame"] == 80)
    assert f80["trim_ratio"] == 8 / 79 and f80["approval_status"] == "pending"


def test_stale_endpoint_exception_is_not_applied_to_new_motion(context):
    proposal = context.policy["endpoints"]["legacy_research_endpoints"][0]
    proposal["motion_sha256"] = "0" * 64
    audit = pairs.audit_words(context)
    stale = next(r for r in audit["words"][proposal["gloss"]]["research_endpoints"] if r["id"] == proposal["id"])
    assert stale["recheck_status"] == "STALE_INPUT_HASH" and not stale["selected_for_scan"]


def test_self_pair_keeps_two_word_occurrences_and_is_not_a_zero_connector(tmp_path, context):
    motion, record = plan(context, "PLEASE", "PLEASE")
    clip = context.clips["PLEASE"]["positions"]
    start, end = record["transition_start_frame"], record["transition_end_frame"]
    np.testing.assert_array_equal(motion["positions"][:start + 1], clip[:record["exit_frame"] + 1])
    np.testing.assert_array_equal(motion["positions"][end:], clip[record["entry_frame"]:])
    assert end > start and record["transition_duration_s"] >= 0.3
    assert len(record["word_segments"]) == 2
    evidence = verify_record(tmp_path, save_candidate(tmp_path, motion, record), context)
    assert evidence["artifact_contract_passed"] and evidence["word_occurrences"] == 2
    assert evidence["status"] == "FAILED_QUALITY"
    assert evidence["protected_core_preserved"] is None


def test_work_budget_exhaustion_is_not_an_infeasibility_claim(context):
    context.policy["planner"]["max_collision_samples"] = 2
    motion, record = plan(context)
    assert motion is None and record["status"] == "FAILED_SEARCH"
    assert record["reason_codes"] == ["DIRECT_CANDIDATE_WORK_BUDGET_EXHAUSTED"]


def test_wall_time_protection_has_distinct_timeout_status(context):
    context.policy["planner"]["wall_time_s"] = 1e-12
    motion, record = plan(context)
    assert motion is None and record["status"] == "TIMEOUT"


def test_direct_collision_retains_diagnostic_candidate(context):
    context.clearance = lambda q: measured(q, np.full(len(q), -0.01))
    motion, record = plan(context)
    assert motion is not None and record["status"] == "FAILED_SEARCH"
    assert "GENERAL_SEARCH_NOT_IMPLEMENTED" in record["reason_codes"]
    assert record["candidate_count"] == 1 and not record["playback_eligible"]


def test_verifier_reconstructs_actual_curve_and_finds_between_frame_collision(tmp_path, context, monkeypatch):
    motion, record = plan(context)
    save_candidate(tmp_path, motion, record)
    start, end = record["transition_start_frame"], record["transition_end_frame"]
    q = motion["positions"][start:end + 1]
    count = max((len(q) - 1) * 4, int(np.ceil(1.875 * np.abs(q[-1] - q[0]).max() / 0.04)))
    dense = _dense_quintic(q[0], q[-1], count)
    needle = next(row for row in dense if not np.any(np.max(np.abs(q - row), axis=1) < 1e-10))
    def hidden_collision(values):
        distances = np.where(np.max(np.abs(values - needle), axis=1) < 1e-10, -0.01, 0.01)
        return measured(values, distances)
    context.clearance = hidden_collision
    monkeypatch.setattr(pairs, "plan_pair", lambda *a, **kw: pytest.fail("Verifier called the planner"))
    assert hidden_collision(q).min_distance_m == 0.01
    evidence = verify_record(tmp_path, record, context)
    assert evidence["status"] == "FAILED_SEARCH"
    assert "DENSE_CONNECTOR_COLLISION" in evidence["reason_codes"]
    assert evidence["dense_recheck_result"][-1]["connector"]["min_clearance_mm"] == -10
    assert evidence["closest_collision_pair"]["distance_m"] == -0.01
    assert record["planning_evidence"]["status"] == "FAILED_QUALITY"
    assert record["planning_evidence"]["min_clearance_mm"] == 10


@pytest.mark.parametrize("mutation,reason", [
    (lambda m, r: m["positions"].__setitem__((0, 0), m["positions"][0, 0] + 0.1), "ORIGINAL_WORD_SLICES_CHANGED_OR_REPEAT_REMOVED"),
    (lambda m, r: m["positions"].__setitem__((r["transition_start_frame"] + 1, 20), 0.123456), "DECLARED_QUINTIC_CURVE_MISMATCH"),
    (lambda m, r: m["timestamps_s"].__setitem__(1, 0.02), "TIMESTAMP_CONTRACT_MISMATCH"),
])
def test_verifier_rejects_numerically_modified_saved_artifacts_even_with_updated_hashes(tmp_path, context, mutation, reason):
    motion, record = plan(context)
    mutation(motion, record)
    save_candidate(tmp_path, motion, record)
    evidence = verify_record(tmp_path, record, context)
    assert evidence["status"] == "ERROR" and reason in evidence["reason_codes"]
    assert evidence["artifact_contract_passed"] is False


@pytest.fixture
def fast_runner(context, monkeypatch):
    def builder(root, policy, *, library=None, clips=None, audit=None):
        return pairs.PairContext(ROOT, policy, library or context.library, clips or context.clips,
                                 context.model, clear, audit or context.audit)
    monkeypatch.setattr(pairs, "build_context", builder)
    # verify_run binds its own construction entry point, sharing only the
    # numerical model/fixture clearance rather than a planner decision.
    monkeypatch.setattr("sign_robot.pair_verification.build_context", builder)
    return context


def test_checkpoint_resume_preserves_completed_candidates_and_all_denominators(tmp_path, fast_runner, monkeypatch):
    policy = fast_runner.policy
    selected = {"HELLO__PLEASE", "PLEASE__HELLO"}
    run_dir, summary = pairs.run_scan(ROOT, policy, "resume", tmp_path, selected_pairs=selected)
    assert summary["groups"]["all"]["denominator"] == 1225
    assert summary["groups"]["all"]["scanned"] == 2
    assert summary["groups"]["self"]["denominator"] == 35
    assert summary["groups"]["non_self"]["denominator"] == 1190
    before = {p.name: file_hash(p) for p in (run_dir / "checkpoints").glob("*.json")}
    monkeypatch.setattr(pairs, "plan_pair", lambda *a, **kw: pytest.fail("Completed pair was replanned"))
    pairs.run_scan(ROOT, policy, "resume", tmp_path, resume=True, selected_pairs=selected)
    after = {p.name: file_hash(p) for p in (run_dir / "checkpoints").glob("*.json")}
    assert before == after
    verified = verify_run(ROOT, run_dir)
    assert verified["verified_records"] == 2
    rows = [json.loads(line) for line in (run_dir / "pairs.jsonl").read_text().splitlines()]
    assert len(rows) == len({r["pair_id"] for r in rows}) == 1225
    assert sum(r["status"] == "NOT_RUN" for r in rows) == 1223
    assert not verified["coverage_complete"] and not verified["L2_complete"]
    for row in rows:
        if row["status"] != "NOT_RUN":
            assert row["planning_evidence"]["validation_resolution"] == {"planning_factor": 1}
            assert row["validation_resolution"]["verification_factors"] == [1, 2, 4]


def test_interruption_after_a_completed_pair_can_resume_without_summary(tmp_path, fast_runner, monkeypatch):
    original = pairs.plan_pair
    count = 0
    def interrupt(*a, **kw):
        nonlocal count
        count += 1
        if count == 2:
            raise KeyboardInterrupt
        return original(*a, **kw)
    monkeypatch.setattr(pairs, "plan_pair", interrupt)
    with pytest.raises(KeyboardInterrupt):
        pairs.run_scan(ROOT, fast_runner.policy, "interrupted", tmp_path, max_pairs=2)
    assert not (tmp_path / "interrupted/summary.json").exists()
    monkeypatch.setattr(pairs, "plan_pair", original)
    run_dir, summary = pairs.run_scan(ROOT, fast_runner.policy, "interrupted", tmp_path, resume=True, max_pairs=1)
    assert summary["groups"]["all"]["scanned"] == 2


@pytest.mark.parametrize("changed", ["code_hash", "code_commit", "model_hash", "library_version", "environment_id"])
def test_resume_rejects_result_affecting_version_changes(tmp_path, fast_runner, monkeypatch, changed):
    pairs.run_scan(ROOT, fast_runner.policy, "versioned", tmp_path, max_pairs=1)
    original = pairs.freeze_library
    def changed_freeze(*a, **kw):
        library, clips = original(*a, **kw)
        if changed == "environment_id":
            library["environment"]["environment_id"] = "changed"
        else:
            library[changed] = "changed"
        return library, clips
    monkeypatch.setattr(pairs, "freeze_library", changed_freeze)
    with pytest.raises(ValueError, match="changed"):
        pairs.run_scan(ROOT, fast_runner.policy, "versioned", tmp_path, resume=True)


def test_resume_rejects_policy_change(tmp_path, fast_runner):
    pairs.run_scan(ROOT, fast_runner.policy, "policy", tmp_path, max_pairs=1)
    changed = deepcopy(fast_runner.policy)
    changed["constraints"]["min_clearance_m"] = 0.003
    with pytest.raises(ValueError, match="changed"):
        pairs.run_scan(ROOT, changed, "policy", tmp_path, resume=True)


@pytest.mark.parametrize("kind", ["checkpoint", "trajectory", "frozen_policy"])
def test_resume_detects_corruption_in_each_checkpoint_layer(tmp_path, fast_runner, kind):
    run_dir, _ = pairs.run_scan(ROOT, fast_runner.policy, "integrity", tmp_path, max_pairs=1)
    if kind == "checkpoint":
        path = next((run_dir / "checkpoints").glob("*.json"))
        envelope = read_json(path)
        envelope["record"]["status"] = "ERROR"
        atomic_json(path, envelope)
    elif kind == "trajectory":
        path = next((run_dir / "trajectories").glob("*.npz"))
        path.write_bytes(path.read_bytes() + b"corruption")
    else:
        path = run_dir / "policy.json"
        value = read_json(path)
        value["policy_id"] = "changed"
        atomic_json(path, value)
    with pytest.raises(ValueError, match="[Ii]nvalid|integrity"):
        pairs.run_scan(ROOT, fast_runner.policy, "integrity", tmp_path, resume=True)


def test_legacy_or_forged_pass_cannot_enter_development_matrix(tmp_path, fast_runner):
    run_dir, _ = pairs.run_scan(ROOT, fast_runner.policy, "forged", tmp_path, max_pairs=1)
    path = next((run_dir / "checkpoints").glob("*.json"))
    envelope = read_json(path)
    envelope["record"]["status"] = "PASS_SIM"
    envelope["record_hash"] = json_hash(envelope["record"])
    atomic_json(path, envelope)
    with pytest.raises(ValueError, match="cannot import PASS_SIM"):
        pairs.summarize_run(run_dir)
