"""Append-only v2 run-store, resume and independent selection tests."""
from copy import deepcopy
from dataclasses import replace
import json
import itertools
from pathlib import Path
import shutil

import pytest

import sign_robot.pair_runner_v2 as runner
from pair_v2_fixtures import NOW, synthetic_inputs
from sign_robot.motion import ROOT
from sign_robot.pair_routes import PairContextV2
from sign_robot.pair_windows import load_window_approvals


@pytest.fixture
def run_context(tmp_path, monkeypatch):
    policy, library, clips, _ = synthetic_inputs(tmp_path)
    library.update(library="hospital_v1", library_version="hospital_v1@" + "a" * 64,
                   model_hash="b" * 64, code_commit="c" * 40, code_hash="d" * 64,
                   environment={"environment_id": "e" * 64}, input_errors=[], couplings=[])
    approvals = load_window_approvals(tmp_path, policy, library, now=NOW)
    import sign_robot.pair_routes as routes
    monkeypatch.setattr(routes, "neutral_pose", lambda names, model: __import__("numpy").zeros(len(names)))
    monkeypatch.setattr(routes, "ik_via_candidates", lambda a, b, names, model: [("up", (a+b)/2)])
    monkeypatch.setattr(routes, "ik_dual_via_candidates", lambda a, b, names, model: [(["out", "out"], [(a+b)/3, 2*(a+b)/3])])
    (tmp_path / "contracts").mkdir()
    shutil.copy2(ROOT / "contracts/all_pairs_v2.json", tmp_path / "contracts/all_pairs_v2.json")
    originals = runner.iter_deterministic_attempts_v2, runner.iter_rrt_attempts_v2
    monkeypatch.setattr(runner, "iter_deterministic_attempts_v2", lambda *a, **kw: itertools.islice(originals[0](*a, **kw), 3))
    monkeypatch.setattr(runner, "iter_rrt_attempts_v2", lambda *a, **kw: itertools.islice(originals[1](*a, **kw), 2))
    context = PairContextV2(tmp_path, policy, library, clips, __import__("test_pair_routes_v2").Model(library["joint_names"]),
                            __import__("test_pair_routes_v2").Clearance(), approvals)
    return tmp_path, policy, context


def create_store(run_context, tmp_path):
    root, policy, context = run_context
    return runner.V2RunStore.create(root, policy, context, root / "results", "run-v2", resume=False)


def numerical_evidence(store, path, *, positive=True):
    trajectory = runner.read_pair_trajectory(path, schema_version=2)
    return {"schema_version": 2, "pair_id": trajectory["pair_id"], "reason_codes": runner.acceptance_pending(store.policy),
            "status": "FAILED_QUALITY", "playback_eligible": False,
            "numerical_checks_passed": positive, "validation_complete": True,
            "artifact_contract_passed": True, "approval_checks_passed": True,
            "protected_core_preserved": True, "original_word_slices_preserved": True,
            "identity": store.manifest["identity"], "word_occurrences": 2,
            "trajectory_file_sha256": runner.file_hash(path), "trajectory_hash": runner.json_hash(trajectory)}


def hashes(directory):
    return {str(path.relative_to(directory)): runner.file_hash(path) for path in directory.rglob("*") if path.is_file()}


def test_run_store_saves_every_attempt_and_fixed_denominators(run_context):
    root, policy, context = run_context
    store = create_store(run_context, root)
    record = store.run_pair("HELLO", "PLEASE", context, seed=5412)
    assert record["completed"] and record["status"] == "FAILED_QUALITY"
    assert record["candidate_count"] > 0
    assert record["method_coverage"]["direct"]["attempted"]
    assert record["method_coverage"]["rrt_connect"]["attempted"]
    assert all(entry["status"] != "PASS_SIM" for entry in record["attempts"])
    store.verify()
    summary = store.summarize()
    assert summary["groups"]["all"]["denominator"] == 1225
    assert summary["groups"]["non_self"]["denominator"] == 1190
    assert summary["groups"]["self"]["denominator"] == 35
    assert summary["groups"]["all"]["scanned"] == 1
    assert (store.run_dir / "attempts/HELLO__PLEASE").is_dir()
    assert len(list((store.run_dir / "candidates/HELLO__PLEASE").glob("*.json"))) == record["candidate_count"]


