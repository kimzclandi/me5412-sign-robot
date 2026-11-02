"""Frozen scope, content integrity and explicit development-only acceptance."""
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from sign_robot.motion import ROOT
from sign_robot.pair_contract import (
    acceptance_pending, atomic_bytes, atomic_motion, boundary_derivatives,
    canonical_array_hash, file_hash, inside, json_hash, load_policy, pair_universe,
    read_motion, run_directory,
)


@pytest.fixture
def policy():
    return load_policy(ROOT / "config/transition_policy.json")


def test_frozen_scope_contains_all_ordered_pairs_and_self_pairs(policy):
    pairs = pair_universe(policy["scope"]["expected_glosses"])
    assert len(pairs) == len({p["pair_id"] for p in pairs}) == 1225
    assert sum(p["self_pair"] for p in pairs) == 35
    assert sum(not p["self_pair"] for p in pairs) == 1190
    assert {"NURSE__DOCTOR", "DOCTOR__NURSE", "NURSE__NURSE"} <= {p["pair_id"] for p in pairs}


@pytest.mark.parametrize("mutation", [
    lambda p: p["scope"].update(include_self=False),
    lambda p: p["scope"]["expected_glosses"].append("HELLO"),
    lambda p: p["quality"].update(freeze_status="frozen"),
    lambda p: p["constraints"].update(min_clearance_m=-0.002),
    lambda p: p["constraints"].update(arm_speed_rad_s=float("nan")),
    lambda p: p["endpoints"].update(approved_windows={"NURSE": [80, 80]}),
    lambda p: p["validation"].update(dense_factors=[1]),
    lambda p: p["planner"].update(max_candidates=2),
])
def test_policy_cannot_silently_change_scope_or_claim_unfrozen_acceptance(tmp_path, policy, mutation):
    import json
    mutation(policy)
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(policy))
    with pytest.raises(ValueError):
        load_policy(path)


def test_review_flags_alone_cannot_promote_a_development_result(policy):
    policy["quality"]["freeze_status"] = "frozen"
    policy["quality"]["limits"] = dict.fromkeys(policy["quality"]["limits"], 1e20)
    policy["endpoints"]["review_status"] = "approved"
    assert acceptance_pending(policy) == ["APPROVED_CORE_CONTRACT_NOT_IMPLEMENTED"]


def test_array_hash_is_canonical_across_byte_orders_layouts_and_npz_formats(tmp_path):
    motion = {"timestamps_s": np.array([0, 0.5, 1.0]), "joint_names": np.array(["elbow", "finger"]),
              "positions": np.array([[0, -0.0], [0.125, 0.5], [0.25, 1.0]])}
    variant = {"timestamps_s": motion["timestamps_s"].astype(">f8"), "joint_names": motion["joint_names"],
               "positions": np.asfortranarray(motion["positions"].astype(">f8"))}
    assert canonical_array_hash(motion) == canonical_array_hash(variant)
    first, second = tmp_path / "first.npz", tmp_path / "second.npz"
    np.savez(first, **motion)
    atomic_motion(second, variant)
    assert file_hash(first) != file_hash(second)
    assert canonical_array_hash(read_motion(first)) == canonical_array_hash(read_motion(second))
    variant["positions"][1, 1] += 1e-5
    assert canonical_array_hash(motion) != canonical_array_hash(variant)


def test_atomic_replacement_failure_preserves_previous_checkpoint(tmp_path, monkeypatch):
    import sign_robot.pair_contract as contract
    path = tmp_path / "checkpoint.json"
    path.write_bytes(b"complete original")
    def fail(*args):
        raise OSError("simulated filesystem interruption")
    monkeypatch.setattr(contract.os, "replace", fail)
    with pytest.raises(OSError):
        atomic_bytes(path, b"new incomplete")
    assert path.read_bytes() == b"complete original"
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("run_id", ["../other", "..", "/tmp/other", "a/b", ""])
def test_run_id_does_not_escape_results_root(tmp_path, run_id):
    with pytest.raises(ValueError):
        run_directory(tmp_path, run_id)


def test_artifact_symlink_cannot_escape_run_directory(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    (tmp_path / "outside").write_text("outside")
    (run / "asset").symlink_to(tmp_path / "outside")
    with pytest.raises(ValueError):
        inside(run, "asset")


@pytest.mark.parametrize("side,frame", [("source", 6), ("target", 2)])
def test_boundary_derivatives_use_timestamps_and_one_sided_windows(side, frame):
    t = np.arange(10) / 30
    q = (1 + 2 * t + 3 * t * t)[:, None]
    result = boundary_derivatives({"timestamps_s": t, "positions": q}, frame, side, 5)
    np.testing.assert_allclose(result["velocity"], [2 + 6 * t[frame]], atol=1e-11)
    np.testing.assert_allclose(result["acceleration"], [6], atol=1e-10)
    if side == "source":
        assert result["frames"][1] == frame
    else:
        assert result["frames"][0] == frame
