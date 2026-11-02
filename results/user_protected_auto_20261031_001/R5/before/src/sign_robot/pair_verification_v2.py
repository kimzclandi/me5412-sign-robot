"""Independent reconstruction of saved v2 curves; no route/timing/search imports."""
from __future__ import annotations

import math
from pathlib import Path
import time

import numpy as np

from sign_robot.motion import load_model
from sign_robot.pair_contract import (
    QUALITY_LIMITS, acceptance_pending, canonical_array_hash, coordinate_errors, file_hash, freeze_library,
    inside, json_hash, rate_limits, read_motion, read_pair_trajectory, run_identity,
    validate_policy_v2,
)
from sign_robot.pair_windows import WindowApprovalError, load_window_approvals
from sign_robot.transitions import MujocoClearance


class VerificationBudgetExceeded(RuntimeError):
    pass


class _Budget:
    def __init__(self, config, started):
        self.config, self.started = config, started
        self.sampled_poses = 0
        self.native_call_upper_bound = 0
        self.completed_poses = 0

    def check_time(self):
        if time.monotonic() - self.started >= self.config["wall_time_s"]:
            raise VerificationBudgetExceeded("VERIFICATION_WALL_TIME_LIMIT")

    def reserve(self, poses, native_calls):
        self.check_time()
        if self.sampled_poses + poses > self.config["max_sampled_poses"]:
            raise VerificationBudgetExceeded("VERIFICATION_POSE_BUDGET_EXHAUSTED")
        if self.native_call_upper_bound + native_calls > self.config["max_native_collision_calls"]:
            raise VerificationBudgetExceeded("VERIFICATION_NATIVE_CALL_BUDGET_EXHAUSTED")
        self.sampled_poses += poses
        self.native_call_upper_bound += native_calls

    def record(self):
        return {"sampled_poses_reserved": self.sampled_poses,
                "completed_geometry_poses": self.completed_poses,
                "native_call_upper_bound_reserved": self.native_call_upper_bound,
                "wall_time_s": time.monotonic() - self.started,
                "limits": self.config}


def _derivative_coefficients(coefficients, order, duration):
    coefficients = np.asarray(coefficients, dtype=float)
    result = np.array([[row[k] * math.factorial(k) / math.factorial(k - order)
                        for k in range(order, len(row))] for row in coefficients]) / duration**order
    if not np.isfinite(result).all():
        raise ValueError("Nonfinite polynomial derivative")
    return result


def _evaluate_polynomial(segment, times, order=0):
    duration = segment["end_time_s"] - segment["start_time_s"]
    u = (np.asarray(times) - segment["start_time_s"]) / duration
    if np.any(u < -1e-10) or np.any(u > 1 + 1e-10):
        raise ValueError("Polynomial evaluation outside its declared interval")
    coefficients = _derivative_coefficients(segment["coefficients"], order, duration)
    return np.vander(np.clip(u, 0, 1), N=coefficients.shape[1], increasing=True) @ coefficients.T


def _polynomial_range(segment, order):
    """All endpoint/real stationary-point values of each supported polynomial."""
    duration = segment["end_time_s"] - segment["start_time_s"]
    coefficients = _derivative_coefficients(segment["coefficients"], order, duration)
    lower, upper = [], []
    for row in coefficients:
        critical = np.polynomial.polynomial.polyder(row)
        critical = np.trim_zeros(critical, "b")
        roots = np.polynomial.polynomial.polyroots(critical) if len(critical) > 1 else []
        points = [0.0, 1.0] + [float(r.real) for r in roots if abs(r.imag) <= 1e-9 and 0 < r.real < 1]
        values = np.polynomial.polynomial.polyval(points, row)
        if not np.isfinite(values).all():
            raise ValueError("Nonfinite polynomial extremum")
        lower.append(float(np.min(values)))
        upper.append(float(np.max(values)))
    return np.array(lower), np.array(upper)


