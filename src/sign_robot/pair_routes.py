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
    EDGE_AWARE_CUT_GENERATORS, LIFT_OFF_ARRIVAL_GENERATOR, acceptance_pending, coordinate_errors, freeze_library, json_hash,
    STAGED_EXIT_METHOD, rate_limits, retained_edge_flags, run_identity, staged_exit_config, staged_group_mask,
    validate_policy_v2, validate_trajectory_v2,
)
from sign_robot.pair_timing import _extrema, cut_boundary_state_v2, time_route_v2
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


def _model_bounds(context, clip):
    return np.asarray([context.model.joint(str(n)).range for n in clip["joint_names"]])


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
        automatic = item.get("window_provenance") == "algorithm"
        if automatic:
            item.update(retained_outer_frame=item["protected_core_frames"][0 if role == "source" else 1],
                        outer_cut_rule="protection_bounds_v1")
        checks, valid = [], []
        screened = None
        if automatic and context.policy["endpoints"].get("retained_edge_screen"):
            bounds = np.asarray([context.model.joint(str(n)).range for n in clip["joint_names"]])
            screened, cuts = retained_edge_flags(clip, item["protected_core_frames"], bounds,
                                                 context.policy["endpoints"]["retained_edge_screen"])
        for frame in item["allowed_frames"]:
            pose = clip["positions"][frame:frame + 1]
            measured = _sampled_clearance(context, pose, budget, label=f"{role}:{frame}")
            coordinates = coordinate_errors(pose, clip["joint_names"], context.model, context.library["couplings"])
            limits = context.policy["constraints"]
            state = cut_boundary_state_v2(clip, frame, role, context.policy, _model_bounds(context, clip))
            speed_ratio = float(np.max(np.abs(state["velocity"]) / rate_limits(clip["joint_names"], context.policy)))
            boundary_valid = bool(np.all(np.abs(state["velocity"]) <= rate_limits(clip["joint_names"], context.policy) + limits["speed_tolerance_rad_s"]))
            bound = np.asarray([context.model.joint(str(n)).range for n in clip["joint_names"]])
            limited = np.asarray([bool(context.model.joint(str(n)).limited[0]) for n in clip["joint_names"]])
            directed_v = np.asarray(state["velocity"]) * (1 if role == "source" else -1)
            tangent_bad = limited & (((pose[0] <= bound[:, 0] + limits["joint_limit_tolerance_rad"]) & (directed_v < -limits["speed_tolerance_rad_s"]))
                                     | ((pose[0] >= bound[:, 1] - limits["joint_limit_tolerance_rad"]) & (directed_v > limits["speed_tolerance_rad_s"])))
            tangent_valid = not np.any(tangent_bad)
            edge_valid = True
            if screened is not None:
                c0, c1 = item["protected_core_frames"]
                if role == "source":
                    edge_valid = not screened[c1 + 1:frame + 1 if cuts else frame].any()
                else:
                    edge_valid = not screened[frame if cuts else frame + 1:c0].any()
            good = (measured["passed"] and coordinates["joint_limit_error"] <= limits["joint_limit_tolerance_rad"]
                    and coordinates["coupling_error"] <= limits["coupling_tolerance_rad"]
                    and ((boundary_valid and tangent_valid) or not automatic) and edge_valid)
            checks.append({"frame": frame, "engineering_valid": bool(good), **measured, **coordinates,
                           "boundary_state": state, "boundary_speed_ratio": speed_ratio,
                           "boundary_speed_valid": bool(boundary_valid),
                           "boundary_limit_viable": bool(tangent_valid),
                           "outward_limit_joints": [str(n) for n in clip["joint_names"][tangent_bad]],
                           **({} if screened is None else {"retained_edge_valid": bool(edge_valid)}),
                           "original_time_s": float(clip["timestamps_s"][frame])})
            if good:
                valid.append(frame)
        if automatic and role == "source" and staged_exit_config(context.policy, item["gloss"]) is not None:
            # A staged exit leaves exactly at the protected core end.
            valid = [frame for frame in valid if frame == item["protected_core_frames"][1]]
            item["staged_exit"] = True
        if automatic:
            measurements = {c["frame"]: c for c in checks}
            valid.sort(key=lambda frame: (measurements[frame]["boundary_speed_ratio"],
                                         abs(frame - item["protected_core_frames"][1 if role == "source" else 0]), frame))
        item.update(valid_frames=valid, endpoint_checks=checks)
    return selection


