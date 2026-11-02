"""Polynomial finger phase strategies; dependent joints are never drivers."""
from __future__ import annotations

from copy import deepcopy
import math

import numpy as np

from sign_robot.pair_contract import V2_FINGER_STRATEGIES, polynomial_boundary_v2


def _couplings(names, couplings):
    index = {str(name): column for column, name in enumerate(names)}
    if len(index) != len(names):
        raise ValueError("Finger coordinates must be uniquely named")
    remaining, children = [], set()
    for coupling in couplings:
        parent, child = coupling["parent"], coupling["child"]
        if parent not in index or child not in index or parent == child or child in children:
            raise ValueError("Coupling must have unique children and valid distinct named joints")
        if not parent.startswith(("L_", "R_")) or not child.startswith(("L_", "R_")):
            raise ValueError("Finger strategies cannot recouple an arm or fixed coordinate")
        if (type(coupling["multiplier"]) not in (int, float) or type(coupling["offset"]) not in (int, float)
                or not np.isfinite(coupling["multiplier"]) or not np.isfinite(coupling["offset"])):
            raise ValueError("Coupling coefficients must be finite")
        children.add(child)
        remaining.append(coupling)
    ordered = []
    while remaining:
        pending_children = {c["child"] for c in remaining}
        ready = [c for c in remaining if c["parent"] not in pending_children]
        if not ready:
            raise ValueError("Cyclic finger coupling is not supported")
        ordered.extend(ready)
        remaining = [c for c in remaining if c not in ready]
    return index, ordered, children


def coupling_error_v2(positions, names, couplings):
    q = np.asarray(positions, dtype=float)
    if q.ndim != 2 or q.shape[1] != len(names) or not np.isfinite(q).all():
        raise ValueError("Coupling measurements require finite named-coordinate rows")
    index, ordered, _ = _couplings(names, couplings)
    errors = [np.abs(q[:, index[c["child"]]] - c["offset"] - c["multiplier"] * q[:, index[c["parent"]]])
              for c in ordered]
    return float(np.max(errors)) if errors else 0.0


def _endpoints(start, end, names, couplings, tolerance):
    if type(tolerance) not in (int, float) or not np.isfinite(tolerance) or tolerance < 0:
        raise ValueError("Coupling tolerance must be finite and nonnegative")
    start, end = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
    if (start.shape != end.shape or start.ndim != 1 or len(start) != len(names)
            or not np.isfinite(start).all() or not np.isfinite(end).all()):
        raise ValueError("Finger endpoints must be finite named vectors")
    if coupling_error_v2(np.stack([start, end]), names, couplings) > tolerance:
        raise ValueError("Finger endpoint violates coupling")
    return start, end


def _restrict(segment, start, end):
    """Exact affine substitution from old u to new v; preserves the arm curve."""
    c = np.asarray(segment["coefficients"], dtype=float)
    duration = segment["end_time_s"] - segment["start_time_s"]
    alpha = (start - segment["start_time_s"]) / duration
    beta = (end - start) / duration
    result = np.zeros_like(c)
    for power in range(6):
        for degree in range(power, 6):
            result[:, power] += c[:, degree] * math.comb(degree, power) * alpha**(degree - power) * beta**power
    return result


def _at(segments, moment):
    for segment in segments:
        if segment["start_time_s"] - 1e-10 <= moment <= segment["end_time_s"] + 1e-10:
            return segment
    raise ValueError("Finger phase does not cover the base timeline")