def test_interrupted_pair_resumes_without_duplicate_attempts(run_context):
    root, policy, context = run_context
    store = create_store(run_context, root)
    with pytest.raises(KeyboardInterrupt, match="immutable attempt checkpoint"):
        store.run_pair("HELLO", "PLEASE", context, seed=5412, max_new_attempts=2)
    partial = runner.V2RunStore.load(root, store.run_dir, recover=True)
    before = partial._head_record("HELLO__PLEASE")
    assert before["planning_state"] == "RUNNING" and len(before["attempts"]) == 2
    resumed = partial.run_pair("HELLO", "PLEASE", context, seed=5412)
    assert resumed["completed"] and len(resumed["attempts"]) > 2
    ids = [entry["attempt_id"] for entry in resumed["attempts"]]
    assert ids == [f"attempt_{i:05d}" for i in range(1, len(ids) + 1)]
    assert partial.manifest["heads"]["HELLO__PLEASE"]["sequence"] >= len(ids)


def test_resume_rejects_policy_or_code_identity_change(run_context):
    root, policy, context = run_context
    store = create_store(run_context, root)
    with pytest.raises(KeyboardInterrupt):
        store.run_pair("HELLO", "PLEASE", context, seed=5412, max_new_attempts=1)
    changed = deepcopy(policy)
    changed["planner"]["seed"] += 1
    with pytest.raises(ValueError, match="changed"):
        runner.V2RunStore.create(root, changed, context, root / "results", "run-v2", resume=True)


def test_attempt_tampering_is_detected_before_resume(run_context):
    root, policy, context = run_context
    store = create_store(run_context, root)
    with pytest.raises(KeyboardInterrupt):
        store.run_pair("HELLO", "PLEASE", context, seed=5412, max_new_attempts=1)
    attempt = next((store.run_dir / "attempts/HELLO__PLEASE").glob("*.json"))
    attempt.write_text(attempt.read_text().replace("FAILED_QUALITY", "ERROR", 1))
    with pytest.raises(ValueError, match="integrity|differs"):
        runner.V2RunStore.load(root, store.run_dir, recover=True)


def test_independent_verification_selects_only_complete_numerical_candidate(run_context, monkeypatch):
    root, policy, context = run_context
    store = create_store(run_context, root)
    record = store.run_pair("HELLO", "PLEASE", context, seed=5412)
    def fake_verify(root_arg, path, policy_arg):
        return numerical_evidence(store, path)
    monkeypatch.setattr(runner, "verify_saved_pair_v2", fake_verify)
    selected = store.verify_pair("HELLO__PLEASE")
    assert selected["verification_state"] == "COMPLETE"
    assert selected["selected_candidate_id"] in selected["candidate_ids"]
    assert selected["status"] == "FAILED_QUALITY"
    assert selected["formal_acceptance"] is False and selected["playback_eligible"] is False
    store.verify()


def test_verification_artifact_tampering_is_detected(run_context, monkeypatch):
    root, policy, context = run_context
    store = create_store(run_context, root)
    store.run_pair("HELLO", "PLEASE", context, seed=5412)
    monkeypatch.setattr(runner, "verify_saved_pair_v2", lambda root, path, policy: numerical_evidence(store, path, positive=False))
    store.verify_pair("HELLO__PLEASE")
    evidence = next((store.run_dir / "verification/HELLO__PLEASE").glob("*.json"))
    evidence.write_text(evidence.read_text().replace("FAILED_QUALITY", "PASS_SIM", 1))
    with pytest.raises(ValueError, match="hash mismatch|Invalid independent"):
        runner.V2RunStore.load(root, store.run_dir)


def test_self_pair_checkpoint_keeps_two_occurrences(run_context):
    root, policy, context = run_context
    store = create_store(run_context, root)
    record = store.run_pair("HELLO", "HELLO", context, seed=5412)
    assert record["pair_id"] == "HELLO__HELLO"
    assert record["source_gloss"] == record["target_gloss"] == "HELLO"
    assert record["candidate_count"] > 0


