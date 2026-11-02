"""Batch control: soft stops at saved breakpoints, single writer, backlog gate and frozen batch files."""
import json
from types import SimpleNamespace

import pytest

import sign_robot.pair_runner_v2 as runner
from sign_robot.batch_control import (
    GIB, BatchControlError, SingleWriterLock, SoftBudget, load_batch_manifest, run_pair_batch, write_new_log,
)
from sign_robot.pair_contract import file_hash
from test_pair_runner_v2 import create_store, numerical_evidence, run_context  # noqa: F401  (fixture)

HELLO_PLEASE_SEED = 5412 + 1  # universe index 1, as in run_scan_v2


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def disk(free):
    return lambda path: SimpleNamespace(free=free, total=free * 10)


def budget(root, *, clock=None, free=10**12, floor=0, wall=100):
    return SoftBudget(wall, floor, root, clock=clock or Clock(), disk_usage=disk(free))


def batch(*pairs):
    return {"batch_id": "b1", "group": "test", "pair_ids": list(pairs)}


def test_soft_wall_time_stops_between_pairs_and_selects_nothing(run_context, monkeypatch):
    root, policy, context = run_context
    store = create_store(run_context, root)
    clock = Clock()
    original = store.run_pair

    def plan_then_expire(*args, **kwargs):
        result = original(*args, **kwargs)
        clock.now = 1_000
        return result

    monkeypatch.setattr(store, "run_pair", plan_then_expire)
    result = run_pair_batch(store, context, batch("HELLO__PLEASE", "PLEASE__HELLO"), budget=budget(root, clock=clock),
                            seed_base=5412)
    states = {s["pair_id"]: s for s in result["pairs"]}
    assert result["stop_reason"] == "SOFT_WALL_TIME_REACHED"
    assert states["HELLO__PLEASE"]["planning_state"] == "COMPLETE"
    assert states["HELLO__PLEASE"]["verification_state"] == "NOT_RUN"
    assert states["PLEASE__HELLO"]["status"] == "NOT_RUN"
    assert all(s.get("selected_candidate_id") is None for s in result["pairs"])
    reloaded = runner.V2RunStore.load(root, store.run_dir, recover=True)
    summary = reloaded.summarize()
    assert summary["verification_complete"] is False and summary["formal_acceptance_enabled"] is False


def test_verification_pauses_at_a_candidate_breakpoint_and_resume_reuses_saved_reviews(run_context, monkeypatch):
    root, policy, context = run_context
    store = create_store(run_context, root)
    monkeypatch.setattr(runner, "verify_saved_pair_v2", lambda r, path, p: numerical_evidence(store, path))
    record = store.run_pair("HELLO", "PLEASE", context, seed=HELLO_PLEASE_SEED)
    assert record["candidate_count"] >= 2
    calls = {"count": 0}

    def stop_after_one_review():
        calls["count"] += 1
        return "SOFT_WALL_TIME_REACHED" if calls["count"] > 1 else None

    with pytest.raises(runner.VerificationPaused):
        store.verify_pair("HELLO__PLEASE", should_stop=stop_after_one_review)
    paused = store._head_record("HELLO__PLEASE")
    assert paused["verification_state"] == "NOT_RUN" and paused["selected_candidate_id"] is None
    saved = sorted((store.run_dir / "verification/HELLO__PLEASE").glob("attempt_*.json"))
    assert len(saved) == 1
    before = saved[0].read_bytes()
    result = run_pair_batch(store, context, batch("HELLO__PLEASE"), budget=budget(root), seed_base=5412)
    assert result["stop_reason"] == "BATCH_COMPLETE" and saved[0].read_bytes() == before
    assert store._head_record("HELLO__PLEASE")["selected_candidate_id"] is not None
    store.verify()


def test_disk_floor_stops_before_any_new_work(run_context):
    root, policy, context = run_context
    store = create_store(run_context, root)
    result = run_pair_batch(store, context, batch("HELLO__PLEASE"), budget=budget(root, free=GIB, floor=5 * GIB),
                            seed_base=5412)
    assert result["stop_reason"] == "DISK_FREE_BELOW_FLOOR"
    assert store.manifest["heads"] == {} and result["pairs"][0]["status"] == "NOT_RUN"


def test_unreviewed_backlog_blocks_the_next_batch_but_not_its_own_resume(run_context, monkeypatch):
    root, policy, context = run_context
    store = create_store(run_context, root)
    store.run_pair("HELLO", "PLEASE", context, seed=HELLO_PLEASE_SEED)
    blocked = run_pair_batch(store, context, batch("PLEASE__HELLO"), budget=budget(root), seed_base=5412)
    assert blocked["stop_reason"] == "BACKLOG_NOT_CLEARED" and blocked["backlog"] == ["HELLO__PLEASE"]
    assert store._head_record("PLEASE__HELLO") is None
    monkeypatch.setattr(runner, "verify_saved_pair_v2", lambda r, path, p: numerical_evidence(store, path))
    resumed = run_pair_batch(store, context, batch("HELLO__PLEASE"), budget=budget(root), seed_base=5412)
    assert resumed["stop_reason"] == "BATCH_COMPLETE" and resumed["backlog_after"] == []