def apply_finger_strategy_to_segments_v2(segments, names, strategy, couplings, *,
                                         coupling_tolerance=1e-8, max_segments=256):
    """Preserve the entire arm curve and finger knots, with fixed endpoint p/v/a.

    Early compresses the finger route into the first 65%; late into the last
    65%. A same-pose prefix/tail matches nonzero source/target derivatives when
    a pure stationary hold would violate them. Those extra curves are checked
    by timing and independent geometry, never assumed collision-free.
    """
    from sign_robot.pair_timing import quintic_coefficients_v2
    if strategy not in V2_FINGER_STRATEGIES or not segments:
        raise ValueError("An explicit supported finger strategy and base segments are required")
    if type(max_segments) is not int or max_segments < 1 or len(segments) > max_segments:
        raise ValueError("Finger route exceeds the segment budget")
    index, ordered, children = _couplings(names, couplings)
    finger = np.asarray([str(name).startswith(("L_", "R_")) for name in names])
    drivers = np.asarray([i for i, name in enumerate(names) if finger[i] and str(name) not in children], dtype=int)
    for segment in segments:
        c = np.asarray(segment["coefficients"], dtype=float)
        if (segment.get("kind") != "polynomial_v2" or c.shape != (len(names), 6) or not np.isfinite(c).all()
                or segment["end_time_s"] <= segment["start_time_s"]):
            raise ValueError("Finger strategy requires finite named polynomial base segments")
    first = polynomial_boundary_v2(segments[0], "start")
    last = polynomial_boundary_v2(segments[-1], "end")
    _endpoints(first["position"], last["position"], names, couplings, coupling_tolerance)
    for state in (first, last):
        for coupling in ordered:
            parent, child = index[coupling["parent"]], index[coupling["child"]]
            for key in ("velocity", "acceleration"):
                if abs(state[key][child] - coupling["multiplier"] * state[key][parent]) > coupling_tolerance:
                    raise ValueError("Endpoint derivatives violate finger coupling")
    start, end = segments[0]["start_time_s"], segments[-1]["end_time_s"]
    duration = end - start
    if not len(drivers) or strategy == "synchronous":
        result = deepcopy(segments)
    else:
        def independent(state, *, stationary=False):
            return {key: (np.zeros(len(drivers)) if stationary and key != "position" else
                          np.asarray(state[key])[drivers]).tolist()
                    for key in ("position", "velocity", "acceleration")}
        def piece(left, right, a, b):
            return {"kind": "polynomial_v2", "start_time_s": float(left), "end_time_s": float(right),
                    "coefficients": quintic_coefficients_v2(a, b, float(right - left)).tolist()}
        phases = []
        shift = 0.0 if strategy == "early" else 0.35 * duration
        if strategy == "late":
            phases.append(piece(start, start + shift, independent(first), independent(first, stationary=True)))
        for i, segment in enumerate(segments):
            a = polynomial_boundary_v2(segment, "start")
            b = polynomial_boundary_v2(segment, "end")
            phases.append(piece(start + shift + 0.65 * (segment["start_time_s"] - start),
                                start + shift + 0.65 * (segment["end_time_s"] - start),
                                independent(a, stationary=(strategy == "late" and i == 0)),
                                independent(b, stationary=(strategy == "early" and i == len(segments) - 1))))
        if strategy == "early":
            phases.append(piece(start + 0.65 * duration, end, independent(last, stationary=True), independent(last)))
        boundaries = sorted({float(value) for segment in [*segments, *phases]
                             for value in (segment["start_time_s"], segment["end_time_s"])})
        knots = []
        for value in boundaries:
            if not knots or value - knots[-1] > 1e-10:
                knots.append(value)
        if len(knots) - 1 > max_segments:
            raise ValueError("Finger phase subdivision exceeds the segment budget")
        result = []
        for left, right in zip(knots, knots[1:]):
            middle = (left + right) / 2
            c = _restrict(_at(segments, middle), left, right)
            c[drivers] = _restrict(_at(phases, middle), left, right)
            result.append({"kind": "polynomial_v2", "start_time_s": left,
                           "end_time_s": right, "coefficients": c.tolist()})
    maximum_residual = 0.0
    for segment in result:
        c = np.asarray(segment["coefficients"], dtype=float)
        for coupling in ordered:
            parent, child = index[coupling["parent"]], index[coupling["child"]]
            c[child] = coupling["multiplier"] * c[parent]
            c[child, 0] += coupling["offset"]
            residual = c[child] - coupling["multiplier"] * c[parent]
            residual[0] -= coupling["offset"]
            maximum_residual = max(maximum_residual, float(np.sum(np.abs(residual))))
        segment["coefficients"] = c.tolist()
    for state, segment, endpoint in ((first, result[0], "start"), (last, result[-1], "end")):
        actual = polynomial_boundary_v2(segment, endpoint)
        if any(not np.allclose(state[key], actual[key], atol=1e-7, rtol=0) for key in state):
            raise ValueError("Finger phase changed the full endpoint state")
    return result, {"strategy": strategy, "version": 2,
                    "independent_finger_names": [str(names[i]) for i in drivers],
                    "coupling_error_coefficient_bound": maximum_residual,
                    "endpoint_preserved": True, "arm_curve_preserved": True,
                    "finger_knots_preserved": True, "requires_geometry_recheck": True}


