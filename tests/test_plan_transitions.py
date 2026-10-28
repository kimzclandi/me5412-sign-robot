"""Transition contract checks, separate from source-clip quality/ASL review."""

import json

import numpy as np
import pytest

from sign_robot.motion import ROOT, validate_motion
from sign_robot.transitions import (
    FPS,
    ClearanceResult,
    MujocoClearance,
    joint_rate_limits,
    minimum_jerk_blend,
    plan_sentence,
    plan_transition,
)


SENTENCES = (
    ("HELLO", "YOU", "APPOINTMENT", "HAVE"),
    ("MEDICINE", "MORNING", "NIGHT", "TAKE"),
    ("NOW", "NURSE", "BLOOD-DRAW"),
    ("PLEASE", "WAIT", "DOCTOR", "COME", "SOON"),
    ("YOU", "BUY", "BOOK"),
    ("YOU", "HURT", "WHERE"),
    ("YOU", "NEED", "INTERPRETER"),
    ("YOU", "UNDERSTAND"),
    ("BREATHE-DEEP",),
    ("THANK-YOU",),
)


def clear(positions):
    return ClearanceResult(True, sampled_frames=len(positions))


@pytest.fixture(scope="module")
def words():
    # Resolve independently of the planner: hospital-ready clips take precedence.
    entries = {
        row["gloss"]: row
        for row in json.loads((ROOT / "motions/hospital_v1_motions.json").read_text())["glosses"]
        if row["motion_ready"]
    }
    for library in ("studio_galt_v1", "wlasl_video_v1"):
        for row in json.loads((ROOT / "motions" / library / "index.json").read_text())["words"]:
            if row["robot_status"] != "poor":
                entries.setdefault(row["gloss"], row)
    return entries


def test_joint_rate_limits_match_library_categories():
    names = np.array([
        "left_shoulder_pitch_joint", "right_elbow_joint", "right_wrist_pitch_joint",
        "L_thumb_distal_joint", "R_index_proximal_joint", "waist_yaw_joint",
    ])
    limits = joint_rate_limits(names)
    np.testing.assert_array_equal(limits[:5], [15, 15, 15, 10, 10])
    assert np.isinf(limits[5])


def test_quintic_uses_shortest_continuously_rate_safe_integer_duration():
    names = np.array(["left_shoulder_pitch_joint", "R_thumb_distal_joint"])
    start = np.zeros(2)
    end = np.array([1.6, 2.7])
    positions = minimum_jerk_blend(start, end, names)
    intervals = len(positions) - 1
    limits = np.array([15.0, 10.0])
    # The derivative of 10u^3 - 15u^4 + 6u^5 peaks at 15/8.
    peak_rates = 1.875 * np.abs(end - start) * FPS / intervals
    assert np.all(peak_rates <= limits + 1e-12)
    assert intervals >= 3  # At least two interior blend samples.
    assert np.any(1.875 * np.abs(end - start) * FPS / (intervals - 1) > limits)
    u = np.linspace(0.0, 1.0, len(positions))[:, None]
    expected = start + (10 * u**3 - 15 * u**4 + 6 * u**5) * (end - start)
    np.testing.assert_allclose(positions, expected, atol=1e-12)
    np.testing.assert_array_equal(positions[[0, -1]], np.stack([start, end]))
    assert np.all(np.abs(np.diff(positions, axis=0)) * FPS <= limits + 1e-12)


def test_stationary_blend_keeps_two_interior_samples():
    pose = np.array([0.2, 0.6])
    positions = minimum_jerk_blend(pose, pose, ["right_elbow_joint", "L_index_proximal_joint"])
    assert len(positions) >= 4
    np.testing.assert_array_equal(positions, np.broadcast_to(pose, positions.shape))


