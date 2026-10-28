"""Transition contract checks, separate from source-clip quality/ASL review."""

import json
import math

import numpy as np
import pytest

from sign_robot.motion import ROOT, apply_frame, load_model, validate_motion
from sign_robot.transitions import (
    FPS,
    ENDPOINT_NEAR_M,
    PENETRATION_TOLERANCE_M,
    VIA_DIRECTIONS,
    VIA_DISPLACEMENT_M,
    ClearanceResult,
    MujocoClearance,
    ik_via_candidates,
    ik_dual_via_candidates,
    joint_rate_limits,
    minimum_jerk_blend,
    neutral_pose,
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


def distance_result(distance, positions, frame=0):
    contact = {"bodies": ["torso_link", "right_wrist_yaw_link"],
               "geoms": ["torso_geom", "wrist_geom"],
               "distance_m": distance, "frame": frame,
               "location": "start_endpoint" if frame == 0 else "interior"}
    violations = [contact] if distance < PENETRATION_TOLERANCE_M else []
    return ClearanceResult(not violations, distance, violations, len(positions),
                           [contact] if distance < ENDPOINT_NEAR_M else [], contact)


def clear(positions):
    return distance_result(0.01, positions)


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
        assert segment["method"] == "direct"
        assert segment["status"] == "PASS" and not segment["source_near"]
        assert isinstance(segment["min_clearance_mm"], (int, float))
        assert math.isfinite(segment["min_clearance_mm"])
        assert segment["min_clearance_mm"] == 10.0
        assert segment["endpoint_clearances_mm"] == [10.0, 10.0]
        assert segment["closest_pair"]["bodies"] == ["torso_link", "right_wrist_yaw_link"]
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
    return distance_result(distance, positions, frame)


def test_collision_tries_named_vias_and_preserves_endpoints():
    names = np.array(["left_shoulder_pitch_joint", "right_elbow_joint", "R_index_proximal_joint"])
    start, end = np.zeros(3), np.array([0.7, 0.9, 1.5])
    via = (start + end) / 2 + np.array([-0.25, 0.3, 0.0])
    checks, vias, duals = [], [], []

    def clearance(positions):
        checks.append(positions.copy())
        if len(positions) == 1 or len(positions) > 10:
            return clear(positions)
        return collision_result(-0.01, positions, 3)

    def via_factory(a, b, joint_names):
        vias.append((a.copy(), b.copy()))
        np.testing.assert_array_equal(joint_names, names)
        return [("up", via)]

    def dual_factory(a, b, joint_names):
        duals.append((a.copy(), b.copy()))
        return [(["out", "out"], [via, via + [0.1, 0, 0]])]

    plan = plan_transition(start, end, names, clearance=clearance,
                           via_factory=via_factory, via2_factory=dual_factory)
    assert len(checks) == 5 and len(vias) == len(duals) == 1
    assert plan.status == "PASS" and plan.used_via
    assert plan.method == "via1" and plan.via_direction == "up"
    assert [a["kind"] for a in plan.attempts] == ["direct", "via1", "via2"]
    for attempt in plan.attempts[1:]:
        assert all(leg / FPS >= 0.3 for leg in attempt["leg_intervals"])
    np.testing.assert_array_equal(plan.positions[0], start)
    np.testing.assert_array_equal(plan.positions[-1], end)
    assert any(np.array_equal(row, via) for row in plan.positions)
    assert np.all(np.abs(np.diff(plan.positions, axis=0)) * FPS <= joint_rate_limits(names) + 1e-10)


@pytest.mark.parametrize("margins,chosen", [
    ([-0.004, 0.002, 0.001], 1),  # Only one direction passes the +2 mm line.
    ([0.003, 0.005, 0.004], 1),  # Select best, not first passing direction.
    ([0.003, 0.02, 0.004], 1),  # Separated candidates rank by numeric distance.
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
        return distance_result(distance, positions, 3)

    plan = plan_transition(start, end, names, clearance=clearance,
                           via_factory=lambda *args: vias, via2_factory=lambda *args: [])
    assert len(whole_paths) == 4
    assert plan.status == "PASS" and plan.via_direction == directions[chosen]
    np.testing.assert_array_equal(plan.positions, whole_paths[chosen + 1])
    assert plan.attempts[plan.selected_attempt]["clearance"]["min_distance_m"] == margins[chosen]
    for path in whole_paths:
        np.testing.assert_array_equal(path[[0, -1]], np.stack([start, end]))
        assert np.all(np.abs(np.diff(path, axis=0)) * FPS <= joint_rate_limits(names) + 1e-10)


@pytest.mark.parametrize("single_margin,dual_margin,method", [
    (0.003, 0.005, "via2"), (0.005, 0.003, "via1"),
    (0.001, 0.01, "via2"), (0.003, -0.004, "via1"),
])
def test_via1_and_via2_compete_on_whole_path_clearance(single_margin, dual_margin, method):
    names = ["right_shoulder_pitch_joint", "R_index_proximal_joint"]
    start, end = np.zeros(2), np.array([0.8, 1.2])
    via1, via2 = np.array([-0.4, 0.4]), np.array([-0.2, 0.8])
    paths = []

    def clearance(positions):
        if len(positions) == 1:
            return clear(positions)
        paths.append(positions.copy())
        distance = [-0.01, single_margin, dual_margin][len(paths) - 1]
        return distance_result(distance, positions, 4)

    def unexpected_hub(*args):
        pytest.fail("Hub is a fallback after every via candidate fails")

    plan = plan_transition(start, end, names, clearance=clearance,
                           via_factory=lambda *args: [("up", via1)],
                           via2_factory=lambda *args: [(["neutral_retreat", "out"], [via1, via2])],
                           hub_factory=unexpected_hub)
    assert len(paths) == 3
    assert plan.status == "PASS" and plan.method == method
    assert len(plan.attempts[2]["leg_intervals"]) == 3
    assert sum(plan.attempts[2]["leg_intervals"]) == len(paths[2]) - 1
    assert all(n / FPS >= 0.3 for n in plan.attempts[2]["leg_intervals"])
    for knot in (via1, via2):
        assert any(np.array_equal(row, knot) for row in paths[2])
    for path in paths:
        np.testing.assert_array_equal(path[[0, -1]], [start, end])
        assert np.all(np.abs(np.diff(path, axis=0)) * FPS <= joint_rate_limits(names) + 1e-10)
    if method == "via2":
        assert plan.via_direction is None
        assert plan.via_directions == ["neutral_retreat", "out"]
        np.testing.assert_array_equal(plan.positions, paths[2])


def test_hub_fallback_selected_only_after_mocked_vias_fail_and_both_legs_clear():
    names = ["right_shoulder_pitch_joint", "R_index_proximal_joint"]
    start, end, hub = np.zeros(2), np.ones(2), np.array([-0.6, -0.4])
    hub_paths = []

    def clearance(positions):
        if len(positions) == 1:
            return clear(positions)
        if any(np.array_equal(row, hub) for row in positions):
            hub_paths.append(positions.copy())
            return distance_result(0.003, positions)
        return collision_result(-0.01, positions, 4)

    plan = plan_transition(start, end, names, clearance=clearance,
                           via_factory=lambda *args: [("out", np.full(2, 0.3))],
                           via2_factory=lambda *args: [(["out", "up"], [np.full(2, 0.2), np.full(2, 0.8)])],
                           hub_factory=lambda n: hub)
    assert plan.status == "PASS" and plan.method == "hub"
    assert [attempt["kind"] for attempt in plan.attempts] == ["direct", "via1", "via2", "hub"]
    assert plan.selected_attempt == 3
    assert len(hub_paths) == 3  # Complete path and both independently checked legs.
    chosen = plan.attempts[plan.selected_attempt]
    assert len(chosen["leg_clearance"]) == 2
    assert all(result["passed"] for result in chosen["leg_clearance"])
    assert all(n / FPS >= 0.3 for n in chosen["leg_intervals"])
    np.testing.assert_array_equal(plan.positions[[0, -1]], [start, end])
    assert np.all(np.abs(np.diff(plan.positions, axis=0)) * FPS <= joint_rate_limits(names) + 1e-10)


def test_persistent_interior_collision_checks_hub_and_reports_worst_pair():
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
                           via_factory=lambda a, b, n: [(d, (a + b) / 2) for d, _ in VIA_DIRECTIONS],
                           via2_factory=lambda a, b, n: [(["neutral_retreat", "out"], [a + 0.2, b + 0.2])],
                           hub_factory=lambda names: np.full(len(names), -0.3))
    assert len(calls) == 3 + len(VIA_DIRECTIONS) + 1 + 3  # Via2, hub whole path and both legs.
    assert plan.status == "FAILED" and plan.method == "direct"
    assert plan.attempts[-1]["kind"] == "hub"
    assert len(plan.attempts[-1]["leg_clearance"]) == 2
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


@pytest.mark.parametrize("distance,passed", [(0.003, True), (0.0015, False), (-0.0015, False), (-0.0025, False)])
def test_real_mujoco_clearance_requires_positive_two_mm(distance, passed):
    model = sphere_pair_model("torso_link", "right_wrist_yaw_link")
    checker = MujocoClearance(model, np.array(["right_wrist_pitch_joint"]))
    # Endpoints are separated; the middle sample determines signed clearance.
    result = checker(np.array([[0.005], [distance], [0.005]]))
    assert result.passed is passed
    assert result.sampled_frames == 3
    assert result.min_distance_m == pytest.approx(distance, abs=1e-10)
    if passed:
        assert result.collisions == []
    else:
        assert len(result.collisions) == 1
        collision = result.collisions[0]
        assert set(collision["bodies"]) == {"torso_link", "right_wrist_yaw_link"}
        assert collision["distance_m"] == pytest.approx(distance, abs=1e-10)
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


@pytest.mark.parametrize("gap", [0.005, 1.2])
def test_separated_clearance_and_planned_pass_are_finite_with_closest_pair(gap):
    model = sphere_pair_model("fixed_mount", "right_wrist_yaw_link")
    names = ["right_wrist_pitch_joint"]
    checker = MujocoClearance(model, names)
    margins, pair_margins = model.geom_margin.copy(), model.pair_margin.copy()
    masks = (model.geom_contype.copy(), model.geom_conaffinity.copy())
    apply_frame(model, checker.data, names, [gap])
    assert checker.data.ncon == 0  # No contacts with the original zero margins.
    result = checker(np.array([[gap], [gap + 0.005]]))
    assert isinstance(result.min_distance_m, (int, float)) and math.isfinite(result.min_distance_m)
    assert result.min_distance_m == pytest.approx(gap)
    assert result.passed and len(result.worst_contact["bodies"]) == 2
    assert "fixed_mount" in result.worst_contact["bodies"]
    assert len(result.worst_contact["geoms"]) == 2
    plan = plan_transition([gap], [gap + 0.005], names, clearance=checker)
    chosen = plan.attempts[plan.selected_attempt]
    assert plan.status == "PASS" and not plan.source_near
    assert math.isfinite(chosen["clearance"]["min_distance_m"])
    assert chosen["worst_collision"]["bodies"] == result.worst_contact["bodies"]
    np.testing.assert_array_equal(model.geom_margin, margins)
    np.testing.assert_array_equal(model.pair_margin, pair_margins)
    np.testing.assert_array_equal(model.geom_contype, masks[0])
    np.testing.assert_array_equal(model.geom_conaffinity, masks[1])


@pytest.mark.parametrize("distance", [-0.0008, 0.0, 0.001999999, 0.002, 0.003])
def test_normal_path_uses_absolute_positive_two_mm_floor(distance):
    def clearance(positions):
        return clear(positions) if len(positions) == 1 else distance_result(distance, positions, 4)

    plan = plan_transition([0.0], [0.5], ["right_elbow_joint"], clearance=clearance,
                           via_factory=lambda *args: [], via2_factory=lambda *args: [],
                           hub_factory=lambda *args: [-0.5])
    assert not plan.source_near and plan.endpoint_floor_m is None
    assert plan.status == ("PASS" if distance >= 0.002 else "FAILED")


@pytest.mark.parametrize("endpoint", [0, 1])
@pytest.mark.parametrize("distance", [-0.0008, -0.002, -0.004, 0.001])
def test_real_near_endpoint_direct_passes_only_at_relative_floor(endpoint, distance):
    model = sphere_pair_model("fixed_mount", "right_wrist_yaw_link")
    names = ["right_wrist_pitch_joint"]
    checker = MujocoClearance(model, names)
    endpoints = [[0.005], [0.005]]
    endpoints[endpoint] = [distance]
    checks = []

    def clearance(positions):
        checks.append(positions.copy())
        return checker(positions)

    def unexpected_search(*args):
        pytest.fail("A direct path meeting the relative floor needs no escalation")

    plan = plan_transition(*endpoints, names, clearance=clearance,
                           via_factory=unexpected_search, via2_factory=unexpected_search,
                           hub_factory=unexpected_search)
    assert len(checks) == 3 and len(checks[0]) == len(checks[1]) == 1
    assert plan.status == "source_near" and plan.method == "direct" and not plan.used_via
    assert plan.source_near and plan.attempts[0]["relative_floor_passed"]
    assert plan.via_direction is None and plan.via_directions == []
    assert len(plan.attempts) == 1
    near = plan.endpoint_clearance[endpoint]
    assert near["min_distance_m"] == pytest.approx(distance)
    assert set(near["near_contacts"][0]["bodies"]) == {"fixed_mount", "right_wrist_yaw_link"}
    assert not near["passed"]  # Absolute clearance and relative acceptance are separate.
    np.testing.assert_array_equal(plan.positions[[0, -1]], endpoints)


@pytest.mark.parametrize("endpoint_distance,status", [
    (0.002, "PASS"), (0.003, "PASS"), (0.001999999, "source_near"), (0.001, "source_near"),
])
def test_endpoint_near_threshold_is_strict(endpoint_distance, status):
    assert ENDPOINT_NEAR_M == 0.002
    assert PENETRATION_TOLERANCE_M == 0.002

    def clearance(positions):
        return distance_result(endpoint_distance, positions)

    plan = plan_transition([0.0], [0.5], ["right_elbow_joint"], clearance=clearance)
    assert plan.status == status and plan.method == "direct"
    assert plan.endpoint_clearance[0]["min_distance_m"] == endpoint_distance


@pytest.mark.parametrize("start,end", [
    (-0.004, 0.005), (0.005, -0.004), (-0.004, -0.003), (-0.004, -0.004),
])
def test_real_source_near_no_worse_than_endpoints_is_accepted(start, end):
    model = sphere_pair_model("torso_link", "right_wrist_yaw_link")
    names = ["right_wrist_pitch_joint"]
    checker = MujocoClearance(model, names)

    def unexpected_via(*args):
        pytest.fail("An unchanged source collision should not need a via")

    plan = plan_transition([start], [end], names, clearance=checker, via_factory=unexpected_via)
    assert plan.status == "source_near" and not plan.used_via
    assert plan.reasons == []
    assert plan.endpoint_floor_m == pytest.approx(min(start, end))
    assert checker(plan.positions).min_distance_m >= plan.endpoint_floor_m


@pytest.mark.parametrize("floor", [-0.004, -0.0008, 0.001])
@pytest.mark.parametrize("worsening", [0.0, 1e-9, 0.056])
def test_source_near_relative_floor_escalates_all_candidates_before_failed(floor, worsening):
    names = ["right_shoulder_pitch_joint", "right_elbow_joint"]
    start, end = np.zeros(2), np.array([0.6, 0.9])
    full_paths, factories = [], []

    def clearance(positions):
        if len(positions) == 1:
            return distance_result(floor, positions)
        full_paths.append(positions.copy())
        return distance_result(floor - worsening, positions, 4)

    def vias(*args):
        factories.append("via1")
        return [("out", (start + end) / 2 + 0.1)]

    def duals(*args):
        factories.append("via2")
        return [(["neutral_retreat", "out"], [start + 0.2, end + 0.2])]

    def hub(*args):
        factories.append("hub")
        return np.full(2, -0.5)

    plan = plan_transition(start, end, names, clearance=clearance,
                           via_factory=vias, via2_factory=duals, hub_factory=hub)
    assert plan.source_near and plan.endpoint_floor_m == floor
    assert plan.status == ("FAILED" if worsening else "source_near")
    assert plan.method == "direct"  # Stable tie order, but FAILED never counts as accepted.
    assert factories == (["via1", "via2", "hub"] if worsening else [])
    assert len(full_paths) == (6 if worsening else 1)
    assert [a["kind"] for a in plan.attempts] == (["direct", "via1", "via2", "hub"] if worsening else ["direct"])
    assert plan.attempts[plan.selected_attempt]["relative_floor_passed"] is (not worsening)
    assert bool(plan.reasons) == bool(worsening)
    if worsening:
        assert plan.attempts[-1]["status"] == "FAILED"
        assert plan.attempts[plan.selected_attempt]["worst_collision"]["distance_m"] == floor - worsening


@pytest.mark.parametrize("method", ["via1", "via2", "hub"])
@pytest.mark.parametrize("endpoint", [0, 1])
@pytest.mark.parametrize("floor", [-0.0008, 0.001])
def test_source_near_search_accepts_route_at_worse_endpoint_floor(method, endpoint, floor):
    endpoint_calls, path_calls, factories = [], [], []
    endpoints = [0.006, 0.006]
    endpoints[endpoint] = floor

    def clearance(positions):
        if len(positions) == 1:
            distance = endpoints[len(endpoint_calls)]
            endpoint_calls.append(positions.copy())
        else:
            kind = ["direct", "via1", "via2", "hub", "hub", "hub"][len(path_calls)]
            path_calls.append(positions.copy())
            distance = floor if kind == method else -0.056
        return distance_result(distance, positions)

    def vias(*args):
        factories.append("via1")
        return [("out", [0.2])]

    def duals(*args):
        factories.append("via2")
        return [(["neutral_retreat", "out"], [[0.1], [0.4]])]

    def hub(*args):
        factories.append("hub")
        return [-0.5]

    plan = plan_transition([0.0], [0.5], ["right_elbow_joint"], clearance=clearance,
                           via_factory=vias, via2_factory=duals, hub_factory=hub)
    assert plan.status == "source_near" and plan.source_near
    assert plan.method == method and plan.used_via
    assert plan.endpoint_floor_m == floor
    assert factories == (["via1", "via2", "hub"] if method == "hub" else ["via1", "via2"])
    assert plan.attempts[0]["status"] == "FAILED"  # The -56 mm direct is never accepted.
    chosen = plan.attempts[plan.selected_attempt]
    assert chosen["relative_floor_passed"] and chosen["clearance"]["min_distance_m"] == floor
    if method == "hub":
        assert len(chosen["leg_clearance"]) == 2
        assert all(r["min_distance_m"] == floor for r in chosen["leg_clearance"])


def test_source_near_report_separates_counts_and_hands_off_source_frames(words):
    def clearance(positions):
        return collision_result(-0.004, positions)

    _, report = plan_sentence(["YOU", "BUY"], clearance=clearance)
    assert report["transition_count"] == report["source_near_count"] == report["accepted_count"] == 1
    assert report["pass_count"] == report["failed_count"] == 0
    assert report["status"] == "source_near"
    assert {(row["word"], row["frame"]) for row in report["source_near_handoff"]} == {
        ("YOU", words["YOU"]["sign_frames"][1]), ("BUY", words["BUY"]["sign_frames"][0]),
    }
    assert all(row["distance_m"] == -0.004 and "torso_link" in row["bodies"]
               for row in report["source_near_handoff"])


@pytest.mark.parametrize("floor", [-0.0008, 0.001])
def test_failed_source_near_report_is_not_accepted_and_keeps_handoff(words, monkeypatch, floor):
    import sign_robot.transitions as transitions

    monkeypatch.setattr(transitions, "ik_via_candidates", lambda *args: [])
    monkeypatch.setattr(transitions, "ik_dual_via_candidates", lambda *args: [])
    monkeypatch.setattr(transitions, "neutral_pose", lambda names, model=None: np.zeros(len(names)))

    def clearance(positions):
        return distance_result(floor if len(positions) == 1 else -0.056, positions)

    _, report = plan_sentence(["YOU", "BUY"], clearance=clearance)
    assert report["transition_count"] == report["failed_count"] == 1
    assert report["pass_count"] == report["source_near_count"] == report["accepted_count"] == 0
    transition, = report["transitions"]
    assert report["status"] == transition["status"] == "FAILED"
    assert transition["source_near"] and not transition["relative_floor_passed"]
    assert transition["min_clearance_mm"] == -56.0
    assert transition["closest_pair"]["distance_m"] == -0.056
    assert {(row["word"], row["frame"]) for row in report["source_near_handoff"]} == {
        ("YOU", words["YOU"]["sign_frames"][1]), ("BUY", words["BUY"]["sign_frames"][0]),
    }


@pytest.mark.parametrize("distance", [-0.0008, 0.001])
def test_mild_contacts_and_small_positive_gaps_are_in_source_near_handoff(words, distance):
    def clearance(positions):
        contact = {"bodies": ["fixed_mount", "right_wrist_yaw_link"],
                   "distance_m": distance, "frame": 0, "location": "start_endpoint"}
        return ClearanceResult(False, distance, sampled_frames=len(positions),
                               near_contacts=[contact], worst_contact=contact)

    _, report = plan_sentence(["YOU", "BUY"], clearance=clearance)
    assert report["source_near_count"] == 1 and report["pass_count"] == 0
    transition, = report["transitions"]
    assert transition["method"] == "direct" and transition["status"] == "source_near"
    assert transition["source_near"] and not transition["used_via"]
    assert transition["min_clearance_mm"] == distance * 1000
    assert {(row["word"], row["frame"]) for row in report["source_near_handoff"]} == {
        ("YOU", words["YOU"]["sign_frames"][1]), ("BUY", words["BUY"]["sign_frames"][0]),
    }
    assert all(row["clearance_mm"] == distance * 1000 for row in report["source_near_handoff"])


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


def test_dual_ik_family_uses_neutral_qpos0_arms_and_solves_every_knot(words, monkeypatch):
    from sign_robot.retarget import G1Retargeter

    model = load_model()
    with np.load(ROOT / words["YOU"]["motion"]) as source:
        names = source["joint_names"].copy()
        start, end = source["positions"][[words["YOU"]["sign_frames"][0],
                                           words["YOU"]["sign_frames"][1]]].copy()
    addresses = [int(model.joint(str(n)).qposadr[0]) for n in names]
    np.testing.assert_array_equal(neutral_pose(names, model), model.qpos0[addresses])
    arm = np.array([any(part in str(n) for part in ("shoulder", "elbow", "wrist")) for n in names])
    seeds = []
    solve = G1Retargeter.solve_arms

    def recorded_solve(self, q, sides, goals, previous, pairs):
        seeds.append(q.copy())
        return solve(self, q, sides, goals, previous, pairs)

    monkeypatch.setattr(G1Retargeter, "solve_arms", recorded_solve)
    candidates = list(ik_dual_via_candidates(start, end, names, model))
    assert len(candidates) == len(VIA_DIRECTIONS) + 3 + 6
    assert len(seeds) == 2 * len(VIA_DIRECTIONS) + 1 + 3 + 12
    ids = [model.joint(str(n)).id for n in names]
    for directions, knots in candidates:
        assert len(directions) == len(knots) == 2
        for knot in knots:
            assert np.isfinite(knot).all()
            assert np.all(knot >= model.jnt_range[ids, 0]) and np.all(knot <= model.jnt_range[ids, 1])
        if directions[0].startswith("neutral_retreat"):
            np.testing.assert_array_equal(knots[0][~arm], (start + (end - start) / 3)[~arm])
            np.testing.assert_array_equal(knots[1][~arm], (start + 2 * (end - start) / 3)[~arm])
        else:
            np.testing.assert_array_equal(knots[0][~arm], start[~arm])
            np.testing.assert_array_equal(knots[1][~arm], end[~arm])
    retreat_seed = seeds[2 * len(VIA_DIRECTIONS)][addresses]
    np.testing.assert_array_equal(retreat_seed[arm], neutral_pose(names, model)[arm])
    assert [d for d, _ in candidates[len(VIA_DIRECTIONS):len(VIA_DIRECTIONS) + 3]] == [
        ["neutral_retreat", "out"], ["neutral_retreat", "out+up"], ["neutral_retreat", "out+forward"],
    ]
    serialized_start = 2 * len(VIA_DIRECTIONS) + 1 + 3
    for parked_side, seed_offset in (("left", serialized_start), ("right", serialized_start + 6)):
        parked = arm & np.array([str(n).startswith(parked_side + "_") for n in names])
        moving = arm & ~parked
        for i in range(3):
            first, second = (seeds[seed_offset + 2 * i + j][addresses] for j in (0, 1))
            np.testing.assert_array_equal(first[parked], neutral_pose(names, model)[parked])
            np.testing.assert_array_equal(second[parked], neutral_pose(names, model)[parked])
            np.testing.assert_array_equal(first[moving], start[moving])
            np.testing.assert_array_equal(second[moving], end[moving])


@pytest.mark.parametrize("first,second,excluded", [
    ("R_index_proximal", "right_wrist_yaw_link", True),
    ("L_thumb_proximal", "L_index_proximal", True),
    ("R_index_proximal", "left_wrist_yaw_link", False),
    ("R_index_proximal", "right_elbow_link", False),
    ("fixed_mount", "right_wrist_yaw_link", False),
])
def test_real_contact_excludes_only_same_hand_adjacency(first, second, excluded):
    model = sphere_pair_model(first, second)
    if excluded:
        # Keep an eligible far pair so exclusion does not require a null or
        # invented clearance. The contacting hand pair must remain excluded.
        import mujoco
        xml = f"""
            <mujoco><worldbody>
              <body name="{first}"><geom type="sphere" size="0.01"/></body>
              <body name="{second}" pos="0.02 0 0">
                <joint name="right_wrist_pitch_joint" type="slide" axis="1 0 0"/>
                <geom type="sphere" size="0.01"/>
              </body>
              <body name="torso_link" pos="0.5 0 0"><geom type="sphere" size="0.01"/></body>
            </worldbody></mujoco>"""
        model = mujoco.MjModel.from_xml_string(xml)
    checker = MujocoClearance(model, ["right_wrist_pitch_joint"])
    result = checker(np.array([[-0.004], [-0.004]]))
    assert checker.data.ncon > 0  # Filtering, rather than missing contacts, explains PASS.
    assert result.passed is excluded
    if excluded:
        assert result.collisions == [] and math.isfinite(result.min_distance_m)
        assert result.min_distance_m > 0.002
        assert "torso_link" in result.worst_contact["bodies"]
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
                           via_factory=lambda a, b, n: [("up", (a + b) / 2 + [0, 0.3])],
                           via2_factory=lambda *args: [])
    assert len(calls) == 2
    assert plan.status == "PASS" and not plan.used_via
    assert plan.warnings
    assert plan.attempts[1]["status"] == "FAILED"
    np.testing.assert_array_equal(plan.positions, direct)
