"""General bounded RRT-Connect in arm plus independent-finger coordinates."""
from __future__ import annotations

from dataclasses import dataclass
import itertools
import math
import time

import numpy as np

from sign_robot.pair_contract import acceptance_pending, coordinate_errors, json_hash
from sign_robot.pair_fingers import _couplings, coupling_error_v2
from sign_robot.pair_routes import (
    CandidateAttemptV2, PairWorkBudget, PlanningBudgetExceeded, _sampled_clearance,
    assemble_pair_trajectory_v2, check_timed_route_v2, valid_endpoint_choices_v2,
)
from sign_robot.pair_timing import boundary_state_v2, time_route_v2
from sign_robot.pair_windows import WindowApprovalError


@dataclass
class SearchPathV2:
    raw_path: np.ndarray | None
    shortcut_path: np.ndarray | None
    diagnostics: dict


def control_space_v2(context, a, b, names):
    """Finite control bounds intersect all affine coupled-child bounds."""
    index, couplings, children = _couplings(names, context.library["couplings"])
    endpoint_errors = coordinate_errors(np.stack([a, b]), names, context.model, couplings)
    if endpoint_errors["joint_limit_error"] > context.policy["constraints"]["joint_limit_tolerance_rad"]:
        raise ValueError("Search endpoint is outside model joint limits")
    if endpoint_errors["coupling_error"] > context.policy["constraints"]["coupling_tolerance_rad"]:
        raise ValueError("Search endpoint violates coupling")
    moving = getattr(context.clearance, "moving_joint_ids", None)
    columns = []
    for column, name in enumerate(names):
        name = str(name)
        arm = any(part in name for part in ("shoulder", "elbow", "wrist"))
        finger = name.startswith(("L_", "R_")) and name not in children
        allowed = moving is None or context.model.joint(name).id in moving
        if arm or (finger and allowed):
            columns.append(column)
    columns = np.asarray(columns, dtype=int)
    if not len(columns):
        raise ValueError("No finite independent arm/finger control space")
    joints = [context.model.joint(str(names[column])) for column in columns]
    bounds = np.asarray([joint.range for joint in joints], dtype=float)
    if (not np.isfinite(bounds).all() or np.any(bounds[:, 0] >= bounds[:, 1])
            or not all(bool(joint.limited[0]) for joint in joints)):
        raise ValueError("RRT needs finite limited control coordinates")
    relations = {str(names[column]): (dimension, 1.0, 0.0) for dimension, column in enumerate(columns)}
    for coupling in couplings:
        relation = relations.get(coupling["parent"])
        if relation is None:
            continue
        dimension, multiplier, offset = relation
        multiplier *= coupling["multiplier"]
        offset = coupling["multiplier"] * offset + coupling["offset"]
        relations[coupling["child"]] = (dimension, multiplier, offset)
        child = context.model.joint(coupling["child"])
        if bool(child.limited[0]) and multiplier:
            lo, hi = sorted((np.asarray(child.range, dtype=float) - offset) / multiplier)
            bounds[dimension, 0] = max(bounds[dimension, 0], lo)
            bounds[dimension, 1] = min(bounds[dimension, 1], hi)
    if np.any(bounds[:, 0] > bounds[:, 1]):
        raise ValueError("Coupled joint limits leave an empty control interval")
    fixed = np.ones(len(names), dtype=bool)
    fixed[columns] = False
    for child in children:
        fixed[index[child]] = False
    tolerance = context.policy["constraints"]["position_tolerance_rad"]
    if np.any(np.abs(a[fixed] - b[fixed]) > tolerance):
        raise ValueError("Search endpoints change non-actuated fixed coordinates")
    for pose in (a, b):
        if coupling_error_v2(pose[None, :], names, couplings) > context.policy["constraints"]["coupling_tolerance_rad"]:
            raise ValueError("Search endpoint violates coupling")
        if np.any(pose[columns] < bounds[:, 0] - tolerance) or np.any(pose[columns] > bounds[:, 1] + tolerance):
            raise ValueError("Search endpoint is outside coupled control bounds")
    def decode(controls):
        controls = np.asarray(controls, dtype=float)
        full = np.tile(a, (len(controls), 1))
        full[:, columns] = controls
        for coupling in couplings:
            full[:, index[coupling["child"]]] = coupling["offset"] + coupling["multiplier"] * full[:, index[coupling["parent"]]]
        return full
    return columns, bounds, decode