def assemble_pair_trajectory_v2(context, selection, source_frame, target_frame, segments, method, strategy, seed):
    source, target = selection["source"], selection["target"]
    automatic = context.policy["endpoints"]["strategy"] == "user_protected_auto_windows_v1"
    source_start = source["retained_outer_frame"] if automatic else 0
    target_end = target["retained_outer_frame"] if automatic else target["frame_count"] - 1
    instances = []
    reference = ("protection_id", "protection_sha256", "window_provenance") if automatic else ("approval_id", "approval_sha256")
    for item, frames in ((source, [source_start, source_frame]), (target, [target_frame, target_end])):
        instances.append({key: item[key] for key in ("instance_id", "gloss", "motion_sha256", "protected_core_frames",
                                                    *reference)})
        instances[-1]["source_frames"] = frames
    first, second = context.clips[source["gloss"]], context.clips[target["gloss"]]
    end_time = segments[-1]["end_time_s"]
    phase = {"synchronous": (0.0, 1.0), "early": (0.0, 0.65), "late": (0.35, 1.0)}[strategy]
    trajectory = {
        "schema_version": 2, "representation": "piecewise_polynomial_v2", "pair_id": selection["pair_id"],
        "fps": 30, "joint_names": first["joint_names"].tolist(), "word_instances": instances,
        "segments": [
            {"kind": "source_slice_v2", "start_time_s": 0.0, "end_time_s": (source_frame - source_start) / 30,
             "word_instance_id": source["instance_id"], "source_frames": [source_start, source_frame], "interpolation": "linear", "time_scale": 1.0},
            *segments,
            {"kind": "source_slice_v2", "start_time_s": end_time,
             "end_time_s": end_time + (target_end - target_frame) / 30,
             "word_instance_id": target["instance_id"], "source_frames": [target_frame, target_end],
             "interpolation": "linear", "time_scale": 1.0},
        ],
        "finger_strategy": {"name": strategy, "version": 2, "start_fraction": phase[0], "end_fraction": phase[1]},
        "planner": {"method": method, "method_version": 2, "seed": int(seed), "budget": dict(context.policy["planner"]["budget"])},
        "boundary": {"method": "linear_replay_one_sided_v2",
                     "start": cut_boundary_state_v2(first, source_frame, "source", context.policy, _model_bounds(context, first)),
                     "end": cut_boundary_state_v2(second, target_frame, "target", context.policy, _model_bounds(context, second))},
        "identity": run_identity(context.library, context.policy),
    }
    if automatic:
        trajectory["endpoint_mode"] = "user_protected_auto_windows_v1"
    return validate_trajectory_v2(trajectory)


def target_finger_arrival_v1(context, clip, target_frame):
    """Lift-off arrival plan under the v3 cut generator, else None."""
    if context.policy["endpoints"].get("generator_version") != LIFT_OFF_ARRIVAL_GENERATOR:
        return None
    from sign_robot.pair_fingers import finger_arrival_plan_v1
    names = clip["joint_names"]
    bounds = np.asarray([context.model.joint(str(n)).range for n in names])
    return finger_arrival_plan_v1(clip, int(target_frame), names, bounds, context.policy, context.library["couplings"])


def retained_edge_jerk_v2(clip, core, frame, role):
    """Squared-jerk integral of the original frames kept between core and cut.

    Uses the verifier's 30 Hz finite-difference stencil on the source clip
    alone, so it is a ranking estimate; the saved replay is still rechecked.
    """
    q, t = clip["positions"], clip["timestamps_s"]
    jerk = np.gradient(np.gradient(np.gradient(q, t, axis=0, edge_order=2), t, axis=0, edge_order=2), t, axis=0, edge_order=2)
    energy = np.sum(jerk * jerk, axis=1)
    first, last = (core[1], frame) if role == "source" else (frame, core[0])
    return float(np.trapezoid(energy[first:last + 1], x=t[first:last + 1])) if last > first else 0.0


