"""Planned return from a sentence's last word to the library rest pose (rest_tail_v1).

Every library clip starts on the same retargeted hands-down pose, so that pose is the
rest target. The tail leaves the last word somewhere in its exit window (after the
protected core), reuses the pair route families and quintic timing, and ends at rest
with zero velocity and acceleration. Candidates are tried in exit-frame order and the
fewest frames from the protected core end to rest win; smoothness breaks ties.
The independent sequence verifier rechecks the saved curve; nothing here is a pass.
"""
from __future__ import annotations

import numpy as np

from sign_robot.pair_contract import json_hash
from sign_robot.pair_routes import (
    PairWorkBudget, PlanningBudgetExceeded, _route_specs, check_timed_route_v2, valid_endpoint_choices_v2,
)
from sign_robot.pair_timing import cut_boundary_state_v2, time_route_v2
from sign_robot.pair_windows import WindowApprovalError
from sign_robot.sequence_contract import BOUNDARY_METHOD, REST_POSE_V1, REST_TAIL_V1, library_rest_pose_v1, rest_state_v1

STRAIGHT_ROUTES = ("direct", "neutral")


def plan_rest_tail_v1(context, gloss, config):
    """Plan one tail for ``gloss``; returns a JSON record with every attempt and the winner (or None)."""
    policy = context.policy
    budget = PairWorkBudget(policy)
    record = {"schema_version": 1, "version": REST_TAIL_V1, "gloss": gloss, "config": dict(config),
              "attempts": [], "selected": None, "status": "FAILED_SEARCH", "reason_codes": [],
              "search_stopped_by": None}
    best = None
    try:
        selection = valid_endpoint_choices_v2(context, gloss, gloss, budget)["source"]
        clip = context.clips[gloss]
        names = clip["joint_names"]
        bounds = np.array([context.model.joint(str(name)).range for name in names])
        rest = library_rest_pose_v1(context.clips)
        tolerance = policy["constraints"]["position_tolerance_rad"]
        core_end = selection["protected_core_frames"][1]
        frames = sorted(f for f in selection["valid_frames"] if np.abs(clip["positions"][f] - rest).max() > tolerance)
        frames = frames[:config["max_exit_frames"]]
        record.update(protected_core_frames=selection["protected_core_frames"], exit_frames_tried_in_order=frames,
                      rest_pose={"version": REST_POSE_V1, "position": rest.tolist()})
        floor = max(1, int(np.ceil(policy["planner"]["minimum_duration_s"] * 30 - 1e-12)))
        target = {"positions": rest[None, :]}
        # Pass 1 tries the two straight routes at every exit frame; pass 2 the detours, where they can still win.
        # A frame whose boundary cannot be stopped fails every route up to the duration limit, so trying all
        # routes frame by frame can spend the whole sample budget before a slower, later frame is reached.
        for families in (STRAIGHT_ROUTES, None):
            for frame in frames:
                if best is not None and frame - core_end + floor >= best["core_gap_frames"]:
                    break  # every later exit keeps more source frames than the winner's whole gap
                a = clip["positions"][frame]
                start = cut_boundary_state_v2(clip, frame, "source", policy, bounds)
                for method, route_name, knots, parameters, prechecks in _route_specs(
                        context, a, rest, names, clip, target, frame, 0, budget):
                    if families is not None and method not in families:
                        break  # the route generator yields the straight routes first
                    if families is None and method in STRAIGHT_ROUTES:
                        continue
                    attempt = {"exit_frame": frame, "method": method, "route_name": route_name,
                               "route_parameters": parameters, "prechecks": prechecks}
                    record["attempts"].append(attempt)
                    if knots is None or not np.isfinite(knots).all() or any(not p["passed"] for p in prechecks):
                        attempt.update(status="FAILED_SEARCH", reason_codes=["ROUTE_FACTORY_OR_GUIDE_FAILED"])
                        continue
                    if best is not None and frame - core_end + floor * (len(knots) - 1) >= best["core_gap_frames"]:
                        # Every route segment lasts at least the minimum duration, so this route cannot win.
                        attempt.update(status="PRUNED_BY_CORE_GAP_BOUND", reason_codes=[])
                        continue
                    knots = np.asarray(knots, dtype=float)
                    knots[-1] = rest  # the rest guide is exact; never a near copy
                    timed = time_route_v2(knots, start, rest_state_v1(rest), names, bounds, policy,
                                          couplings=context.library["couplings"], finger_strategy="synchronous",
                                          deadline=budget.deadline,
                                          validate_curve=lambda segments: check_timed_route_v2(context, segments, budget))
                    attempt.update(route_hash=json_hash({"joint_names": names.tolist(), "knots": knots.tolist()}),
                                   timing_status=timed.diagnostics["status"], reason_codes=timed.diagnostics["reason_codes"],
                                   timing_attempts=len(timed.diagnostics["attempts"]))
                    if timed.segments is None:
                        attempt["status"] = "TIMEOUT" if timed.diagnostics["status"] == "TIMEOUT" else "FAILED_SEARCH"
                        if attempt["status"] == "TIMEOUT":
                            raise PlanningBudgetExceeded("REST_TAIL_TIME_OR_SAMPLE_BUDGET")
                        continue
                    metrics = timed.diagnostics["attempts"][-1]["metrics"]
                    frames_ = round((timed.segments[-1]["end_time_s"] - timed.segments[0]["start_time_s"]) * 30)
                    limits = policy["quality"]["limits"]
                    attempt.update(status="TIMED_CANDIDATE", connector_frames=frames_, core_gap_frames=frame - core_end + frames_,
                                   metrics={k: metrics[k] for k in ("peak_acceleration_rad_s2", "peak_jerk_rad_s3",
                                                                     "jerk_integral_rad2_s5", "maximum_transition_duration_s")},
                                   variant=timed.diagnostics["attempts"][-1].get("variant"))
                    key = (attempt["core_gap_frames"], metrics["peak_jerk_rad_s3"] / limits["peak_jerk_rad_s3"],
                           metrics["peak_acceleration_rad_s2"] / limits["peak_acceleration_rad_s2"],
                           metrics["jerk_integral_rad2_s5"], policy["planner"]["methods"].index(method), json_hash(timed.segments))
                    if best is None or key < best["key"]:
                        best = {"key": key, "core_gap_frames": attempt["core_gap_frames"], "attempt": attempt,
                                "segments": timed.segments, "start": start, "rest": rest}
    except PlanningBudgetExceeded as exc:
        # The best tail so far is still offered; the record says the search did not finish.
        record.update(search_stopped_by=str(exc), status="TIMEOUT", reason_codes=[str(exc)])
    except WindowApprovalError as exc:
        record.update(status="BLOCKED_INPUT", reason_codes=[exc.code])
        best = None
    if best is not None:
        attempt = best["attempt"]
        record.update(status="TIMED_CANDIDATE", reason_codes=["INDEPENDENT_SEQUENCE_RECHECK_REQUIRED"], selected={
            "attempt_index": record["attempts"].index(attempt), "exit_frame": attempt["exit_frame"],
            "method": attempt["method"], "route_name": attempt["route_name"],
            "connector_frames": attempt["connector_frames"], "core_gap_frames": attempt["core_gap_frames"],
            "boundary": {"method": BOUNDARY_METHOD, "start": best["start"], "end": rest_state_v1(best["rest"])},
            "segments": best["segments"]})
    elif record["status"] == "FAILED_SEARCH":
        record["reason_codes"] = ["NO_TIMED_REST_TAIL"]
    record["budget"] = budget.snapshot()
    return record