def _analytic_metrics(polynomials):
    ranges = [_polynomial_range(segment, 0) for segment in polynomials]
    peaks = {}
    for order, name in ((1, "speed"), (2, "acceleration"), (3, "jerk")):
        peaks[name] = np.max([np.maximum(np.abs(lo), np.abs(hi))
                             for lo, hi in (_polynomial_range(s, order) for s in polynomials)], axis=0)
    integral = 0.0
    for segment in polynomials:
        duration = segment["end_time_s"] - segment["start_time_s"]
        jerk = _derivative_coefficients(segment["coefficients"], 3, duration)
        for row in jerk:
            squared = np.polynomial.polynomial.polymul(row, row)
            integral += duration * float(np.sum(squared / np.arange(1, len(squared) + 1)))
    if not np.isfinite(integral) or integral < -1e-6:
        raise ValueError("Invalid analytic squared-jerk integral")
    return {"lower_positions": np.min([r[0] for r in ranges], axis=0),
            "upper_positions": np.max([r[1] for r in ranges], axis=0),
            **peaks, "jerk_integral": max(0.0, integral)}


def _source_values(segment, times, clips, instances):
    word = instances[segment["word_instance_id"]]
    clip = clips[word["gloss"]]
    first, last = segment["source_frames"]
    source_times = clip["timestamps_s"][first:last + 1]
    shifted = np.asarray(times) - segment["start_time_s"] + source_times[0]
    if np.any(shifted < source_times[0] - 1e-10) or np.any(shifted > source_times[-1] + 1e-10):
        raise ValueError("Source reconstruction outside the mapped frames")
    return np.column_stack([np.interp(shifted, source_times, clip["positions"][first:last + 1, j])
                            for j in range(len(clip["joint_names"]))])


def _sample_times(segment, factor, policy, clips, instances, remaining):
    config = policy["validation"]
    duration = segment["end_time_s"] - segment["start_time_s"]
    if segment["kind"] == "polynomial_v2":
        lo, hi = _polynomial_range(segment, 1)
        speed_bound = float(np.maximum(np.abs(lo), np.abs(hi)).max())
        count = max(factor, math.ceil(duration * 30 * factor),
                    math.ceil(duration / config["maximum_time_step_s"]),
                    math.ceil(duration * speed_bound / config["maximum_step_rad"]))
        if count > 2 ** config["max_subdivision_depth"]:
            raise VerificationBudgetExceeded("VERIFICATION_SUBDIVISION_LIMIT")
        if count + 1 > remaining:
            raise VerificationBudgetExceeded("VERIFICATION_POSE_BUDGET_EXHAUSTED")
        return np.linspace(segment["start_time_s"], segment["end_time_s"], count + 1)
    word = instances[segment["word_instance_id"]]
    clip = clips[word["gloss"]]
    first, last = segment["source_frames"]
    t, q = clip["timestamps_s"][first:last + 1], clip["positions"][first:last + 1]
    counts = [max(factor, math.ceil(float(dt) / config["maximum_time_step_s"]),
                  math.ceil(float(np.max(np.abs(right - left))) / config["maximum_step_rad"]))
              for dt, left, right in zip(np.diff(t), q, q[1:])]
    if max(counts) > 2 ** config["max_subdivision_depth"]:
        raise VerificationBudgetExceeded("VERIFICATION_SUBDIVISION_LIMIT")
    if sum(counts) + 1 > remaining:
        raise VerificationBudgetExceeded("VERIFICATION_POSE_BUDGET_EXHAUSTED")
    pieces = [np.array([segment["start_time_s"]])]
    for index, count in enumerate(counts):
        left, right = t[index:index + 2] - t[0] + segment["start_time_s"]
        pieces.append(np.linspace(left, right, count + 1)[1:])
    return np.concatenate(pieces)


def _full_replay(trajectory, clips, *, max_samples=None):
    count = round(trajectory["segments"][-1]["end_time_s"] * 30)
    if max_samples is not None and count + 1 > max_samples:
        raise VerificationBudgetExceeded("VERIFICATION_PLAYBACK_GRID_BUDGET_EXHAUSTED")
    times = np.arange(count + 1) / 30
    instances = {w["instance_id"]: w for w in trajectory["word_instances"]}
    q = np.empty((len(times), 53))
    assigned = np.zeros(len(times), dtype=bool)
    for segment in trajectory["segments"]:
        mask = (times >= segment["start_time_s"] - 1e-10) & (times <= segment["end_time_s"] + 1e-10)
        values = (_evaluate_polynomial(segment, times[mask]) if segment["kind"] == "polynomial_v2" else
                  _source_values(segment, times[mask], clips, instances))
        if np.any(assigned & mask) and not np.allclose(q[assigned & mask], values[assigned[mask]], atol=1e-7, rtol=0):
            raise ValueError("Position discontinuity between saved segments")
        q[mask] = values
        assigned[mask] = True
    if not np.all(assigned) or not np.isfinite(q).all():
        raise ValueError("Incomplete full-clip replay")
    return {"timestamps_s": times, "positions": q, "joint_names": np.asarray(trajectory["joint_names"])}


