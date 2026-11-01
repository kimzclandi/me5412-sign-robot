"""Coverage, endpoint audit and resumable direct-candidate development scan.

The R13c sentence entry point is deliberately separate. This first milestone
does not implement the later general search or final acceptance contract.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import io
import csv
import math
from pathlib import Path
import time

import numpy as np

from sign_robot.motion import ROOT, load_model
from sign_robot.pair_contract import (
    STATUSES, acceptance_pending, atomic_bytes, atomic_json, atomic_motion,
    boundary_derivatives, canonical_array_hash, coordinate_errors, file_hash,
    freeze_library, inside, json_bytes, json_hash, pair_universe, quintic_samples,
    rate_limits, read_json, run_directory, run_identity,
)
from sign_robot.transitions import MujocoClearance, _library_joint_ranges

COLLISION_SCOPE = {
    "geometry": "delivered Unitree G1 / Inspire DFQ collision geoms only",
    "moving_pairs": "native MuJoCo pair eligibility; same-hand pairs excluded",
    "static_pairs": "equal moving-ancestor sets; measured separately, not gated",
    "continuous_collision_certified": False,
    "word_interpolation": "piecewise linear between delivered samples",
    "connector_interpolation": "one analytic minimum-jerk quintic",
    "unmodelled_contacts": "not covered; no dynamics, hardware or language certification",
}


def clearance_summary(result):
    return {"min_clearance_mm": float(result.min_distance_m * 1000),
            "closest_collision_pair": result.worst_contact,
            "sampled_frames": int(result.sampled_frames)}


@dataclass
class PairContext:
    root: Path
    policy: dict
    library: dict
    clips: dict
    model: object
    clearance: object
    audit: dict


def build_context(root, policy, *, library=None, clips=None, audit=None):
    root = Path(root).resolve()
    if library is None or clips is None:
        library, clips = freeze_library(root, policy)
    model, clearance = None, None
    if not library["input_errors"] and all(not w["input_errors"] for w in library["words"]):
        try:
            model = load_model(root)
            expected = [model.joint(i).name for i in range(model.njnt)]
            if expected != library["joint_names"]:
                raise ValueError("Trajectory order differs from the named model contract")
            _library_joint_ranges.cache_clear()
            clearance = MujocoClearance(model, np.array(expected), library_path=root / "motions/hospital_v1_motions.json")
        except (OSError, ValueError, KeyError) as exc:
            library["input_errors"].append({"code": "MODEL_OR_COLLISION_INPUT_INVALID", "details": str(exc)})
    context = PairContext(root, policy, library, clips, model, clearance, audit or {})
    if audit is None:
        context.audit = audit_words(context)
    return context


def audit_words(context):
    policy, library = context.policy, context.library
    constraints = policy["constraints"]
    audited = {}
    for word in library["words"]:
        gloss = word["gloss"]
        issues = list(word["input_errors"])
        item = {"gloss": gloss, "motion_hash": word.get("motion_sha256"),
                "robot_status": word["robot_status"], "robot_note": word.get("robot_note"),
                "geometric_core_hint": word.get("core_frames"),
                "geometric_sign_hint": word.get("sign_frames"),
                "semantic_core": None, "semantic_review_status": "unreviewed",
                "window_review_status": "pending_group2_confirmation",
                "allowed_entry_frames": [word["sign_frames"][0]],
                "allowed_exit_frames": [word["sign_frames"][1]],
                "window_basis": "original geometric sign_frames; no new trimming permission",
                "input_errors": issues, "endpoints": {}, "research_endpoints": []}
        audited[gloss] = item
        if gloss not in context.clips or context.clearance is None:
            continue
        motion = context.clips[gloss]
        q, t, names = (motion[k] for k in ("positions", "timestamps_s", "joint_names"))
        try:
            result = context.clearance(q)
            profile = result.frame_clearances_m
            item.update(frames=len(q), duration_s=float(t[-1] - t[0]),
                        timestamps_strictly_increasing=True, joint_count=len(names),
                        **coordinate_errors(q, names, context.model, library["couplings"]),
                        peak_speed_rad_s=float(np.max(np.abs(np.diff(q, axis=0)) / np.diff(t)[:, None])),
                        speed_limit_excess_rad_s=float(np.maximum(
                            np.abs(np.diff(q, axis=0)) / np.diff(t)[:, None] - rate_limits(names, policy), 0).max()),
                        **clearance_summary(result), frame_clearances_m=profile,
                        original_collision_frames=[i for i, d in enumerate(profile) if d < constraints["min_clearance_m"]])
            meta = read_json(context.root / Path(word["motion"]).with_suffix(".json"))
            item["source"] = meta.get("source")
            item["source_license_review_status"] = "recorded_source_only; not a new redistribution approval"
            item["delivered_inputs"] = {"trajectory": True, "metadata": True,
                                         "raw_source_required_for_scan": False}
            for role, frame in (("target", word["sign_frames"][0]), ("source", word["sign_frames"][1])):
                measured = context.clearance(q[frame:frame + 1])
                errors = coordinate_errors(q[frame:frame + 1], names, context.model, library["couplings"])
                valid = (measured.min_distance_m >= constraints["min_clearance_m"] and
                         errors["joint_limit_error"] <= constraints["joint_limit_tolerance_rad"] and
                         errors["coupling_error"] <= constraints["coupling_tolerance_rad"])
                item["endpoints"][role] = {
                    "frame": frame, "engineering_valid": bool(valid), **errors,
                    **clearance_summary(measured),
                    "boundary_derivatives": boundary_derivatives(motion, frame, role,
                        policy["quality"]["derivative_window_frames"])}
            for proposal in policy["endpoints"]["legacy_research_endpoints"]:
                if proposal["gloss"] != gloss:
                    continue
                if proposal["motion_sha256"] != word["motion_sha256"]:
                    item["research_endpoints"].append({**proposal, "selected_for_scan": False,
                        "motion_hash_matches_proposal": False, "recheck_status": "STALE_INPUT_HASH"})
                    continue
                frame = proposal["frame"]
                if frame >= len(q):
                    raise ValueError("Research endpoint is outside its hash-bound motion")
                sample = context.clearance(q[frame:frame + 1])
                trim = (word["sign_frames"][1] - frame if proposal["role"] == "source" else
                        frame - word["sign_frames"][0])
                item["research_endpoints"].append({
                    **proposal, "motion_hash": word["motion_sha256"],
                    "motion_hash_matches_proposal": word["motion_sha256"] == proposal["motion_sha256"],
                    "trim_count": trim, "trim_ratio": trim / (word["core_frames"][1] - word["core_frames"][0] + 1),
                    "approval_status": "pending", "selected_for_scan": False,
                    **clearance_summary(sample)})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            issues.append(f"WORD_AUDIT_ERROR: {exc}")
    return {"schema_version": 1, "library_version": library["library_version"],
            "sampling_factor": 1, "collision_scope": COLLISION_SCOPE,
            "collision_derivation": getattr(context.clearance, "derivation", None),
            "vendor_structural_gaps": getattr(context.clearance, "vendor_structural_gaps", []),
            "global_input_errors": library["input_errors"], "words": audited}


def initial_record(source, target, context, seed):
    policy, library = context.policy, context.library
    words = {w["gloss"]: w for w in library["words"]}
    return {
        "schema_version": 1, "pair_id": f"{source}__{target}", "source_gloss": source,
        "target_gloss": target, "self_pair": source == target, "attempt_id": 1,
        **run_identity(library, policy), "source_motion_hash": words.get(source, {}).get("motion_sha256"),
        "target_motion_hash": words.get(target, {}).get("motion_sha256"),
        "entry_frame": None, "exit_frame": None,
        "endpoint_window_version": policy["endpoints"]["window_version"], "exception_ids": [],
        "method": "not_attempted", "candidate_count": 0, "seed": int(seed),
        "work_budget": {"max_candidates": 1, "max_collision_samples": policy["planner"]["max_collision_samples"]},
        "collision_samples_used": 0, "wall_time_s": 0.0,
        "status": "NOT_RUN", "reason_codes": [], "diagnostic_details": {},
        "transition_duration_s": None, "full_clip_duration_s": None,
        "min_clearance_mm": None, "closest_collision_pair": None,
        "collision_scope": COLLISION_SCOPE, "validation_resolution": {"planning_factor": 1},
        "dense_recheck_result": None, "joint_limit_error": None, "coupling_error": None,
        "peak_arm_speed": None, "peak_finger_speed": None, "peak_acceleration": None, "peak_jerk": None,
        "position_jump": None, "velocity_jump": None, "acceleration_jump": None, "jerk_integral": None,
        "protected_core_preserved": None, "trim_count": 0, "trim_ratio": 0.0,
        "trajectory_file": None, "trajectory_file_hash": None, "canonical_array_hash": None,
        "verification_file": None, "verification_hash": None,
        "language_review_status": "unreviewed", "hardware_validation_status": "unvalidated",
        "playback_eligible": False,
    }


def plan_pair(source_gloss, target_gloss, *, library_version, policy, seed, root=ROOT, context=None):
    """Return (assembled two-word candidate or None, structured diagnostic record).

    Only frozen hospital glosses are supported; the broader R13c lookup is never
    used. Every saved candidate is for research and still needs independent
    verification. No development candidate is promoted to PASS_SIM here.
    """
    context = build_context(root, policy) if context is None else context
    if json_hash(policy) != json_hash(context.policy):
        raise ValueError("The pair policy differs from its frozen context")
    source, target = str(source_gloss).upper(), str(target_gloss).upper()
    record = initial_record(source, target, context, seed)
    started = time.monotonic()

    def finish(status, reasons, motion=None, details=None):
        record.update(status=status, reason_codes=list(dict.fromkeys(reasons)),
                      wall_time_s=time.monotonic() - started)
        record["planning_evidence"] = {key: record[key] for key in
            ("status", "reason_codes", "min_clearance_mm", "closest_collision_pair", "validation_resolution", "wall_time_s")}
        if details is not None:
            record["diagnostic_details"] = details
        return motion, record

    if library_version not in (context.library["library"], context.library["library_version"]):
        return finish("BLOCKED_INPUT", ["LIBRARY_VERSION_MISMATCH"])
    if source not in context.audit["words"] or target not in context.audit["words"]:
        return finish("BLOCKED_INPUT", ["UNKNOWN_GLOSS"])
    audits = [context.audit["words"][g] for g in (source, target)]
    if context.audit["global_input_errors"] or any(a["input_errors"] for a in audits):
        return finish("BLOCKED_INPUT", ["FROZEN_INPUT_INVALID"], details={
            "global": context.audit["global_input_errors"],
            "source": audits[0]["input_errors"], "target": audits[1]["input_errors"]})
    source_endpoint, target_endpoint = audits[0]["endpoints"]["source"], audits[1]["endpoints"]["target"]
    record.update(exit_frame=source_endpoint["frame"], entry_frame=target_endpoint["frame"])
    bad = [role for role, endpoint in (("source", source_endpoint), ("target", target_endpoint))
           if not endpoint["engineering_valid"]]
    if bad:
        return finish("BLOCKED_ENDPOINT", [f"{role.upper()}_ENDPOINT_INVALID" for role in bad], details={
            "source": source_endpoint, "target": target_endpoint})
    first, second = context.clips[source], context.clips[target]
    a, b = first["positions"][record["exit_frame"]], second["positions"][record["entry_frame"]]
    names = first["joint_names"]
    rates = rate_limits(names, policy)
    duration = max(policy["planner"]["minimum_duration_s"], float(np.max(1.875 * np.abs(b - a) / rates)))
    intervals = max(1, math.ceil(duration * policy["fps"] - 1e-12))
    if intervals + 1 > policy["planner"]["max_collision_samples"]:
        return finish("FAILED_SEARCH", ["DIRECT_CANDIDATE_WORK_BUDGET_EXHAUSTED"])
    q = quintic_samples(a, b, intervals)
    record.update(method=policy["planner"]["method"], candidate_count=1,
                  transition_duration_s=intervals / policy["fps"],
                  finger_strategy="synchronous quintic progress; all 53 coordinates checked")
    minimum, worst = float("inf"), None
    for start in range(0, len(q), 16):
        if time.monotonic() - started >= policy["planner"]["wall_time_s"]:
            return finish("TIMEOUT", ["PAIR_WALL_TIME_LIMIT"])
        measured = context.clearance(q[start:start + 16])
        record["collision_samples_used"] += measured.sampled_frames
        if measured.min_distance_m < minimum:
            minimum, worst = measured.min_distance_m, dict(measured.worst_contact or {})
            if "frame" in worst:
                worst["frame"] += start
    if time.monotonic() - started >= policy["planner"]["wall_time_s"]:
        return finish("TIMEOUT", ["PAIR_WALL_TIME_LIMIT"])
    errors = coordinate_errors(q, names, context.model, context.library["couplings"])
    record.update(min_clearance_mm=float(minimum * 1000), closest_collision_pair=worst, **errors)
    source_end = record["exit_frame"]
    target_start = source_end + len(q) - 1
    full = np.vstack([first["positions"][:source_end + 1], q[1:-1],
                      second["positions"][record["entry_frame"]:]])
    motion = {"joint_names": names.copy(), "positions": full,
              "timestamps_s": np.arange(len(full), dtype=float) / policy["fps"]}
    record.update(transition_start_frame=source_end, transition_end_frame=target_start,
                  full_clip_duration_s=float(motion["timestamps_s"][-1]),
                  word_segments=[
                      {"gloss": source, "start_frame": 0, "end_frame": source_end,
                       "source_frames": [0, source_end]},
                      {"gloss": target, "start_frame": target_start, "end_frame": len(full) - 1,
                       "source_frames": [record["entry_frame"], len(second["positions"]) - 1]}])
    if minimum < policy["constraints"]["min_clearance_m"]:
        return finish("FAILED_SEARCH", ["DIRECT_CANDIDATE_COLLISION", "GENERAL_SEARCH_NOT_IMPLEMENTED"], motion)
    return finish("FAILED_QUALITY", [*acceptance_pending(policy), "INDEPENDENT_RECHECK_REQUIRED"], motion)


def save_checkpoint(run_dir, record):
    identity = read_json(Path(run_dir) / "manifest.json")["identity"]["identity_hash"]
    if record.get("identity_hash") != identity or record["status"] not in STATUSES:
        raise ValueError("Checkpoint identity/status differs from the frozen run")
    atomic_json(Path(run_dir) / "checkpoints" / f"{record['pair_id']}.json",
                {"record": record, "record_hash": json_hash(record)})


def read_checkpoints(run_dir, manifest, *, check_artifacts=True):
    records = {}
    universe = {p["pair_id"]: p for p in read_json(Path(run_dir) / "pair_universe.json")}
    for path in sorted((Path(run_dir) / "checkpoints").glob("*.json")):
        envelope = read_json(path)
        record = envelope["record"]
        pair_id = record["pair_id"]
        if (json_hash(record) != envelope["record_hash"] or pair_id != path.stem or pair_id not in universe
                or any(record[k] != universe[pair_id][k] for k in ("source_gloss", "target_gloss", "self_pair"))
                or any(record.get(k) != v for k, v in manifest["identity"].items())
                or record["status"] not in STATUSES):
            raise ValueError(f"Invalid checkpoint: {path.name}")
        if record["status"] == "PASS_SIM":
            raise ValueError("This development contract cannot import PASS_SIM checkpoints")
        if check_artifacts:
            for key, digest in (("trajectory_file", "trajectory_file_hash"), ("verification_file", "verification_hash")):
                if record.get(key) and file_hash(inside(run_dir, record[key])) != record[digest]:
                    raise ValueError(f"Checkpoint artifact integrity mismatch: {record[key]}")
        records[pair_id] = record
    return records


def check_frozen_files(run_dir, manifest):
    for relative, digest in manifest["frozen_files"].items():
        if file_hash(inside(run_dir, relative)) != digest:
            raise ValueError(f"Frozen run file integrity mismatch: {relative}")


def initialize_run(root, policy, run_id, results_root, *, resume=False):
    run_dir = run_directory(results_root, run_id)
    library, clips = freeze_library(root, policy)
    identity = run_identity(library, policy)
    if run_dir.exists():
        if not resume:
            raise ValueError("Run already exists; use --resume or a new run_id")
        manifest = read_json(run_dir / "manifest.json")
        check_frozen_files(run_dir, manifest)
        if manifest["identity"] != identity:
            raise ValueError("Code, policy, model, environment or inputs changed; use a new run_id")
        context = build_context(root, policy, library=library, clips=clips, audit=read_json(run_dir / "word_audit.json"))
        read_checkpoints(run_dir, manifest)
        return run_dir, context, manifest
    context = build_context(root, policy, library=library, clips=clips)
    # build_context may discover a model-contract error; freeze that diagnosis.
    snapshots = {"policy.json": policy, "library_manifest.json": library,
                 "word_audit.json": context.audit,
                 "pair_universe.json": pair_universe(policy["scope"]["expected_glosses"])}
    run_dir.mkdir(parents=True)
    for relative, value in snapshots.items():
        atomic_json(run_dir / relative, value)
    manifest = {"schema_version": 1, "run_id": run_id, "identity": identity,
                "frozen_files": {relative: file_hash(run_dir / relative) for relative in snapshots},
                "planner": policy["planner"]["method"], "acceptance_level": "development_scan_only",
                "planning_complete": False, "verification_complete": False,
                "collision_scope": COLLISION_SCOPE, "files": {}}
    atomic_json(run_dir / "manifest.json", manifest)
    return run_dir, context, manifest


def run_scan(root, policy, run_id, results_root, *, resume=False, max_pairs=None,
             selected_pairs=None, progress=None):
    if max_pairs is not None and max_pairs < 0:
        raise ValueError("max_pairs must be non-negative")
    if selected_pairs is not None and not selected_pairs <= {p["pair_id"] for p in pair_universe(policy["scope"]["expected_glosses"])}:
        raise ValueError("Selected pairs must belong to the frozen vocabulary")
    run_dir, context, manifest = initialize_run(root, policy, run_id, results_root, resume=resume)
    records = read_checkpoints(run_dir, manifest)
    executed = 0
    for pair in pair_universe(policy["scope"]["expected_glosses"]):
        if pair["pair_id"] in records or (selected_pairs is not None and pair["pair_id"] not in selected_pairs):
            continue
        if max_pairs is not None and executed >= max_pairs:
            break
        try:
            motion, record = plan_pair(pair["source_gloss"], pair["target_gloss"],
                library_version=context.library["library_version"], policy=policy,
                seed=policy["planner"]["seed"], context=context)
        except Exception as exc:
            motion = None
            record = initial_record(pair["source_gloss"], pair["target_gloss"], context, policy["planner"]["seed"])
            record.update(status="ERROR", reason_codes=["PLANNER_EXCEPTION"],
                          diagnostic_details={"type": type(exc).__name__, "message": str(exc)})
        record["run_id"] = run_id
        if "planning_evidence" not in record:
            record["planning_evidence"] = {key: record[key] for key in
                ("status", "reason_codes", "min_clearance_mm", "closest_collision_pair", "validation_resolution", "wall_time_s")}
        if motion is not None:
            relative = f"trajectories/{pair['pair_id']}.npz"
            atomic_motion(run_dir / relative, motion)
            record.update(trajectory_file=relative, trajectory_file_hash=file_hash(run_dir / relative),
                          canonical_array_hash=canonical_array_hash(motion))
        save_checkpoint(run_dir, record)
        records[pair["pair_id"]] = record
        executed += 1
        if progress:
            progress(len(records), len(context.library["words"]) ** 2, record)
    summary = summarize_run(run_dir)
    return run_dir, summary


def summarize_run(run_dir):
    run_dir = Path(run_dir)
    manifest = read_json(run_dir / "manifest.json")
    check_frozen_files(run_dir, manifest)
    records = read_checkpoints(run_dir, manifest)
    universe = read_json(run_dir / "pair_universe.json")
    rows = [{**p, "run_id": manifest["run_id"], "status": "NOT_RUN", "reason_codes": [], **records.get(p["pair_id"], {})}
            for p in universe]
    statuses = {p["pair_id"]: p["status"] for p in rows}
    glosses = read_json(run_dir / "policy.json")["scope"]["expected_glosses"]
    matrix = io.StringIO(newline="")
    writer = csv.writer(matrix)
    writer.writerow(["source_gloss/target_gloss", *glosses])
    writer.writerows([[source, *[statuses[f"{source}__{target}"] for target in glosses]] for source in glosses])
    atomic_bytes(run_dir / "matrix.csv", matrix.getvalue().encode("utf-8"))
    atomic_bytes(run_dir / "pairs.jsonl", b"".join(json_bytes(row) for row in rows))
    groups = {}
    for label, subset in (("all", rows), ("non_self", [r for r in rows if not r["self_pair"]]),
                          ("self", [r for r in rows if r["self_pair"]])):
        counts = Counter(r["status"] for r in subset)
        groups[label] = {"denominator": len(subset), "status_counts": {s: counts[s] for s in STATUSES},
                         "scanned": len(subset) - counts["NOT_RUN"],
                         "pass_sim_rate": counts["PASS_SIM"] / len(subset) if subset else 0.0}
    reasons = Counter(reason for row in rows for reason in row["reason_codes"])
    candidates = [r for r in records.values() if r.get("trajectory_file")]
    verified = [r for r in records.values() if r.get("verification_hash")]
    summary = {"run_id": manifest["run_id"], "identity": manifest["identity"], "groups": groups,
               "reason_counts": dict(sorted(reasons.items())), "saved_candidates": len(candidates),
               "verified_records": len(verified),
               "verification_complete": len(verified) == len(universe),
               "coverage_complete": groups["all"]["scanned"] == len(universe),
               "L2_complete": False, "acceptance_level": "development_scan_only"}
    summary["resources"] = {"planning_wall_time_sum_s": sum(r.get("wall_time_s", 0) for r in records.values()),
                            "trajectory_bytes": sum(inside(run_dir, r["trajectory_file"]).stat().st_size for r in candidates),
                            "search_attempts": 0, "general_search_implemented": False}
    atomic_json(run_dir / "summary.json", summary)
    manifest.update(planning_complete=summary["coverage_complete"],
                    verification_complete=summary["verification_complete"],
                    completed_pair_count=len(records), saved_candidate_count=len(candidates))
    # Include frozen inputs, every checkpoint, trajectory and verification file.
    # The manifest excludes itself and is atomically replaced last.
    files = sorted(p for p in run_dir.rglob("*") if p.is_file()
                   and p.name != "manifest.json" and not p.name.endswith(".part"))
    manifest["files"] = {str(p.relative_to(run_dir)): {"sha256": file_hash(p), "bytes": p.stat().st_size}
                         for p in files}
    atomic_json(run_dir / "manifest.json", manifest)
    return summary