def _sample(segments, moments):
    result = []
    for moment in moments:
        segment = _at(segments, float(moment))
        u = (moment - segment["start_time_s"]) / (segment["end_time_s"] - segment["start_time_s"])
        result.append(np.asarray(segment["coefficients"]) @ (u ** np.arange(6)))
    return np.asarray(result)


def finger_strategy_curve_v2(start, end, joint_names, strategy, couplings, *, samples=31,
                             coupling_tolerance=1e-8):
    """Sample a bounded polynomial finger preview, including pure finger motion."""
    from sign_robot.pair_timing import quintic_coefficients_v2
    if type(samples) is not int or samples < 2:
        raise ValueError("A finger curve needs at least two samples")
    start, end = _endpoints(start, end, joint_names, couplings, coupling_tolerance)
    first = {"position": start.tolist(), "velocity": np.zeros(len(start)).tolist(), "acceleration": np.zeros(len(start)).tolist()}
    last = {"position": end.tolist(), "velocity": np.zeros(len(end)).tolist(), "acceleration": np.zeros(len(end)).tolist()}
    base = [{"kind": "polynomial_v2", "start_time_s": 0.0, "end_time_s": 1.0,
             "coefficients": quintic_coefficients_v2(first, last, 1.0).tolist()}]
    segments, info = apply_finger_strategy_to_segments_v2(base, joint_names, strategy, couplings,
                                                         coupling_tolerance=coupling_tolerance)
    q = _sample(segments, np.linspace(0, 1, samples))
    q[0], q[-1] = start, end
    info.update(samples=samples, coupling_error=coupling_error_v2(q, joint_names, couplings))
    return q, info


def apply_finger_strategy_to_path_v2(path, start, end, joint_names, strategy, couplings, *,
                                     coupling_tolerance=1e-8):
    """Sample-only helper. Actual planners use the saved-polynomial adapter."""
    path = np.asarray(path, dtype=float)
    start, end = _endpoints(start, end, joint_names, couplings, coupling_tolerance)
    if path.ndim != 2 or path.shape[1] != len(joint_names) or len(path) < 2 or not np.isfinite(path).all():
        raise ValueError("The base path must be a finite named-coordinate array")
    if not np.allclose(path[[0, -1]], np.stack([start, end]), atol=coupling_tolerance, rtol=0):
        raise ValueError("Base path endpoints differ from the fixed finger endpoints")
    finger = np.asarray([str(name).startswith(("L_", "R_")) for name in joint_names])
    curve, info = finger_strategy_curve_v2(start, end, joint_names, strategy, couplings,
                                           samples=len(path), coupling_tolerance=coupling_tolerance)
    result = path.copy()
    result[:, finger] = curve[:, finger]
    info.update(base_path_preserved=True, coupling_error=coupling_error_v2(result, joint_names, couplings))
    return result, info