def _shortcut_path(path, edge_ok):
    result = [path[0]]
    index = 0
    while index < len(path) - 1:
        target = len(path) - 1
        while target > index + 1 and not edge_ok(path[index], path[target]):
            target -= 1
        result.append(path[target])
        index = target
    return np.asarray(result)


def bounded_rrt_path_v2(context, a, b, names, budget, *, seed):
    """No gloss allowlist. A finite failure is never an infeasibility proof."""
    started = time.monotonic()
    deadline = min(budget.deadline, started + context.policy["planner"]["rrt"]["wall_time_s"])
    search_deadline = started + 0.8 * (deadline - started)
    info = {"method": "rrt_connect", "method_version": 2, "seed": int(seed), "outcome": "not_started",
            "iterations": 0, "path_found": False, "shortcut_checked": False,
            "infeasibility_proven": False, "continuous_collision_certified": False}
    raw = shortcut = None
    def check(limit=deadline):
        budget.check()
        if time.monotonic() >= limit:
            raise PlanningBudgetExceeded("RRT_WALL_TIME_LIMIT")
    def done():
        info.update(runtime_s=time.monotonic() - started, budget=budget.snapshot())
        return SearchPathV2(raw, shortcut, info)
    try:
        check()
        a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
        if a.shape != b.shape or a.shape != (len(names),) or not np.isfinite([a, b]).all():
            raise ValueError("RRT needs finite matching full-coordinate endpoints")
        columns, bounds, decode = control_space_v2(context, a, b, names)
        info.update(control_joint_names=[str(names[i]) for i in columns], control_bounds=bounds.tolist())
        start = np.clip(a[columns], bounds[:, 0], bounds[:, 1])
        goal = np.clip(b[columns], bounds[:, 0], bounds[:, 1])
        rng = np.random.default_rng(seed)
        step = context.policy["planner"]["rrt"]["step_rad"]
        resolution = context.policy["planner"]["rrt"]["edge_resolution_rad"]
        def edge_ok(left, right, limit=deadline):
            check(limit)
            endpoints = decode(np.stack([left, right]))
            count = max(1, math.ceil(float(np.abs(endpoints[1] - endpoints[0]).max()) / resolution))
            if count + 1 > budget.limits["max_collision_samples"] - budget.sampled_poses:
                raise PlanningBudgetExceeded("PAIR_COLLISION_SAMPLE_BUDGET_EXHAUSTED")
            samples = decode(np.linspace(left, right, count + 1))
            result = _sampled_clearance(context, samples, budget, label="rrt_linear_edge")
            check(limit)
            return result["passed"]
        trees = [{"nodes": [start], "parents": [-1], "from_source": True},
                 {"nodes": [goal], "parents": [-1], "from_source": False}]
        budget.node()
        budget.node()
        if edge_ok(start, goal, search_deadline):
            controls = np.stack([start, goal])
        else:
            controls = None
        def extend(tree, target):
            check(search_deadline)
            positions = np.asarray(tree["nodes"])
            nearest = int(np.argmin(np.linalg.norm(positions - target, axis=1)))
            left = positions[nearest]
            delta = target - left
            distance = float(np.linalg.norm(delta))
            if distance <= 1e-12:
                return nearest, "reached"
            reached = distance <= step
            right = target.copy() if reached else left + delta * step / distance
            if not edge_ok(left, right, search_deadline):
                return nearest, "trapped"
            budget.node()
            tree["nodes"].append(right)
            tree["parents"].append(nearest)
            return len(tree["nodes"]) - 1, "reached" if reached else "advanced"
        def branch(tree, index):
            path = []
            while index >= 0:
                path.append(tree["nodes"][index])
                index = tree["parents"][index]
            return path[::-1]
        while controls is None and info["iterations"] < 4 * budget.limits["max_nodes"]:
            check(search_deadline)
            info["iterations"] += 1
            active, passive = trees
            target = (passive["nodes"][0].copy() if rng.random() < context.policy["planner"]["rrt"]["goal_bias"]
                      else rng.uniform(bounds[:, 0], bounds[:, 1]))
            node, state = extend(active, target)
            if state != "trapped":
                other, state = extend(passive, active["nodes"][node])
                while state == "advanced":
                    other, state = extend(passive, active["nodes"][node])
                if state == "reached":
                    first, second = branch(active, node), branch(passive, other)
                    controls = np.asarray(first + second[-2::-1])
                    if not active["from_source"]:
                        controls = controls[::-1]
            trees.reverse()
        if controls is None:
            info.update(outcome="bounded_search_exhausted", reason_code="RRT_ITERATION_BUDGET_EXHAUSTED")
            return done()
        raw = decode(controls)
        raw[0], raw[-1] = a, b
        info.update(path_found=True, outcome="path_found", raw_knots=len(raw),
                    raw_path_hash=json_hash(raw.tolist()), raw_edges_checked=True)
        try:
            short_controls = _shortcut_path(controls, lambda left, right: edge_ok(left, right))
            shortcut = decode(short_controls)
            shortcut[0], shortcut[-1] = a, b
            info.update(shortcut_checked=True, shortcut_knots=len(shortcut),
                        shortcut_path_hash=json_hash(shortcut.tolist()))
        except PlanningBudgetExceeded as exc:
            info.update(shortcut_status="incomplete_keep_raw", shortcut_reason=str(exc))
        return done()
    except PlanningBudgetExceeded as exc:
        info.update(outcome="budget_exhausted", reason_code=str(exc))
        return done()
    except (OSError, ValueError, KeyError, TypeError, np.linalg.LinAlgError) as exc:
        info.update(outcome="invalid_input_or_search_error", reason_code="RRT_INPUT_OR_ENGINE_ERROR",
                    details={"type": type(exc).__name__, "message": str(exc)})
        return done()


