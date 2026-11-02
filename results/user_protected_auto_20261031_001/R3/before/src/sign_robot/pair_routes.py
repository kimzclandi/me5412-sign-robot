"""Uniform, bounded v2 deterministic routes; no legacy PASS or endpoint override."""
from __future__ import annotations

from dataclasses import dataclass, field
import itertools
import math
from pathlib import Path
import time

import numpy as np

from sign_robot.motion import load_model
from sign_robot.pair_contract import (
    acceptance_pending, coordinate_errors, freeze_library, json_hash, run_identity,
    validate_policy_v2, validate_trajectory_v2,
)
from sign_robot.pair_timing import _extrema, boundary_state_v2, time_route_v2
from sign_robot.pair_windows import WindowApprovalError, load_window_inputs, select_pair_windows
from sign_robot.transitions import (
    MujocoClearance, ik_dual_via_candidates, ik_via_candidates, neutral_pose,
)


class PlanningBudgetExceeded(RuntimeError):
    pass


class PairWorkBudget:
    def __init__(self, policy):
        self.limits = policy["planner"]["budget"]
        self.started = time.monotonic()
        self.deadline = self.started + self.limits["wall_time_s"]
        self.candidates = self.sampled_poses = self.nodes = 0

    def check(self):
        if time.monotonic() >= self.deadline:
            raise PlanningBudgetExceeded("PAIR_WALL_TIME_LIMIT")

    def candidate(self):
        self.check()
        if self.candidates >= self.limits["max_candidates"]:
            raise PlanningBudgetExceeded("PAIR_CANDIDATE_BUDGET_EXHAUSTED")
        self.candidates += 1

    def poses(self, count):
        self.check()
        if self.sampled_poses + count > self.limits["max_collision_samples"]:
            raise PlanningBudgetExceeded("PAIR_COLLISION_SAMPLE_BUDGET_EXHAUSTED")
        self.sampled_poses += count

    def node(self):
        self.check()
        if self.nodes >= self.limits["max_nodes"]:
            raise PlanningBudgetExceeded("PAIR_NODE_BUDGET_EXHAUSTED")
        self.nodes += 1

    def snapshot(self):
        return {"candidates_used": self.candidates, "collision_samples_used": self.sampled_poses,
                "nodes_used": self.nodes, "wall_time_s": time.monotonic() - self.started,
                "limits": dict(self.limits)}


@dataclass
class PairContextV2:
    root: Path
    policy: dict
    library: dict
    clips: dict
    model: object | None
    clearance: object | None
    approvals: dict
    input_blockers: list = field(default_factory=list)


@dataclass
class CandidateAttemptV2:
    trajectory: dict | None
    diagnostic: dict
    timing_trajectories: list = field(default_factory=list)


def build_pair_context_v2(root, policy):
    validate_policy_v2(policy)
    root = Path(root).resolve()
    library, clips = freeze_library(root, policy)
    blockers = list(library["input_errors"])
    blockers.extend({"code": "INVALID_WORD_INPUT", "gloss": w["gloss"], "details": w["input_errors"]}
                    for w in library["words"] if w["input_errors"])
    approvals, model, clearance = {}, None, None
    try:
        approvals = load_window_inputs(root, policy, library)
    except WindowApprovalError as exc:
        blockers.append({"code": exc.code, "details": exc.details})
    if not blockers:
        try:
            model = load_model(root)
            if [model.joint(i).name for i in range(model.njnt)] != library["joint_names"]:
                raise ValueError("Frozen joint order differs from model")
            clearance = MujocoClearance(model, np.asarray(library["joint_names"]),
                                        library_path=root / "motions/hospital_v1_motions.json")
        except (OSError, ValueError, KeyError) as exc:
            blockers.append({"code": "MODEL_OR_COLLISION_INPUT_INVALID", "details": str(exc)})
    return PairContextV2(root, policy, library, clips, model, clearance, approvals, blockers)