def finger_arrival_plan_v1(clip, target_frame, names, bounds, policy, couplings):
    """Lift-off arrival for target fingers that leave a joint limit at entry.

    A single quintic that must reach a finger just off its limit while moving
    away from it dips through the limit. When that would happen, fingers first
    come to rest at an earlier frame of the same target clip, then a short
    quintic re-creates the original lift-off to the entry state. The longest
    in-limit lift-off (earliest staging frame) is chosen; None means unneeded
    or infeasible, and timing proceeds unchanged. An infeasible plan is
    returned with feasible=False so shortlists can rank it last.
    """
    from sign_robot.pair_timing import _extrema, cut_boundary_state_v2, quintic_coefficients_v2
    from sign_robot.pair_contract import rate_limits
    index, ordered, children = _couplings(names, couplings)
    bounds = np.asarray(bounds, dtype=float)
    drivers = np.asarray([i for i, name in enumerate(names) if str(name).startswith(("L_", "R_")) and str(name) not in children], dtype=int)
    if not len(drivers) or target_frame < 1:
        return None
    end = cut_boundary_state_v2(clip, target_frame, "target", policy, bounds)
    p, v = np.asarray(end["position"])[drivers], np.asarray(end["velocity"])[drivers]
    room = np.where(v > 0, p - bounds[drivers, 0], bounds[drivers, 1] - p)
    reach = 0.4 * np.abs(v) * policy["planner"]["minimum_duration_s"]
    needed = (np.abs(v) > policy["constraints"]["speed_tolerance_rad_s"]) & (room < reach)
    if not np.any(needed):
        return None
    tolerance = policy["constraints"]["joint_limit_tolerance_rad"]
    limits = policy["quality"]["limits"]
    rates = rate_limits(np.asarray(names)[drivers], policy)
    rejected = []
    for staging in range(target_frame):
        duration = (target_frame - staging) / 30
        rest = {"position": np.asarray(clip["positions"][staging])[drivers].tolist(),
                "velocity": np.zeros(len(drivers)).tolist(), "acceleration": np.zeros(len(drivers)).tolist()}
        c = quintic_coefficients_v2(rest, {k: np.asarray(end[k])[drivers].tolist() for k in end}, duration)
        lo, hi = _extrema(c, duration, 0)
        joint_speed = np.max(np.abs(np.stack(_extrema(c, duration, 1))), axis=0)
        speed = float(joint_speed.max())
        acceleration, jerk = (np.max(np.abs(np.concatenate(_extrema(c, duration, order)))) for order in (2, 3))
        reasons = [code for code, bad in (
            ("JOINT_LIMIT", np.any(lo < bounds[drivers, 0] - tolerance) or np.any(hi > bounds[drivers, 1] + tolerance)),
            ("SPEED", np.any(joint_speed > rates + policy["constraints"]["speed_tolerance_rad_s"])),
            ("PEAK_ACCELERATION", acceleration > limits["peak_acceleration_rad_s2"]),
            ("PEAK_JERK", jerk > limits["peak_jerk_rad_s3"])) if bad]
        if not reasons:
            return {"version": 1, "feasible": True, "staging_frame": staging, "target_frame": int(target_frame), "arrival_s": duration,
                    "staging_position": np.asarray(clip["positions"][staging]).tolist(),
                    "lift_off_names": [str(names[drivers[i]]) for i in np.flatnonzero(needed)],
                    "lift_off_peaks": {"speed_rad_s": float(speed), "acceleration_rad_s2": float(acceleration), "jerk_rad_s3": float(jerk)},
                    "rejected_staging": rejected}
        rejected.append({"staging_frame": staging, "reason_codes": reasons})
    return {"version": 1, "feasible": False, "target_frame": int(target_frame),
            "lift_off_names": [str(names[drivers[i]]) for i in np.flatnonzero(needed)], "rejected_staging": rejected}


