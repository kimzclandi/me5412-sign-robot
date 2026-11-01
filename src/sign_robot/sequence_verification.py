"""Independent reconstruction of saved sequences; no assembly/route/timing/search imports."""
from __future__ import annotations

from pathlib import Path
import time

import numpy as np

from sign_robot.motion import load_model
from sign_robot.pair_contract import (
    CONNECTOR_ONLY_METHOD_V4, acceptance_pending, canonical_array_hash, coordinate_errors, file_hash, freeze_library,
    clamped_stop_joints, inside, json_hash, rate_limits, read_json, retained_edge_contacts, read_motion, read_pair_trajectory, run_identity, validate_policy_v2,
)
from sign_robot.pair_verification_v2 import (
    VerificationBudgetExceeded, _Budget, _analytic_metrics, _evaluate_polynomial, _full_replay, _masked_trapezoid,
    _protected_source_audit, _sample_times, _source_values, connector_masks,
)
from sign_robot.pair_windows import WindowApprovalError, load_window_inputs
from sign_robot.sequence_contract import (
    library_rest_pose_v1, load_sequence_policy, read_sequence, sequence_identity,
)
from sign_robot.transitions import MujocoClearance

REGION_LIMITS = ("peak_acceleration_rad_s2", "peak_jerk_rad_s3", "jerk_integral_rad2_s5")
# The automatic-window wording predates user-supplied protected intervals; it is
# reported but never made a precondition for the user's own protection choice.
LEGACY_FORMAL_WORDING = ("ALGORITHM_WINDOWS_NOT_HUMAN_REVIEWED",)


def _check_sources(candidate_root, sequence, instances, identity):
    """Every connector must equal its hash-bound, same-identity pair candidate."""
    checks = []
    for edge in sequence["edges"]:
        path = inside(candidate_root, edge["source"]["candidate_file"])
        if file_hash(path) != edge["source"]["candidate_file_sha256"]:
            raise ValueError("Pair candidate file differs from its recorded hash")
        candidate = read_pair_trajectory(path, schema_version=2)
        if json_hash(candidate) != edge["source"]["candidate_trajectory_hash"] or candidate["identity"] != identity:
            raise ValueError("Pair candidate content or identity differs from the sequence")
        source, target = (instances[edge["from_instance_id"]], instances[edge["to_instance_id"]])
        if (candidate["pair_id"] != edge["pair_id"] or candidate["word_instances"][0]["source_frames"][1] != edge["exit_frame"]
                or candidate["word_instances"][1]["source_frames"][0] != edge["entry_frame"]
                or candidate["finger_strategy"] != edge["finger_strategy"] or candidate["boundary"] != edge["boundary"]):
            raise ValueError("Edge differs from its pair candidate")
        for word, saved in ((source, candidate["word_instances"][0]), (target, candidate["word_instances"][1])):
            if any(word[k] != saved[k] for k in ("gloss", "motion_sha256", "protected_core_frames", "protection_id",
                                                 "protection_sha256")):
                raise ValueError("Occurrence reference differs from its pair candidate")
        original = candidate["segments"][1:-1]
        first, last = edge["segment_indices"]
        copied = sequence["segments"][first:last + 1]
        offset = copied[0]["start_time_s"] - original[0]["start_time_s"]
        duration_error = max(abs((c["end_time_s"] - c["start_time_s"]) - (o["end_time_s"] - o["start_time_s"]))
                             for c, o in zip(copied, original)) if len(copied) == len(original) else np.inf
        if (len(copied) != len(original) or any(c["coefficients"] != o["coefficients"] for c, o in zip(copied, original))
                or duration_error > 1e-9
                or any(abs(c["start_time_s"] - o["start_time_s"] - offset) > 1e-9 for c, o in zip(copied, original))):
            raise ValueError("Connector coefficients, durations or internal timing changed")
        checks.append({"edge_index": edge["edge_index"], "pair_id": edge["pair_id"], **edge["source"],
                       "coefficients_identical": True, "max_segment_duration_error_s": float(duration_error)})
    return checks


