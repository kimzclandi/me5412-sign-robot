"""Deterministic v2 route adapter tests with synthetic reviewed inputs."""
from copy import deepcopy
import itertools

import numpy as np
import pytest

import sign_robot.pair_routes as routes
from pair_v2_fixtures import NOW, seal_bundle, synthetic_inputs
from sign_robot.pair_windows import load_window_approvals


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


class Clearance:
    def __init__(self, *args, **kwargs):
        self.vendor_structural_gaps = []

    def __call__(self, q):
        q = np.asarray(q)
        distance = 0.01 if np.max(np.abs(q)) < 0.5 else -0.01
        contact = {"bodies": ["left", "right"], "geoms": ["a", "b"], "geom_ids": [0, 1],
                   "distance_m": distance, "frame": 0}
        from sign_robot.transitions import ClearanceResult
        return ClearanceResult(distance >= 0.002, distance, [contact] if distance < 0 else [], len(q), [], contact, [], [distance] * len(q))


@pytest.fixture
def context(tmp_path, monkeypatch):
    policy, library, clips, bundle = synthetic_inputs(tmp_path)
    library.update(library="hospital_v1", library_version="hospital_v1@" + "a" * 64,
                   model_hash="b" * 64, code_commit="c" * 40, code_hash="d" * 64,
                   environment={"environment_id": "e" * 64}, input_errors=[], couplings=[])
    approvals = load_window_approvals(tmp_path, policy, library, now=NOW)
    monkeypatch.setattr(routes, "neutral_pose", lambda names, model: np.zeros(len(names)))
    monkeypatch.setattr(routes, "ik_via_candidates", lambda a, b, names, model: [("up", (a+b)/2)])
    monkeypatch.setattr(routes, "ik_dual_via_candidates", lambda a, b, names, model: [(["out", "out"], [(a+b)/3, 2*(a+b)/3])])
    return routes.PairContextV2(tmp_path, policy, library, clips, Model(library["joint_names"]), Clearance(), approvals), policy


def test_all_deterministic_methods_emit_uniform_attempt_records(context):
    ctx, policy = context
    attempts = list(routes.iter_deterministic_attempts_v2(ctx, "HELLO", "PLEASE", seed=5412))
    assert attempts
    methods = {attempt.diagnostic["method"] for attempt in attempts}
    assert {"direct", "neutral", "ik_via1", "ik_via2", "retract_approach"} <= methods
    for attempt in attempts:
        record = attempt.diagnostic
        assert record["method_version"] == 2
        assert record["status"] in {"FAILED_QUALITY", "FAILED_SEARCH", "BLOCKED_ENDPOINT", "TIMEOUT", "ERROR"}
        assert "budget" in record
        if attempt.trajectory is not None:
            assert attempt.trajectory["pair_id"] == "HELLO__PLEASE"
            assert record["candidate_available"] is True


def test_self_pair_keeps_two_instances_and_method_hash(context):
    ctx, _ = context
    attempts = [a for a in routes.iter_deterministic_attempts_v2(ctx, "HELLO", "HELLO", seed=5412)
                if a.trajectory is not None]
    assert attempts
    trajectory = attempts[0].trajectory
    assert trajectory["pair_id"] == "HELLO__HELLO"
    assert trajectory["word_instances"][0]["instance_id"] != trajectory["word_instances"][1]["instance_id"]
    assert attempts[0].diagnostic["route_hash"]


def test_missing_real_input_is_blocked_before_route_factories():
    from sign_robot.pair_routes import build_pair_context_v2, iter_deterministic_attempts_v2
    from sign_robot.pair_contract import load_policy
    from sign_robot.motion import ROOT
    policy = load_policy(ROOT / "config/transition_policy_v2.json", supported_versions=(1, 2))
    ctx = build_pair_context_v2(ROOT, policy)
    assert any(b["code"] == "MISSING_APPROVAL_BUNDLE" for b in ctx.input_blockers)
    attempt = next(iter_deterministic_attempts_v2(ctx, "HELLO", "PLEASE", seed=5412))
    assert attempt.diagnostic["status"] == "BLOCKED_INPUT"
    assert "MISSING_APPROVAL_BUNDLE" in attempt.diagnostic["reason_codes"]


