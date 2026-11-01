"""Boundary-derivative and bounded retiming tests."""
from copy import deepcopy
import itertools

import numpy as np
import pytest

from sign_robot.pair_timing import (
    boundary_state_v2, connector_quality_v2, quintic_coefficients_v2, time_route_v2,
)
from sign_robot.pair_contract import load_policy


def policy():
    return load_policy("config/transition_policy_v2.json", supported_versions=(1, 2))


def state(position, velocity=None, acceleration=None):
    n = len(position)
    return {"position": list(position), "velocity": list(velocity or [0.0] * n),
            "acceleration": list(acceleration or [0.0] * n)}


def test_boundary_state_uses_one_sided_linear_replay_and_zero_interval_acceleration():
    t = np.arange(5) / 30
    q = np.column_stack([2 * t + 0.5, -3 * t])
    clip = {"timestamps_s": t, "positions": q}
    source = boundary_state_v2(clip, 3, "source")
    target = boundary_state_v2(clip, 1, "target")
    np.testing.assert_allclose(source["position"], q[3])
    np.testing.assert_allclose(source["velocity"], [2, -3])
    np.testing.assert_allclose(source["acceleration"], [0, 0])
    np.testing.assert_allclose(target["velocity"], [2, -3])
    with pytest.raises(ValueError, match="Insufficient"):
        boundary_state_v2(clip, 0, "source")


def test_quintic_coefficients_match_all_nonzero_boundary_states():
    start = state([0.1, -0.2], [0.3, -0.4], [0.5, -0.6])
    end = state([0.8, 0.4], [-0.2, 0.1], [-0.3, 0.2])
    duration = 0.7
    coefficients = quintic_coefficients_v2(start, end, duration)
    def evaluate(order, u):
        row = coefficients
        for _ in range(order):
            row = np.column_stack([k * row[:, k] for k in range(1, row.shape[1])])
        return row @ (u ** np.arange(row.shape[1])) / duration**order
    np.testing.assert_allclose(evaluate(0, 0), start["position"])
    np.testing.assert_allclose(evaluate(1, 0), start["velocity"])
    np.testing.assert_allclose(evaluate(2, 0), start["acceleration"])
    np.testing.assert_allclose(evaluate(0, 1), end["position"])
    np.testing.assert_allclose(evaluate(1, 1), end["velocity"])
    np.testing.assert_allclose(evaluate(2, 1), end["acceleration"])


def test_connector_quality_checks_speed_limits_coupling_and_analytic_integral():
    p = policy()
    names = np.array(["right_elbow_joint", "R_index_proximal_joint"])
    bounds = np.array([[-2, 2], [-2, 2]], dtype=float)
    c = quintic_coefficients_v2(state([0, 0]), state([1, 0.5]), 1.0)
    segments = [{"kind": "polynomial_v2", "start_time_s": 0.0, "end_time_s": 1.0,
                 "coefficients": c.tolist()}]
    metrics, errors = connector_quality_v2(segments, bounds, names, p)
    assert not errors
    assert metrics["peak_acceleration_rad_s2"] == pytest.approx(10 / np.sqrt(3) * 1.0)
    assert metrics["peak_jerk_rad_s3"] == pytest.approx(60.0)
    assert metrics["jerk_integral_rad2_s5"] == pytest.approx(720 * (1 + 0.25))


def test_time_route_re_solves_after_each_duration_change_and_rechecks_geometry():
    p = policy()
    names = np.array(["right_elbow_joint", "R_index_proximal_joint"])
    bounds = np.array([[-2, 2], [-2, 2]], dtype=float)
    start, end = state([0, 0], [0.1, 0.1]), state([0.2, 0.1], [0.1, 0.0])
    calls = []
    def geometry(segments):
        calls.append((segments[0]["end_time_s"], np.array(segments[0]["coefficients"])))
        return {"passed": len(calls) > 1, "attempt": len(calls)}
    result = time_route_v2(np.array([[0, 0], [0.2, 0.1]]), start, end, names, bounds, p,
                            validate_curve=geometry)
    assert result.segments is not None and result.diagnostics["status"] == "TIMED_CANDIDATE"
    assert len(calls) >= 2 and not np.array_equal(calls[0][1], calls[1][1])
    assert result.diagnostics["geometry_checked"]
    assert result.diagnostics["formal_acceptance"] is False