def _check_rest_tail(candidate_root, sequence, tail, library_clips):
    """The tail must equal its hash-bound planning record and end on the fresh library rest pose."""
    path = inside(candidate_root, tail["source"]["file"])
    if file_hash(path) != tail["source"]["file_sha256"]:
        raise ValueError("Rest-tail record differs from its recorded hash")
    record = read_json(path)
    selected = record["selected"]
    if (selected is None or json_hash(selected) != tail["source"]["selected_hash"] or record["gloss"] != tail["gloss"]
            or selected["exit_frame"] != tail["exit_frame"] or selected["boundary"] != tail["boundary"]):
        raise ValueError("Rest tail differs from its planning record")
    rest = library_rest_pose_v1(library_clips)
    if not np.array_equal(np.asarray(tail["rest_pose"]["position"]), rest):
        raise ValueError("Saved rest pose differs from the fresh library rest pose")
    first, last = tail["segment_indices"]
    copied, original = sequence["segments"][first:last + 1], selected["segments"]
    offset = copied[0]["start_time_s"] - original[0]["start_time_s"]
    if (len(copied) != len(original) or any(c["coefficients"] != o["coefficients"] for c, o in zip(copied, original))
            or any(abs(c["start_time_s"] - o["start_time_s"] - offset) > 1e-9
                   or abs((c["end_time_s"] - c["start_time_s"]) - (o["end_time_s"] - o["start_time_s"])) > 1e-9
                   for c, o in zip(copied, original))):
        raise ValueError("Rest-tail coefficients, durations or internal timing changed")
    return {"file": tail["source"]["file"], "file_sha256": tail["source"]["file_sha256"], "coefficients_identical": True,
            "rest_pose_equals_library_first_frames": True, "library_clip_count": len(library_clips)}, rest


def _protected_mask(sequence, times):
    mask = np.zeros(len(times), dtype=bool)
    spans = []
    for word, segment in zip(sequence["word_instances"], (s for s in sequence["segments"] if s["kind"] == "source_slice_v2")):
        c0, c1 = word["protected_core_frames"]
        start = segment["start_time_s"] + (c0 - segment["source_frames"][0]) / 30
        end = segment["start_time_s"] + (c1 - segment["source_frames"][0]) / 30
        mask |= (times >= start - 1e-9) & (times <= end + 1e-9)
        spans.append((start, end))
    return mask, spans