def test_candidate_budget_stops_without_silent_route_drop(context):
    ctx, policy = context
    ctx.policy = deepcopy(policy)
    ctx.policy["planner"]["budget"]["max_candidates"] = 1
    attempts = list(routes.iter_deterministic_attempts_v2(ctx, "HELLO", "PLEASE", seed=5412))
    assert attempts[-1].diagnostic["status"] == "TIMEOUT"
    assert "PAIR_CANDIDATE_BUDGET_EXHAUSTED" in attempts[-1].diagnostic["reason_codes"]


def test_geometry_failure_is_diagnostic_and_no_candidate_is_promoted(context, monkeypatch):
    ctx, _ = context
    monkeypatch.setattr(routes, "_sampled_clearance", lambda *args, **kwargs: {
        "passed": kwargs.get("label", "").startswith(("source:", "target:")), "label": kwargs.get("label", "mock"),
        "min_clearance_mm": 10.0 if kwargs.get("label", "").startswith(("source:", "target:")) else -10.0,
        "worst_contact": {"bodies": ["a", "b"], "distance_m": -0.01}, "sample_count": 1,
        "continuous_collision_certified": False})
    attempts = list(routes.iter_deterministic_attempts_v2(ctx, "HELLO", "PLEASE", seed=5412))
    assert all(a.trajectory is None for a in attempts if a.diagnostic["status"] != "TIMEOUT")
    assert any("RETRACT_OR_APPROACH_GUIDE_COLLISION" in a.diagnostic["reason_codes"] for a in attempts)


def test_factory_exception_is_saved_as_error_and_following_methods_continue(context, monkeypatch):
    ctx, _ = context
    def fail(*args, **kwargs):
        raise ValueError("synthetic IK failure")
    monkeypatch.setattr(routes, "ik_via_candidates", fail)
    attempts = list(routes.iter_deterministic_attempts_v2(ctx, "HELLO", "PLEASE", seed=5412))
    assert any(a.diagnostic["method"] == "ik_via1" and a.diagnostic["status"] == "ERROR" for a in attempts)
    assert any(a.diagnostic["method"] == "ik_via2" for a in attempts)


def test_endpoint_selection_checks_hash_bound_frames(context):
    ctx, _ = context
    selection = routes.valid_endpoint_choices_v2(ctx, "HELLO", "PLEASE", routes.PairWorkBudget(ctx.policy))
    assert selection["source"]["valid_frames"] == [6, 7]
    assert selection["target"]["valid_frames"] == [2, 1]
    assert all(item["engineering_valid"] for role in ("source", "target") for item in selection[role]["endpoint_checks"])


def revise_synthetic_motion(ctx, gloss, positions):
    import json
    from sign_robot.pair_contract import file_hash
    word = next(w for w in ctx.library["words"] if w["gloss"] == gloss)
    ctx.clips[gloss]["positions"] = positions.copy()
    path = ctx.root / word["motion"]
    np.savez(path, **ctx.clips[gloss])
    word["motion_sha256"] = file_hash(path)
    bundle = json.loads((ctx.root / ctx.policy["endpoints"]["approval_file"]).read_text())
    for record in bundle["records"]:
        record["entry_window_frames"], record["exit_window_frames"] = [2, 2], [6, 6]
        if record["gloss"] == gloss:
            record["motion_sha256"] = word["motion_sha256"]
    seal_bundle(ctx.root, ctx.policy, bundle)
    ctx.approvals = load_window_approvals(ctx.root, ctx.policy, ctx.library, now=NOW)


