"""Small arm-space developer checks; no full MuJoCo RRT success is required."""
from types import SimpleNamespace

import numpy as np
import pytest

import sign_robot.transitions as transitions


NAMES = np.array(["left_elbow_joint", "right_elbow_joint", "L_index_proximal_joint", "waist_yaw_joint"])
START = np.array([-0.8, 0.0, 0.1, 0.0])
GOAL = np.array([0.8, 0.0, 0.9, 0.0])


def tiny_model():
    return SimpleNamespace(joint=lambda name: SimpleNamespace(
        limited=np.array([True]), range=np.array([-1.0, 1.0])))


def result(distance, q):
    return transitions.ClearanceResult(distance >= 0.002, distance, sampled_frames=len(q))


def obstacle(q):
    # A disk obstructs the straight start→goal edge; going around it is feasible.
    distance = -0.01 if np.any(np.linalg.norm(q[:, :2], axis=1) < 0.35) else 0.003
    return result(distance, q)


def run_search(**kwargs):
    return transitions.rrt_connect(
        START, GOAL, NAMES, model=tiny_model(), clearance=obstacle,
        required_clearance_m=0.002, clock=lambda: 0.0, **kwargs)


def test_rrt_fixed_seed_hook_is_stable():
    seeds = []

    def rng_factory(seed):
        seeds.append(seed)
        return np.random.default_rng(seed)

    first, second = run_search(rng_factory=rng_factory), run_search(rng_factory=rng_factory)
    assert seeds == [5412, 5412]
    assert first.info["rrt_found"] and second.info["rrt_found"]
    assert first.info["rrt_nodes"] == second.info["rrt_nodes"]
    assert first.info["rrt_seed"] == transitions.RRT_SEED
    np.testing.assert_array_equal(first.positions, second.positions)
    np.testing.assert_array_equal(first.positions[[0, -1]], [START, GOAL])
    assert first.clearance.min_distance_m >= 0.002


def test_rrt_arm_indices_use_exact_contract_and_never_search_fingers():
    from sign_robot.retarget import ARM_SUFFIXES
    arms = [f"{side}_{suffix}" for side in ("left", "right") for suffix in ARM_SUFFIXES]
    names = np.array(["waist_yaw_joint", "L_index_proximal_joint", *arms,
                      "left_wrist_imaginary_joint", "R_thumb_distal_joint"])
    columns, bounds = transitions.rrt_arm_space(names, tiny_model())
    np.testing.assert_array_equal(columns, np.arange(2, 16))
    np.testing.assert_array_equal(bounds, np.tile([-1.0, 1.0], (14, 1)))
    checked = []

    def clearance(q):
        checked.extend(q.copy())
        return obstacle(q)

    found = transitions.rrt_connect(
        START, GOAL, NAMES, model=tiny_model(), clearance=clearance,
        required_clearance_m=0.002, clock=lambda: 0.0)
    assert found.info["rrt_found"]
    q = np.asarray(checked)
    assert np.all(q[:, :2] >= -1.0) and np.all(q[:, :2] <= 1.0)
    assert np.all(q[:, 3] == 0.0)
    assert np.all(q[:, 2] >= START[2]) and np.all(q[:, 2] <= GOAL[2])
    # Policy weights are derived from arm progress; no finger dimension was sampled.
    assert found.info["rrt_arm_joint_names"] == NAMES[:2].tolist()
    assert "projection" in found.info["rrt_non_arm_policy"]
    assert np.all(np.abs(np.diff(found.positions, axis=0)) * transitions.FPS <=
                  transitions.joint_rate_limits(NAMES) + 1e-10)
    assert (len(found.positions) - 1) / transitions.FPS >= 0.3


