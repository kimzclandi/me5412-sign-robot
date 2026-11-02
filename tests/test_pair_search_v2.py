"""Generic bounded RRT geometry, fingers, coupling and postprocess regressions."""
from copy import deepcopy
import itertools
from types import SimpleNamespace
import json

import numpy as np
import pytest

import sign_robot.pair_search as search
from sign_robot.pair_contract import json_hash, load_policy
from sign_robot.pair_routes import PairWorkBudget
from sign_robot.transitions import ClearanceResult
from test_pair_routes_v2 import context, revise_synthetic_motion


class Joint:
    def __init__(self, name, identifier):
        self.name, self.id = name, identifier
        self.range = np.array([-1.0, 1.0])
        self.limited = np.array([True])


class Model:
    def __init__(self, names):
        self.joints = {str(name): Joint(str(name), i) for i, name in enumerate(names)}

    def joint(self, name):
        return self.joints[str(name)]


class Geometry:
    def __init__(self, predicate=None):
        self.predicate = predicate or (lambda q: np.zeros(len(q), dtype=bool))

    def __call__(self, q):
        q = np.asarray(q)
        distances = np.where(self.predicate(q), -0.01, 0.01)
        frame = int(np.argmin(distances))
        distance = float(distances[frame])
        contact = {"bodies": ["obstacle", "robot"], "geoms": ["a", "b"], "geom_ids": [0, 1],
                   "distance_m": distance, "frame": frame}
        return ClearanceResult(distance >= 0.002, distance, [], len(q), [], contact, [], distances.tolist())


def small_context(names, predicate=None, couplings=()):
    policy = load_policy("config/transition_policy_v2.json", supported_versions=(1, 2))
    return SimpleNamespace(policy=policy, model=Model(names), clearance=Geometry(predicate),
                           library={"couplings": list(couplings)})


def test_fixed_seed_rrt_finds_obstacle_detour_reproducibly():
    names = np.array(["left_shoulder_roll_joint", "right_elbow_joint"])
    ctx = small_context(names, lambda q: (np.abs(q[:, 0]) < 0.1) & (np.abs(q[:, 1]) < 0.45))
    a, b = np.array([-0.8, 0.0]), np.array([0.8, 0.0])
    first = search.bounded_rrt_path_v2(ctx, a, b, names, PairWorkBudget(ctx.policy), seed=5412)
    second = search.bounded_rrt_path_v2(ctx, a, b, names, PairWorkBudget(ctx.policy), seed=5412)
    assert first.raw_path is not None and first.diagnostics["path_found"]
    np.testing.assert_array_equal(first.raw_path, second.raw_path)
    assert len(first.raw_path) > 2
    for left, right in zip(first.raw_path, first.raw_path[1:]):
        assert ctx.clearance(np.linspace(left, right, 101)).min_distance_m >= 0.002
    assert first.diagnostics["infeasibility_proven"] is False


def test_same_arm_different_fingers_has_a_real_search_dimension():
    names = np.array(["right_elbow_joint", "R_index_proximal_joint"])
    ctx = small_context(names)
    a, b = np.array([0.0, -0.5]), np.array([0.0, 0.5])
    result = search.bounded_rrt_path_v2(ctx, a, b, names, PairWorkBudget(ctx.policy), seed=4)
    assert result.raw_path is not None
    np.testing.assert_allclose(result.raw_path[:, 0], 0)
    np.testing.assert_array_equal(result.raw_path[[0, -1]], np.stack([a, b]))
    assert "R_index_proximal_joint" in result.diagnostics["control_joint_names"]


def test_coupled_children_are_not_drivers_and_tighten_parent_bounds():
    names = np.array(["right_elbow_joint", "R_thumb_proximal_pitch_joint", "R_thumb_distal_joint"])
    coupling = {"parent": names[1], "child": names[2], "multiplier": 2.0, "offset": 0.1}
    ctx = small_context(names, couplings=[coupling])
    a, b = np.array([0, 0.1, 0.3]), np.array([0.2, 0.2, 0.5])
    columns, bounds, decode = search.control_space_v2(ctx, a, b, names)
    assert columns.tolist() == [0, 1]
    np.testing.assert_allclose(bounds[1], [-0.55, 0.45])
    decoded = decode(np.array([[0.0, -0.5], [0.1, 0.4]]))
    np.testing.assert_allclose(decoded[:, 2], 0.1 + 2 * decoded[:, 1])