def test_obstacle_requires_a_detour_and_neutral_is_rechecked(context, monkeypatch):
    ctx, _ = context
    names = ctx.library["joint_names"]
    x, y = names.index("right_elbow_joint"), names.index("right_shoulder_roll_joint")
    target = ctx.clips["PLEASE"]["positions"].copy()
    target[:, x] = 0.2
    revise_synthetic_motion(ctx, "PLEASE", target)
    class Obstacle(Clearance):
        def __call__(self, values):
            from sign_robot.transitions import ClearanceResult
            values = np.asarray(values)
            distances = np.where((values[:, x] > 0.04) & (values[:, x] < 0.16) & (np.abs(values[:, y]) < 0.1), -0.01, 0.01)
            frame = int(np.argmin(distances))
            contact = {"bodies": ["a", "b"], "geom_ids": [0, 1], "geoms": ["a", "b"],
                       "distance_m": float(distances[frame]), "frame": frame}
            return ClearanceResult(distances[frame] > 0.002, float(distances[frame]), [], len(values), [], contact, [], distances.tolist())
    ctx.clearance = Obstacle()
    via = np.zeros(53)
    via[x], via[y] = 0.1, 0.8
    monkeypatch.setattr(routes, "neutral_pose", lambda names, model: via.copy())
    attempts = list(itertools.islice(routes.iter_deterministic_attempts_v2(ctx, "HELLO", "PLEASE", seed=5412), 4))
    assert all(a.diagnostic["method"] == "direct" and a.trajectory is None for a in attempts[:3])
    assert attempts[3].diagnostic["method"] == "neutral" and attempts[3].trajectory is not None
    assert attempts[3].diagnostic["planner_geometry_passed"] is True


def test_retract_slice_collision_is_not_hidden_by_route_waypoint_reduction(context):
    ctx, _ = context
    positions = ctx.clips["HELLO"]["positions"].copy()
    positions[7, ctx.library["joint_names"].index("right_elbow_joint")] = 0.8
    revise_synthetic_motion(ctx, "HELLO", positions)
    attempts = list(routes.iter_deterministic_attempts_v2(ctx, "HELLO", "PLEASE", seed=5412))
    retract = [a for a in attempts if a.diagnostic.get("method") == "retract_approach"]
    assert len(retract) == 3 and all(a.trajectory is None for a in retract)
    assert all(a.diagnostic["reason_codes"] == ["RETRACT_OR_APPROACH_GUIDE_COLLISION"] for a in retract)
    assert any(not check["passed"] for check in retract[0].diagnostic["prechecks"])


def test_invalid_source_endpoint_blocks_all_methods(context):
    ctx, _ = context
    positions = ctx.clips["HELLO"]["positions"].copy()
    positions[:, ctx.library["joint_names"].index("right_elbow_joint")] = 0.8
    revise_synthetic_motion(ctx, "HELLO", positions)
    attempts = list(routes.iter_deterministic_attempts_v2(ctx, "HELLO", "PLEASE", seed=5412))
    assert len(attempts) == 1 and attempts[0].trajectory is None
    assert attempts[0].diagnostic["status"] == "BLOCKED_ENDPOINT"
    assert attempts[0].diagnostic["reason_codes"] == ["SOURCE_ENDPOINT_INVALID"]


def test_deterministic_candidate_hashes_exclude_runtime_and_inputs_are_unchanged(context):
    from sign_robot.pair_contract import json_hash
    ctx, _ = context
    before = {g: c["positions"].copy() for g, c in ctx.clips.items()}
    first = list(itertools.islice(routes.iter_deterministic_attempts_v2(ctx, "HELLO", "PLEASE", seed=5412), 3))
    second = list(itertools.islice(routes.iter_deterministic_attempts_v2(ctx, "HELLO", "PLEASE", seed=5412), 3))
    assert [json_hash(a.trajectory) for a in first] == [json_hash(a.trajectory) for a in second]
    for gloss, values in before.items():
        np.testing.assert_array_equal(ctx.clips[gloss]["positions"], values)
