"""Positive and negative tests for the opt-in all-pairs v2 representation."""
from copy import deepcopy
import json

import numpy as np
import pytest

from sign_robot.motion import ROOT
from sign_robot.pair_contract import (
    V2_REPRESENTATION,
    json_hash,
    file_hash,
    freeze_library,
    load_policy,
    read_pair_trajectory,
    save_pair_trajectory,
    validate_trajectory_v2,
)


def _identity():
    base = {
        "library_version": "hospital_v1@" + "a" * 64,
        "model_hash": "b" * 64,
        "code_commit": "c" * 40,
        "code_hash": "d" * 64,
        "policy_hash": "e" * 64,
        "environment_id": "f" * 64,
    }
    return {**base, "identity_hash": json_hash(base)}


def _trajectory():
    names = [f"joint_{i}" for i in range(53)]
    zero = [0.0] * 53
    coeff = [[0.0] * 6 for _ in range(53)]
    return {
        "schema_version": 2,
        "representation": V2_REPRESENTATION,
        "pair_id": "HELLO__PLEASE",
        "fps": 30,
        "joint_names": names,
        "word_instances": [
            {"instance_id": "HELLO#0", "gloss": "HELLO", "motion_sha256": "1" * 64,
             "source_frames": [0, 3], "protected_core_frames": [1, 2],
             "approval_id": "hello-pending", "approval_sha256": "2" * 64},
            {"instance_id": "PLEASE#1", "gloss": "PLEASE", "motion_sha256": "3" * 64,
             "source_frames": [0, 3], "protected_core_frames": [1, 2],
             "approval_id": "please-pending", "approval_sha256": "4" * 64},
        ],
        "segments": [
            {"kind": "source_slice_v2", "start_time_s": 0.0, "end_time_s": 0.1,
             "word_instance_id": "HELLO#0", "source_frames": [0, 3],
             "interpolation": "linear", "time_scale": 1.0},
            {"kind": "polynomial_v2", "start_time_s": 0.1, "end_time_s": 0.4,
             "coefficients": coeff},
            {"kind": "source_slice_v2", "start_time_s": 0.4, "end_time_s": 0.5,
             "word_instance_id": "PLEASE#1", "source_frames": [0, 3],
             "interpolation": "linear", "time_scale": 1.0},
        ],
        "finger_strategy": {"name": "synchronous", "version": 2,
                             "start_fraction": 0.0, "end_fraction": 1.0},
        "planner": {"method": "direct", "method_version": 2, "seed": 5412,
                    "budget": {"max_candidates": 128, "max_collision_samples": 32768,
                               "max_nodes": 4096, "max_segments": 256, "max_time_attempts": 12,
                               "wall_time_s": 30.0}},
        "boundary": {"method": "linear_replay_one_sided_v2",
                      "start": {"position": zero, "velocity": zero, "acceleration": zero},
                      "end": {"position": zero, "velocity": zero, "acceleration": zero}},
        "identity": _identity(),
    }


def test_v1_default_reader_remains_strict_and_v2_is_explicit():
    v1 = load_policy(ROOT / "config/transition_policy.json")
    assert v1["schema_version"] == 1
    with pytest.raises(ValueError, match="Unsupported transition policy schema"):
        load_policy(ROOT / "config/transition_policy_v2.json")
    v2 = load_policy(ROOT / "config/transition_policy_v2.json", supported_versions=(1, 2))
    assert v2["schema_version"] == 2 and v2["formal_acceptance_enabled"] is False


def test_v2_policy_contract_file_is_hash_bound_and_pending():
    policy = load_policy(ROOT / "config/transition_policy_v2.json", supported_versions=(1, 2))
    contract = ROOT / policy["contract"]["path"]
    assert contract.is_file()
    assert file_hash(contract) == policy["contract"]["sha256"]
    assert policy["endpoints"]["review_status"] == "pending"
    assert policy["validation"]["approval_status"] == "pending"
    assert policy["quality"]["freeze_status"] == "pending"


def test_v2_valid_pair_round_trips_through_integrity_envelope(tmp_path):
    trajectory = _trajectory()
    assert validate_trajectory_v2(trajectory) is trajectory
    path = tmp_path / "pair-v2.json"
    save_pair_trajectory(path, trajectory)
    loaded = read_pair_trajectory(path, schema_version=2)
    assert loaded["pair_id"] == "HELLO__PLEASE"
    assert loaded["representation"] == V2_REPRESENTATION
    with pytest.raises(ValueError):
        read_pair_trajectory(path, schema_version=1)


@pytest.mark.parametrize("mutation,match", [
    (lambda t: t.update(pair_id="NOPE__PLEASE"), "Pair identity"),
    (lambda t: t["segments"][1].update(kind="unknown"), "Unsupported segment representation"),
    (lambda t: t["segments"][1].update(start_time_s=0.2), "contiguous timeline"),
    (lambda t: t["segments"][0].update(time_scale=0.9), "timing changed"),
    (lambda t: t["word_instances"][1].update(approval_sha256="bad"), "lowercase SHA-256"),
    (lambda t: t["finger_strategy"].update(name="random"), "Unsupported finger strategy"),
    (lambda t: t["identity"].update(identity_hash="0" * 64), "identity hash"),
    (lambda t: t["segments"][1]["coefficients"][0].__setitem__(0, float("nan")), "JSON compliant"),
    (lambda t: t["segments"][2].update(source_frames=[0, 4]), "timing changed"),
    (lambda t: t["word_instances"][0].update(protected_core_frames=[0, 4]), "protected core"),
    (lambda t: t["planner"]["budget"].update(max_nodes=True), "integer >= 1"),
    (lambda t: t["segments"][1]["coefficients"][0].__setitem__(0, True), "finite number"),
    (lambda t: t["segments"][1]["coefficients"][0].pop(), "6 coordinates"),
])
def test_v2_rejects_malformed_or_unapproved_representation(mutation, match):
    trajectory = _trajectory()
    mutation(trajectory)
    with pytest.raises(ValueError, match=match):
        validate_trajectory_v2(trajectory)


