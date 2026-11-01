"""Re-read saved candidates and verify the declared replay curve independently.

The verifier never invokes plan_pair or imports a legacy PASS decision. It uses
the same geometric measurement primitive, with fresh model/data and word files.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from sign_robot.all_pairs import (
    COLLISION_SCOPE, build_context, check_frozen_files, clearance_summary,
    read_checkpoints, save_checkpoint, summarize_run,
)
from sign_robot.pair_contract import (
    QUALITY_LIMITS, acceptance_pending, atomic_json, boundary_derivatives,
    canonical_array_hash, coordinate_errors, file_hash, freeze_library, inside,
    linear_dense, load_policy, rate_limits, read_json, read_motion, run_identity,
)


def _peak(values, columns):
    return float(np.abs(values[:, columns]).max(initial=0))


def verify_saved_pair_v2(root, trajectory_path, policy):
    """Explicit v2 entry; the legacy v1 run verifier remains version-restricted."""
    from sign_robot.pair_verification_v2 import verify_saved_pair_v2 as verify
    return verify(root, trajectory_path, policy)


def trajectory_metrics(motion, connector, first, second, exit_frame, entry_frame, policy):
    q, names, t = (motion[k] for k in ("positions", "joint_names", "timestamps_s"))
    arms = [i for i, n in enumerate(names) if any(part in str(n) for part in ("shoulder", "elbow", "wrist"))]
    fingers = [i for i, n in enumerate(names) if str(n).startswith(("L_", "R_"))]
    velocity = np.diff(q, axis=0) / np.diff(t)[:, None]
    acceleration = np.gradient(np.gradient(q, t, axis=0, edge_order=2), t, axis=0, edge_order=2)
    jerk = np.gradient(acceleration, t, axis=0, edge_order=2)
    window = policy["quality"]["derivative_window_frames"]
    source = boundary_derivatives(first, exit_frame, "source", window)
    target = boundary_derivatives(second, entry_frame, "target", window)
    v_jump = np.abs(np.array([source["velocity"], target["velocity"]]))
    a_jump = np.abs(np.array([source["acceleration"], target["acceleration"]]))
    duration = (len(connector) - 1) / policy["fps"]
    delta = connector[-1] - connector[0]
    return {
        "peak_arm_speed": _peak(velocity, arms), "peak_finger_speed": _peak(velocity, fingers),
        "peak_acceleration": float(np.abs(acceleration).max()),
        "peak_jerk": float(np.abs(jerk).max()),
        "jerk_integral": float(np.trapezoid(np.sum(jerk * jerk, axis=1), x=t)),
        "metric_method": "full saved-clip finite differences at playback times; boundary one-sided quadratic fits",
        "velocity_jump": float(v_jump.max()), "acceleration_jump": float(a_jump.max()),
        "velocity_jump_arm_rad_s": _peak(v_jump, arms),
        "velocity_jump_finger_rad_s": _peak(v_jump, fingers),
        "acceleration_jump_arm_rad_s2": _peak(a_jump, arms),
        "acceleration_jump_finger_rad_s2": _peak(a_jump, fingers),
        "boundary_derivatives": {"source": source, "target": target,
                                  "connector_velocity": "analytic zero at both ends",
                                  "connector_acceleration": "analytic zero at both ends"},
        "analytic_connector_peak_speed_rad_s": float(1.875 * np.abs(delta).max() / duration),
        "analytic_connector_peak_acceleration_rad_s2": float(10 / math.sqrt(3) * np.abs(delta).max() / duration**2),
        "analytic_connector_peak_jerk_rad_s3": float(60 * np.abs(delta).max() / duration**3),
        "analytic_connector_jerk_integral_rad2_s5": float(720 * (delta @ delta) / duration**5),
    }


def _dense_quintic(a, b, count):
    # Independent reconstruction of the declared polynomial, not saved frames
    # treated as collision-safe waypoints.
    u = np.linspace(0, 1, count + 1)[:, None]
    scale = u**3 * (10 + u * (-15 + 6 * u))
    q = (1 - scale) * a + scale * b
    q[0], q[-1] = a, b
    return q


def _endpoint(context, word, role):
    frame = word["sign_frames"][1 if role == "source" else 0]
    motion = context.clips[word["gloss"]]
    pose = motion["positions"][frame:frame + 1]
    measured = context.clearance(pose)
    errors = coordinate_errors(pose, motion["joint_names"], context.model, context.library["couplings"])
    constraints = context.policy["constraints"]
    return {"frame": frame, **clearance_summary(measured), **errors,
            "engineering_valid": (measured.min_distance_m >= constraints["min_clearance_m"]
                and errors["joint_limit_error"] <= constraints["joint_limit_tolerance_rad"]
                and errors["coupling_error"] <= constraints["coupling_tolerance_rad"])}


def verify_record(run_dir, record, context, *, word_cache=None):
    """Return evidence and an updated main status; never manufacture final PASS."""
    word_cache = {} if word_cache is None else word_cache
    policy = context.policy
    words = {w["gloss"]: w for w in context.library["words"]}
    source, target = record["source_gloss"], record["target_gloss"]
    evidence = {"schema_version": 1, "pair_id": record["pair_id"], "identity_hash": record["identity_hash"],
                "trajectory_file_hash": record.get("trajectory_file_hash"),
                "canonical_array_hash": record.get("canonical_array_hash"),
                "collision_scope": COLLISION_SCOPE, "status": record["status"],
                "reason_codes": [], "artifact_contract_passed": None,
                "numerical_checks_passed": None, "acceptance_pending": acceptance_pending(policy)}
    if context.library["input_errors"] or any(w["input_errors"] for w in (words[source], words[target])):
        evidence.update(status="BLOCKED_INPUT", reason_codes=["FROZEN_INPUT_INVALID"])
        return evidence
    source_endpoint, target_endpoint = _endpoint(context, words[source], "source"), _endpoint(context, words[target], "target")
    evidence["endpoint_recheck"] = {"source": source_endpoint, "target": target_endpoint}
    bad = [role for role, ep in (("source", source_endpoint), ("target", target_endpoint)) if not ep["engineering_valid"]]
    if bad:
        evidence.update(status="BLOCKED_ENDPOINT", reason_codes=[f"{role.upper()}_ENDPOINT_INVALID" for role in bad],
                        numerical_checks_passed=False)
        return evidence
    if not record.get("trajectory_file"):
        reasons = list(record["reason_codes"])
        if record["status"] not in ("FAILED_SEARCH", "TIMEOUT", "ERROR"):
            reasons.append("MISSING_CANDIDATE_TRAJECTORY")
            evidence["status"] = "ERROR"
        evidence.update(reason_codes=reasons, verification_scope="diagnosis only; no trajectory was produced")
        return evidence
    path = inside(run_dir, record["trajectory_file"])
    motion = read_motion(path)
    first, second = context.clips[source], context.clips[target]
    exit_frame, entry_frame = words[source]["sign_frames"][1], words[target]["sign_frames"][0]
    q, names, t = (motion[k] for k in ("positions", "joint_names", "timestamps_s"))
    start, end = record["transition_start_frame"], record["transition_end_frame"]
    errors = []
    if (record["exit_frame"] != exit_frame or record["entry_frame"] != entry_frame
            or not isinstance(start, int) or not isinstance(end, int)
            or start != exit_frame or not 0 <= start < end < len(q)):
        errors.append("RECORDED_BOUNDARY_MISMATCH")
    if file_hash(path) != record["trajectory_file_hash"] or canonical_array_hash(motion) != record["canonical_array_hash"]:
        errors.append("TRAJECTORY_HASH_MISMATCH")
    if not np.array_equal(names, first["joint_names"]) or not np.array_equal(names, second["joint_names"]):
        errors.append("JOINT_ORDER_MISMATCH")
    if not np.allclose(t, np.arange(len(t)) / policy["fps"], atol=1e-12, rtol=0):
        errors.append("TIMESTAMP_CONTRACT_MISMATCH")
    if (record["source_motion_hash"] != words[source]["motion_sha256"]
            or record["target_motion_hash"] != words[target]["motion_sha256"]
            or record["method"] != policy["planner"]["method"] or record["candidate_count"] != 1
            or record["exception_ids"] or record["trim_count"] != 0):
        errors.append("PLANNER_PROVENANCE_MISMATCH")
    if (not np.isclose(record["transition_duration_s"], (end - start) / policy["fps"], atol=1e-12, rtol=0)
            or not np.isclose(record["full_clip_duration_s"], t[-1], atol=1e-12, rtol=0)):
        errors.append("DURATION_METADATA_MISMATCH")
    if errors:
        evidence.update(status="ERROR", reason_codes=errors, artifact_contract_passed=False)
        return evidence
    connector = q[start:end + 1]
    expected_length = end + len(second["positions"]) - entry_frame
    if (len(q) != expected_length or not np.array_equal(q[:start + 1], first["positions"][:exit_frame + 1])
            or not np.array_equal(q[end:], second["positions"][entry_frame:])):
        errors.append("ORIGINAL_WORD_SLICES_CHANGED_OR_REPEAT_REMOVED")
    position_jump = float(max(np.abs(connector[0] - first["positions"][exit_frame]).max(),
                              np.abs(connector[-1] - second["positions"][entry_frame]).max()))
    if position_jump > policy["constraints"]["position_tolerance_rad"]:
        errors.append("POSITION_BOUNDARY_MISMATCH")
    expected = _dense_quintic(first["positions"][exit_frame], second["positions"][entry_frame], len(connector) - 1)
    if not np.allclose(connector, expected, atol=1e-12, rtol=0):
        errors.append("DECLARED_QUINTIC_CURVE_MISMATCH")
    segments = [
        {"gloss": source, "start_frame": 0, "end_frame": start, "source_frames": [0, exit_frame]},
        {"gloss": target, "start_frame": end, "end_frame": len(q) - 1,
         "source_frames": [entry_frame, len(second["positions"]) - 1]},
    ]
    if record.get("word_segments") != segments:
        errors.append("WORD_SEGMENT_METADATA_MISMATCH")
    if errors:
        evidence.update(status="ERROR", reason_codes=errors, artifact_contract_passed=False)
        return evidence
    evidence.update(artifact_contract_passed=True, position_jump=position_jump,
                    original_word_slices_preserved=True, word_occurrences=2,
                    protected_core_preserved=None)
    metrics = trajectory_metrics(motion, connector, first, second, exit_frame, entry_frame, policy)
    coordinates = coordinate_errors(q, names, context.model, context.library["couplings"])
    evidence.update(metrics=metrics, **coordinates)
    constraints = policy["constraints"]
    if coordinates["joint_limit_error"] > constraints["joint_limit_tolerance_rad"]:
        errors.append("FULL_CLIP_JOINT_LIMIT_VIOLATION")
    if coordinates["coupling_error"] > constraints["coupling_tolerance_rad"]:
        errors.append("FULL_CLIP_COUPLING_VIOLATION")
    speed = np.abs(np.diff(q, axis=0)) / np.diff(t)[:, None]
    if np.any(speed > rate_limits(names, policy) + constraints["speed_tolerance_rad_s"]):
        errors.append("FULL_CLIP_SPEED_VIOLATION")
    analytic_speed = 1.875 * np.abs(connector[-1] - connector[0]) / ((len(connector) - 1) / policy["fps"])
    if np.any(analytic_speed > rate_limits(names, policy) + constraints["speed_tolerance_rad_s"]):
        errors.append("CONNECTOR_CONTINUOUS_SPEED_VIOLATION")
    quality_metrics = {**metrics, "peak_acceleration_rad_s2": metrics["peak_acceleration"],
                       "peak_jerk_rad_s3": metrics["peak_jerk"], "jerk_integral_rad2_s5": metrics["jerk_integral"],
                       "maximum_transition_duration_s": (len(connector) - 1) / policy["fps"]}
    for key in QUALITY_LIMITS:
        limit = policy["quality"]["limits"][key]
        if limit is not None and quality_metrics[key] > limit:
            errors.append(f"QUALITY_LIMIT_{key.upper()}")
    resolutions, connector_cache = [], {}
    for factor in policy["validation"]["dense_factors"]:
        count = max((len(connector) - 1) * factor, int(math.ceil(
            1.875 * np.abs(connector[-1] - connector[0]).max() / policy["validation"]["maximum_step_rad"])))
        dense = _dense_quintic(connector[0], connector[-1], count)
        if count not in connector_cache:
            connector_cache[count] = clearance_summary(context.clearance(dense))
        measured = connector_cache[count]
        word_results = []
        for gloss, role, slice_q in ((source, "source", first["positions"][:exit_frame + 1]),
                                     (target, "target", second["positions"][entry_frame:])):
            key = (gloss, role, factor)
            if key not in word_cache:
                original_dense = linear_dense(slice_q, factor, policy["validation"]["maximum_step_rad"])
                word_cache[key] = clearance_summary(context.clearance(original_dense))
            word_results.append({"gloss": gloss, "role": role, **word_cache[key]})
        result = {"requested_factor": factor, "connector": measured, "original_words": word_results,
                  "connector_maximum_step_rad": float(np.abs(np.diff(dense, axis=0)).max()),
                  "full_clip_min_clearance_mm": min(measured["min_clearance_mm"],
                      *(w["min_clearance_mm"] for w in word_results))}
        resolutions.append(result)
    threshold_mm = constraints["min_clearance_m"] * 1000
    if any(r["connector"]["min_clearance_mm"] < threshold_mm for r in resolutions):
        errors.append("DENSE_CONNECTOR_COLLISION")
    if any(w["min_clearance_mm"] < threshold_mm for r in resolutions for w in r["original_words"]):
        errors.append("ORIGINAL_WORD_SLICE_COLLISION")
    evidence.update(dense_recheck_result=resolutions, numerical_checks_passed=not errors,
                    min_clearance_mm=min(r["connector"]["min_clearance_mm"] for r in resolutions),
                    closest_collision_pair=min(resolutions, key=lambda r: r["connector"]["min_clearance_mm"])["connector"]["closest_collision_pair"],
                    full_clip_min_clearance_mm=min(r["full_clip_min_clearance_mm"] for r in resolutions),
                    reason_codes=[*errors, *acceptance_pending(policy)])
    evidence["status"] = "FAILED_SEARCH" if "DENSE_CONNECTOR_COLLISION" in errors else "FAILED_QUALITY"
    if evidence["status"] == "FAILED_SEARCH":
        evidence["reason_codes"].append("GENERAL_SEARCH_NOT_IMPLEMENTED")
    return evidence


def verify_run(root, run_dir, *, max_pairs=None, progress=None):
    run_dir = Path(run_dir).resolve()
    manifest = read_json(run_dir / "manifest.json")
    if manifest.get("schema_version") == 2:
        from sign_robot.pair_runner_v2 import verify_run_v2
        return verify_run_v2(root, run_dir, max_pairs=max_pairs, progress=progress)
    check_frozen_files(run_dir, manifest)
    policy = load_policy(run_dir / "policy.json")
    library, clips = freeze_library(root, policy)
    if run_identity(library, policy) != manifest["identity"]:
        raise ValueError("Verifier code, environment or inputs differ from the run; reproduce the frozen version")
    context = build_context(root, policy, library=library, clips=clips, audit=read_json(run_dir / "word_audit.json"))
    records = read_checkpoints(run_dir, manifest)
    cache, completed = {}, 0
    for record in records.values():
        if record.get("verification_hash"):
            continue
        if max_pairs is not None and completed >= max_pairs:
            break
        try:
            evidence = verify_record(run_dir, record, context, word_cache=cache)
        except Exception as exc:
            evidence = {"schema_version": 1, "pair_id": record["pair_id"],
                        "identity_hash": record["identity_hash"], "status": "ERROR",
                        "reason_codes": ["INDEPENDENT_VERIFIER_EXCEPTION"],
                        "diagnostic_details": {"type": type(exc).__name__, "message": str(exc)},
                        "artifact_contract_passed": False, "numerical_checks_passed": None}
        relative = f"verification/{record['pair_id']}.json"
        atomic_json(run_dir / relative, evidence)
        record.update(status=evidence["status"], reason_codes=evidence["reason_codes"],
                      verification_file=relative, verification_hash=file_hash(run_dir / relative),
                      dense_recheck_result=evidence.get("dense_recheck_result"))
        for key in ("joint_limit_error", "coupling_error", "position_jump", "protected_core_preserved", "min_clearance_mm", "closest_collision_pair"):
            if key in evidence:
                record[key] = evidence[key]
        for key in ("peak_arm_speed", "peak_finger_speed", "peak_acceleration", "peak_jerk",
                    "velocity_jump", "acceleration_jump", "jerk_integral"):
            record[key] = evidence.get("metrics", {}).get(key)
        record["playback_eligible"] = False
        record["validation_resolution"] = {**record["validation_resolution"],
            "verification_factors": policy["validation"]["dense_factors"],
            "verification_maximum_step_rad": policy["validation"]["maximum_step_rad"]}
        save_checkpoint(run_dir, record)
        completed += 1
        if progress:
            progress(sum(bool(r.get("verification_hash")) for r in records.values()), len(records), record)
    return summarize_run(run_dir)