def test_rrt_smoothing_recheck_failure_keeps_feasible_unsmoothed_path(monkeypatch):
    # Emulate a broken shortcut implementation accepting the obstructed direct edge.
    monkeypatch.setattr(transitions, "shortcut_rrt_path", lambda path, *args, **kwargs: path[[0, -1]])
    found = run_search()
    assert found.info["rrt_found"]
    assert not found.info["smoothed"]
    assert found.info["rrt_smoothing_recheck_passed"] is False
    assert found.info["rrt_smoothing_fallback"] == "checked_unsmoothed"
    assert obstacle(found.positions).min_distance_m >= 0.002
    assert len(found.positions) > 2


def test_rrt_accepts_negative_endpoint_relative_floor_without_relaxing_normal_gate():
    floor = -0.0008092600523539207

    def near_clearance(q):
        blocked = np.any(np.linalg.norm(q[:, :2], axis=1) < 0.35)
        at_source = np.any(np.all(q == START, axis=1))
        return result(-0.01 if blocked else floor if at_source else 0.003, q)

    found = transitions.rrt_connect(
        START, GOAL, NAMES, model=tiny_model(), clearance=near_clearance,
        required_clearance_m=floor, clock=lambda: 0.0)
    assert found.info["rrt_found"]
    assert found.clearance.min_distance_m == floor
    assert not found.clearance.passed  # The unchanged absolute +2 mm gate fails.
    assert transitions.PENETRATION_TOLERANCE_M == 0.002


def test_rrt_pair_allowlist_contains_exactly_the_two_authorized_pairs():
    assert isinstance(transitions.RRT_PAIRS, frozenset)
    assert transitions.RRT_PAIRS == frozenset({("MEDICINE", "MORNING"), ("NURSE", "BLOOD-DRAW")})


@pytest.mark.parametrize("pair,expected_calls", [
    (("MEDICINE", "MORNING"), 1), (("NURSE", "BLOOD-DRAW"), 1),
    (("nurse", "blood-draw"), 1), (("MORNING", "MEDICINE"), 0),
    (("BLOOD-DRAW", "NURSE"), 0), (("YOU", "BUY"), 0),
])
def test_rrt_timeout_needs_group2_fix_once_only_for_allowlisted_pairs(pair, expected_calls):
    calls = []
    tick = iter(range(100))

    def timed_search(*args, **kwargs):
        calls.append(1)
        return transitions.rrt_connect(*args, **kwargs, clock=lambda: float(next(tick)), budget_s=0.1)

    def colliding(q):
        return result(-0.0008 if len(q) == 1 else -0.01, q)

    plan = transitions.plan_transition(
        START, GOAL, NAMES, model=tiny_model(), clearance=colliding,
        via_factory=lambda *args: [], via2_factory=lambda *args: [],
        hub_factory=lambda names: np.zeros(len(names)),
        source_retract=[START, START / 2], target_approach=[GOAL / 2, GOAL],
        from_gloss=pair[0], to_gloss=pair[1], rrt_factory=timed_search)
    assert len(calls) == expected_calls
    assert sum(a["kind"] == "rrt_connect" for a in plan.attempts) == expected_calls
    chosen = plan.attempts[plan.selected_attempt]
    if expected_calls:
        assert plan.status == chosen["status"] == "needs_group2_fix"
        assert plan.method == "rrt_connect"
        assert chosen["rrt_outcome"] == "timeout"
        assert not chosen["rrt_found"] and not chosen["relative_floor_passed"]
        assert chosen["in_slice_collision"]
        assert chosen["diagnostic_method"] == "retract_approach"
        assert chosen["required_clearance_m"] == -0.0008
    else:
        assert plan.status == "FAILED" and plan.method == "retract_approach"


@pytest.mark.parametrize("pair", [("MEDICINE", "MORNING"), ("NURSE", "BLOOD-DRAW")])
def test_rrt_is_not_invoked_when_prior_route_passes(pair):
    def unexpected(*args, **kwargs):
        pytest.fail("A passing earlier route must not invoke RRT")

    plan = transitions.plan_transition(
        START, GOAL, NAMES, clearance=lambda q: result(0.003, q),
        from_gloss=pair[0], to_gloss=pair[1], rrt_factory=unexpected)
    assert plan.status == "PASS" and plan.method == "direct"
