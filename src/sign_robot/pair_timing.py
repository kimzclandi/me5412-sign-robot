"""Bounded connector timing with fixed nonzero position/velocity/acceleration."""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import time

import numpy as np

from sign_robot.pair_contract import BOUNDARY_BRAKING_V1, json_hash, rate_limits


@dataclass
class TimingResult:
    segments: list | None
    diagnostics: dict
    attempt_segments: list = field(default_factory=list)


def boundary_state_v2(clip, frame, role):
    """Exact one-sided derivatives of the unchanged linear word replay."""
    if type(frame) is not int or role not in ("source", "target"):
        raise ValueError("A scalar integer frame and explicit source/target role are required")
    q, t = np.asarray(clip["positions"], dtype=float), np.asarray(clip["timestamps_s"], dtype=float)
    if len(q) != len(t) or not np.isfinite(q).all() or not np.isfinite(t).all() or np.any(np.diff(t) <= 0):
        raise ValueError("Boundary replay samples must be finite with increasing timestamps")
    left, right = (frame - 1, frame) if role == "source" else (frame, frame + 1)
    if not 0 <= left < right < len(q):
        raise ValueError("Insufficient one-sided replay samples")
    return {"position": q[frame].tolist(),
            "velocity": ((q[right] - q[left]) / (t[right] - t[left])).tolist(),
            "acceleration": np.zeros(q.shape[1]).tolist()}


def cut_boundary_state_v2(clip, frame, role, policy, bounds):
    """boundary_state_v2, with clamped stop joints at rest when the policy enables clamped_joint_stop_v1."""
    from sign_robot.pair_contract import clamped_stop_joints
    state = boundary_state_v2(clip, frame, role)
    if not policy["endpoints"].get("clamped_joint_stop"):
        return state
    velocity = np.asarray(state["velocity"])
    velocity[clamped_stop_joints(state["position"], velocity, role, bounds)] = 0.0
    return {**state, "velocity": velocity.tolist()}


def quintic_coefficients_v2(start, end, duration_s):
    """Ascending normalized-u coefficients, recomputed for this exact duration."""
    if type(duration_s) not in (int, float) or not np.isfinite(duration_s) or duration_s <= 0:
        raise ValueError("Duration must be finite and positive")
    first = [np.asarray(start[key], dtype=float) for key in ("position", "velocity", "acceleration")]
    last = [np.asarray(end[key], dtype=float) for key in ("position", "velocity", "acceleration")]
    shape = first[0].shape
    if len(shape) != 1 or not shape[0] or any(a.shape != shape or not np.isfinite(a).all() for a in first + last):
        raise ValueError("All finite boundary state vectors must have the same nonempty shape")
    p0, v0, a0 = first
    p1, v1, a1 = last
    c = np.zeros((len(p0), 6))
    c[:, :3] = np.column_stack([p0, v0 * duration_s, 0.5 * a0 * duration_s**2])
    rhs = np.vstack([p1 - c[:, :3].sum(axis=1),
                     v1 * duration_s - c[:, 1] - 2 * c[:, 2],
                     a1 * duration_s**2 - 2 * c[:, 2]])
    c[:, 3:] = np.linalg.solve(np.array([[1, 1, 1], [3, 4, 5], [6, 12, 20]], dtype=float), rhs).T
    if not np.isfinite(c).all():
        raise ValueError("Nonfinite boundary polynomial")
    return c


def _extrema(coefficients, duration, derivative):
    lower, upper = [], []
    for row in coefficients:
        values = np.polynomial.polynomial.polyder(row, derivative) / duration**derivative
        critical = np.polynomial.polynomial.polyder(values)
        # Planner-side descending polynomial roots; the saved-file verifier
        # independently reconstructs and uses its own ascending representation.
        roots = np.roots(np.trim_zeros(critical[::-1], "f")) if np.count_nonzero(critical) else []
        points = [0.0, 1.0] + [float(root.real) for root in roots if abs(root.imag) < 1e-9 and 0 < root.real < 1]
        measured = np.polyval(values[::-1], points)
        lower.append(float(np.min(measured)))
        upper.append(float(np.max(measured)))
    return np.asarray(lower), np.asarray(upper)