def verify_saved_pair_v2(root, trajectory_path, policy):
    """Fresh file/model/review reconstruction; numerical pass remains pending.

    Native query counts are conservative upper bounds: each pose includes one
    forward pass plus up to five expanded-margin collision passes. Setup also
    charges the forward/collision passes and individual vendor gap queries.
    """
    started = time.monotonic()
    evidence = {"schema_version": 2, "status": "ERROR", "reason_codes": [],
                "artifact_contract_passed": False, "approval_checks_passed": False,
                "numerical_checks_passed": None, "validation_complete": False,
                "continuous_collision_certified": False, "playback_eligible": False}
    budget = None
    try:
        validate_policy_v2(policy)
        budget = _Budget(policy["validation"], started)
        root = Path(root).resolve()
        path = Path(trajectory_path).resolve()
        trajectory = read_pair_trajectory(path, schema_version=2)
        evidence.update(pair_id=trajectory["pair_id"], trajectory_file_sha256=file_hash(path),
                        trajectory_hash=json_hash(trajectory), artifact_contract_passed=True)
        library, _ = freeze_library(root, policy)
        if library["input_errors"] or any(w.get("input_errors") for w in library["words"]):
            evidence.update(status="BLOCKED_INPUT", reason_codes=["FROZEN_INPUT_INVALID"],
                            input_errors=library["input_errors"])
            return evidence
        identity = run_identity(library, policy)
        if trajectory["identity"] != identity:
            raise ValueError("Saved trajectory identity differs from fresh frozen inputs")
        approvals = load_window_approvals(root, policy, library)
        words = {w["gloss"]: w for w in library["words"]}
        clips = {}
        for index, word in enumerate(trajectory["word_instances"]):
            gloss = word["gloss"]
            if gloss not in words or gloss not in approvals:
                raise WindowApprovalError("MISSING_WORD_APPROVAL", gloss)
            approved = approvals[gloss]
            clip_path = inside(root, words[gloss]["motion"])
            if file_hash(clip_path) != word["motion_sha256"]:
                raise ValueError("Saved word motion hash differs from current file")
            clip = read_motion(clip_path)
            clips[gloss] = clip
            if clip["joint_names"].tolist() != trajectory["joint_names"]:
                raise ValueError("Saved word joint order differs from trajectory")
            if (word["approval_id"] != approved.approval_id or word["approval_sha256"] != approved.approval_sha256
                    or word["protected_core_frames"] != list(approved.protected_core_frames)):
                raise ValueError("Saved approval/core reference differs from actual review")
            first, last = word["source_frames"]
            window = approved.exit_window_frames if index == 0 else approved.entry_window_frames
            endpoint = last if index == 0 else first
            if not window[0] <= endpoint <= window[1] or (first != 0 if index == 0 else last != len(clip["positions"]) - 1):
                raise ValueError("Saved source slice is outside the approved window")
        budget.check_time()
        evidence["approval_checks_passed"] = True
        model = load_model(root)
        if [model.joint(i).name for i in range(model.njnt)] != trajectory["joint_names"]:
            raise ValueError("Saved coordinate order differs from actual model")
        checker = MujocoClearance(model, np.asarray(trajectory["joint_names"]),
                                  library_path=root / "motions/hospital_v1_motions.json")
        budget.reserve(0, 2 + len(checker.vendor_structural_gaps))
        polynomials = trajectory["segments"][1:-1]
        analytic = _analytic_metrics(polynomials)
        motion = _full_replay(trajectory, clips, max_samples=policy["validation"]["max_sampled_poses"])
        names, q, t = motion["joint_names"], motion["positions"], motion["timestamps_s"]
        if len(q) > policy["validation"]["max_sampled_poses"]:
            raise VerificationBudgetExceeded("VERIFICATION_PLAYBACK_GRID_BUDGET_EXHAUSTED")
        errors = []
        coordinates = coordinate_errors(q, names, model, library["couplings"])
        constraints = policy["constraints"]
        if coordinates["joint_limit_error"] > constraints["joint_limit_tolerance_rad"]:
            errors.append("FULL_CLIP_JOINT_LIMIT_VIOLATION")
        if coordinates["coupling_error"] > constraints["coupling_tolerance_rad"]:
            errors.append("FULL_CLIP_COUPLING_VIOLATION")
        lower = np.array([model.joint(str(n)).range[0] for n in names])
        upper = np.array([model.joint(str(n)).range[1] for n in names])
        limited = np.array([bool(model.joint(str(n)).limited[0]) for n in names])
        if (np.any(analytic["lower_positions"][limited] < lower[limited] - constraints["joint_limit_tolerance_rad"])
                or np.any(analytic["upper_positions"][limited] > upper[limited] + constraints["joint_limit_tolerance_rad"])):
            errors.append("CONNECTOR_ANALYTIC_JOINT_LIMIT_VIOLATION")
        columns = {str(name): index for index, name in enumerate(names)}
        for segment in polynomials:
            coefficients = np.asarray(segment["coefficients"])
            for coupling in library["couplings"]:
                residual = coefficients[columns[coupling["child"]]] - coupling["multiplier"] * coefficients[columns[coupling["parent"]]]
                residual[0] -= coupling["offset"]
                if np.sum(np.abs(residual)) > constraints["coupling_tolerance_rad"]:
                    errors.append("CONNECTOR_ANALYTIC_COUPLING_VIOLATION")
        rates = rate_limits(names, policy)
        velocity = np.diff(q, axis=0) / np.diff(t)[:, None]
        if np.any(np.abs(velocity) > rates + constraints["speed_tolerance_rad_s"]):
            errors.append("FULL_CLIP_SPEED_VIOLATION")
        if np.any(analytic["speed"] > rates + constraints["speed_tolerance_rad_s"]):
            errors.append("CONNECTOR_ANALYTIC_SPEED_VIOLATION")
        acceleration = np.gradient(np.gradient(q, t, axis=0, edge_order=2), t, axis=0, edge_order=2)
        jerk = np.gradient(acceleration, t, axis=0, edge_order=2)
        arms = np.array([any(s in str(n) for s in ("shoulder", "elbow", "wrist")) for n in names])
        fingers = np.array([str(n).startswith(("L_", "R_")) for n in names])
        velocity_jumps, acceleration_jumps, positions = [], [], []
        for index, endpoint in ((0, "start"), (1, "end")):
            word = trajectory["word_instances"][index]
            clip = clips[word["gloss"]]
            frame = word["source_frames"][1 if index == 0 else 0]
            left, right = (frame - 1, frame) if index == 0 else (frame, frame + 1)
            actual_velocity = (clip["positions"][right] - clip["positions"][left]) / (clip["timestamps_s"][right] - clip["timestamps_s"][left])
            polynomial = polynomials[0 if index == 0 else -1]
            moment = polynomial["start_time_s"] if index == 0 else polynomial["end_time_s"]
            positions.append(float(np.max(np.abs(_evaluate_polynomial(polynomial, [moment])[0] - clip["positions"][frame]))))
            velocity_jumps.append(np.abs(_evaluate_polynomial(polynomial, [moment], 1)[0] - actual_velocity))
            acceleration_jumps.append(np.abs(_evaluate_polynomial(polynomial, [moment], 2)[0]))
        vjump, ajump = np.asarray(velocity_jumps), np.asarray(acceleration_jumps)
        metrics = {
            "position_jump_rad": max(positions),
            "velocity_jump_arm_rad_s": float(vjump[:, arms].max(initial=0)),
            "velocity_jump_finger_rad_s": float(vjump[:, fingers].max(initial=0)),
            "acceleration_jump_arm_rad_s2": float(ajump[:, arms].max(initial=0)),
            "acceleration_jump_finger_rad_s2": float(ajump[:, fingers].max(initial=0)),
            "peak_acceleration_rad_s2": float(np.abs(acceleration).max()),
            "peak_jerk_rad_s3": float(np.abs(jerk).max()),
            "jerk_integral_rad2_s5": float(np.trapezoid(np.sum(jerk * jerk, axis=1), x=t)),
            "maximum_transition_duration_s": polynomials[-1]["end_time_s"] - polynomials[0]["start_time_s"],
            "analytic_connector_peak_acceleration_rad_s2": float(analytic["acceleration"].max()),
            "analytic_connector_peak_jerk_rad_s3": float(analytic["jerk"].max()),
            "analytic_connector_jerk_integral_rad2_s5": analytic["jerk_integral"],
        }
        if not np.isfinite(list(metrics.values())).all():
            raise ValueError("Nonfinite trajectory metrics")
        if metrics["position_jump_rad"] > constraints["position_tolerance_rad"]:
            errors.append("POSITION_BOUNDARY_MISMATCH")
        strategy = trajectory["finger_strategy"]
        if strategy["name"] != "synchronous" and np.any(fingers):
            phase = strategy["end_fraction"] if strategy["name"] == "early" else strategy["start_fraction"]
            moment = polynomials[0]["start_time_s"] + phase * metrics["maximum_transition_duration_s"]
            segment = next(s for s in polynomials if s["start_time_s"] - 1e-10 <= moment <= s["end_time_s"] + 1e-10)
            word = trajectory["word_instances"][1 if strategy["name"] == "early" else 0]
            frame = word["source_frames"][0 if strategy["name"] == "early" else 1]
            expected = clips[word["gloss"]]["positions"][frame]
            phase_errors = {
                "position_rad": float(np.max(np.abs(_evaluate_polynomial(segment, [moment])[0, fingers] - expected[fingers]))),
                "velocity_rad_s": float(np.max(np.abs(_evaluate_polynomial(segment, [moment], 1)[0, fingers]))),
                "acceleration_rad_s2": float(np.max(np.abs(_evaluate_polynomial(segment, [moment], 2)[0, fingers]))),
            }
            evidence["finger_phase_recheck"] = {"strategy": strategy["name"], "curve_time_s": moment, **phase_errors}
            if (phase_errors["position_rad"] > constraints["position_tolerance_rad"]
                    or phase_errors["velocity_rad_s"] > policy["quality"]["limits"]["velocity_jump_finger_rad_s"]
                    or phase_errors["acceleration_rad_s2"] > policy["quality"]["limits"]["acceleration_jump_finger_rad_s2"]):
                errors.append("FINGER_PHASE_CONTRACT_VIOLATION")
        for key in QUALITY_LIMITS:
            if metrics[key] > policy["quality"]["limits"][key]:
                errors.append("QUALITY_LIMIT_" + key.upper())
        for analytic_key, limit_key in (("analytic_connector_peak_acceleration_rad_s2", "peak_acceleration_rad_s2"),
                                        ("analytic_connector_peak_jerk_rad_s3", "peak_jerk_rad_s3"),
                                        ("analytic_connector_jerk_integral_rad2_s5", "jerk_integral_rad2_s5")):
            if metrics[analytic_key] > policy["quality"]["limits"][limit_key]:
                errors.append("QUALITY_LIMIT_" + analytic_key.upper())
        evidence.update(identity=identity, metrics=metrics, **coordinates,
                        original_word_slices_preserved=True, protected_core_preserved=True,
                        word_occurrences=2, source_replay_continuous_derivatives_certified=False,
                        reconstructed_motion_canonical_hash=canonical_array_hash(motion),
                        replay_frame_count=len(q), replay_duration_s=float(t[-1]))
        instances = {word["instance_id"]: word for word in trajectory["word_instances"]}
        measurements = []
        evidence["dense_recheck_result"] = measurements
        endpoint_minima = {"source": float("inf"), "target": float("inf")}
        for factor in policy["validation"]["dense_factors"]:
            for index, segment in enumerate(trajectory["segments"]):
                budget.check_time()
                remaining = policy["validation"]["max_sampled_poses"] - budget.sampled_poses
                times = _sample_times(segment, factor, policy, clips, instances, remaining)
                values = (_evaluate_polynomial(segment, times) if segment["kind"] == "polynomial_v2" else
                          _source_values(segment, times, clips, instances))
                if (np.max(np.diff(times)) > policy["validation"]["maximum_time_step_s"] * (1 + 1e-10)
                        or np.max(np.abs(np.diff(values, axis=0))) > policy["validation"]["maximum_step_rad"] * (1 + 1e-9)):
                    raise ValueError("Reconstructed sampling resolution is incomplete")
                minimum, worst = float("inf"), None
                for start in range(0, len(values), 16):
                    batch = values[start:start + 16]
                    budget.reserve(len(batch), 6 * len(batch))
                    measured = checker(batch)
                    if (not np.isfinite(measured.min_distance_m) or measured.sampled_frames != len(batch)
                            or len(measured.frame_clearances_m) != len(batch)
                            or not np.isfinite(measured.frame_clearances_m).all()):
                        raise ValueError("Nonfinite or incomplete native clearance")
                    budget.completed_poses += len(batch)
                    if index == 1 and start == 0:
                        endpoint_minima["source"] = min(endpoint_minima["source"], float(measured.frame_clearances_m[0]))
                    if index == len(trajectory["segments"]) - 2 and start + len(batch) == len(values):
                        endpoint_minima["target"] = min(endpoint_minima["target"], float(measured.frame_clearances_m[-1]))
                    if measured.min_distance_m < minimum:
                        minimum = float(measured.min_distance_m)
                        worst = dict(measured.worst_contact or {})
                        local_frame = int(worst.get("frame", 0)) + start
                        worst.update(curve_time_s=float(times[local_frame]), segment_index=index,
                                     segment_sample_index=local_frame)
                    evidence["active_segment_progress"] = {
                        "factor": factor, "segment_index": index, "checked_samples": start + len(batch),
                        "requested_samples": len(values), "partial_min_clearance_mm": minimum * 1000,
                        "worst_contact": worst,
                    }
                    budget.check_time()
                measurements.append({"factor": factor, "segment_index": index, "kind": segment["kind"],
                                     "samples": len(values), "min_clearance_mm": minimum * 1000,
                                     "worst_contact": worst})
                if minimum < constraints["min_clearance_m"]:
                    errors.append("DENSE_CONNECTOR_COLLISION" if segment["kind"] == "polynomial_v2" else "ORIGINAL_WORD_SLICE_COLLISION")
        budget.check_time()
        for role, minimum in endpoint_minima.items():
            if minimum < constraints["min_clearance_m"]:
                errors.append(role.upper() + "_ENDPOINT_INVALID")
        status = ("BLOCKED_ENDPOINT" if any(code.endswith("_ENDPOINT_INVALID") for code in errors) else
                  "FAILED_SEARCH" if "DENSE_CONNECTOR_COLLISION" in errors else "FAILED_QUALITY")
        evidence.update(validation_complete=True, dense_recheck_result=measurements,
                        endpoint_recheck={role: {"min_clearance_mm": minimum * 1000,
                                                "engineering_valid": minimum >= constraints["min_clearance_m"]}
                                          for role, minimum in endpoint_minima.items()},
                        min_clearance_mm=min(x["min_clearance_mm"] for x in measurements),
                        numerical_checks_passed=not errors,
                        status=status,
                        reason_codes=list(dict.fromkeys([*errors, *acceptance_pending(policy)])))
    except WindowApprovalError as exc:
        evidence.update(status="BLOCKED_INPUT", reason_codes=[exc.code], diagnostic_details=exc.details)
    except VerificationBudgetExceeded as exc:
        evidence.update(status="TIMEOUT", numerical_checks_passed=None,
                        validation_complete=False, reason_codes=[str(exc)])
    except (OSError, KeyError, TypeError, ValueError, OverflowError, FloatingPointError, np.linalg.LinAlgError) as exc:
        evidence.update(status="ERROR", reason_codes=["V2_VERIFICATION_INPUT_OR_CURVE_INVALID"],
                        diagnostic_details={"type": type(exc).__name__, "message": str(exc)})
    finally:
        if budget is not None:
            evidence["verification_budget"] = budget.record()
    return evidence