@pytest.mark.parametrize("mutation,match", [
    (lambda p: p.update(formal_acceptance_enabled=True), "Formal v2 acceptance"),
    (lambda p: p["validation"].update(maximum_step_rad=0.05), "coarsen"),
    (lambda p: p["quality"].update(freeze_status="frozen"), "approval evidence"),
    (lambda p: p["validation"].update(approval_status="approved"), "approval evidence"),
    (lambda p: p["planner"]["budget"].update(max_nodes=0), "integer >= 1"),
])
def test_v2_policy_rejects_unapproved_relaxations(mutation, match, tmp_path):
    policy = json.loads((ROOT / "config/transition_policy_v2.json").read_text())
    mutation(policy)
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(policy))
    with pytest.raises(ValueError, match=match):
        load_policy(path, supported_versions=(1, 2))


def test_v2_does_not_treat_approval_status_as_approval():
    policy = load_policy(ROOT / "config/transition_policy_v2.json", supported_versions=(1, 2))
    policy["endpoints"]["review_status"] = "approved"
    with pytest.raises(ValueError, match="hash-bound bundle"):
        from sign_robot.pair_contract import validate_policy_v2
        validate_policy_v2(policy)


def test_multisegment_curve_retains_c2_continuity_and_two_self_occurrences(tmp_path):
    trajectory = _trajectory()
    trajectory["pair_id"] = "HELLO__HELLO"
    trajectory["word_instances"][1]["gloss"] = "HELLO"
    first = trajectory["segments"][1]
    second = deepcopy(first)
    first["end_time_s"] = 0.25
    second["start_time_s"] = 0.25
    trajectory["segments"].insert(2, second)
    path = tmp_path / "self.json"
    save_pair_trajectory(path, trajectory)
    loaded = read_pair_trajectory(path, schema_version=2)
    assert len(loaded["word_instances"]) == 2
    assert len({w["instance_id"] for w in loaded["word_instances"]}) == 2
    second["coefficients"][0][0] = 0.001
    with pytest.raises(ValueError, match="continuity"):
        validate_trajectory_v2(trajectory)


def test_integrity_and_declared_boundaries_are_separate_checks(tmp_path):
    path = tmp_path / "curve.json"
    save_pair_trajectory(path, _trajectory())
    envelope = json.loads(path.read_text())
    envelope["trajectory"]["segments"][1]["coefficients"][0][1] = 0.01
    path.write_text(json.dumps(envelope))
    with pytest.raises(ValueError, match="integrity mismatch"):
        read_pair_trajectory(path, schema_version=2)
    envelope["trajectory_hash"] = json_hash(envelope["trajectory"])
    path.write_text(json.dumps(envelope))
    with pytest.raises(ValueError, match="boundary differs"):
        read_pair_trajectory(path, schema_version=2)


@pytest.mark.parametrize("version", [0, 3, True, "2", 2.0])
def test_unknown_or_noninteger_saved_versions_are_rejected(version, tmp_path):
    with pytest.raises(ValueError):
        read_pair_trajectory(tmp_path / "not-read", schema_version=version)


def test_legacy_saved_motion_still_round_trips(tmp_path):
    motion = {"timestamps_s": np.array([0.0, 1 / 30]),
              "positions": np.array([[0.0], [0.1]]), "joint_names": np.array(["elbow"])}
    path = tmp_path / "v1.npz"
    np.savez(path, **motion)
    loaded = read_pair_trajectory(path, schema_version=1)
    for key in motion:
        np.testing.assert_array_equal(loaded[key], motion[key])


def test_saved_polynomial_expresses_nonzero_boundary_derivatives():
    trajectory = _trajectory()
    trajectory["segments"][1]["coefficients"][0] = [0.0, 1.0, 2.0, 3.0, 0.0, 0.0]
    for side, values in (("start", (0.0, 1 / 0.3, 4 / 0.3**2)),
                         ("end", (6.0, 14 / 0.3, 22 / 0.3**2))):
        trajectory["boundary"][side] = {
            name: [value] + [0.0] * 52
            for name, value in zip(("position", "velocity", "acceleration"), values)
        }
    assert validate_trajectory_v2(trajectory) is trajectory


def test_frozen_v2_inputs_include_actual_contract_bytes():
    policy = load_policy(ROOT / "config/transition_policy_v2.json", supported_versions=(1, 2))
    policy["contract"]["sha256"] = "0" * 64
    library, _ = freeze_library(ROOT, policy)
    assert {"code": "RESOURCE_HASH_MISMATCH", "path": "contracts/all_pairs_v2.json"} in library["input_errors"]