def connector_quality_v2(segments, bounds, names, policy, couplings=()):
    """Analytic connector checks only; original word FD/geometry stays separate."""
    bounds = np.asarray(bounds, dtype=float)
    if not segments:
        raise ValueError("A connector needs at least one polynomial segment")
    if bounds.shape != (len(names), 2) or not np.isfinite(bounds).all() or np.any(bounds[:, 0] > bounds[:, 1]):
        raise ValueError("Every timing coordinate needs explicit finite joint bounds")
    errors = []
    peaks = {"speed": np.zeros(len(names)), "acceleration": np.zeros(len(names)), "jerk": np.zeros(len(names))}
    integral = 0.0
    columns = {str(name): index for index, name in enumerate(names)}
    for segment in segments:
        duration = segment["end_time_s"] - segment["start_time_s"]
        c = np.asarray(segment["coefficients"])
        lo, hi = _extrema(c, duration, 0)
        if (np.any(lo < bounds[:, 0] - policy["constraints"]["joint_limit_tolerance_rad"])
                or np.any(hi > bounds[:, 1] + policy["constraints"]["joint_limit_tolerance_rad"])):
            errors.append("TIMED_CURVE_JOINT_LIMIT_VIOLATION")
        for order, name in ((1, "speed"), (2, "acceleration"), (3, "jerk")):
            lo, hi = _extrema(c, duration, order)
            peaks[name] = np.maximum(peaks[name], np.maximum(np.abs(lo), np.abs(hi)))
        for row in c:
            jerk = np.polynomial.polynomial.polyder(row, 3) / duration**3
            square = np.convolve(jerk, jerk)
            integral += duration * float(np.dot(square, 1 / np.arange(1, len(square) + 1)))
        for coupling in couplings:
            child, parent = columns[coupling["child"]], columns[coupling["parent"]]
            residual = c[child] - coupling["multiplier"] * c[parent]
            residual[0] -= coupling["offset"]
            if np.sum(np.abs(residual)) > policy["constraints"]["coupling_tolerance_rad"]:
                errors.append("TIMED_CURVE_COUPLING_VIOLATION")
    metrics = {"peak_speed_by_joint_rad_s": peaks["speed"].tolist(),
               "peak_acceleration_rad_s2": float(peaks["acceleration"].max()),
               "peak_jerk_rad_s3": float(peaks["jerk"].max()),
               "jerk_integral_rad2_s5": max(0.0, integral),
               "maximum_transition_duration_s": segments[-1]["end_time_s"] - segments[0]["start_time_s"]}
    if not np.isfinite([*peaks["speed"], *peaks["acceleration"], *peaks["jerk"], integral]).all():
        raise ValueError("Nonfinite connector quality")
    if np.any(peaks["speed"] > rate_limits(names, policy) + policy["constraints"]["speed_tolerance_rad_s"]):
        errors.append("TIMED_CURVE_SPEED_VIOLATION")
    for key in ("peak_acceleration_rad_s2", "peak_jerk_rad_s3", "jerk_integral_rad2_s5", "maximum_transition_duration_s"):
        if metrics[key] > policy["quality"]["limits"][key]:
            errors.append("TIMED_CURVE_LIMIT_" + key.upper())
    return metrics, list(dict.fromkeys(errors))