def test_cli_v2_dispatch_uses_schema_two_without_formal_pass(run_context, monkeypatch, capsys):
    root, policy, context = run_context
    store = create_store(run_context, root)
    from scripts import plan_all_pairs
    monkeypatch.setattr(plan_all_pairs, "ROOT", root)
    monkeypatch.setattr(plan_all_pairs, "run_scan", lambda *args, **kwargs: pytest.fail("v1 runner called"))
    # The script imports the v2 runner lazily and one selected pair is enough
    # to verify dispatch; direct CLI output is not the acceptance artifact.
    monkeypatch.setattr(plan_all_pairs, "load_policy", lambda path, supported_versions=(1,): policy)
    monkeypatch.setattr(runner, "build_pair_context_v2", lambda *args: context)
    assert plan_all_pairs.main(["--include-self", "--policy", str(root / "policy.json"), "--run-id", "cli-v2",
                                "--results-root", str(root / "cli-results"), "--max-pairs", "0"]) == 0
    assert "formal_acceptance_enabled" in capsys.readouterr().out


def test_completed_pair_resume_preserves_all_saved_bytes(run_context, monkeypatch):
    root, policy, context = run_context
    store = create_store(run_context, root)
    record = store.run_pair("HELLO", "PLEASE", context, seed=5412)
    store.summarize()
    before = hashes(store.run_dir)
    monkeypatch.setattr(runner, "iter_deterministic_attempts_v2", lambda *a, **kw: pytest.fail("completed pair replanned"))
    restored = runner.V2RunStore.create(root, policy, context, root / "results", "run-v2", resume=True)
    assert restored.run_pair("HELLO", "PLEASE", context, seed=5412) == record
    restored.summarize()
    assert hashes(store.run_dir) == before


def test_different_incomplete_replay_is_rejected_and_saved_bytes_retained(run_context, monkeypatch):
    root, policy, context = run_context
    store = create_store(run_context, root)
    with pytest.raises(KeyboardInterrupt):
        store.run_pair("HELLO", "PLEASE", context, seed=5412, max_new_attempts=1)
    before = hashes(store.run_dir)
    original = runner.iter_deterministic_attempts_v2
    def changed(*args, **kwargs):
        for attempt in original(*args, **kwargs):
            attempt.diagnostic["reason_codes"] = ["SYNTHETIC_DIFFERENT_REPLAY"]
            yield attempt
    monkeypatch.setattr(runner, "iter_deterministic_attempts_v2", changed)
    with pytest.raises(runner.RunIntegrityError, match="replay differs"):
        store.run_pair("HELLO", "PLEASE", context, seed=5412)
    assert hashes(store.run_dir) == before


def test_duplicate_attempt_with_different_content_cannot_overwrite(run_context):
    root, policy, context = run_context
    store = create_store(run_context, root)
    with pytest.raises(KeyboardInterrupt):
        store.run_pair("HELLO", "PLEASE", context, seed=5412, max_new_attempts=1)
    before = hashes(store.run_dir)
    attempt = next(runner.iter_deterministic_attempts_v2(context, "HELLO", "PLEASE", seed=5412))
    attempt.diagnostic["reason_codes"] = ["SYNTHETIC_DIFFERENT_ATTEMPT"]
    with pytest.raises(runner.RunIntegrityError, match="replay differs"):
        store.save_attempt("HELLO__PLEASE", "attempt_00001", attempt)
    assert hashes(store.run_dir) == before


@pytest.mark.parametrize("field", ["library_version", "model_hash", "code_commit", "code_hash", "environment"])
def test_resume_refuses_each_frozen_identity_change(run_context, field):
    root, policy, context = run_context
    create_store(run_context, root)
    library = deepcopy(context.library)
    library[field] = {"environment_id": "f" * 64} if field == "environment" else "changed-version"
    with pytest.raises(runner.RunIntegrityError, match="changed"):
        runner.V2RunStore.create(root, policy, replace(context, library=library), root / "results", "run-v2", resume=True)