def _sampled_clearance(context, q, budget, *, label):
    minimum, worst = float("inf"), None
    for start in range(0, len(q), 16):
        batch = q[start:start + 16]
        budget.poses(len(batch))
        result = context.clearance(batch)
        budget.check()
        if (not np.isfinite(result.min_distance_m) or result.sampled_frames != len(batch)
                or len(result.frame_clearances_m) != len(batch) or not np.isfinite(result.frame_clearances_m).all()):
            raise ValueError("Nonfinite or incomplete planning clearance")
        if result.min_distance_m < minimum:
            minimum, worst = float(result.min_distance_m), dict(result.worst_contact or {})
            worst["sample_index"] = int(worst.get("frame", 0)) + start
    return {"passed": minimum >= context.policy["constraints"]["min_clearance_m"],
            "label": label, "min_clearance_mm": minimum * 1000, "worst_contact": worst,
            "sample_count": len(q), "continuous_collision_certified": False}


def check_timed_route_v2(context, segments, budget):
    """Planner-side sampling; the independent verifier reconstructs again."""
    checks = []
    try:
        for index, segment in enumerate(segments):
            duration = segment["end_time_s"] - segment["start_time_s"]
            c = np.asarray(segment["coefficients"])
            lo, hi = _extrema(c, duration, 1)
            velocity = float(np.maximum(np.abs(lo), np.abs(hi)).max())
            count = max(1, math.ceil(duration / context.policy["validation"]["maximum_time_step_s"]),
                        math.ceil(duration * velocity / context.policy["validation"]["maximum_step_rad"]))
            if count + 1 > budget.limits["max_collision_samples"] - budget.sampled_poses:
                raise PlanningBudgetExceeded("PAIR_COLLISION_SAMPLE_BUDGET_EXHAUSTED")
            u = np.linspace(0, 1, count + 1)
            q = np.vander(u, N=6, increasing=True) @ c.T
            checks.append(_sampled_clearance(context, q, budget, label=f"connector:{index}"))
        return {"passed": all(c["passed"] for c in checks), "segments": checks}
    except PlanningBudgetExceeded as exc:
        return {"passed": False, "budget_exhausted": str(exc), "segments": checks}


def valid_endpoint_choices_v2(context, source, target, budget):
    selection = select_pair_windows(source, target, context.approvals, context.library)
    for role in ("source", "target"):
        item = selection[role]
        clip = context.clips[item["gloss"]]
        checks, valid = [], []
        for frame in item["allowed_frames"]:
            pose = clip["positions"][frame:frame + 1]
            measured = _sampled_clearance(context, pose, budget, label=f"{role}:{frame}")
            coordinates = coordinate_errors(pose, clip["joint_names"], context.model, context.library["couplings"])
            limits = context.policy["constraints"]
            good = (measured["passed"] and coordinates["joint_limit_error"] <= limits["joint_limit_tolerance_rad"]
                    and coordinates["coupling_error"] <= limits["coupling_tolerance_rad"])
            checks.append({"frame": frame, "engineering_valid": bool(good), **measured, **coordinates})
            if good:
                valid.append(frame)
        item.update(valid_frames=valid, endpoint_checks=checks)
    return selection


def assemble_pair_trajectory_v2(context, selection, source_frame, target_frame, segments, method, strategy, seed):
    source, target = selection["source"], selection["target"]
    instances = []
    for item, frames in ((source, [0, source_frame]), (target, [target_frame, target["frame_count"] - 1])):
        instances.append({key: item[key] for key in ("instance_id", "gloss", "motion_sha256", "protected_core_frames",
                                                    "approval_id", "approval_sha256")})
        instances[-1]["source_frames"] = frames
    first, second = context.clips[source["gloss"]], context.clips[target["gloss"]]
    end_time = segments[-1]["end_time_s"]
    phase = {"synchronous": (0.0, 1.0), "early": (0.0, 0.65), "late": (0.35, 1.0)}[strategy]
    trajectory = {
        "schema_version": 2, "representation": "piecewise_polynomial_v2", "pair_id": selection["pair_id"],
        "fps": 30, "joint_names": first["joint_names"].tolist(), "word_instances": instances,
        "segments": [
            {"kind": "source_slice_v2", "start_time_s": 0.0, "end_time_s": source_frame / 30,
             "word_instance_id": source["instance_id"], "source_frames": [0, source_frame], "interpolation": "linear", "time_scale": 1.0},
            *segments,
            {"kind": "source_slice_v2", "start_time_s": end_time,
             "end_time_s": end_time + (len(second["positions"]) - 1 - target_frame) / 30,
             "word_instance_id": target["instance_id"], "source_frames": [target_frame, len(second["positions"]) - 1],
             "interpolation": "linear", "time_scale": 1.0},
        ],
        "finger_strategy": {"name": strategy, "version": 2, "start_fraction": phase[0], "end_fraction": phase[1]},
        "planner": {"method": method, "method_version": 2, "seed": int(seed), "budget": dict(context.policy["planner"]["budget"])},
        "boundary": {"method": "linear_replay_one_sided_v2", "start": boundary_state_v2(first, source_frame, "source"),
                     "end": boundary_state_v2(second, target_frame, "target")},
        "identity": run_identity(context.library, context.policy),
    }
    return validate_trajectory_v2(trajectory)