def time_route_v2(knots, start, end, names, bounds, policy, *, start_time_s=0.0,
                  couplings=(), finger_strategy="synchronous", validate_curve=None, deadline=None,
                  finger_arrival=None):
    """Produce a timed candidate or a bounded diagnostic, never formal PASS.

    Fixed boundary derivatives are resolved again after every duration change.
    Optional geometry validation is called on each freshly solved candidate.
    Without it diagnostics explicitly say geometry_checked=false, and the saved
    candidate must still pass the independent complete-clip verifier.
    """
    started = time.monotonic()
    budget = policy["planner"]["budget"]
    deadline = min(deadline, started + budget["wall_time_s"]) if deadline is not None else started + budget["wall_time_s"]
    diagnostics = {"method_version": 2, "status": "TIMING_FAILED", "attempts": [],
                   "reason_codes": [], "geometry_checked": False, "formal_acceptance": False}
    attempted_curves = []

    def finish(segments, reasons, status="TIMING_FAILED"):
        diagnostics.update(status=status, reason_codes=list(reasons), wall_time_s=time.monotonic() - started)
        return TimingResult(segments, diagnostics, attempted_curves)

    try:
        q = np.asarray(knots, dtype=float)
        if (q.ndim != 2 or q.shape[1] != len(names) or len(q) < 2 or not np.isfinite(q).all()
                or len(q) - 1 > budget["max_segments"]):
            raise ValueError("Finite knots must match named coordinates and the segment budget")
        if type(start_time_s) not in (int, float) or not np.isfinite(start_time_s) or start_time_s < 0:
            raise ValueError("Connector start time must be finite and nonnegative")
        bounds = np.asarray(bounds, dtype=float)
        if bounds.shape != (len(names), 2) or not np.isfinite(bounds).all() or np.any(bounds[:, 0] > bounds[:, 1]):
            raise ValueError("Every route coordinate needs explicit finite joint bounds")
        if (np.any(q < bounds[:, 0] - policy["constraints"]["joint_limit_tolerance_rad"])
                or np.any(q > bounds[:, 1] + policy["constraints"]["joint_limit_tolerance_rad"])):
            return finish(None, ["ROUTE_KNOT_JOINT_LIMIT_VIOLATION"])
        for state, pose in ((start, q[0]), (end, q[-1])):
            if not np.allclose(state["position"], pose, atol=policy["constraints"]["position_tolerance_rad"], rtol=0):
                raise ValueError("Route knots differ from fixed boundary positions")
            if np.any(np.abs(state["velocity"]) > rate_limits(names, policy) + policy["constraints"]["speed_tolerance_rad_s"]):
                return finish(None, ["BOUNDARY_SPEED_LIMIT_EXCEEDED"])
            if np.any(np.abs(state["acceleration"]) > policy["quality"]["limits"]["peak_acceleration_rad_s2"]):
                return finish(None, ["BOUNDARY_ACCELERATION_LIMIT_EXCEEDED"])
        rates = rate_limits(names, policy)

        def initial_intervals(knots_):
            initial = np.maximum(policy["planner"]["minimum_duration_s"],
                                 1.875 * np.max(np.abs(np.diff(knots_, axis=0)) / rates, axis=1))
            return np.maximum(1, np.ceil(initial * 30 - 1e-12).astype(int))

        def schedule(knots_, intervals, fixed, variant):
            """Retry with longer free edges; fixed (braking) edges keep their duration."""
            for _ in range(budget["max_time_attempts"]):
                if time.monotonic() >= deadline:
                    return None, ["TIMING_WALL_TIME_LIMIT"], "TIMEOUT"
                durations = intervals / 30
                if float(np.sum(durations)) > policy["quality"]["limits"]["maximum_transition_duration_s"] + 1e-12:
                    return None, ["TIMING_MAXIMUM_DURATION_REACHED"], "TIMING_FAILED"
                segments, metrics, errors, geometry, finger_evidence = timed_curve(knots_, durations)
                entry = {"attempt": len(diagnostics["attempts"]) + 1, "durations_s": durations.tolist(),
                         "metrics": metrics, "reason_codes": errors, "geometry": geometry,
                         "finger_strategy": finger_evidence, "curve_hash": json_hash(segments)}
                if "boundary_braking" in policy["planner"]:
                    entry["variant"] = variant
                diagnostics["attempts"].append(entry)
                if geometry is not None and geometry.get("budget_exhausted"):
                    return None, [geometry["budget_exhausted"]], "TIMEOUT"
                if time.monotonic() >= deadline:
                    return None, ["TIMING_WALL_TIME_LIMIT"], "TIMEOUT"
                if not errors:
                    return segments, [], "TIMED_CANDIDATE"
                # This is a bounded proposal step, not an assumption that the
                # nonzero-boundary curve simply scales with time. Every retry solves.
                grown = np.maximum(intervals + 1, np.ceil(intervals * 1.25).astype(int))
                intervals = np.where(fixed, intervals, grown)
            return None, ["TIMING_BOUNDED_ATTEMPTS_EXHAUSTED"], "TIMING_FAILED"

        def timed_curve(knots_, durations):
            cursor = float(start_time_s)
            segments = []
            for edge, duration in enumerate(durations):
                first = start if edge == 0 else {"position": knots_[edge].tolist(), "velocity": np.zeros(len(names)).tolist(), "acceleration": np.zeros(len(names)).tolist()}
                last = end if edge == len(durations) - 1 else {"position": knots_[edge + 1].tolist(), "velocity": np.zeros(len(names)).tolist(), "acceleration": np.zeros(len(names)).tolist()}
                coefficients = quintic_coefficients_v2(first, last, float(duration))
                segments.append({"kind": "polynomial_v2", "start_time_s": cursor,
                                 "end_time_s": cursor + float(duration), "coefficients": coefficients.tolist()})
                cursor += float(duration)
            from sign_robot.pair_fingers import apply_finger_strategy_to_segments_v2
            segments, finger_evidence = apply_finger_strategy_to_segments_v2(
                segments, names, finger_strategy, couplings,
                coupling_tolerance=policy["constraints"]["coupling_tolerance_rad"],
                max_segments=budget["max_segments"])
            if finger_arrival is not None and finger_arrival["feasible"] and finger_strategy != "early":
                # Early fixes fingers at the target pose by 65%; arrival only
                # composes with synchronous and late phase contracts.
                from sign_robot.pair_fingers import apply_finger_arrival_v1
                total = segments[-1]["end_time_s"] - segments[0]["start_time_s"]
                phase_start = segments[0]["start_time_s"] + (0.35 * total if finger_strategy == "late" else 0.0)
                segments, arrival_evidence = apply_finger_arrival_v1(
                    segments, names, couplings, finger_arrival, phase_start=phase_start,
                    coupling_tolerance=policy["constraints"]["coupling_tolerance_rad"], max_segments=budget["max_segments"])
                finger_evidence = {**finger_evidence, "arrival": arrival_evidence}
            attempted_curves.append(segments)
            metrics, errors = connector_quality_v2(segments, bounds, names, policy, couplings)
            geometry = None
            if validate_curve is not None:
                geometry = validate_curve(segments)
                diagnostics["geometry_checked"] = True
                if not isinstance(geometry, dict) or type(geometry.get("passed")) is not bool:
                    raise ValueError("Geometry callback must return an explicit passed boolean and evidence")
                if not geometry["passed"]:
                    errors.append("GEOMETRY_AFTER_TIMING_FAILED")
            return segments, metrics, errors, geometry, finger_evidence

        segments, reasons, status = schedule(q, initial_intervals(q), np.zeros(len(q) - 1, dtype=bool),
                                             "carry_boundary_velocity")
        braking = policy["planner"].get("boundary_braking")
        if segments is None and braking is not None and status != "TIMEOUT":
            rests = {role: _boundary_rest_v1(state, role, names, bounds, policy, couplings)
                     for role, state in (("source", start), ("target", end))}
            diagnostics["boundary_braking"] = {"version": braking["version"], **{
                role: (None if rest is None else {k: v for k, v in rest.items() if k != "rest"})
                for role, rest in rests.items()}}
            usable = [rest for rest in rests.values() if rest is not None]
            if not usable or not all(rest["feasible"] for rest in usable):
                reasons = [*reasons, "BOUNDARY_BRAKING_INFEASIBLE"]
            elif len(q) + len(usable) - 1 > budget["max_segments"]:
                reasons = [*reasons, "BOUNDARY_BRAKING_SEGMENT_BUDGET"]
            else:
                braked = [q[0]]
                if rests["source"] is not None:
                    braked.append(np.asarray(rests["source"]["rest"]["position"]))
                braked.extend(q[1:-1])
                if rests["target"] is not None:
                    braked.append(np.asarray(rests["target"]["rest"]["position"]))
                braked = np.asarray([*braked, q[-1]])
                intervals = initial_intervals(braked)
                fixed = np.zeros(len(braked) - 1, dtype=bool)
                if rests["source"] is not None:
                    fixed[0], intervals[0] = True, rests["source"]["frames"]
                if rests["target"] is not None:
                    fixed[-1], intervals[-1] = True, rests["target"]["frames"]
                braked_segments, braked_reasons, braked_status = schedule(braked, intervals, fixed, BOUNDARY_BRAKING_V1)
                if braked_segments is not None:
                    return finish(braked_segments, [], "TIMED_CANDIDATE")
                reasons = [*reasons, *("BRAKED_" + r for r in braked_reasons)]
                status = "TIMEOUT" if braked_status == "TIMEOUT" else status
        return finish(segments, reasons, status)
    except (ValueError, KeyError, TypeError, OverflowError, FloatingPointError, np.linalg.LinAlgError) as exc:
        diagnostics["details"] = {"type": type(exc).__name__, "message": str(exc)}
        return finish(None, ["INVALID_TIMING_INPUT"])


