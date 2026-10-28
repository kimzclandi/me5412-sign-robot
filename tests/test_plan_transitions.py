"""Transition contract checks, separate from source-clip quality/ASL review."""

import json

import numpy as np
import pytest

from sign_robot.motion import ROOT, apply_frame, load_model, validate_motion
from sign_robot.transitions import (
    FPS,
    VIA_DIRECTIONS,
    VIA_DISPLACEMENT_M,
    ClearanceResult,
    MujocoClearance,
    ik_via_candidates,
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
    assert intervals / FPS >= 0.3
    assert np.any(1.875 * np.abs(end - start) * FPS / (intervals - 1) > limits)
    u = np.linspace(0.0, 1.0, len(positions))[:, None]
    expected = start + (10 * u**3 - 15 * u**4 + 6 * u**5) * (end - start)
    np.testing.assert_allclose(positions, expected, atol=1e-12)
    np.testing.assert_array_equal(positions[[0, -1]], np.stack([start, end]))
    assert np.all(np.abs(np.diff(positions, axis=0)) * FPS <= limits + 1e-12)


def test_stationary_blend_keeps_minimum_duration():
    pose = np.array([0.2, 0.6])
    positions = minimum_jerk_blend(pose, pose, ["right_elbow_joint", "L_index_proximal_joint"])
    assert (len(positions) - 1) / FPS == 0.3
    np.testing.assert_array_equal(positions, np.broadcast_to(pose, positions.shape))


def test_tiny_joint_delta_still_takes_point_three_seconds():
    positions = minimum_jerk_blend(np.zeros(2), np.full(2, 1e-8),
                                   ["right_elbow_joint", "L_index_proximal_joint"])
    assert len(positions) - 1 == 9
    assert (len(positions) - 1) / FPS >= 0.3


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
        assert (end_frame - start_frame) / FPS >= 0.3
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


def collision_result(distance, positions, frame=0):
    return ClearanceResult(False, distance, [{"bodies": ["torso_link", "right_wrist_yaw_link"],
                                              "distance_m": distance, "frame": frame,
                                              "location": "interior"}], len(positions))


def test_collision_tries_named_vias_and_preserves_endpoints():
    names = np.array(["left_shoulder_pitch_joint", "right_elbow_joint", "R_index_proximal_joint"])
    start, end = np.zeros(3), np.array([0.7, 0.9, 1.5])
    via = (start + end) / 2 + np.array([-0.25, 0.3, 0.0])
    checks, vias = [], []

    def clearance(positions):
        checks.append(positions.copy())
        if len(positions) == 1 or len(positions) > 10:
            return clear(positions)
        return collision_result(-0.01, positions, 3)

    def via_factory(a, b, joint_names):
        vias.append((a.copy(), b.copy()))
        np.testing.assert_array_equal(joint_names, names)
        return [("up", via)]

    plan = plan_transition(start, end, names, clearance=clearance, via_factory=via_factory)
    assert len(checks) == 4 and len(vias) == 1  # Two endpoints, direct, complete via path.
    assert plan.status == "PASS" and plan.used_via
    assert plan.via_direction == "up"
    assert all(leg / FPS >= 0.3 for leg in plan.attempts[1]["leg_intervals"])
    np.testing.assert_array_equal(plan.positions[0], start)
    np.testing.assert_array_equal(plan.positions[-1], end)
    assert any(np.array_equal(row, via) for row in plan.positions)
    assert np.all(np.abs(np.diff(plan.positions, axis=0)) * FPS <= joint_rate_limits(names) + 1e-10)


@pytest.mark.parametrize("margins,chosen", [
    ([-0.004, -0.001, -0.003], 1),  # Only one direction passes.
    ([-0.001, -0.0003, -0.0008], 1),  # Select best, not first passing direction.
    ([-0.001, None, -0.0008], 1),  # No detected contacts stays null in the report.
])
def test_multi_candidate_selects_largest_passing_clearance(margins, chosen):
    names = ["right_shoulder_pitch_joint", "right_elbow_joint"]
    start, end = np.zeros(2), np.array([0.6, 0.9])
    directions = ["out", "up", "forward"]
    vias = [(direction, (start + end) / 2 + [0, i + 1])
            for i, direction in enumerate(directions)]
    whole_paths = []

    def clearance(positions):
        if len(positions) == 1:
            return clear(positions)
        whole_paths.append(positions.copy())
        if len(whole_paths) == 1:
            return collision_result(-0.01, positions, 3)
        distance = margins[len(whole_paths) - 2]
        return (collision_result(distance, positions, 3) if distance is not None and distance < -0.002
                else ClearanceResult(True, distance, sampled_frames=len(positions)))

    plan = plan_transition(start, end, names, clearance=clearance,
                           via_factory=lambda *args: vias)
    assert len(whole_paths) == 4
    assert plan.status == "PASS" and plan.via_direction == directions[chosen]
    np.testing.assert_array_equal(plan.positions, whole_paths[chosen + 1])
    assert plan.attempts[plan.selected_attempt]["clearance"]["min_distance_m"] == margins[chosen]
    for path in whole_paths:
        np.testing.assert_array_equal(path[[0, -1]], np.stack([start, end]))
        assert np.all(np.abs(np.diff(path, axis=0)) * FPS <= joint_rate_limits(names) + 1e-10)


def test_persistent_interior_collision_reports_worst_pair_without_extra_search():
    names = np.array(["right_shoulder_pitch_joint", "L_index_proximal_joint"])
    calls = []

    def clearance(positions):
        calls.append(positions.copy())
        if len(positions) == 1:
            return clear(positions)
        result = collision_result(-0.01, positions, 4)
        result.collisions.append({"bodies": ["left_elbow_link", "right_elbow_link"],
                                  "distance_m": -0.005, "frame": 5, "location": "interior"})
        return result

    plan = plan_transition(np.zeros(2), np.ones(2), names, clearance=clearance,
                           via_factory=lambda a, b, n: [(d, (a + b) / 2) for d, _ in VIA_DIRECTIONS])
    assert len(calls) == 3 + len(VIA_DIRECTIONS)
    assert plan.status == "FAILED" and plan.used_via
    assert plan.reasons
    worst = plan.attempts[plan.selected_attempt]["worst_collision"]
    assert worst["distance_m"] == -0.01 and "torso_link" in worst["bodies"]
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


@pytest.mark.parametrize("start,end", [
    (-0.004, 0.005), (0.005, -0.004), (-0.004, -0.003), (-0.004, -0.004),
])
def test_real_source_collisions_no_worse_than_endpoints_are_accepted(start, end):
    model = sphere_pair_model("torso_link", "right_wrist_yaw_link")
    names = ["right_wrist_pitch_joint"]
    checker = MujocoClearance(model, names)

    def unexpected_via(*args):
        pytest.fail("An unchanged source collision should not need a via")

    plan = plan_transition([start], [end], names, clearance=checker, via_factory=unexpected_via)
    assert plan.status == "source_collision" and not plan.used_via
    assert plan.reasons == []
    assert plan.endpoint_floor_m == pytest.approx(min(start, end))
    assert checker(plan.positions).min_distance_m >= plan.endpoint_floor_m


@pytest.mark.parametrize("via_distance,expected", [
    (-0.004, "source_collision"), (-0.004000001, "FAILED"), (-0.006, "FAILED"),
])
def test_source_collision_interior_worsening_requires_relative_via_clearance(via_distance, expected):
    names = ["right_shoulder_pitch_joint", "right_elbow_joint"]
    start, end = np.zeros(2), np.array([0.6, 0.9])
    full_paths = []

    def clearance(positions):
        if len(positions) == 1:
            return collision_result(-0.004, positions)
        full_paths.append(positions.copy())
        return collision_result(-0.008 if len(full_paths) == 1 else via_distance, positions, 4)

    plan = plan_transition(start, end, names, clearance=clearance,
                           via_factory=lambda a, b, n: [("out", (a + b) / 2 + [0, 0.3])])
    assert len(full_paths) == 2 and plan.used_via
    assert plan.attempts[0]["status"] == "FAILED"
    assert plan.status == expected
    assert bool(plan.reasons) is (expected == "FAILED")


def test_source_collision_report_separates_counts_and_hands_off_source_frames(words):
    def clearance(positions):
        return collision_result(-0.004, positions)

    _, report = plan_sentence(["YOU", "BUY"], clearance=clearance)
    assert report["transition_count"] == report["source_collision_count"] == report["accepted_count"] == 1
    assert report["pass_count"] == report["failed_count"] == 0
    assert report["status"] == "source_collision"
    assert {(row["word"], row["frame"]) for row in report["source_collision_handoff"]} == {
        ("YOU", words["YOU"]["sign_frames"][1]), ("BUY", words["BUY"]["sign_frames"][0]),
    }
    assert all(row["distance_m"] == -0.004 and "torso_link" in row["bodies"]
               for row in report["source_collision_handoff"])


def test_ik_vias_use_robot_axes_bounded_arms_and_convex_fingers(words, monkeypatch):
    import mujoco
    from sign_robot.retarget import G1Retargeter

    model = load_model()
    with np.load(ROOT / words["YOU"]["motion"]) as source:
        names = source["joint_names"].copy()
        start, end = source["positions"][[0, words["YOU"]["sign_frames"][1]]].copy()
    arm = np.array([any(part in str(n) for part in ("shoulder", "elbow", "wrist")) for n in names])
    for i, name in enumerate(names):
        if arm[i]:
            value = (-0.5 if "shoulder_pitch" in name else 0.8 if "elbow" in name else
                     0.2 if "left_shoulder_roll" in name else -0.2 if "right_shoulder_roll" in name else 0.0)
            start[i] = end[i] = value
    midpoint = (start + end) / 2
    data = mujoco.MjData(model)
    wrist_ids = [model.body(f"{side}_wrist_yaw_link").id for side in ("left", "right")]
    apply_frame(model, data, names, midpoint)
    wrists = data.xpos[wrist_ids].copy()
    # Existing model shoulder offsets confirm +Y is left; foot tips extend +X.
    assert data.xpos[model.body("left_shoulder_pitch_link").id, 1] > 0
    assert data.xpos[model.body("right_shoulder_pitch_link").id, 1] < 0
    goals_and_seeds = []
    solve = G1Retargeter.solve_arms

    def recorded_solve(self, q, sides, goals, previous, pairs):
        goals_and_seeds.append((goals, q.copy()))
        return solve(self, q, sides, goals, previous, pairs)

    monkeypatch.setattr(G1Retargeter, "solve_arms", recorded_solve)
    candidates = list(ik_via_candidates(start, end, names, model))
    assert [direction for direction, _ in candidates] == [direction for direction, _ in VIA_DIRECTIONS]
    ids = [model.joint(str(n)).id for n in names]
    for (direction, via), (_, vector), (goals, seed) in zip(candidates, VIA_DIRECTIONS, goals_and_seeds):
        np.testing.assert_array_equal(via[~arm], midpoint[~arm])
        np.testing.assert_array_equal(seed, midpoint)
        assert np.all(via >= model.jnt_range[ids, 0]) and np.all(via <= model.jnt_range[ids, 1])
        apply_frame(model, data, names, via)
        displacement = data.xpos[wrist_ids] - wrists
        target = VIA_DISPLACEMENT_M * np.asarray(vector) / np.linalg.norm(vector)
        expected = np.stack([target, target * [1, -1, 1]])
        # The requested target is exact; bounded IK may only partly reach it.
        requested = np.stack([goals[side][0] for side in ("left", "right")]) - wrists
        np.testing.assert_allclose(requested, expected, atol=1e-12, err_msg=direction)
        assert np.all(np.sum(displacement * expected, axis=1) > 0), direction


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
        if len(positions) == 1:
            return clear(positions)
        calls.append(positions.copy())
        return ClearanceResult(len(calls) == 1, min_distance_m=0.01 if len(calls) == 1 else -0.01)

    def height_check(positions):
        return {"passed": len(calls) > 1}

    plan = plan_transition(start, end, names, clearance=clearance, height_check=height_check,
                           via_factory=lambda a, b, n: [("up", (a + b) / 2 + [0, 0.3])])
    assert len(calls) == 2
    assert plan.status == "PASS" and not plan.used_via
    assert plan.warnings
    assert plan.attempts[1]["status"] == "FAILED"
    np.testing.assert_array_equal(plan.positions, direct)
