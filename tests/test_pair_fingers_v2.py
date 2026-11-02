"""Finger phase and coupling recovery tests."""
import numpy as np
import pytest

from sign_robot.pair_fingers import (
    apply_finger_strategy_to_path_v2, apply_finger_strategy_to_segments_v2,
    coupling_error_v2, finger_strategy_curve_v2, _sample,
)


NAMES = np.array(["right_elbow_joint", "R_thumb_proximal_pitch_joint",
                  "R_thumb_intermediate_joint", "R_index_proximal_joint",
                  "R_index_intermediate_joint"])
COUPLINGS = [
    {"parent": "R_thumb_proximal_pitch_joint", "child": "R_thumb_intermediate_joint", "multiplier": 1.6, "offset": 0.0},
    {"parent": "R_index_proximal_joint", "child": "R_index_intermediate_joint", "multiplier": 1.0, "offset": 0.0},
]
START = np.array([0.2, 0.1, 0.16, 0.2, 0.2])
END = np.array([0.3, 0.6, 0.96, -0.4, -0.4])


@pytest.mark.parametrize("strategy", ["synchronous", "early", "late"])
def test_all_finger_strategies_preserve_endpoints_and_couplings(strategy):
    q, info = finger_strategy_curve_v2(START, END, NAMES, strategy, COUPLINGS, samples=11)
    np.testing.assert_allclose(q[0], START)
    np.testing.assert_allclose(q[-1], END)
    assert info["version"] == 2 and info["endpoint_preserved"]
    assert coupling_error_v2(q, NAMES, COUPLINGS) == pytest.approx(0)
    u = np.linspace(0, 1, 11)
    np.testing.assert_allclose(q[:, 0], START[0] + (END[0] - START[0]) * (10*u**3 - 15*u**4 + 6*u**5))


def test_early_and_late_phase_change_at_different_times():
    sync, _ = finger_strategy_curve_v2(START, END, NAMES, "synchronous", COUPLINGS, samples=101)
    early, _ = finger_strategy_curve_v2(START, END, NAMES, "early", COUPLINGS, samples=101)
    late, _ = finger_strategy_curve_v2(START, END, NAMES, "late", COUPLINGS, samples=101)
    thumb = 1
    assert early[65, thumb] == pytest.approx(END[thumb])
    assert late[35, thumb] == pytest.approx(START[thumb])
    assert sync[50, thumb] == pytest.approx((START[thumb] + END[thumb]) / 2)
    assert np.all(np.diff(early[:, thumb]) * (END[thumb] - START[thumb]) >= -1e-12)
    assert np.all(np.diff(late[:, thumb]) * (END[thumb] - START[thumb]) >= -1e-12)


def test_pure_finger_change_keeps_arm_path_constant():
    start, end = START.copy(), END.copy()
    end[0] = start[0]
    q, _ = finger_strategy_curve_v2(start, end, NAMES, "late", COUPLINGS, samples=31)
    np.testing.assert_allclose(q[:, 0], start[0])
    assert np.max(np.abs(q[:, 1:] - start[1:])) > 0
    assert coupling_error_v2(q, NAMES, COUPLINGS) < 1e-12


def test_apply_strategy_preserves_nonfinger_base_path_and_endpoints():
    base = np.linspace(START, END, 9)
    base[1:-1, 1:] = START[1:]
    result, info = apply_finger_strategy_to_path_v2(base, START, END, NAMES, "early", COUPLINGS)
    np.testing.assert_allclose(result[:, 0], base[:, 0])
    np.testing.assert_allclose(result[0], START)
    np.testing.assert_allclose(result[-1], END)
    assert info["base_path_preserved"] and info["requires_geometry_recheck"]


@pytest.mark.parametrize("kind", ["endpoint", "missing_child", "unknown_strategy", "nan", "too_few"])
def test_invalid_finger_inputs_are_rejected(kind):
    start, end, names, couplings = START.copy(), END.copy(), NAMES.copy(), COUPLINGS
    if kind == "endpoint":
        end[2] = 0.7
    elif kind == "missing_child":
        couplings = [dict(COUPLINGS[0], child="R_missing")]
    elif kind == "unknown_strategy":
        strategy = "random"
    elif kind == "nan":
        start[0] = np.nan
    else:
        strategy = "synchronous"
    with pytest.raises(ValueError):
        finger_strategy_curve_v2(start, end, names, locals().get("strategy", "synchronous"), couplings,
                                 samples=1 if kind == "too_few" else 11)


def test_coupling_is_restored_from_parent_not_treated_as_independent_command():
    q, _ = finger_strategy_curve_v2(START, END, NAMES, "synchronous", COUPLINGS, samples=17)
    q[1:-1, 2] += np.linspace(0, 0.2, len(q) - 2)
    assert coupling_error_v2(q, NAMES, COUPLINGS) > 0
    repaired, _ = apply_finger_strategy_to_path_v2(q, START, END, NAMES, "synchronous", COUPLINGS)
    assert coupling_error_v2(repaired, NAMES, COUPLINGS) < 1e-12