@pytest.mark.parametrize("glosses", SENTENCES, ids=lambda seq: "_".join(seq))
def test_sentence_boundaries_rates_and_source_frames(glosses, words):
    motion, report = plan_sentence(glosses, clearance=clear)
    validate_motion(motion)
    positions = motion["positions"]
    names = motion["joint_names"]
    np.testing.assert_allclose(np.diff(motion["timestamps_s"]), 1 / FPS)
    assert len(report["transitions"]) == len(glosses) - 1
    limits = joint_rate_limits(names)

    for previous, following, segment in zip(glosses, glosses[1:], report["transitions"]):
        assert segment["from_gloss"] == previous
        assert segment["to_gloss"] == following
        start_frame, end_frame = segment["start_frame"], segment["end_frame"]
        assert end_frame - start_frame >= 3
        transition = positions[start_frame:end_frame + 1]
        with np.load(ROOT / words[previous]["motion"]) as source:
            np.testing.assert_array_equal(names, source["joint_names"])
            np.testing.assert_array_equal(transition[0], source["positions"][words[previous]["sign_frames"][1]])
        with np.load(ROOT / words[following]["motion"]) as target:
            np.testing.assert_array_equal(transition[-1], target["positions"][words[following]["sign_frames"][0]])
        assert np.all(np.abs(np.diff(transition, axis=0)) * FPS <= limits + 1e-10)

    assert len(report["word_segments"]) == len(glosses)
    for index, (gloss, segment) in enumerate(zip(glosses, report["word_segments"])):
        assert segment["gloss"] == gloss
        with np.load(ROOT / words[gloss]["motion"]) as clip:
            expected_start = 0 if index == 0 else words[gloss]["sign_frames"][0]
            expected_end = len(clip["positions"]) - 1 if index == len(glosses) - 1 else words[gloss]["sign_frames"][1]
            assert segment["source_start_frame"] == expected_start
            assert segment["source_end_frame"] == expected_end
            np.testing.assert_array_equal(
                positions[segment["start_frame"]:segment["end_frame"] + 1],
                clip["positions"][expected_start:expected_end + 1],
            )


def test_collision_tries_exactly_one_via_and_preserves_endpoints():
    names = np.array(["left_shoulder_pitch_joint", "right_elbow_joint", "R_index_proximal_joint"])
    start, end = np.zeros(3), np.array([0.7, 0.9, 1.5])
    via = (start + end) / 2 + np.array([-0.25, 0.3, 0.0])
    checks, vias = [], []

    def clearance(positions):
        checks.append(positions.copy())
        return ClearanceResult(len(checks) > 1, min_distance_m=-0.01 if len(checks) == 1 else 0.01)

    def via_factory(a, b, joint_names):
        vias.append((a.copy(), b.copy()))
        np.testing.assert_array_equal(joint_names, names)
        return via

    plan = plan_transition(start, end, names, clearance=clearance, via_factory=via_factory)
    assert len(checks) == 2 and len(vias) == 1
    assert plan.status == "PASS" and plan.used_via
    np.testing.assert_array_equal(plan.positions[0], start)
    np.testing.assert_array_equal(plan.positions[-1], end)
    assert any(np.array_equal(row, via) for row in plan.positions)
    assert np.all(np.abs(np.diff(plan.positions, axis=0)) * FPS <= joint_rate_limits(names) + 1e-10)


def test_persistent_collision_reports_failure_without_repeated_retries():
    names = np.array(["right_shoulder_pitch_joint", "L_index_proximal_joint"])
    calls = []

    def clearance(positions):
        calls.append(positions.copy())
        return ClearanceResult(False, min_distance_m=-0.01, sampled_frames=len(positions))

    plan = plan_transition(np.zeros(2), np.ones(2), names, clearance=clearance)
    assert len(calls) == 2
    assert plan.status == "FAILED" and plan.used_via
    assert plan.reasons
    assert plan.positions.ndim == 2 and np.isfinite(plan.positions).all()


def test_unknown_gloss_rejected_before_planning():
    with pytest.raises((ValueError, SystemExit), match="UNKNOWN-GLOSS"):
        plan_sentence(["UNKNOWN-GLOSS"], clearance=clear)