def test_power_loss_after_journal_before_manifest_recovers_attempt(run_context, monkeypatch):
    root, policy, context = run_context
    store = create_store(run_context, root)
    atomic = runner.atomic_json
    def power_loss(path, value):
        if Path(path).name == "manifest.json" and value["heads"].get("HELLO__PLEASE", {}).get("sequence") == 2:
            raise OSError("synthetic power loss before manifest update")
        return atomic(path, value)
    with monkeypatch.context() as scope:
        scope.setattr(runner, "atomic_json", power_loss)
        with pytest.raises(OSError, match="power loss"):
            store.run_pair("HELLO", "PLEASE", context, seed=5412)
    before = hashes(store.run_dir / "attempts")
    restored = runner.V2RunStore.load(root, store.run_dir, recover=True)
    assert len(restored._head_record("HELLO__PLEASE")["attempts"]) == 1
    record = restored.run_pair("HELLO", "PLEASE", context, seed=5412)
    assert record["completed"]
    assert all(hashes(store.run_dir / "attempts")[p] == digest for p, digest in before.items())
    restored.verify()


def test_power_loss_after_attempt_before_journal_recovers_without_overwrite(run_context, monkeypatch):
    root, policy, context = run_context
    store = create_store(run_context, root)
    commit = runner.V2RunStore._commit
    def power_loss(self, record):
        if len(record["attempts"]) == 1:
            raise OSError("synthetic power loss after saving attempt")
        return commit(self, record)
    with monkeypatch.context() as scope:
        scope.setattr(runner.V2RunStore, "_commit", power_loss)
        with pytest.raises(OSError, match="power loss"):
            store.run_pair("HELLO", "PLEASE", context, seed=5412)
    before = {p: h for p, h in hashes(store.run_dir).items() if p.startswith(("attempts/", "candidates/", "timing_attempts/"))}
    restored = runner.V2RunStore.load(root, store.run_dir, recover=True)
    assert restored._head_record("HELLO__PLEASE")["attempts"] == []
    record = restored.run_pair("HELLO", "PLEASE", context, seed=5412)
    assert record["completed"] and len(record["attempts"]) == 5
    after = hashes(store.run_dir)
    assert all(after[p] == digest for p, digest in before.items())


def test_power_loss_during_curve_write_reuses_only_identical_orphan_curves(run_context, monkeypatch):
    root, policy, context = run_context
    store = create_store(run_context, root)
    immutable = runner._immutable_json
    def power_loss(path, value):
        if "attempts" in Path(path).parts:
            raise OSError("synthetic power loss after saving curves")
        return immutable(path, value)
    with monkeypatch.context() as scope:
        scope.setattr(runner, "_immutable_json", power_loss)
        with pytest.raises(OSError, match="power loss"):
            store.run_pair("HELLO", "PLEASE", context, seed=5412)
    before = hashes(store.run_dir / "candidates")
    assert before
    restored = runner.V2RunStore.load(root, store.run_dir, recover=True)
    assert restored.run_pair("HELLO", "PLEASE", context, seed=5412)["completed"]
    assert all(hashes(store.run_dir / "candidates")[p] == digest for p, digest in before.items())


@pytest.mark.parametrize("relative", ["candidates/HELLO__PLEASE/attempt_00001.json",
                                      "timing_attempts/HELLO__PLEASE/attempt_00001/curve_0001.json",
                                      "policy.json", "contract.json"])
def test_corrupt_curve_or_frozen_file_is_rejected(run_context, relative):
    root, policy, context = run_context
    store = create_store(run_context, root)
    with pytest.raises(KeyboardInterrupt):
        store.run_pair("HELLO", "PLEASE", context, seed=5412, max_new_attempts=1)
    path = store.run_dir / relative
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="integrity|mismatch"):
        runner.V2RunStore.load(root, store.run_dir, recover=True)