def endpoint_pairs_v1(context, selection):
    """Bounded shortlist after safety screening, ordered by boundary motion.

    With the edge-aware cut generator the retained-edge jerk estimate ranks
    right after the limit-violation estimate, before boundary speed.
    """
    source, target = selection["source"], selection["target"]
    measurements = {role: {c["frame"]: c for c in selection[role]["endpoint_checks"]} for role in ("source", "target")}
    bound = np.asarray([context.model.joint(str(n)).range for n in context.library["joint_names"]])
    u = np.linspace(0, 1, 17)[:, None]
    duration = context.policy["planner"]["minimum_duration_s"]
    edge_aware = context.policy["endpoints"].get("generator_version") in EDGE_AWARE_CUT_GENERATORS
    edges, arrivals = {}, {}
    fingers = np.asarray([str(n).startswith(("L_", "R_")) for n in context.library["joint_names"]])
    if context.policy["endpoints"].get("generator_version") == LIFT_OFF_ARRIVAL_GENERATOR:
        arrivals = {f: target_finger_arrival_v1(context, context.clips[target["gloss"]], f) for f in target["valid_frames"]}
    if edge_aware:
        for role, item in (("source", source), ("target", target)):
            clip = context.clips[item["gloss"]]
            edges[role] = {f: retained_edge_jerk_v2(clip, item["protected_core_frames"], f, role) for f in item["valid_frames"]}
    def score(pair):
        a, b = pair
        pa, pb = (np.asarray(measurements[role][f]["boundary_state"]["position"]) for role,f in (("source",a),("target",b)))
        va, vb = (np.asarray(measurements[role][f]["boundary_state"]["velocity"]) for role,f in (("source",a),("target",b)))
        delta = pb - pa
        values = pa + va*duration*u + (10*delta-(6*va+4*vb)*duration)*u**3 + (-15*delta+(8*va+7*vb)*duration)*u**4 + (6*delta-3*(va+vb)*duration)*u**5
        excess = np.maximum(np.maximum(bound[:,0]-values,values-bound[:,1]),0)
        arrival = arrivals.get(b)
        if arrival is not None and arrival["feasible"]:
            excess = excess[:, ~fingers]  # lift-off arrival replaces these finger curves
        estimated_violation = float(excess.max())
        # A ranking estimate only; analytic extrema and geometry are still mandatory.
        displacement = np.max(np.abs(delta))
        retained = a - source["protected_core_frames"][0] + target["protected_core_frames"][1] - b
        if edge_aware:
            return (bool(arrival is not None and not arrival["feasible"]), round(estimated_violation, 10), round(edges["source"][a] + edges["target"][b], 6),
                    max(measurements['source'][a]['boundary_speed_ratio'], measurements['target'][b]['boundary_speed_ratio']),
                    float(displacement), retained, a, b)
        return (round(estimated_violation, 10), max(measurements['source'][a]['boundary_speed_ratio'], measurements['target'][b]['boundary_speed_ratio']),
                float(displacement), retained, a, b)
    ranked = sorted(itertools.product(source["valid_frames"], target["valid_frames"]), key=score)
    if "boundary_braking" not in context.policy["planner"]:
        return ranked[:8]
    # Braking fallback: the ranking above prefers cuts next to the protected core, where the
    # source may still move fast toward a joint limit and cannot be stopped within the limits.
    # Interleave that shortlist with up to 8 cut pairs that both sides can brake (fewest braking
    # frames first, ties keep the ranking above), so every method family reaches a brakeable cut
    # within its time slice; the top-ranked pair stays first.
    from sign_robot.pair_timing import _boundary_rest_v1
    names = context.library["joint_names"]
    stops = {}
    for role, item in (("source", source), ("target", target)):
        for frame in item["valid_frames"]:
            rest = _boundary_rest_v1(measurements[role][frame]["boundary_state"], role, names, bound,
                                     context.policy, context.library["couplings"])
            stops[role, frame] = 0 if rest is None else (rest["frames"] if rest["feasible"] else None)
    brakeable = [p for p in ranked[8:] if stops["source", p[0]] is not None and stops["target", p[1]] is not None]
    brakeable.sort(key=lambda p: stops["source", p[0]] + stops["target", p[1]])
    head, extra = ranked[:8], brakeable[:8]
    return [p for pair in itertools.zip_longest(head, extra) for p in pair if p is not None]