def sphere_pair_model(first_body, second_body):
    """Two real collision geoms; the second sphere slides along their centres."""
    import mujoco

    return mujoco.MjModel.from_xml_string(f"""
        <mujoco>
          <option gravity="0 0 0"/>
          <worldbody>
            <body name="{first_body}">
              <geom type="sphere" size="0.01"/>
            </body>
            <body name="{second_body}" pos="0.02 0 0">
              <joint name="right_wrist_pitch_joint" type="slide" axis="1 0 0"/>
              <geom type="sphere" size="0.01"/>
            </body>
          </worldbody>
        </mujoco>
    """)


@pytest.mark.parametrize("penetration,passed", [(0.0015, True), (0.0025, False)])
def test_real_mujoco_contact_respects_explicit_penetration_tolerance(penetration, passed):
    model = sphere_pair_model("torso_link", "right_wrist_yaw_link")
    checker = MujocoClearance(model, np.array(["right_wrist_pitch_joint"]))
    # Endpoints are separated; only the middle transition sample collides.
    result = checker(np.array([[0.005], [-penetration], [0.005]]))
    assert result.passed is passed
    assert result.sampled_frames == 3
    assert result.min_distance_m == pytest.approx(-penetration, abs=1e-10)
    if passed:
        assert result.collisions == []
    else:
        assert len(result.collisions) == 1
        collision = result.collisions[0]
        assert set(collision["bodies"]) == {"torso_link", "right_wrist_yaw_link"}
        assert collision["distance_m"] == pytest.approx(-penetration, abs=1e-10)
        assert collision["frame"] == 1 and collision["location"] == "interior"


@pytest.mark.parametrize("frame,location", [(0, "start_endpoint"), (2, "end_endpoint")])
def test_clearance_checks_both_transition_endpoints(frame, location):
    model = sphere_pair_model("torso_link", "right_wrist_yaw_link")
    checker = MujocoClearance(model, ["right_wrist_pitch_joint"])
    positions = np.full((3, 1), 0.005)
    positions[frame] = -0.003
    result = checker(positions)
    assert not result.passed
    assert result.collisions[0]["frame"] == frame
    assert result.collisions[0]["location"] == location


@pytest.mark.parametrize("first,second,excluded", [
    ("R_index_proximal", "right_wrist_yaw_link", True),
    ("L_thumb_proximal", "L_index_proximal", True),
    ("R_index_proximal", "left_wrist_yaw_link", False),
    ("R_index_proximal", "right_elbow_link", False),
])
def test_real_contact_excludes_only_same_hand_adjacency(first, second, excluded):
    model = sphere_pair_model(first, second)
    checker = MujocoClearance(model, ["right_wrist_pitch_joint"])
    result = checker(np.array([[-0.004], [-0.004]]))
    assert checker.data.ncon > 0  # Filtering, rather than missing contacts, explains PASS.
    assert result.passed is excluded
    if excluded:
        assert result.collisions == [] and result.min_distance_m is None
    else:
        assert result.min_distance_m == pytest.approx(-0.004, abs=1e-10)
        assert result.collisions


def test_sag_guard_does_not_replace_a_clear_blend_with_colliding_via():
    names = np.array(["right_shoulder_pitch_joint", "right_elbow_joint"])
    start, end = np.zeros(2), np.array([0.6, 0.9])
    direct = minimum_jerk_blend(start, end, names)
    calls = []

    def clearance(positions):
        calls.append(positions.copy())
        return ClearanceResult(len(calls) == 1, min_distance_m=0.01 if len(calls) == 1 else -0.01)

    def height_check(positions):
        return {"passed": len(calls) > 1}

    plan = plan_transition(start, end, names, clearance=clearance, height_check=height_check)
    assert len(calls) == 2
    assert plan.status == "PASS" and not plan.used_via
    assert plan.warnings
    assert plan.attempts[1]["status"] == "FAILED"
    np.testing.assert_array_equal(plan.positions, direct)