@pytest.mark.parametrize("mutation", ["pass", "playback", "incomplete", "one_word", "identity", "curve_hash"])
def test_forged_or_incomplete_numerical_evidence_cannot_select(run_context, monkeypatch, mutation):
    root, policy, context = run_context
    store = create_store(run_context, root)
    store.run_pair("HELLO", "PLEASE", context, seed=5412)
    def invalid(root_arg, path, policy_arg):
        evidence = numerical_evidence(store, path)
        if mutation == "pass":
            evidence["status"] = "PASS_SIM"
        elif mutation == "playback":
            evidence["playback_eligible"] = True
        elif mutation == "incomplete":
            evidence["validation_complete"] = False
        elif mutation == "one_word":
            evidence["word_occurrences"] = 1
        elif mutation == "identity":
            evidence["identity"] = {"identity_hash": "0" * 64}
        else:
            evidence["trajectory_file_sha256"] = "0" * 64
        return evidence
    monkeypatch.setattr(runner, "verify_saved_pair_v2", invalid)
    with pytest.raises(runner.RunIntegrityError):
        store.verify_pair("HELLO__PLEASE")
    assert store._head_record("HELLO__PLEASE")["verification_state"] == "NOT_RUN"


def test_saved_winner_is_recomputed_and_partial_reviews_are_refused(run_context, monkeypatch):
    root, policy, context = run_context
    store = create_store(run_context, root)
    store.run_pair("HELLO", "PLEASE", context, seed=5412)
    monkeypatch.setattr(runner, "verify_saved_pair_v2", lambda root, path, policy: numerical_evidence(store, path))
    record = store.verify_pair("HELLO__PLEASE")
    other = next(a for a in record["candidate_ids"] if a != record["selected_candidate_id"])
    with pytest.raises(runner.RunIntegrityError, match="recomputed"):
        store._commit({**record, "selected_candidate_id": other})
    with pytest.raises(runner.RunIntegrityError, match="every eligible candidate"):
        store._commit({**record, "verifications": record["verifications"][:-1]})


@pytest.mark.parametrize("self_pair", [False, True])
def test_real_independent_verifier_reconstructs_saved_runner_outputs(run_context, monkeypatch, self_pair):
    import sign_robot.pair_verification_v2 as verifier
    from test_pair_routes_v2 import Model, Clearance
    root, policy, context = run_context
    monkeypatch.setattr(verifier, "freeze_library", lambda root, policy: (context.library, context.clips))
    monkeypatch.setattr(verifier, "load_model", lambda root: Model(context.library["joint_names"]))
    monkeypatch.setattr(verifier, "MujocoClearance", Clearance)
    monkeypatch.setattr(runner, "build_pair_context_v2", lambda *args: context)
    store = create_store(run_context, root)
    target = "HELLO" if self_pair else "PLEASE"
    record = store.run_pair("HELLO", target, context, seed=5412)
    summary = runner.verify_run_v2(root, store.run_dir)
    restored = runner.V2RunStore.load(root, store.run_dir)
    reviewed = restored._head_record(record["pair_id"])
    assert reviewed["verification_state"] == "COMPLETE" and reviewed["selected_candidate_id"]
    assert all(v["numerical_checks_passed"] for v in reviewed["verifications"])
    assert summary["saved_candidates"] == len(reviewed["verifications"])
    for review in reviewed["verifications"]:
        evidence = runner.read_json(store.run_dir / review["path"])["evidence"]
        assert evidence["word_occurrences"] == 2 and evidence["reconstructed_motion_canonical_hash"]
        assert len(evidence["dense_recheck_result"]) >= 9
    assert summary["groups"]["all"]["status_counts"]["PASS_SIM"] == 0


