"""Fresh-file v2 reconstruction and failure cases; synthetic reviews only."""
from copy import deepcopy
import itertools
import json

import numpy as np
import pytest

import sign_robot.pair_verification_v2 as verifier
from sign_robot.pair_contract import run_identity, save_pair_trajectory
from sign_robot.pair_windows import load_window_approvals
from sign_robot.transitions import ClearanceResult
from pair_v2_fixtures import NOW, synthetic_inputs


class Joint:
    def __init__(self, name):
        self.name = name
        self.range = np.array([-10.0, 10.0])
        self.limited = np.array([True])


class Model:
    def __init__(self, names):
        self._joints = {str(name): Joint(str(name)) for name in names}
        self.njnt = len(names)

    def joint(self, value):
        if isinstance(value, (int, np.integer)):
            return list(self._joints.values())[int(value)]
        return self._joints[str(value)]


class FakeClearance:
    def __init__(self, model, names, library_path=None):
        self.vendor_structural_gaps = []

    def __call__(self, positions):
        q = np.asarray(positions)
        # Narrow synthetic obstruction at a non-playback segment boundary.
        distances = np.where(np.abs(q[:, 0] - 0.4) < 1e-6, -0.01, 0.01)
        frame = int(np.argmin(distances))
        distance = float(distances[frame])
        contact = {"bodies": ["left_hand", "right_hand"], "geoms": ["a", "b"],
                   "geom_ids": [0, 1], "distance_m": distance, "frame": frame}
        return ClearanceResult(distance >= 0.002, distance, [contact] if distance < 0 else [], len(q),
                               [], contact, [], distances.tolist())


def _trajectory(policy, library, approvals):
    zero = [0.0] * 53
    return {
        "schema_version": 2, "representation": "piecewise_polynomial_v2", "pair_id": "HELLO__PLEASE",
        "fps": 30, "joint_names": library["joint_names"],
        "word_instances": [
            {"instance_id": "HELLO#0", "gloss": "HELLO", "motion_sha256": approvals["HELLO"].motion_sha256,
             "source_frames": [0, 6], "protected_core_frames": [3, 5],
             "approval_id": approvals["HELLO"].approval_id, "approval_sha256": approvals["HELLO"].approval_sha256},
            {"instance_id": "PLEASE#1", "gloss": "PLEASE", "motion_sha256": approvals["PLEASE"].motion_sha256,
             "source_frames": [2, 8], "protected_core_frames": [3, 5],
             "approval_id": approvals["PLEASE"].approval_id, "approval_sha256": approvals["PLEASE"].approval_sha256},
        ],
        "segments": [
            {"kind": "source_slice_v2", "start_time_s": 0.0, "end_time_s": 0.2,
             "word_instance_id": "HELLO#0", "source_frames": [0, 6], "interpolation": "linear", "time_scale": 1.0},
            {"kind": "polynomial_v2", "start_time_s": 0.2, "end_time_s": 0.5,
             "coefficients": [[0.0] * 6 for _ in range(53)]},
            {"kind": "source_slice_v2", "start_time_s": 0.5, "end_time_s": 0.7,
             "word_instance_id": "PLEASE#1", "source_frames": [2, 8], "interpolation": "linear", "time_scale": 1.0},
        ],
        "finger_strategy": {"name": "synchronous", "version": 2, "start_fraction": 0.0, "end_fraction": 1.0},
        "planner": {"method": "direct", "method_version": 2, "seed": 5412, "budget": policy["planner"]["budget"]},
        "boundary": {"method": "linear_replay_one_sided_v2",
                      "start": {"position": zero.copy(), "velocity": zero.copy(), "acceleration": zero.copy()},
                      "end": {"position": zero.copy(), "velocity": zero.copy(), "acceleration": zero.copy()}},
        "identity": run_identity(library, policy),
    }


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    policy, library, clips, bundle = synthetic_inputs(tmp_path)
    library.update(library="hospital_v1", library_version="hospital_v1@" + "a" * 64,
                   model_hash="b" * 64, code_commit="c" * 40, code_hash="d" * 64,
                   environment={"environment_id": "e" * 64}, input_errors=[], couplings=[])
    for word in library["words"]:
        word["input_errors"] = []
    approvals = load_window_approvals(tmp_path, policy, library, now=NOW)
    trajectory = _trajectory(policy, library, approvals)
    monkeypatch.setattr(verifier, "freeze_library", lambda root, policy: (library, clips))
    monkeypatch.setattr(verifier, "load_model", lambda root: Model(library["joint_names"]))
    monkeypatch.setattr(verifier, "MujocoClearance", FakeClearance)
    return policy, library, clips, trajectory


def write_trajectory(tmp_path, trajectory, policy, library):
    trajectory["identity"] = run_identity(library, policy)
    path = tmp_path / "pair-v2.json"
    save_pair_trajectory(path, trajectory)
    return path


def test_saved_curve_reconstruction_preserves_slices_and_stays_pending(inputs, tmp_path):
    policy, library, clips, trajectory = inputs
    evidence = verifier.verify_saved_pair_v2(tmp_path, write_trajectory(tmp_path, trajectory, policy, library), policy)
    assert evidence["artifact_contract_passed"] and evidence["approval_checks_passed"]
    assert evidence["validation_complete"] and evidence["numerical_checks_passed"]
    assert evidence["status"] == "FAILED_QUALITY" and evidence["playback_eligible"] is False
    assert evidence["word_occurrences"] == 2 and evidence["protected_core_preserved"]
    assert len(evidence["dense_recheck_result"]) == 9


