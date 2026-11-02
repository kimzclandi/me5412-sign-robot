"""Mocked clearance profiles for the Round 9 acceptance gate; no RRT search."""

import numpy as np
import pytest

from sign_robot.transitions import (
    ClearanceResult,
    check_sub_2mm_endpoint_attached,
    plan_transition,
    sample_clearance_profile,
)


@pytest.mark.parametrize("target", [False, True], ids=["source", "target"])
def test_sub_two_mm_passes_monotonic_endpoint_run_without_redip(target):
    profile = [-0.0008, -0.0008, 0.0005, 0.0015, 0.002, 0.004, 0.002]
    if target:
        profile.reverse()
    result = check_sub_2mm_endpoint_attached(profile)
    assert result["sub_2mm_monotonic_ok"] is True
    assert result["sub_2mm_frame_intervals"] == ([[3, 6]] if target else [[0, 3]])
    assert result["sub_2mm_attached_endpoint"] == ("target" if target else "source")
    assert result["sub_2mm_first_clear_frame"] == (2 if target else 4)
    assert result["sub_2mm_frame_reference"] == "path-local inclusive, zero-based"


@pytest.mark.parametrize("target", [False, True], ids=["source", "target"])
def test_sub_two_mm_rejects_redip_after_first_clear_sample(target):
    profile = [0.0005, 0.001, 0.002, 0.004, 0.0015, 0.004]
    if target:
        profile.reverse()
    result = check_sub_2mm_endpoint_attached(profile)
    assert result["sub_2mm_monotonic_ok"] is False
    assert result["sub_2mm_frame_intervals"] == ([[1, 1], [4, 5]] if target else [[0, 1], [4, 4]])
    assert "disjoint" in result["sub_2mm_reason"]


@pytest.mark.parametrize("target", [False, True], ids=["source", "target"])
def test_sub_two_mm_rejects_nonmonotonic_endpoint_run(target):
    # The dip stays above the endpoint floor, so the old relative gate passes.
    profile = [-0.0008, 0.001, 0.0005, 0.0015, 0.002, 0.004]
    if target:
        profile.reverse()
    result = check_sub_2mm_endpoint_attached(profile)
    assert result["sub_2mm_monotonic_ok"] is False
    assert result["sub_2mm_frame_intervals"] == ([[2, 5]] if target else [[0, 3]])
    assert "decreases" in result["sub_2mm_reason"]


def test_sub_two_mm_rejects_interior_run_or_unqualified_own_endpoint():
    interior = check_sub_2mm_endpoint_attached([0.004, 0.001, 0.0015, 0.004])
    assert interior["sub_2mm_monotonic_ok"] is False
    assert interior["sub_2mm_frame_intervals"] == [[1, 2]]
    wrong_endpoint = check_sub_2mm_endpoint_attached(
        [0.001, 0.0015, 0.004], endpoint_clearances_m=[0.004, 0.001])
    assert wrong_endpoint["sub_2mm_monotonic_ok"] is False
    assert "own near endpoint" in wrong_endpoint["sub_2mm_reason"]


def test_clear_path_and_monotonic_all_near_path_have_explicit_reports():
    clear = check_sub_2mm_endpoint_attached([0.002, 0.005, 0.002])
    assert clear["sub_2mm_monotonic_ok"] is True
    assert clear["sub_2mm_frame_intervals"] == []
    assert clear["sub_2mm_attached_endpoint"] is None
    all_near = check_sub_2mm_endpoint_attached([0.0015, 0.001, 0.0005])
    assert all_near["sub_2mm_monotonic_ok"] is True
    assert all_near["sub_2mm_attached_endpoint"] == "target"
    assert all_near["sub_2mm_frame_intervals"] == [[0, 2]]
    assert all_near["sub_2mm_first_clear_frame"] is None


def test_missing_clearance_profile_is_measured_per_pose():
    poses = np.array([[0.001], [0.0015], [0.003]])
    calls = []

    def clearance(q):
        calls.append(q.copy())
        return ClearanceResult(False, float(q[0, 0]))

    result = ClearanceResult(False, 0.001)
    assert sample_clearance_profile(result, poses, clearance) == [0.001, 0.0015, 0.003]
    assert len(calls) == len(poses)
    assert result.frame_clearances_m == [0.001, 0.0015, 0.003]


@pytest.mark.parametrize("profile", [
    [0.0005, 0.001, 0.002, 0.004, 0.0015, 0.004],
    [0.0005, 0.0015, 0.001, 0.002, 0.004],
])
def test_planner_rejects_relative_floor_passing_candidate_when_endpoint_gate_fails(profile):
    def clearance(q):
        if len(q) == 1:
            values = [0.0005 if q[0, 0] == 0 else 0.004]
        else:
            # Repeat samples without introducing extra extrema to fit each
            # route's own frame count. The full relative floor still passes.
            indices = np.floor(np.linspace(0, len(profile) - 1, len(q))).astype(int)
            values = np.asarray(profile)[indices].tolist()
        return ClearanceResult(False, min(values), sampled_frames=len(q),
                               frame_clearances_m=values)

    plan = plan_transition([0.0], [0.5], ["right_elbow_joint"], clearance=clearance,
                           via_factory=lambda *args: [], via2_factory=lambda *args: [],
                           hub_factory=lambda *args: [-0.5])
    assert plan.status == "FAILED"
    assert all(attempt["status"] == "FAILED" for attempt in plan.attempts)
    chosen = plan.attempts[plan.selected_attempt]
    assert chosen["clearance"]["min_distance_m"] == chosen["required_clearance_m"]
    assert chosen["sub_2mm_monotonic_ok"] is False
    assert chosen["relative_floor_passed"] is False