def test_completed_failure_is_neither_replanned_nor_reselected(run_context, monkeypatch):
    root, policy, context = run_context
    store = create_store(run_context, root)
    monkeypatch.setattr(runner, "verify_saved_pair_v2", lambda r, path, p: numerical_evidence(store, path, positive=False))
    first = run_pair_batch(store, context, batch("HELLO__PLEASE"), budget=budget(root), seed_base=5412)
    assert first["stop_reason"] == "BATCH_COMPLETE" and first["pairs"][0]["selected_candidate_id"] is None
    attempts = first["pairs"][0]["attempt_count"]
    monkeypatch.setattr(runner, "iter_deterministic_attempts_v2", lambda *a, **k: pytest.fail("completed pair replanned"))
    monkeypatch.setattr(runner, "verify_saved_pair_v2", lambda *a, **k: pytest.fail("completed review repeated"))
    again = run_pair_batch(store, context, batch("HELLO__PLEASE"), budget=budget(root), seed_base=5412)
    assert again["stop_reason"] == "BATCH_COMPLETE" and again["pairs"][0]["attempt_count"] == attempts
    assert again["pairs"][0]["selected_candidate_id"] is None


def test_second_writer_is_refused_and_lock_is_released(tmp_path):
    lock = tmp_path / "control/run.lock"
    with SingleWriterLock(lock):
        with pytest.raises(BatchControlError) as caught:
            with SingleWriterLock(lock):
                pass
        assert caught.value.code == "RUN_LOCKED_BY_ANOTHER_WRITER"
    with SingleWriterLock(lock):
        pass


def test_invocation_logs_are_append_only(tmp_path):
    first = write_new_log(tmp_path / "logs", {"n": 1})
    second = write_new_log(tmp_path / "logs", {"n": 2})
    assert first != second and json.loads(first.read_text()) == {"n": 1}


def _manifest(root, batches, *, universe, policy="policy.json"):
    (root / policy).write_text("{}")
    entries = []
    for name, pairs in batches.items():
        path = root / f"{name}.json"
        path.write_text(json.dumps({"pair_ids": pairs}))
        entries.append({"batch_id": name, "group": "g", "file": path.name, "sha256": file_hash(path), "pair_count": len(pairs)})
    manifest = {"schema_version": 1, "kind": "hospital35_pair_batches_v1", "policy": {"path": policy, "sha256": file_hash(root / policy)},
                "batches": entries, "order": list(batches), "limits": {}}
    (root / "manifest.json").write_text(json.dumps(manifest))
    return file_hash(root / "manifest.json")


def test_frozen_batch_manifest_rejects_tampering_overlap_gaps_and_oversize(tmp_path):
    universe = ["A__A", "A__B", "B__A", "B__B"]
    good = _manifest(tmp_path, {"one": ["A__A", "A__B"], "two": ["B__A", "B__B"]}, universe=universe)
    manifest, batches = load_batch_manifest(tmp_path, "manifest.json", good, universe, "policy.json")
    assert list(batches) == ["one", "two"]
    cases = {
        "BATCHES_OVERLAP": {"one": ["A__A", "A__B"], "two": ["A__B", "B__A", "B__B"]},
        "BATCHES_DO_NOT_COVER_UNIVERSE_IN_ORDER": {"one": ["A__A", "A__B"], "two": ["B__A"]},
    }
    for code, layout in cases.items():
        sha = _manifest(tmp_path, layout, universe=universe)
        with pytest.raises(BatchControlError) as caught:
            load_batch_manifest(tmp_path, "manifest.json", sha, universe, "policy.json")
        assert caught.value.code == code
    big = [f"P{i}__P{i}" for i in range(17)]
    sha = _manifest(tmp_path, {"big": big}, universe=big)
    with pytest.raises(BatchControlError) as caught:
        load_batch_manifest(tmp_path, "manifest.json", sha, big, "policy.json")
    assert caught.value.code == "INVALID_BATCH"
    sha = _manifest(tmp_path, {"one": ["A__A", "A__B"], "two": ["B__A", "B__B"]}, universe=universe)
    (tmp_path / "two.json").write_text(json.dumps({"pair_ids": ["B__B", "B__A"]}))
    with pytest.raises(BatchControlError) as caught:
        load_batch_manifest(tmp_path, "manifest.json", sha, universe, "policy.json")
    assert caught.value.code == "BATCH_FILE_HASH_MISMATCH"
    with pytest.raises(BatchControlError) as caught:
        load_batch_manifest(tmp_path, "manifest.json", "0" * 64, universe, "policy.json")
    assert caught.value.code == "BATCH_MANIFEST_HASH_MISMATCH"


def test_stop_request_and_identity_drift_stop_before_new_work(run_context, monkeypatch, tmp_path):
    root, policy, context = run_context
    store = create_store(run_context, root)
    stop_file = tmp_path / "run.stop"
    stop_file.write_text("")
    stopped = run_pair_batch(store, context, batch("HELLO__PLEASE"),
                             budget=SoftBudget(100, 0, root, stop_file=stop_file, clock=Clock(), disk_usage=disk(10**12)),
                             seed_base=5412)
    assert stopped["stop_reason"] == "STOP_REQUESTED" and store.manifest["heads"] == {}
    drifted = []
    monkeypatch.setattr(runner, "verify_saved_pair_v2", lambda *a, **k: pytest.fail("review ran after identity drift"))
    original = store.run_pair

    def plan_then_drift(*args, **kwargs):
        result = original(*args, **kwargs)
        drifted.append(True)
        return result

    monkeypatch.setattr(store, "run_pair", plan_then_drift)
    guarded = SoftBudget(100, 0, root, drift=lambda: "IDENTITY_CHANGED_DURING_RUN" if drifted else None,
                         clock=Clock(), disk_usage=disk(10**12))
    result = run_pair_batch(store, context, batch("HELLO__PLEASE"), budget=guarded, seed_base=5412)
    assert result["stop_reason"] == "IDENTITY_CHANGED_DURING_RUN"
    assert result["pairs"][0]["verification_state"] == "NOT_RUN" and result["pairs"][0]["reviewed_candidates"] == 0
    assert not (store.run_dir / "verification/HELLO__PLEASE").exists()