def test_geometry_recheck_is_explicit_in_strategy_metadata():
    q, info = finger_strategy_curve_v2(START, END, NAMES, "synchronous", COUPLINGS)
    assert info["requires_geometry_recheck"] is True
    assert q.shape == (31, len(NAMES))


@pytest.mark.parametrize("strategy", ["synchronous", "early", "late"])
def test_polynomial_phase_preserves_nonzero_derivatives_and_entire_arm_curve(strategy):
    from sign_robot.pair_timing import quintic_coefficients_v2
    from sign_robot.pair_contract import polynomial_boundary_v2
    first = {"position": START.tolist(), "velocity": [0.1, 0.3, 0.48, 0.2, 0.2],
             "acceleration": [0.2, 0.1, 0.16, 0.2, 0.2]}
    last = {"position": END.tolist(), "velocity": [-0.2, -0.2, -0.32, 0.1, 0.1],
            "acceleration": [0.1, 0.2, 0.32, -0.1, -0.1]}
    base = [{"kind": "polynomial_v2", "start_time_s": 0.0, "end_time_s": 2.0,
             "coefficients": quintic_coefficients_v2(first, last, 2.0).tolist()}]
    result, info = apply_finger_strategy_to_segments_v2(base, NAMES, strategy, COUPLINGS)
    for endpoint, expected, segment in (("start", first, result[0]), ("end", last, result[-1])):
        actual = polynomial_boundary_v2(segment, endpoint)
        for key in expected:
            np.testing.assert_allclose(actual[key], expected[key], atol=1e-9)
    times = np.linspace(0, 2, 1001)
    np.testing.assert_allclose(_sample(result, times)[:, 0], _sample(base, times)[:, 0], atol=1e-10)
    assert coupling_error_v2(_sample(result, times), NAMES, COUPLINGS) < 1e-10
    for left, right in zip(result, result[1:]):
        for key in ("position", "velocity", "acceleration"):
            np.testing.assert_allclose(polynomial_boundary_v2(left, "end")[key],
                                       polynomial_boundary_v2(right, "start")[key], atol=1e-8)
    assert info["arm_curve_preserved"] and info["finger_knots_preserved"]


def test_early_finger_strategy_retains_intermediate_route_knot():
    from sign_robot.pair_timing import quintic_coefficients_v2
    zero = [0.0] * len(NAMES)
    via = (START + END) / 2
    states = [{"position": q.tolist(), "velocity": zero, "acceleration": zero} for q in (START, via, END)]
    base = [{"kind": "polynomial_v2", "start_time_s": float(i), "end_time_s": float(i+1),
             "coefficients": quintic_coefficients_v2(states[i], states[i+1], 1.0).tolist()} for i in range(2)]
    result, _ = apply_finger_strategy_to_segments_v2(base, NAMES, "early", COUPLINGS)
    np.testing.assert_allclose(_sample(result, [0.65])[0, 1:], via[1:], atol=1e-10)
    np.testing.assert_allclose(_sample(result, [1.0])[0, 0], _sample(base, [1.0])[0, 0], atol=1e-10)


def test_finger_collision_after_phase_change_remains_a_failed_candidate():
    from sign_robot.pair_contract import load_policy
    from sign_robot.pair_timing import time_route_v2
    p = load_policy("config/transition_policy_v2.json", supported_versions=(1, 2))
    names = np.array(["right_elbow_joint", "R_index_proximal_joint"])
    first = {"position": [0.0, -1.0], "velocity": [0.0, 0.0], "acceleration": [0.0, 0.0]}
    last = {"position": [0.0, 1.0], "velocity": [0.0, 0.0], "acceleration": [0.0, 0.0]}
    def geometry(segments):
        midpoint = (segments[0]["start_time_s"] + segments[0]["end_time_s"]) / 2
        collided = abs(_sample(segments, [midpoint])[0, 1]) < 1e-6
        return {"passed": not collided, "finger_crossing_detected": collided}
    result = time_route_v2(np.array([first["position"], last["position"]]), first, last, names,
                           np.array([[-2, 2], [-2, 2]]), p, finger_strategy="early", validate_curve=geometry)
    assert result.segments is None
    assert result.diagnostics["attempts"]
    assert all(attempt["geometry"]["finger_crossing_detected"] for attempt in result.diagnostics["attempts"])


def test_cyclic_coupling_and_endpoint_changes_are_rejected():
    cycle = [dict(COUPLINGS[0]), {"parent": "R_thumb_intermediate_joint", "child": "R_thumb_proximal_pitch_joint", "multiplier": 0.625, "offset": 0.0}]
    with pytest.raises(ValueError, match="Cyclic"):
        finger_strategy_curve_v2(START, END, NAMES, "early", cycle)
    path = np.linspace(START, END, 9)
    path[-1, 2] += 0.1
    with pytest.raises(ValueError, match="endpoints differ"):
        apply_finger_strategy_to_path_v2(path, START, END, NAMES, "late", COUPLINGS)