@pytest.mark.parametrize("kind", ["poses", "nodes"])
def test_tiny_work_budget_stops_without_no_solution_claim(kind):
    names = np.array(["left_shoulder_roll_joint", "right_elbow_joint"])
    ctx = small_context(names, lambda q: (np.abs(q[:, 0]) < 0.1) & (np.abs(q[:, 1]) < 0.45))
    ctx.policy = deepcopy(ctx.policy)
    if kind == "poses":
        ctx.policy["planner"]["budget"]["max_collision_samples"] = 1
    else:
        ctx.policy["planner"]["budget"]["max_nodes"] = 1
    result = search.bounded_rrt_path_v2(ctx, np.array([-0.8, 0]), np.array([0.8, 0]), names, PairWorkBudget(ctx.policy), seed=5412)
    assert result.raw_path is None
    assert result.diagnostics["outcome"] == "budget_exhausted"
    assert result.diagnostics["infeasibility_proven"] is False


def test_rrt_adapter_is_open_to_nonlegacy_gloss_pairs(context):
    ctx, _ = context
    attempts = list(search.iter_rrt_attempts_v2(ctx, "HELLO", "PLEASE", seed=5412))
    assert any(a.diagnostic.get("event") == "search" and a.diagnostic["search"]["path_found"] for a in attempts)
    assert any(a.trajectory is not None for a in attempts)
    assert all(a.diagnostic["method"] == "rrt_connect" for a in attempts)
    assert all(a.diagnostic["status"] != "PASS_SIM" for a in attempts)


def test_faulty_shortcut_is_rechecked_after_timing_and_checked_raw_fallback_remains(context, monkeypatch):
    ctx, _ = context
    names = ctx.library["joint_names"]
    x, y = names.index("right_elbow_joint"), names.index("right_shoulder_roll_joint")
    target = ctx.clips["PLEASE"]["positions"].copy()
    target[:, x] = 0.2
    revise_synthetic_motion(ctx, "PLEASE", target)
    ctx.clearance = Geometry(lambda q: (q[:, x] > 0.04) & (q[:, x] < 0.16) & (np.abs(q[:, y]) < 0.05))
    def fake_search(context, a, b, names, budget, seed):
        via = (a + b) / 2
        via[y] = 0.4
        raw = np.stack([a, via, b])
        shortcut = np.stack([a, b])
        return search.SearchPathV2(raw, shortcut, {"path_found": True, "outcome": "path_found",
            "shortcut_checked": True, "raw_path_hash": json_hash(raw.tolist())})
    monkeypatch.setattr(search, "bounded_rrt_path_v2", fake_search)
    attempts = list(search.iter_rrt_attempts_v2(ctx, "HELLO", "PLEASE", seed=5412))
    shortcuts = [a for a in attempts if a.diagnostic.get("variant") == "shortcut"]
    raw = [a for a in attempts if a.diagnostic.get("variant") == "raw"]
    assert shortcuts and all(a.trajectory is None for a in shortcuts)
    assert raw and any(a.trajectory is not None for a in raw)
    assert all(a.diagnostic["status"] != "PASS_SIM" for a in attempts)


def test_search_wall_clock_limit_is_distinct_and_cooperative(monkeypatch):
    names = np.array(["left_shoulder_roll_joint", "right_elbow_joint"])
    ctx = small_context(names, lambda q: True)
    ticks = itertools.chain([0.0, 0.0, 0.0], itertools.repeat(11.0))
    monkeypatch.setattr(search.time, "monotonic", lambda: next(ticks))
    result = search.bounded_rrt_path_v2(ctx, np.array([-0.8, 0]), np.array([0.8, 0]), names,
                                        PairWorkBudget(ctx.policy), seed=5412)
    assert result.raw_path is None and result.diagnostics["outcome"] == "budget_exhausted"
    assert result.diagnostics["reason_code"] == "RRT_WALL_TIME_LIMIT"


def test_invalid_control_endpoints_and_fixed_coordinates_are_rejected():
    names = np.array(["left_shoulder_roll_joint", "right_elbow_joint"])
    ctx = small_context(names)
    with pytest.raises(ValueError, match="outside"):
        search.control_space_v2(ctx, np.array([-2.0, 0]), np.array([0.8, 0]), names)
    fixed_names = np.array(["left_shoulder_roll_joint", "right_elbow_joint", "waist_pitch_joint"])
    fixed_context = small_context(fixed_names)
    with pytest.raises(ValueError, match="non-actuated"):
        search.control_space_v2(fixed_context, np.array([-0.8, 0, 0]), np.array([0.8, 0, 0.2]), fixed_names)


def test_search_records_actual_path_hash_and_budget_use():
    names = np.array(["left_shoulder_roll_joint", "right_elbow_joint"])
    ctx = small_context(names)
    result = search.bounded_rrt_path_v2(ctx, np.array([-0.8, 0]), np.array([0.8, 0]), names,
                                        PairWorkBudget(ctx.policy), seed=5412)
    assert result.diagnostics["raw_path_hash"] == json_hash(result.raw_path.tolist())
    assert result.diagnostics["budget"]["nodes_used"] == 2
    assert result.diagnostics["budget"]["collision_samples_used"] <= ctx.policy["planner"]["budget"]["max_collision_samples"]
    assert result.diagnostics["continuous_collision_certified"] is False