def verify_saved_sequence_v1(root, sequence_path, policy_path, *, candidate_root=None):
    """Fresh file/model/protection reconstruction of a whole chain.

    Candidate paths resolve under ``candidate_root`` (default: the repository root).
    """
    started = time.monotonic()
    evidence = {"schema_version": 1, "status": "ERROR", "reason_codes": [], "artifact_contract_passed": False,
                "input_checks_passed": False, "numerical_checks_passed": None, "validation_complete": False,
                "formal_acceptance_enabled": False, "formal_status": "NOT_ENABLED", "playback_eligible": False,
                "continuous_collision_certified": False, "pair_labels_inherited": False}
    budget = None
    try:
        root = Path(root).resolve()
        policy, pair_policy = load_sequence_policy(root, policy_path)
        validate_policy_v2(pair_policy)
        budget = _Budget({k: policy["validation"][k] for k in ("max_sampled_poses", "max_native_collision_calls",
                                                               "wall_time_s")}, started)
        path = Path(sequence_path).resolve()
        sequence = read_sequence(path, policy)
        evidence.update(sequence_id=sequence["sequence_id"], sequence_file_sha256=file_hash(path),
                        sequence_hash=json_hash(sequence), artifact_contract_passed=True)
        library, library_clips = freeze_library(root, pair_policy)
        if library["input_errors"] or any(w.get("input_errors") for w in library["words"]):
            evidence.update(status="BLOCKED_INPUT", reason_codes=["FROZEN_INPUT_INVALID"])
            return evidence
        identity = run_identity(library, pair_policy)
        if sequence["pair_identity"] != identity:
            raise ValueError("Saved pair identity differs from fresh frozen inputs")
        if sequence["sequence_identity"] != sequence_identity(root, policy, library, identity):
            raise ValueError("Saved sequence implementation identity differs from current code/policy")
        protections = load_window_inputs(root, pair_policy, library)
        words = {w["gloss"]: w for w in library["words"]}
        instances = {w["instance_id"]: w for w in sequence["word_instances"]}
        clips = {}
        for word in sequence["word_instances"]:
            gloss = word["gloss"]
            if gloss not in protections or gloss not in words:
                raise WindowApprovalError("MISSING_WORD_APPROVAL", gloss)
            protected = protections[gloss]
            clip_path = inside(root, words[gloss]["motion"])
            if file_hash(clip_path) != word["motion_sha256"]:
                raise ValueError("Saved word motion hash differs from current file")
            if (word["protection_id"] != protected.protection_id or word["protection_sha256"] != protected.protection_sha256
                    or word["protected_core_frames"] != list(protected.protected_core_frames)):
                raise ValueError("Saved protection reference differs from the user protection bundle")
            clips[gloss] = clips.get(gloss) or read_motion(clip_path)
            if clips[gloss]["joint_names"].tolist() != sequence["joint_names"]:
                raise ValueError("Saved word joint order differs from sequence")
            if word["source_frames"][1] >= len(clips[gloss]["positions"]):
                raise ValueError("Source slice exceeds its motion")
        evidence["source_candidate_checks"] = _check_sources(Path(candidate_root or root).resolve(), sequence, instances, identity)
        tail, rest = sequence.get("rest_tail"), None
        if tail is not None:
            evidence["rest_tail_source_check"], rest = _check_rest_tail(
                Path(candidate_root or root).resolve(), sequence, tail, library_clips)
        evidence["input_checks_passed"] = True
        budget.check_time()
        model = load_model(root)
        if [model.joint(i).name for i in range(model.njnt)] != sequence["joint_names"]:
            raise ValueError("Saved coordinate order differs from actual model")
        checker = MujocoClearance(model, np.asarray(sequence["joint_names"]),
                                  library_path=root / "motions/hospital_v1_motions.json")
        budget.reserve(0, 2 + len(checker.vendor_structural_gaps))
        motion = _full_replay(sequence, clips, max_samples=policy["validation"]["max_sampled_poses"])
        names, q, t = motion["joint_names"], motion["positions"], motion["timestamps_s"]
        constraints, limits = pair_policy["constraints"], pair_policy["quality"]["limits"]
        errors, source_findings = [], []
        connector_only = pair_policy["quality"]["full_clip_method"] == CONNECTOR_ONLY_METHOD_V4
        protected, spans = _protected_mask(sequence, t)
        if protected.all():
            raise ValueError("No replay frames remain outside protected cores")
        on_connector = np.ones(len(t), dtype=bool)
        if connector_only:
            on_connector = np.zeros(len(t), dtype=bool)
            for edge in [*sequence["edges"], *([tail] if tail is not None else [])]:
                first, last = edge["segment_indices"]
                on_connector |= connector_masks(sequence["segments"][first:last + 1], t)[0]
        evidence["protected_source_audit"] = {}
        for word in sequence["word_instances"]:
            audit = _protected_source_audit(clips[word["gloss"]], word["protected_core_frames"], pair_policy, model, library["couplings"])
            audit["excluded_from_quality_gate"] = [d for d in audit["defects"] if connector_only or d["metric"] in REGION_LIMITS[:2]]
            evidence["protected_source_audit"][word["instance_id"]] = audit
            if any(d["metric"] not in REGION_LIMITS[:2] for d in audit["defects"]):
                (source_findings if connector_only else errors).append(f"{word['instance_id'].upper()}_PROTECTED_SOURCE_QUALITY_VIOLATION")
        if connector_only:
            whole = coordinate_errors(q, names, model, library["couplings"])
            if whole["joint_limit_error"] > constraints["joint_limit_tolerance_rad"]:
                source_findings.append("CHAIN_JOINT_LIMIT_VIOLATION")
            if whole["coupling_error"] > constraints["coupling_tolerance_rad"]:
                source_findings.append("CHAIN_COUPLING_VIOLATION")
        if pair_policy["endpoints"].get("retained_edge_screen"):
            evidence["retained_edge_screen"] = {"version": pair_policy["endpoints"]["retained_edge_screen"], "instances": {}}
            for word in sequence["word_instances"]:
                clip = clips[word["gloss"]]
                bounds = np.array([model.joint(str(n)).range for n in clip["joint_names"]])
                flagged = retained_edge_contacts(clip, word["protected_core_frames"], bounds, word["source_frames"],
                                                 pair_policy["endpoints"]["retained_edge_screen"])
                evidence["retained_edge_screen"]["instances"][word["instance_id"]] = {"flagged_frames": flagged}
                if flagged:
                    errors.append(f"{word['instance_id'].upper()}_RETAINED_EDGE_NEW_ARM_LIMIT_CONTACT")
        coordinates = coordinate_errors(q[on_connector], names, model, library["couplings"])
        if coordinates["joint_limit_error"] > constraints["joint_limit_tolerance_rad"]:
            errors.append("CONNECTOR_JOINT_LIMIT_VIOLATION" if connector_only else "CHAIN_JOINT_LIMIT_VIOLATION")
        if coordinates["coupling_error"] > constraints["coupling_tolerance_rad"]:
            errors.append("CONNECTOR_COUPLING_VIOLATION" if connector_only else "CHAIN_COUPLING_VIOLATION")
        rates = rate_limits(names, pair_policy)
        fast = np.any(np.abs(np.diff(q, axis=0) / np.diff(t)[:, None]) > rates + constraints["speed_tolerance_rad_s"], axis=1)
        inside_connector = on_connector[:-1] & on_connector[1:]
        if np.any(fast & inside_connector):
            errors.append("CONNECTOR_SPEED_VIOLATION" if connector_only else "CHAIN_SPEED_VIOLATION")
        if connector_only and np.any(fast & ~inside_connector):
            source_findings.append("CHAIN_SPEED_VIOLATION")
        acceleration = np.gradient(np.gradient(q, t, axis=0, edge_order=2), t, axis=0, edge_order=2)
        jerk = np.gradient(acceleration, t, axis=0, edge_order=2)
        squared = np.sum(jerk * jerk, axis=1)
        lower = np.array([model.joint(str(n)).range[0] for n in names])
        upper = np.array([model.joint(str(n)).range[1] for n in names])
        limited = np.array([bool(model.joint(str(n)).limited[0]) for n in names])
        arms = np.array([any(s in str(n) for s in ("shoulder", "elbow", "wrist")) for n in names])
        fingers = np.array([str(n).startswith(("L_", "R_")) for n in names])
        columns = {str(n): i for i, n in enumerate(names)}
        transitions, covered = [], np.zeros(len(t), dtype=bool)
        for edge in [*sequence["edges"], *([tail] if tail is not None else [])]:
            is_tail = edge is tail
            code = "REST_TAIL_" if is_tail else f"EDGE_{edge['edge_index']}_"
            first, last = edge["segment_indices"]
            polynomials = sequence["segments"][first:last + 1]
            analytic = _analytic_metrics(polynomials)
            if (np.any(analytic["lower_positions"][limited] < lower[limited] - constraints["joint_limit_tolerance_rad"])
                    or np.any(analytic["upper_positions"][limited] > upper[limited] + constraints["joint_limit_tolerance_rad"])):
                errors.append(code + "CONNECTOR_ANALYTIC_JOINT_LIMIT_VIOLATION")
            if np.any(analytic["speed"] > rates + constraints["speed_tolerance_rad_s"]):
                errors.append(code + "CONNECTOR_ANALYTIC_SPEED_VIOLATION")
            for segment in polynomials:
                coefficients = np.asarray(segment["coefficients"])
                for coupling in library["couplings"]:
                    residual = coefficients[columns[coupling["child"]]] - coupling["multiplier"] * coefficients[columns[coupling["parent"]]]
                    residual[0] -= coupling["offset"]
                    if np.sum(np.abs(residual)) > constraints["coupling_tolerance_rad"]:
                        errors.append(code + "CONNECTOR_ANALYTIC_COUPLING_VIOLATION")
            jumps, clamped = {}, {}
            for role, frame, polynomial, moment in (
                    ("exit", edge["exit_frame"], polynomials[0], polynomials[0]["start_time_s"]),
                    ("entry", None if is_tail else edge["entry_frame"], polynomials[-1], polynomials[-1]["end_time_s"])):
                if frame is None:  # a rest tail ends on the held rest pose
                    expected, slope = rest, np.zeros(len(rest))
                else:
                    word = instances[edge["from_instance_id"] if role == "exit" else edge["to_instance_id"]]
                    clip = clips[word["gloss"]]
                    left, right = (frame - 1, frame) if role == "exit" else (frame, frame + 1)
                    slope = (clip["positions"][right] - clip["positions"][left]) / (clip["timestamps_s"][right] - clip["timestamps_s"][left])
                    expected = clip["positions"][frame]
                    if pair_policy["endpoints"].get("clamped_joint_stop"):
                        stopped = clamped_stop_joints(expected, slope, "source" if role == "exit" else "target",
                                                      np.column_stack([lower, upper]))
                        clamped[role] = [str(n) for n in np.asarray(names)[stopped]]
                        slope = np.where(stopped, 0.0, slope)
                position = np.abs(_evaluate_polynomial(polynomial, [moment])[0] - expected)
                velocity = np.abs(_evaluate_polynomial(polynomial, [moment], 1)[0] - slope)
                accel = np.abs(_evaluate_polynomial(polynomial, [moment], 2)[0])
                jumps[role] = {"position_jump_rad": float(position.max()),
                               "velocity_jump_arm_rad_s": float(velocity[arms].max(initial=0)),
                               "velocity_jump_finger_rad_s": float(velocity[fingers].max(initial=0)),
                               "acceleration_jump_arm_rad_s2": float(accel[arms].max(initial=0)),
                               "acceleration_jump_finger_rad_s2": float(accel[fingers].max(initial=0))}
                if jumps[role]["position_jump_rad"] > constraints["position_tolerance_rad"]:
                    errors.append(code + "POSITION_BOUNDARY_MISMATCH")
                for key in ("velocity_jump_arm_rad_s", "velocity_jump_finger_rad_s",
                            "acceleration_jump_arm_rad_s2", "acceleration_jump_finger_rad_s2"):
                    if jumps[role][key] > limits[key]:
                        errors.append(code + "QUALITY_LIMIT_" + key.upper())
            duration = polynomials[-1]["end_time_s"] - polynomials[0]["start_time_s"]
            strategy, phase_record = edge["finger_strategy"], None
            if strategy["name"] != "synchronous" and np.any(fingers):
                phase = strategy["end_fraction"] if strategy["name"] == "early" else strategy["start_fraction"]
                moment = polynomials[0]["start_time_s"] + phase * duration
                segment = next(s for s in polynomials if s["start_time_s"] - 1e-10 <= moment <= s["end_time_s"] + 1e-10)
                word = instances[edge["to_instance_id"] if strategy["name"] == "early" else edge["from_instance_id"]]
                frame = edge["entry_frame"] if strategy["name"] == "early" else edge["exit_frame"]
                expected = clips[word["gloss"]]["positions"][frame]
                phase_record = {"strategy": strategy["name"], "curve_time_s": moment,
                    "position_rad": float(np.max(np.abs(_evaluate_polynomial(segment, [moment])[0, fingers] - expected[fingers]))),
                    "velocity_rad_s": float(np.max(np.abs(_evaluate_polynomial(segment, [moment], 1)[0, fingers]))),
                    "acceleration_rad_s2": float(np.max(np.abs(_evaluate_polynomial(segment, [moment], 2)[0, fingers])))}
                if (phase_record["position_rad"] > constraints["position_tolerance_rad"]
                        or phase_record["velocity_rad_s"] > limits["velocity_jump_finger_rad_s"]
                        or phase_record["acceleration_rad_s2"] > limits["acceleration_jump_finger_rad_s2"]):
                    errors.append(code + "FINGER_PHASE_CONTRACT_VIOLATION")
            if connector_only:
                region = connector_masks(polynomials, t)[1]
                region_start, region_end = float(t[region][0]), float(t[region][-1])
            else:
                region_start, region_end = spans[edge["edge_index"]][1], spans[edge["edge_index"] + 1][0]
                region = (t > region_start + 1e-9) & (t < region_end - 1e-9)
            if not region.any() or np.any(covered & region):
                raise ValueError("Transition scoring regions must be nonempty and disjoint")
            covered |= region
            metrics = {
                "peak_acceleration_rad_s2": float(np.abs(acceleration[region]).max()),
                "peak_jerk_rad_s3": float(np.abs(jerk[region]).max()),
                "jerk_integral_rad2_s5": _masked_trapezoid(squared, t, region),
                "maximum_transition_duration_s": duration,
                "analytic_connector_peak_acceleration_rad_s2": float(analytic["acceleration"].max()),
                "analytic_connector_peak_jerk_rad_s3": float(analytic["jerk"].max()),
                "analytic_connector_jerk_integral_rad2_s5": analytic["jerk_integral"],
            }
            if not np.isfinite(list(metrics.values())).all():
                raise ValueError("Nonfinite transition metrics")
            for key in (*REGION_LIMITS, "maximum_transition_duration_s"):
                if metrics[key] > limits[key]:
                    errors.append(code + "QUALITY_LIMIT_" + key.upper())
            for key in REGION_LIMITS:
                if metrics["analytic_connector_" + key] > limits[key]:
                    errors.append(code + "QUALITY_LIMIT_ANALYTIC_CONNECTOR_" + key.upper())
            scored = {"region_time_s": [float(region_start), float(region_end)],
                      "scored_replay_frames": int(region.sum()), "connector_time_s":
                      [polynomials[0]["start_time_s"], polynomials[-1]["end_time_s"]],
                      "metrics": metrics, "boundary": jumps, "finger_phase_recheck": phase_record,
                      **({"clamped_stop_joints": clamped} if clamped else {})}
            if is_tail:
                evidence["rest_tail"] = {"gloss": tail["gloss"], "exit_frame": tail["exit_frame"], **scored}
            else:
                transitions.append({"edge_index": edge["edge_index"], "pair_id": edge["pair_id"], **scored})
        if not connector_only and not np.array_equal(covered, ~protected):
            raise ValueError("Transition regions do not exactly cover the frames outside protected cores")
        evidence["transitions"] = transitions
        evidence["chain_metrics"] = {
            "scored_jerk_integral_total_rad2_s5": _masked_trapezoid(squared, t, ~protected),
            "unscoped_jerk_integral_rad2_s5": float(np.trapezoid(squared, x=t)),
            "unscoped_peak_acceleration_rad_s2": float(np.abs(acceleration).max()),
            "unscoped_peak_jerk_rad_s3": float(np.abs(jerk).max()), "gate": "informational_only"}
        tolerance = policy["validation"]["protected_relative_timing_tolerance_s"]
        evidence["protected_instance_checks"] = []
        for word, segment in zip(sequence["word_instances"], (s for s in sequence["segments"] if s["kind"] == "source_slice_v2")):
            clip = clips[word["gloss"]]
            c0, c1 = word["protected_core_frames"]
            original = clip["timestamps_s"][c0:c1 + 1]
            mapped = segment["start_time_s"] + original - clip["timestamps_s"][segment["source_frames"][0]]
            poses = _source_values(segment, mapped, clips, instances)
            replay_frames = np.rint(mapped * 30).astype(int)
            replay_equal = bool(np.allclose(mapped * 30, replay_frames, atol=1e-8, rtol=0)
                                and np.array_equal(q[replay_frames], clip["positions"][c0:c1 + 1]))
            timing = float(np.abs((mapped - mapped[0]) - (original - original[0])).max())
            check = {"instance_id": word["instance_id"], "gloss": word["gloss"], "source_frames": [c0, c1],
                     "protected_frame_count": c1 - c0 + 1, "poses_bitwise_equal": bool(np.array_equal(poses, clip["positions"][c0:c1 + 1])),
                     "replay_grid_poses_bitwise_equal": replay_equal, "max_relative_timing_error_s": timing,
                     "curve_time_range_s": [float(mapped[0]), float(mapped[-1])]}
            evidence["protected_instance_checks"].append(check)
            if not check["poses_bitwise_equal"] or not replay_equal or timing > tolerance:
                errors.append(f"{word['instance_id'].upper()}_PROTECTED_CORE_CHANGED")
        sampling = dict(pair_policy["validation"], **{k: policy["validation"][k] for k in (
            "dense_factors", "maximum_step_rad", "maximum_time_step_s", "max_subdivision_depth", "max_sampled_poses")})
        sampling_policy = {**pair_policy, "validation": sampling}
        measurements = []
        for factor in policy["validation"]["dense_factors"]:
            for index, segment in enumerate(sequence["segments"]):
                budget.check_time()
                remaining = policy["validation"]["max_sampled_poses"] - budget.sampled_poses
                times = _sample_times(segment, factor, sampling_policy, clips, instances, remaining)
                values = (_evaluate_polynomial(segment, times) if segment["kind"] == "polynomial_v2" else
                          _source_values(segment, times, clips, instances))
                if (np.max(np.diff(times)) > sampling["maximum_time_step_s"] * (1 + 1e-10)
                        or np.max(np.abs(np.diff(values, axis=0))) > sampling["maximum_step_rad"] * (1 + 1e-9)):
                    raise ValueError("Reconstructed sampling resolution is incomplete")
                minimum, worst = float("inf"), None
                for start in range(0, len(values), 16):
                    batch = values[start:start + 16]
                    budget.reserve(len(batch), 6 * len(batch))
                    measured = checker(batch)
                    if (not np.isfinite(measured.min_distance_m) or measured.sampled_frames != len(batch)
                            or not np.isfinite(measured.frame_clearances_m).all()):
                        raise ValueError("Nonfinite or incomplete native clearance")
                    budget.completed_poses += len(batch)
                    if measured.min_distance_m < minimum:
                        minimum = float(measured.min_distance_m)
                        worst = dict(measured.worst_contact or {})
                        worst.update(curve_time_s=float(times[int(worst.get("frame", 0)) + start]), segment_index=index)
                measurements.append({"factor": factor, "segment_index": index, "kind": segment["kind"],
                                     "instance_id": segment.get("word_instance_id"), "samples": len(values),
                                     "min_clearance_mm": minimum * 1000, "worst_contact": worst})
                if minimum < constraints["min_clearance_m"]:
                    if segment["kind"] == "polynomial_v2":
                        errors.append(f"SEGMENT_{index}_DENSE_CONNECTOR_COLLISION")
                    else:
                        (source_findings if connector_only else errors).append(f"SEGMENT_{index}_WORD_SLICE_COLLISION")
        budget.check_time()
        errors = list(dict.fromkeys(errors))
        if connector_only:
            evidence["source_side_findings"] = {
                "gate": "informational_only", "owner": "source motion (group 2)",
                "reason_codes": list(dict.fromkeys(source_findings)),
                "min_clearance_mm": min(m["min_clearance_mm"] for m in measurements if m["kind"] != "polynomial_v2")}
            measurements_gated = [m for m in measurements if m["kind"] == "polynomial_v2"]
        else:
            measurements_gated = measurements
        pending = acceptance_pending(pair_policy)
        evidence.update(validation_complete=True, numerical_checks_passed=not errors,
                        status="NUMERICAL_PASS" if not errors else "FAILED_NUMERICAL",
                        reason_codes=errors, dense_recheck_result=measurements, pair_identity=identity,
                        sequence_identity=sequence["sequence_identity"],
                        min_clearance_mm=min(m["min_clearance_mm"] for m in measurements_gated), **coordinates,
                        formal_pending_reasons=[r for r in pending if r not in LEGACY_FORMAL_WORDING],
                        legacy_formal_wording_not_a_precondition=[r for r in pending if r in LEGACY_FORMAL_WORDING],
                        word_occurrences=len(sequence["word_instances"]), connector_groups=len(sequence["edges"]),
                        rest_tail_present=tail is not None,
                        reconstructed_motion_canonical_hash=canonical_array_hash(motion),
                        replay_frame_count=len(q), replay_duration_s=float(t[-1]),
                        source_replay_continuous_derivatives_certified=False)
    except WindowApprovalError as exc:
        evidence.update(status="BLOCKED_INPUT", reason_codes=[exc.code])
    except VerificationBudgetExceeded as exc:
        evidence.update(status="TIMEOUT", numerical_checks_passed=None, validation_complete=False, reason_codes=[str(exc)])
    except (OSError, KeyError, TypeError, ValueError, IndexError, OverflowError, FloatingPointError, np.linalg.LinAlgError) as exc:
        evidence.update(status="ERROR", numerical_checks_passed=None, validation_complete=False,
                        reason_codes=["SEQUENCE_VERIFICATION_INPUT_OR_CURVE_INVALID"],
                        diagnostic_details={"type": type(exc).__name__, "message": str(exc)})
    finally:
        if budget is not None:
            evidence["verification_budget"] = budget.record()
    return evidence