def _guide_clearance(context, values, budget, label):
    counts = [max(4, math.ceil(float(np.abs(right - left).max()) / context.policy["validation"]["maximum_step_rad"]))
              for left, right in zip(values, values[1:])]
    if sum(counts) + 1 > budget.limits["max_collision_samples"] - budget.sampled_poses:
        raise PlanningBudgetExceeded("PAIR_COLLISION_SAMPLE_BUDGET_EXHAUSTED")
    dense = np.vstack([values[:1], *[np.linspace(left, right, count + 1)[1:]
                      for left, right, count in zip(values, values[1:], counts)]])
    return _sampled_clearance(context, dense, budget, label=label)


def _route_specs(context, a, b, names, first, second, source_frame, target_frame, budget):
    yield "direct", "direct", np.stack([a, b]), {}, []
    budget.check()
    def failure(method, exc):
        return method, method, None, {"factory_error": {"type": type(exc).__name__, "message": str(exc)}}, []
    exceptions = (OSError, ValueError, KeyError, TypeError, np.linalg.LinAlgError)
    try:
        yield "neutral", "neutral", np.stack([a, neutral_pose(names, context.model), b]), {}, []
    except exceptions as exc:
        yield failure("neutral", exc)
    try:
        singles = iter(ik_via_candidates(a, b, names, context.model))
        while True:
            budget.check()
            try:
                direction, via = next(singles)
            except StopIteration:
                break
            budget.check()
            yield "ik_via1", str(direction), np.stack([a, via, b]), {"directions": [str(direction)]}, []
    except exceptions as exc:
        yield failure("ik_via1", exc)
    try:
        duals = iter(ik_dual_via_candidates(a, b, names, context.model))
        while True:
            budget.check()
            try:
                directions, vias = next(duals)
            except StopIteration:
                break
            budget.check()
            yield "ik_via2", "+".join(directions), np.stack([a, *vias, b]), {"directions": list(directions)}, []
    except exceptions as exc:
        yield failure("ik_via2", exc)
    retract, approach = first["positions"][source_frame:], second["positions"][:target_frame + 1]
    prechecks = [_guide_clearance(context, retract, budget, "source_retract_guide"),
                 _guide_clearance(context, approach, budget, "target_approach_guide")]
    source_indices = np.unique(np.linspace(0, len(retract) - 1, min(4, len(retract))).round().astype(int))
    target_indices = np.unique(np.linspace(0, len(approach) - 1, min(4, len(approach))).round().astype(int))
    points = np.vstack([retract[source_indices], approach[target_indices]])
    keep = np.r_[True, np.any(np.diff(points, axis=0) != 0, axis=1)]
    points = points[keep]
    if len(points) == 1:
        points = np.vstack([points, points])
    yield "retract_approach", "retract_approach", points, {
        "source_guide_frames": (source_indices + source_frame).tolist(), "target_guide_frames": target_indices.tolist(),
        "guide_interpretation": "collision-checked geometry guides; not retimed protected word slices"}, prechecks