def iter_rrt_attempts_v2(context, source, target, *, seed, budget=None):
    budget = PairWorkBudget(context.policy) if budget is None else budget
    base = {"schema_version": 2, "pair_id": f"{source}__{target}", "method": "rrt_connect", "method_version": 2}
    if source not in context.clips or target not in context.clips:
        yield CandidateAttemptV2(None, {**base, "status": "BLOCKED_INPUT", "reason_codes": ["UNKNOWN_GLOSS"], "budget": budget.snapshot()})
        return
    if context.input_blockers:
        yield CandidateAttemptV2(None, {**base, "status": "BLOCKED_INPUT", "reason_codes": [b["code"] for b in context.input_blockers], "budget": budget.snapshot()})
        return
    try:
        selection = valid_endpoint_choices_v2(context, source, target, budget)
        if any(not selection[role]["valid_frames"] for role in ("source", "target")):
            yield CandidateAttemptV2(None, {**base, "status": "BLOCKED_ENDPOINT", "reason_codes": [role.upper() + "_ENDPOINT_INVALID" for role in ("source", "target") if not selection[role]["valid_frames"]], "budget": budget.snapshot()})
            return
        first, second = context.clips[source], context.clips[target]
        names = first["joint_names"]
        bounds = np.asarray([context.model.joint(str(n)).range for n in names])
        for combination, (source_frame, target_frame) in enumerate(itertools.product(selection["source"]["valid_frames"], selection["target"]["valid_frames"])):
            budget.candidate()
            actual_seed = int(seed) + combination
            a, b = first["positions"][source_frame], second["positions"][target_frame]
            found = bounded_rrt_path_v2(context, a, b, names, budget, seed=actual_seed)
            search_record = {**base, "event": "search", "seed": actual_seed, "exit_frame": source_frame, "entry_frame": target_frame,
                             "search": found.diagnostics, "raw_path": None if found.raw_path is None else found.raw_path.tolist(),
                             "shortcut_path": None if found.shortcut_path is None else found.shortcut_path.tolist(), "budget": budget.snapshot()}
            if found.raw_path is None:
                error = found.diagnostics["outcome"] == "invalid_input_or_search_error"
                search_record.update(status="ERROR" if error else "TIMEOUT", reason_codes=[found.diagnostics["reason_code"]])
                yield CandidateAttemptV2(None, search_record)
                if not error:
                    return
                continue
            search_record.update(status="FAILED_QUALITY", reason_codes=["RRT_PATH_REQUIRES_TIMING_AND_INDEPENDENT_RECHECK"])
            yield CandidateAttemptV2(None, search_record)
            variants = []
            if found.shortcut_path is not None and not np.array_equal(found.shortcut_path, found.raw_path):
                variants.append(("shortcut", found.shortcut_path))
            variants.append(("raw", found.raw_path))
            for variant, knots in variants:
                for strategy in context.policy["finger_strategies"]:
                    budget.candidate()
                    timed = time_route_v2(knots, boundary_state_v2(first, source_frame, "source"),
                                           boundary_state_v2(second, target_frame, "target"), names, bounds, context.policy,
                                           start_time_s=source_frame / 30, couplings=context.library["couplings"], finger_strategy=strategy,
                                           deadline=budget.deadline, validate_curve=lambda segments: check_timed_route_v2(context, segments, budget))
                    curves = [assemble_pair_trajectory_v2(context, selection, source_frame, target_frame, segments,
                                                         "rrt_connect", strategy, actual_seed) for segments in timed.attempt_segments]
                    trajectory = curves[-1] if timed.segments is not None else None
                    status = ("TIMEOUT" if timed.diagnostics["status"] == "TIMEOUT" else
                              "ERROR" if "INVALID_TIMING_INPUT" in timed.diagnostics["reason_codes"] else
                              "FAILED_QUALITY" if trajectory is not None else "FAILED_SEARCH")
                    yield CandidateAttemptV2(trajectory, {**base, "event": "timed_candidate", "seed": actual_seed, "variant": variant,
                        "finger_strategy": strategy, "exit_frame": source_frame, "entry_frame": target_frame,
                        "route_hash": json_hash(knots.tolist()), "route_knots": knots.tolist(), "search": found.diagnostics,
                        "timing": timed.diagnostics, "candidate_available": trajectory is not None, "status": status,
                        "reason_codes": ["INDEPENDENT_RECHECK_REQUIRED", *acceptance_pending(context.policy)] if trajectory is not None else timed.diagnostics["reason_codes"],
                        "budget": budget.snapshot()}, curves)
                    if status == "TIMEOUT":
                        return
    except WindowApprovalError as exc:
        yield CandidateAttemptV2(None, {**base, "status": "BLOCKED_INPUT", "reason_codes": [exc.code], "details": exc.details, "budget": budget.snapshot()})
    except PlanningBudgetExceeded as exc:
        yield CandidateAttemptV2(None, {**base, "status": "TIMEOUT", "reason_codes": [str(exc)], "budget": budget.snapshot()})
    except (OSError, ValueError, KeyError, TypeError, np.linalg.LinAlgError) as exc:
        yield CandidateAttemptV2(None, {**base, "status": "ERROR", "reason_codes": ["RRT_ADAPTER_EXCEPTION"],
                                        "details": {"type": type(exc).__name__, "message": str(exc)}, "budget": budget.snapshot()})