def apply_finger_arrival_v1(segments, names, couplings, plan, *, phase_start=None, coupling_tolerance=1e-8, max_segments=256):
    """Replace independent finger curves after phase_start by rest-at-staging plus lift-off.

    Arm coordinates keep their exact curve. The finger state at phase_start is
    read from the given segments, so a late-strategy phase contract is kept.
    """
    from sign_robot.pair_timing import quintic_coefficients_v2
    index, ordered, children = _couplings(names, couplings)
    drivers = np.asarray([i for i, name in enumerate(names) if str(name).startswith(("L_", "R_")) and str(name) not in children], dtype=int)
    start, end = segments[0]["start_time_s"], segments[-1]["end_time_s"]
    begin = start if phase_start is None else float(phase_start)
    split = end - plan["arrival_s"]
    if not len(drivers) or split - begin < 1 / 30 - 1e-10:
        raise ValueError("Finger arrival does not fit inside the connector")
    staging = np.asarray(plan["staging_position"], dtype=float)
    if coupling_error_v2(staging[None], names, couplings) > coupling_tolerance:
        raise ValueError("Finger staging pose violates coupling")
    segment = _at(segments, begin)
    c = np.asarray(segment["coefficients"], dtype=float)
    duration = segment["end_time_s"] - segment["start_time_s"]
    u = (begin - segment["start_time_s"]) / duration
    initial = {}
    for order, key in enumerate(("position", "velocity", "acceleration")):
        derivative = np.polynomial.polynomial.polyder(c[drivers], m=order, axis=1)
        initial[key] = (derivative @ (u ** np.arange(derivative.shape[1])) / duration**order).tolist()
    final = polynomial_boundary_v2(segments[-1], "end")
    rest = {"position": staging[drivers].tolist(), "velocity": np.zeros(len(drivers)).tolist(),
            "acceleration": np.zeros(len(drivers)).tolist()}
    phases = [{"start_time_s": begin, "end_time_s": split, "coefficients": quintic_coefficients_v2(initial, rest, split - begin)},
              {"start_time_s": split, "end_time_s": end, "coefficients": quintic_coefficients_v2(
                  rest, {k: np.asarray(final[k])[drivers].tolist() for k in final}, end - split)}]
    knots = sorted({float(x) for s in segments for x in (s["start_time_s"], s["end_time_s"])} | {begin, split})
    knots = [k for i, k in enumerate(knots) if i == 0 or k - knots[i - 1] > 1e-10]
    if len(knots) - 1 > max_segments:
        raise ValueError("Finger arrival exceeds the segment budget")
    result = []
    for left, right in zip(knots, knots[1:]):
        middle = (left + right) / 2
        coefficients = _restrict(_at(segments, middle), left, right)
        if middle > begin:
            phase = phases[0] if middle < split else phases[1]
            coefficients[drivers] = _restrict({**phase, "coefficients": np.asarray(phase["coefficients"])}, left, right)
        for coupling in ordered:
            parent, child = index[coupling["parent"]], index[coupling["child"]]
            coefficients[child] = coupling["multiplier"] * coefficients[parent]
            coefficients[child, 0] += coupling["offset"]
        result.append({"kind": "polynomial_v2", "start_time_s": left, "end_time_s": right, "coefficients": coefficients.tolist()})
    for state, segment, endpoint in ((polynomial_boundary_v2(segments[0], "start"), result[0], "start"), (final, result[-1], "end")):
        actual = polynomial_boundary_v2(segment, endpoint)
        if any(not np.allclose(state[key], actual[key], atol=1e-7, rtol=0) for key in state):
            raise ValueError("Finger arrival changed the full endpoint state")
    return result, {**{k: plan[k] for k in ("version", "staging_frame", "target_frame", "arrival_s", "lift_off_names")},
                    "phase_start_s": begin, "lift_off_start_s": split, "arm_curve_preserved": True}