def verify_missing_candidate_v2(root, record, policy):
    """Fresh input/endpoint diagnosis, explicitly without a verified curve."""
    started = time.monotonic()
    result = {"schema_version": 2, "pair_id": record["pair_id"], "verification_scope": "no_trajectory_diagnosis",
              "identity": record["identity"], "status": "ERROR", "reason_codes": [],
              "numerical_checks_passed": False, "validation_complete": False,
              "playback_eligible": False, "continuous_collision_certified": False, "infeasibility_proven": False}
    budget = None
    try:
        validate_policy_v2(policy)
        root = Path(root).resolve()
        budget = _Budget(policy["validation"], started)
        library, _ = freeze_library(root, policy)
        if run_identity(library, policy) != record["identity"]:
            raise ValueError("Diagnostic inputs differ from the frozen pair identity")
        if library["input_errors"] or any(word.get("input_errors") for word in library["words"]):
            result.update(status="BLOCKED_INPUT", reason_codes=["FROZEN_INPUT_INVALID"])
            return result
        approvals = load_window_approvals(root, policy, library)
        words = {w["gloss"]: w for w in library["words"]}
        model = load_model(root)
        if [model.joint(i).name for i in range(model.njnt)] != library["joint_names"]:
            raise ValueError("Actual model joint order differs from frozen diagnostic inputs")
        checker = MujocoClearance(model, np.asarray(library["joint_names"]), library_path=Path(root) / "motions/hospital_v1_motions.json")
        budget.reserve(0, 2 + len(checker.vendor_structural_gaps))
        roles = {}
        result["endpoint_recheck"] = roles
        for role in ("source", "target"):
            gloss = record[role + "_gloss"]
            if gloss not in approvals:
                raise WindowApprovalError("MISSING_WORD_APPROVAL", gloss)
            approved = approvals[gloss]
            clip = read_motion(inside(root, words[gloss]["motion"]))
            if clip["joint_names"].tolist() != library["joint_names"]:
                raise ValueError("Actual motion joint order differs from frozen diagnostic inputs")
            window = approved.exit_window_frames if role == "source" else approved.entry_window_frames
            checks = []
            roles[role] = checks
            for frame in range(window[0], window[1] + 1):
                budget.reserve(1, 6)
                pose = clip["positions"][frame:frame + 1]
                geometry = checker(pose)
                if (not np.isfinite(geometry.min_distance_m) or geometry.sampled_frames != 1
                        or len(geometry.frame_clearances_m) != 1 or not np.isfinite(geometry.frame_clearances_m).all()):
                    raise ValueError("Nonfinite or incomplete diagnostic clearance")
                budget.completed_poses += 1
                budget.check_time()
                errors = coordinate_errors(pose, clip["joint_names"], model, library["couplings"])
                limits = policy["constraints"]
                good = (geometry.min_distance_m >= limits["min_clearance_m"]
                        and errors["joint_limit_error"] <= limits["joint_limit_tolerance_rad"]
                        and errors["coupling_error"] <= limits["coupling_tolerance_rad"])
                checks.append({"frame": frame, "engineering_valid": bool(good), "min_clearance_mm": float(geometry.min_distance_m * 1000), **errors})
        invalid = [role.upper() + "_ENDPOINT_INVALID" for role in roles if not any(c["engineering_valid"] for c in roles[role])]
        result.update(status="BLOCKED_ENDPOINT" if invalid else record["status"],
                      reason_codes=invalid or record["reason_codes"], planner_diagnosis_only=not invalid)
    except WindowApprovalError as exc:
        result.update(status="BLOCKED_INPUT", reason_codes=[exc.code], details=exc.details)
    except VerificationBudgetExceeded as exc:
        result.update(status="TIMEOUT", reason_codes=[str(exc)])
    except (OSError, KeyError, TypeError, ValueError, OverflowError, FloatingPointError) as exc:
        result.update(status="ERROR", reason_codes=["V2_DIAGNOSTIC_INPUT_INVALID"], details=str(exc))
    finally:
        if budget is not None:
            result["verification_budget"] = budget.record()
    return result