def _boundary_rest_v1(state, role, names, bounds, policy, couplings):
    """Shortest whole-frame stop (source) or start-from-rest (target) that meets every connector limit.

    Unclamped, p(u) = p0 + v0 T (u - u^3 + u^4 / 2) is monotone from v0 to rest over
    exactly v0 T / 2 with zero boundary accelerations (peaks 1.5 |v0| / T and
    6 |v0| / T^2). A joint whose rest would pass its limit stops at the limit instead
    (coupled children follow their parent); the resulting harder stop is accepted
    only if the curve keeps every joint-limit, speed, coupling, acceleration and jerk
    limit (acceleration/jerk within ``limit_fraction``).
    """
    braking = policy["planner"]["boundary_braking"]
    p, v = np.asarray(state["position"], dtype=float), np.asarray(state["velocity"], dtype=float)
    if float(np.max(np.abs(v))) <= braking["min_speed_rad_s"]:
        return None
    limits = policy["quality"]["limits"]
    bounds = np.asarray(bounds, dtype=float)
    columns = {str(name): index for index, name in enumerate(names)}
    tolerance = policy["constraints"]["joint_limit_tolerance_rad"]
    zeros = np.zeros(len(p)).tolist()
    sign = 1.0 if role == "source" else -1.0
    last_errors = ["BRAKING_LIMITS_NOT_MET"]
    for frames in range(1, braking["max_frames"] + 1):
        duration = frames / 30
        target = p + sign * v * duration / 2
        rest_position = np.clip(target, bounds[:, 0] + tolerance, bounds[:, 1] - tolerance)
        rest_position = np.where((p < bounds[:, 0]) | (p > bounds[:, 1]), target, rest_position)
        for coupling in couplings:
            parent, child = columns[coupling["parent"]], columns[coupling["child"]]
            rest_position[child] = coupling["multiplier"] * rest_position[parent] + coupling["offset"]
        clamped = int(np.count_nonzero(np.abs(rest_position - target) > 1e-12))
        rest = {"position": rest_position.tolist(), "velocity": zeros, "acceleration": zeros}
        first, last = (state, rest) if role == "source" else (rest, state)
        segment = {"kind": "polynomial_v2", "start_time_s": 0.0, "end_time_s": duration,
                   "coefficients": quintic_coefficients_v2(first, last, duration).tolist()}
        metrics, errors = connector_quality_v2([segment], bounds, names, policy, couplings)
        hard = [e for e in errors if e in ("TIMED_CURVE_JOINT_LIMIT_VIOLATION", "TIMED_CURVE_SPEED_VIOLATION",
                                           "TIMED_CURVE_COUPLING_VIOLATION")]
        if hard:
            last_errors = hard
            continue
        if (metrics["peak_acceleration_rad_s2"] <= braking["limit_fraction"] * limits["peak_acceleration_rad_s2"]
                and metrics["peak_jerk_rad_s3"] <= braking["limit_fraction"] * limits["peak_jerk_rad_s3"]):
            return {"feasible": True, "frames": frames, "rest": rest, "clamped_joints": clamped,
                    "travel_rad": float(np.max(np.abs(rest_position - p))),
                    "peak_acceleration_rad_s2": metrics["peak_acceleration_rad_s2"],
                    "peak_jerk_rad_s3": metrics["peak_jerk_rad_s3"]}
        last_errors = ["BRAKING_LIMITS_NOT_MET"]
    return {"feasible": False, "frames": braking["max_frames"], "reason_codes": last_errors}