def test_real_curve_boundary_between_playback_frames_is_checked(inputs, tmp_path):
    policy, library, clips, trajectory = inputs
    first = trajectory["segments"][1]
    second = deepcopy(first)
    first["end_time_s"] = 0.35
    first["coefficients"][0] = [0, 0, 0, 4, -6, 2.4]
    second["start_time_s"] = 0.35
    second["coefficients"][0] = [0.4, 0, 0, -4, 6, -2.4]
    trajectory["segments"].insert(2, second)
    replay = verifier._full_replay(trajectory, clips)
    assert not np.any(np.abs(replay["positions"][:, 0] - 0.4) < 1e-6)
    evidence = verifier.verify_saved_pair_v2(tmp_path, write_trajectory(tmp_path, trajectory, policy, library), policy)
    assert evidence["status"] == "FAILED_SEARCH" and evidence["numerical_checks_passed"] is False
    assert "DENSE_CONNECTOR_COLLISION" in evidence["reason_codes"]
    assert any(row["min_clearance_mm"] < 0 for row in evidence["dense_recheck_result"])


@pytest.mark.parametrize("field,value", [("max_sampled_poses", 1), ("max_native_collision_calls", 1)])
def test_budget_exhaustion_is_incomplete_and_never_passes(inputs, tmp_path, field, value):
    policy, library, clips, trajectory = inputs
    policy["validation"][field] = value
    evidence = verifier.verify_saved_pair_v2(tmp_path, write_trajectory(tmp_path, trajectory, policy, library), policy)
    assert evidence["status"] == "TIMEOUT" and evidence["validation_complete"] is False
    assert evidence["numerical_checks_passed"] is None and evidence["playback_eligible"] is False


def test_wall_time_limit_is_checked_before_geometry(inputs, tmp_path, monkeypatch):
    policy, library, clips, trajectory = inputs
    path = write_trajectory(tmp_path, trajectory, policy, library)
    ticks = itertools.chain([0.0], itertools.repeat(31.0))
    monkeypatch.setattr(verifier.time, "monotonic", lambda: next(ticks))
    evidence = verifier.verify_saved_pair_v2(tmp_path, path, policy)
    assert evidence["status"] == "TIMEOUT"
    assert evidence["reason_codes"] == ["VERIFICATION_WALL_TIME_LIMIT"]


def test_actual_source_motion_mutation_is_rejected(inputs, tmp_path):
    policy, library, clips, trajectory = inputs
    path = write_trajectory(tmp_path, trajectory, policy, library)
    motion_path = tmp_path / library["words"][0]["motion"]
    motion_path.write_bytes(motion_path.read_bytes() + b"altered")
    evidence = verifier.verify_saved_pair_v2(tmp_path, path, policy)
    assert evidence["status"] == "BLOCKED_INPUT"
    assert evidence["reason_codes"] == ["STALE_MOTION_APPROVAL"]


def test_changed_word_mapping_or_fake_core_reference_cannot_pass(inputs, tmp_path):
    policy, library, clips, trajectory = inputs
    trajectory["word_instances"][0]["approval_sha256"] = "0" * 64
    evidence = verifier.verify_saved_pair_v2(tmp_path, write_trajectory(tmp_path, trajectory, policy, library), policy)
    assert evidence["status"] == "ERROR" and evidence["validation_complete"] is False
    assert "actual review" in evidence["diagnostic_details"]["message"]


def test_corrupt_or_unknown_saved_representation_fails_before_geometry(inputs, tmp_path):
    policy, library, clips, trajectory = inputs
    path = write_trajectory(tmp_path, trajectory, policy, library)
    envelope = json.loads(path.read_text())
    envelope["trajectory"]["representation"] = "rrt_samples_with_unknown_interpolation"
    from sign_robot.pair_contract import json_hash
    envelope["trajectory_hash"] = json_hash(envelope["trajectory"])
    path.write_text(json.dumps(envelope))
    evidence = verifier.verify_saved_pair_v2(tmp_path, path, policy)
    assert evidence["status"] == "ERROR" and evidence["artifact_contract_passed"] is False


def test_full_replay_budget_is_checked_before_allocating_timeline(inputs):
    _, _, clips, trajectory = inputs
    with pytest.raises(verifier.VerificationBudgetExceeded, match="PLAYBACK_GRID"):
        verifier._full_replay(trajectory, clips, max_samples=1)


def test_independent_analytic_extrema_and_jerk_integral_match_known_curve():
    segment = {"start_time_s": 0.0, "end_time_s": 1.0,
               "coefficients": [[0, 0, 0, 10, -15, 6]] + [[0] * 6 for _ in range(52)]}
    measured = verifier._analytic_metrics([segment])
    assert measured["speed"][0] == pytest.approx(1.875)
    assert measured["acceleration"][0] == pytest.approx(10 / np.sqrt(3))
    assert measured["jerk"][0] == pytest.approx(60)
    assert measured["jerk_integral"] == pytest.approx(720)
    assert measured["lower_positions"][0] == pytest.approx(0, abs=1e-12)
    assert measured["upper_positions"][0] == pytest.approx(1, abs=1e-12)


def test_self_pair_reconstruction_keeps_two_original_occurrences(inputs, tmp_path):
    policy, library, clips, trajectory = inputs
    target = trajectory["word_instances"][1]
    source = trajectory["word_instances"][0]
    for key in ("gloss", "motion_sha256", "approval_id", "approval_sha256"):
        target[key] = source[key]
    target["instance_id"] = "HELLO#1"
    trajectory["pair_id"] = "HELLO__HELLO"
    trajectory["segments"][-1]["word_instance_id"] = target["instance_id"]
    evidence = verifier.verify_saved_pair_v2(tmp_path, write_trajectory(tmp_path, trajectory, policy, library), policy)
    assert evidence["numerical_checks_passed"] is True
    assert evidence["word_occurrences"] == 2 and evidence["replay_frame_count"] == 22