@pytest.mark.parametrize("kind", ["duration", "boundary_speed", "knots", "nonfinite"])
def test_time_route_reports_bounded_or_invalid_inputs(kind):
    p = policy()
    names = np.array(["right_elbow_joint", "R_index_proximal_joint"])
    bounds = np.array([[-2, 2], [-2, 2]], dtype=float)
    start, end = state([0, 0]), state([1.5, 0.5])
    if kind == "duration":
        p["quality"]["limits"]["maximum_transition_duration_s"] = 0.3
    if kind == "boundary_speed":
        start = state([0, 0], [100, 0])
    knots = np.array([[0, 0], [1.5, 0.5]])
    if kind == "knots":
        knots = np.array([[0.1, 0], [1.5, 0.5]])
    if kind == "nonfinite":
        knots[0, 0] = np.nan
    result = time_route_v2(knots, start, end, names, bounds, p)
    assert result.segments is None
    assert result.diagnostics["reason_codes"]
    assert result.diagnostics["formal_acceptance"] is False


def test_time_route_wall_clock_budget_is_distinct_from_no_solution(monkeypatch):
    p = policy()
    names = np.array(["right_elbow_joint", "R_index_proximal_joint"])
    bounds = np.array([[-2, 2], [-2, 2]], dtype=float)
    ticks = itertools.chain([0.0], itertools.repeat(31.0))
    monkeypatch.setattr("sign_robot.pair_timing.time.monotonic", lambda: next(ticks))
    result = time_route_v2(np.array([[0, 0], [0.2, 0.1]]), state([0, 0]), state([0.2, 0.1]),
                           names, bounds, p)
    assert result.segments is None and result.diagnostics["status"] == "TIMEOUT"
    assert result.diagnostics["reason_codes"] == ["TIMING_WALL_TIME_LIMIT"]


def test_duration_change_does_not_reuse_old_coefficients():
    p = policy()
    names = np.array(["right_elbow_joint", "R_index_proximal_joint"])
    bounds = np.array([[-2, 2], [-2, 2]], dtype=float)
    durations = []
    def geometry(segments):
        durations.append(segments[-1]["end_time_s"])
        return {"passed": False}
    result = time_route_v2(np.array([[0, 0], [1, 0]]), state([0, 0]), state([1, 0]), names, bounds, p,
                           validate_curve=geometry)
    assert result.segments is None
    assert len(durations) == p["planner"]["budget"]["max_time_attempts"]
    assert durations == sorted(set(durations))


def test_same_positions_with_different_derivatives_are_not_a_zero_connector():
    p = policy()
    names = np.array(["right_elbow_joint", "R_index_proximal_joint"])
    bounds = np.array([[-2, 2], [-2, 2]], dtype=float)
    start, end = state([0.2, 0.0], [0.5, 0.0]), state([0.2, 0.0], [-0.5, 0.0])
    result = time_route_v2(np.array([[0.2, 0.0], [0.2, 0.0]]), start, end, names, bounds, p)
    assert result.segments is not None
    coefficients = np.asarray(result.segments[0]["coefficients"])
    assert np.any(np.abs(coefficients[0, 1:]) > 0)
    assert result.diagnostics["geometry_checked"] is False


def test_retiming_rechecks_new_overshoot_even_when_later_geometry_passes():
    p = policy()
    names = np.array(["right_elbow_joint", "R_index_proximal_joint"])
    bounds = np.array([[-0.05, 0.05], [-2, 2]], dtype=float)
    start = state([0, 0], [1, 0])
    end = state([0, 0], [1, 0])
    calls = []
    def geometry(segments):
        calls.append(segments)
        return {"passed": len(calls) > 1}
    result = time_route_v2(np.zeros((2, 2)), start, end, names, bounds, p, validate_curve=geometry)
    assert result.segments is None
    assert "TIMED_CURVE_JOINT_LIMIT_VIOLATION" not in result.diagnostics["attempts"][0]["reason_codes"]
    assert "TIMED_CURVE_JOINT_LIMIT_VIOLATION" in result.diagnostics["attempts"][1]["reason_codes"]


def test_zero_distance_still_has_finite_duration_and_preserves_input():
    p = policy()
    names = np.array(["right_elbow_joint", "R_index_proximal_joint"])
    bounds = np.array([[-2, 2], [-2, 2]], dtype=float)
    knots = np.zeros((2, 2))
    before = knots.copy()
    result = time_route_v2(knots, state([0, 0]), state([0, 0]), names, bounds, p)
    assert result.segments is not None
    assert result.segments[-1]["end_time_s"] >= 0.3
    np.testing.assert_array_equal(knots, before)


@pytest.mark.parametrize("duration", [0, -1, True, float("nan")])
def test_invalid_quintic_duration_is_rejected(duration):
    with pytest.raises(ValueError):
        quintic_coefficients_v2(state([0]), state([1]), duration)