@pytest.mark.parametrize("unconfigured", [False, True])
def test_missing_candidate_diagnosis_reads_real_review_files_and_never_certifies_curve(run_context, monkeypatch, unconfigured):
    import sign_robot.pair_verification_v2 as verifier
    root, policy, context = run_context
    context.input_blockers = [{"code": "SYNTHETIC_UNAVAILABLE_REVIEW"}]
    if unconfigured:
        policy["endpoints"].update(approval_file=None, approval_bundle_sha256=None)
    store = create_store(run_context, root)
    record = store.run_pair("HELLO", "PLEASE", context, seed=5412)
    if not unconfigured:
        (root / policy["endpoints"]["approval_file"]).unlink()
    monkeypatch.setattr(verifier, "freeze_library", lambda root, policy: (context.library, context.clips))
    result = store.verify_pair(record["pair_id"])
    assert result["verification_state"] == "DIAGNOSIS_ONLY" and result["candidate_count"] == 0
    evidence = runner.read_json(store.run_dir / result["diagnosis_file"])["evidence"]
    assert evidence["status"] == "BLOCKED_INPUT"
    assert evidence["reason_codes"] == ["MISSING_APPROVAL_BUNDLE" if unconfigured else "INVALID_APPROVAL_INPUT"]
    assert evidence["numerical_checks_passed"] is False and evidence["validation_complete"] is False
    assert evidence["verification_budget"]["completed_geometry_poses"] == 0
    store.verify()
    path = store.run_dir / result["diagnosis_file"]
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(runner.RunIntegrityError, match="diagnosis hash mismatch"):
        runner.V2RunStore.load(root, store.run_dir)


@pytest.mark.parametrize("mode", ["clear", "blocked", "timeout"])
def test_no_curve_diagnosis_independently_rechecks_approved_endpoint_and_budget(run_context, monkeypatch, mode):
    import sign_robot.pair_verification_v2 as verifier
    from test_pair_routes_v2 import Model, Clearance
    root, policy, context = run_context
    context.input_blockers = [{"code": "SYNTHETIC_PLANNER_BLOCKER"}]
    if mode == "timeout":
        policy["validation"]["max_sampled_poses"] = 1
    store = create_store(run_context, root)
    record = store.run_pair("HELLO", "PLEASE", context, seed=5412)
    monkeypatch.setattr(verifier, "freeze_library", lambda root, policy: (context.library, context.clips))
    monkeypatch.setattr(verifier, "load_model", lambda root: Model(context.library["joint_names"]))
    class EndpointClearance(Clearance):
        def __call__(self, values):
            measured = super().__call__(values)
            if mode == "blocked":
                return replace(measured, min_distance_m=-0.01, frame_clearances_m=[-0.01] * len(values))
            return measured
    monkeypatch.setattr(verifier, "MujocoClearance", EndpointClearance)
    reviewed = store.verify_pair(record["pair_id"])
    evidence = runner.read_json(store.run_dir / reviewed["diagnosis_file"])["evidence"]
    assert evidence["numerical_checks_passed"] is False and evidence["infeasibility_proven"] is False
    if mode == "timeout":
        assert evidence["status"] == "TIMEOUT"
        assert evidence["verification_budget"]["completed_geometry_poses"] == 1
    elif mode == "blocked":
        assert evidence["status"] == "BLOCKED_ENDPOINT"
        assert evidence["reason_codes"] == ["SOURCE_ENDPOINT_INVALID", "TARGET_ENDPOINT_INVALID"]
    else:
        assert evidence["planner_diagnosis_only"] is True
        assert all(check["engineering_valid"] for checks in evidence["endpoint_recheck"].values() for check in checks)
    store.verify()


def test_summary_power_loss_is_recoverable_without_touching_pair_evidence(run_context, monkeypatch):
    root, policy, context = run_context
    store = create_store(run_context, root)
    store.run_pair("HELLO", "PLEASE", context, seed=5412)
    store.summarize()
    before = hashes(store.run_dir / "checkpoints")
    atomic = runner.atomic_bytes
    def power_loss(path, value):
        if Path(path).name == "pairs.jsonl":
            raise OSError("synthetic power loss during summary export")
        return atomic(path, value)
    with monkeypatch.context() as scope:
        scope.setattr(runner, "atomic_bytes", power_loss)
        with pytest.raises(OSError, match="power loss"):
            store.summarize()
    restored = runner.V2RunStore.load(root, store.run_dir, recover=True)
    restored.summarize()
    assert hashes(store.run_dir / "checkpoints") == before