def _iter_auto_deterministic_v1(context, selection, seed, budget, base):
    yield CandidateAttemptV2(None, {**base, "event": "algorithm_window_screen", "status": "FAILED_QUALITY",
        "reason_codes": ["ALGORITHM_ENDPOINT_SCREEN_ONLY"], "endpoint_selection": selection,
        "endpoint_pair_shortlist": [list(p) for p in endpoint_pairs_v1(context, selection)],
        "shortlist_limit": 16 if "boundary_braking" in context.policy["planner"] else 8, "budget": budget.snapshot()})
    staged = staged_exit_config(context.policy, selection["source"]["gloss"])
    if staged is not None:
        yield from _iter_staged_exit_v1(context, selection, seed, budget, base, staged)
        return
    first, second = (context.clips[selection[role]["gloss"]] for role in ("source", "target"))
    names = first["joint_names"]
    bounds = np.array([context.model.joint(str(name)).range for name in names])
    stage_deadline = budget.started + 2 * budget.limits["wall_time_s"] / 3
    for wanted in context.policy["planner"]["methods"][:-1]:
        family_index = context.policy["planner"]["methods"].index(wanted)
        family_deadline = budget.started + (family_index + 1) * (stage_deadline - budget.started) / 5
        # Try direct across the shortlist before constructing any detour.
        for source_frame, target_frame in endpoint_pairs_v1(context, selection):
            if time.monotonic() >= family_deadline:
                break
            a, b = first["positions"][source_frame], second["positions"][target_frame]
            specs = _route_specs(context, a, b, names, first, second, source_frame, target_frame, budget)
            for method, route_name, knots, parameters, prechecks in specs:
                if method != wanted:
                    if context.policy["planner"]["methods"].index(method) > context.policy["planner"]["methods"].index(wanted):
                        break
                    continue
                for strategy in context.policy["finger_strategies"]:
                    if time.monotonic() >= family_deadline:
                        break
                    if (time.monotonic() >= stage_deadline or budget.candidates >= 3 * budget.limits["max_candidates"] // 4
                            or budget.sampled_poses >= 2 * budget.limits["max_collision_samples"] // 3):
                        yield CandidateAttemptV2(None, {**base, "event": "stage_budget", "status": "FAILED_SEARCH",
                            "reason_codes": ["DETERMINISTIC_RESERVE_FOR_BOUNDED_SEARCH"], "budget": budget.snapshot()})
                        return
                    budget.candidate()
                    record = {**base, "method": method, "route_name": route_name, "finger_strategy": strategy,
                        "exit_frame": source_frame, "entry_frame": target_frame, "route_parameters": parameters,
                        "route_knots": None if knots is None else knots.tolist(), "route_hash": None, "prechecks": prechecks}
                    if knots is None or not np.isfinite(knots).all() or any(not p["passed"] for p in prechecks):
                        record.update(status="FAILED_SEARCH", reason_codes=["ROUTE_FACTORY_OR_GUIDE_FAILED"], budget=budget.snapshot())
                        yield CandidateAttemptV2(None, record)
                        continue
                    record["route_hash"] = json_hash({"joint_names": names.tolist(), "knots": knots.tolist()})
                    start_time = (source_frame - selection["source"]["retained_outer_frame"]) / 30
                    timed = time_route_v2(knots, cut_boundary_state_v2(first, source_frame, "source", context.policy, bounds),
                        cut_boundary_state_v2(second, target_frame, "target", context.policy, bounds),
                        names, bounds, context.policy, start_time_s=start_time, couplings=context.library["couplings"],
                        finger_strategy=strategy, deadline=min(budget.deadline, family_deadline),
                        validate_curve=lambda segments: check_timed_route_v2(context, segments, budget),
                        finger_arrival=target_finger_arrival_v1(context, second, target_frame))
                    curves = [assemble_pair_trajectory_v2(context, selection, source_frame, target_frame, segments, method, strategy, seed)
                              for segments in timed.attempt_segments]
                    trajectory = curves[-1] if timed.segments is not None else None
                    record.update(status="FAILED_QUALITY" if trajectory is not None else "FAILED_SEARCH",
                        reason_codes=["INDEPENDENT_RECHECK_REQUIRED", *acceptance_pending(context.policy)] if trajectory is not None else timed.diagnostics["reason_codes"],
                        timing=timed.diagnostics, candidate_available=trajectory is not None,
                        planner_geometry_passed=trajectory is not None, budget=budget.snapshot())
                    yield CandidateAttemptV2(trajectory, record, curves)


def staged_exit_knots(a, b, rest, names, staged, model):
    """(route name, knots) per combination of stage targets: each stage moves only its joint group."""
    from sign_robot.retarget import G1Retargeter
    from sign_robot.transitions import VIA_DIRECTIONS, _ik_wrist_offset
    solver, directions = None, dict(VIA_DIRECTIONS)
    for targets in itertools.product(*(stage["to"] for stage in staged["stages"])):
        q, knots = np.asarray(a, dtype=float), [np.asarray(a, dtype=float)]
        for stage, to in zip(staged["stages"], targets):
            mask = staged_group_mask(names, stage["group"])
            q = q.copy()
            if to.startswith("ik:"):
                _, direction, steps = to.split(":")
                solver = solver or G1Retargeter(model, [])
                side = "left" if stage["group"].startswith("left") else "right"
                moved = q
                for _ in range(int(steps)):
                    moved = _ik_wrist_offset(solver, moved, names, directions[direction], offset_sides=(side,))
                q[mask] = moved[mask]
            else:
                q[mask] = {"rest": np.asarray(rest)[mask], "target": np.asarray(b)[mask], "zero": 0.0}[to]
            if not np.array_equal(q, knots[-1]):
                knots.append(q)
        if not np.array_equal(knots[-1], b):
            knots.append(np.asarray(b, dtype=float))
        yield "+".join(f"{s['group']}:{t}" for s, t in zip(staged["stages"], targets)), np.stack(knots)


def _iter_staged_exit_v1(context, selection, seed, budget, base, staged):
    """Staged routes only, synchronous fingers, from the core end to each valid entry."""
    from sign_robot.sequence_contract import library_rest_pose_v1
    first, second = (context.clips[selection[role]["gloss"]] for role in ("source", "target"))
    names = first["joint_names"]
    bounds = np.array([context.model.joint(str(name)).range for name in names])
    rest = library_rest_pose_v1(context.clips)
    # The exit is the single core-end frame, so try every valid entry, nearest the target core first (fewest
    # retained frames, as the core-gap selection prefers) instead of the generic cut-pair shortlist.
    pairs = [(source_frame, target_frame) for source_frame in selection["source"]["valid_frames"]
             for target_frame in sorted(selection["target"]["valid_frames"], reverse=True)]
    for source_frame, target_frame in pairs:
        a, b = first["positions"][source_frame], second["positions"][target_frame]
        for route_name, knots in staged_exit_knots(a, b, rest, names, staged, context.model):
            if time.monotonic() >= budget.deadline:
                return
            budget.candidate()
            record = {**base, "method": STAGED_EXIT_METHOD, "route_name": route_name, "finger_strategy": "synchronous",
                      "exit_frame": source_frame, "entry_frame": target_frame,
                      "route_parameters": {"stages": staged["stages"]}, "route_knots": knots.tolist(),
                      "route_hash": json_hash({"joint_names": names.tolist(), "knots": knots.tolist()}), "prechecks": []}
            start_time = (source_frame - selection["source"]["retained_outer_frame"]) / 30
            timed = time_route_v2(knots, cut_boundary_state_v2(first, source_frame, "source", context.policy, bounds),
                                  cut_boundary_state_v2(second, target_frame, "target", context.policy, bounds),
                                  names, bounds, context.policy, start_time_s=start_time,
                                  couplings=context.library["couplings"], finger_strategy="synchronous",
                                  deadline=budget.deadline,
                                  validate_curve=lambda segments: check_timed_route_v2(context, segments, budget),
                                  finger_arrival=target_finger_arrival_v1(context, second, target_frame))
            curves = [assemble_pair_trajectory_v2(context, selection, source_frame, target_frame, segments,
                                                  STAGED_EXIT_METHOD, "synchronous", seed)
                      for segments in timed.attempt_segments]
            trajectory = curves[-1] if timed.segments is not None else None
            record.update(status="FAILED_QUALITY" if trajectory is not None else "FAILED_SEARCH",
                          reason_codes=(["INDEPENDENT_RECHECK_REQUIRED", *acceptance_pending(context.policy)]
                                        if trajectory is not None else timed.diagnostics["reason_codes"]),
                          timing=timed.diagnostics, candidate_available=trajectory is not None,
                          planner_geometry_passed=trajectory is not None, budget=budget.snapshot())
            yield CandidateAttemptV2(trajectory, record, curves)


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
        if context.policy["endpoints"]["strategy"] == "user_protected_auto_windows_v1":
            yield from _iter_auto_deterministic_v1(context, selection, seed, budget, base)
            return
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
                    timed = time_route_v2(knots, cut_boundary_state_v2(first, source_frame, "source", context.policy, bounds),
                                           cut_boundary_state_v2(second, target_frame, "target", context.policy, bounds),
                                           names, bounds, context.policy,
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