def iter_deterministic_attempts_v2(context, source, target, *, seed, budget=None):
    budget = PairWorkBudget(context.policy) if budget is None else budget
    words = {w["gloss"] for w in context.library["words"]}
    base = {"schema_version": 2, "pair_id": f"{source}__{target}", "seed": int(seed), "method_version": 2}
    if source not in words or target not in words:
        yield CandidateAttemptV2(None, {**base, "status": "BLOCKED_INPUT", "reason_codes": ["UNKNOWN_GLOSS"], "budget": budget.snapshot()})
        return
    if context.input_blockers:
        yield CandidateAttemptV2(None, {**base, "status": "BLOCKED_INPUT", "reason_codes": [b["code"] for b in context.input_blockers],
                                        "input_blockers": context.input_blockers, "budget": budget.snapshot()})
        return
    try:
        selection = valid_endpoint_choices_v2(context, source, target, budget)
        if any(not selection[role]["valid_frames"] for role in ("source", "target")):
            yield CandidateAttemptV2(None, {**base, "status": "BLOCKED_ENDPOINT", "reason_codes": [
                role.upper() + "_ENDPOINT_INVALID" for role in ("source", "target") if not selection[role]["valid_frames"]],
                "endpoint_selection": selection, "budget": budget.snapshot()})
            return
        first, second = context.clips[source], context.clips[target]
        names = first["joint_names"]
        bounds = np.array([context.model.joint(str(name)).range for name in names])
        for source_frame, target_frame in itertools.product(selection["source"]["valid_frames"], selection["target"]["valid_frames"]):
            a, b = first["positions"][source_frame], second["positions"][target_frame]
            for method, route_name, knots, parameters, prechecks in _route_specs(context, a, b, names, first, second, source_frame, target_frame, budget):
                for strategy in context.policy["finger_strategies"]:
                    budget.candidate()
                    record = {**base, "method": method, "route_name": route_name, "finger_strategy": strategy,
                              "exit_frame": source_frame, "entry_frame": target_frame,
                              "route_parameters": parameters, "route_knots": None if knots is None else knots.tolist(),
                              "route_hash": None,
                              "prechecks": prechecks}
                    if knots is None or not np.isfinite(knots).all():
                        record.update(status="ERROR", reason_codes=["ROUTE_FACTORY_EXCEPTION"], budget=budget.snapshot())
                        yield CandidateAttemptV2(None, record)
                        continue
                    record["route_hash"] = json_hash({"joint_names": names.tolist(), "knots": knots.tolist()})
                    if any(not check["passed"] for check in prechecks):
                        record.update(status="FAILED_SEARCH", reason_codes=["RETRACT_OR_APPROACH_GUIDE_COLLISION"], budget=budget.snapshot())
                        yield CandidateAttemptV2(None, record)
                        continue
                    timed = time_route_v2(knots, boundary_state_v2(first, source_frame, "source"),
                                           boundary_state_v2(second, target_frame, "target"), names, bounds, context.policy,
                                           start_time_s=source_frame / 30, couplings=context.library["couplings"],
                                           finger_strategy=strategy, deadline=budget.deadline,
                                           validate_curve=lambda segments: check_timed_route_v2(context, segments, budget))
                    attempts = [assemble_pair_trajectory_v2(context, selection, source_frame, target_frame, segments, method, strategy, seed)
                                for segments in timed.attempt_segments]
                    trajectory = attempts[-1] if timed.segments is not None else None
                    geometric_failure = any(a.get("geometry") and a["geometry"].get("passed") is False for a in timed.diagnostics["attempts"])
                    status = ("TIMEOUT" if timed.diagnostics["status"] == "TIMEOUT" else
                              "ERROR" if "INVALID_TIMING_INPUT" in timed.diagnostics["reason_codes"] else
                              "FAILED_SEARCH" if trajectory is None and geometric_failure else "FAILED_QUALITY")
                    reasons = (["INDEPENDENT_RECHECK_REQUIRED", *acceptance_pending(context.policy)] if trajectory is not None else timed.diagnostics["reason_codes"])
                    record.update(status=status, reason_codes=reasons, candidate_available=trajectory is not None,
                                  timing=timed.diagnostics, budget=budget.snapshot(),
                                  planner_geometry_passed=trajectory is not None)
                    yield CandidateAttemptV2(trajectory, record, attempts)
                    if status == "TIMEOUT":
                        return
    except WindowApprovalError as exc:
        yield CandidateAttemptV2(None, {**base, "status": "BLOCKED_INPUT", "reason_codes": [exc.code], "details": exc.details, "budget": budget.snapshot()})
    except PlanningBudgetExceeded as exc:
        yield CandidateAttemptV2(None, {**base, "status": "TIMEOUT", "reason_codes": [str(exc)], "budget": budget.snapshot()})
    except (OSError, ValueError, KeyError, TypeError, np.linalg.LinAlgError) as exc:
        yield CandidateAttemptV2(None, {**base, "status": "ERROR", "reason_codes": ["DETERMINISTIC_ROUTE_EXCEPTION"],
                                        "details": {"type": type(exc).__name__, "message": str(exc)}, "budget": budget.snapshot()})
