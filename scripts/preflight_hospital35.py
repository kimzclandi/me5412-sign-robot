#!/usr/bin/env python3
"""Preflight every protected core and both endpoint roles before a library-wide pair run.

Global input blockers, intrinsic protected-source defects (speed, joint limit,
coupling and sampled geometry; acceleration and jerk inside cores are
informational as in v5) and words without a usable exit or entry endpoint are
reported separately. Budget exhaustion is INCOMPLETE, never a pass. Predicted
pair impacts are diagnostics only; pairs are still planned and verified.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

from sign_robot.pair_contract import atomic_json, file_hash, inside, json_hash, load_policy, run_identity
from sign_robot.pair_routes import PairWorkBudget, PlanningBudgetExceeded, build_pair_context_v2, valid_endpoint_choices_v2
from sign_robot.pair_verification_v2 import (
    VerificationBudgetExceeded, _Budget, _protected_source_audit, _sample_times, _source_values,
)

INFORMATIONAL_CORE_METRICS = ("peak_acceleration_rad_s2", "peak_jerk_rad_s3")


def core_geometry(context, gloss, clip, core, budget):
    """Dense clearance of the unchanged core, sampled exactly as the verifier samples word slices."""
    first, last = core
    instances, clips = {"core": {"gloss": gloss}}, {gloss: clip}
    segment = {"kind": "source_slice_v2", "start_time_s": 0.0, "end_time_s": (last - first) / 30,
               "word_instance_id": "core", "source_frames": [first, last]}
    minimum, worst, samples = float("inf"), None, 0
    for factor in context.policy["validation"]["dense_factors"]:
        if last == first:
            times = np.array([0.0])
        else:
            times = _sample_times(segment, factor, context.policy, clips, instances,
                                  context.policy["validation"]["max_sampled_poses"] - budget.sampled_poses)
        values = _source_values(segment, times, clips, instances) if last > first else clip["positions"][first:first + 1]
        for start in range(0, len(values), 16):
            batch = values[start:start + 16]
            budget.reserve(len(batch), 6 * len(batch))
            measured = context.clearance(batch)
            if (not np.isfinite(measured.min_distance_m) or measured.sampled_frames != len(batch)
                    or len(measured.frame_clearances_m) != len(batch)):
                raise ValueError("Nonfinite or incomplete core clearance")
            budget.completed_poses += len(batch)
            samples += len(batch)
            if measured.min_distance_m < minimum:
                minimum = float(measured.min_distance_m)
                local = int(np.argmin(measured.frame_clearances_m)) + start
                worst = {**dict(measured.worst_contact or {}), "factor": factor,
                         "source_frame": float(first + times[local] * 30)}
            budget.check_time()
    return {"samples": samples, "min_clearance_mm": minimum * 1000, "worst_contact": worst,
            "passed": minimum >= context.policy["constraints"]["min_clearance_m"],
            "continuous_collision_certified": False}


def audit_core(context, gloss, clip=None):
    """Protected-core audit from original samples only; returns a complete or explicitly incomplete row."""
    protection = context.approvals[gloss]
    clip = context.clips[gloss] if clip is None else clip
    core = protection.protected_core_frames
    started = time.monotonic()
    budget = _Budget(context.policy["validation"], started)
    row = {"protected_core_frames": list(core), "protected_frame_count": core[1] - core[0] + 1, "defects": [],
           "informational_defects": [], "complete": False, "status": "INCOMPLETE"}
    try:
        audit = _protected_source_audit(clip, core, context.policy, context.model, context.library["couplings"])
        row["source_audit"] = audit
        for defect in audit["defects"]:
            (row["informational_defects"] if defect["metric"] in INFORMATIONAL_CORE_METRICS else row["defects"]).append(defect)
        geometry = core_geometry(context, gloss, clip, core, budget)
        row["geometry"] = geometry
        if not geometry["passed"]:
            row["defects"].append({"metric": "sampled_core_clearance_mm", "value": geometry["min_clearance_mm"],
                                   "limit": context.policy["constraints"]["min_clearance_m"] * 1000,
                                   "source_frame": geometry["worst_contact"]["source_frame"], "origin": "protected_source_clip"})
        row.update(complete=True, status="CORE_SOURCE_DEFECT" if row["defects"] else "CORE_CLEAR")
    except VerificationBudgetExceeded as exc:
        row.update(status="INCOMPLETE", reason=str(exc))
    finally:
        row["budget"] = budget.record()
    return row


def endpoint_roles(context, gloss):
    """Real endpoint screening for the self-pair: source = exit after the core, target = entry before it."""
    budget = PairWorkBudget(context.policy)
    try:
        selection = valid_endpoint_choices_v2(context, gloss, gloss, budget)
    except PlanningBudgetExceeded as exc:
        return {"complete": False, "status": "INCOMPLETE", "reason": str(exc), "budget": budget.snapshot()}
    limits = context.policy["constraints"]
    roles = {}
    for role in ("source", "target"):
        item = selection[role]
        reasons = Counter()
        for check in item["endpoint_checks"]:
            if check["engineering_valid"]:
                continue
            if not check["passed"]:
                reasons["CLEARANCE_BELOW_MIN"] += 1
            if check["joint_limit_error"] > limits["joint_limit_tolerance_rad"]:
                reasons["JOINT_LIMIT"] += 1
            if check["coupling_error"] > limits["coupling_tolerance_rad"]:
                reasons["COUPLING"] += 1
            if not check["boundary_speed_valid"]:
                reasons["BOUNDARY_SPEED"] += 1
            if not check["boundary_limit_viable"]:
                reasons["OUTWARD_MOTION_AT_JOINT_LIMIT"] += 1
        roles[role] = {"window_frames": [item["allowed_frames"][0], item["allowed_frames"][-1]],
                       "allowed_count": len(item["allowed_frames"]), "valid_count": len(item["valid_frames"]),
                       "valid_frames": sorted(item["valid_frames"]), "ranked_first_frames": item["valid_frames"][:8],
                       "failure_reason_counts": dict(sorted(reasons.items())),
                       "min_clearance_mm": min(c["min_clearance_mm"] for c in item["endpoint_checks"])}
    return {"complete": True, "status": "ENDPOINTS_SCREENED", "roles": roles, "budget": budget.snapshot()}


def classify(core, endpoints):
    labels = []
    if not core["complete"] or not endpoints["complete"]:
        labels.append("INCOMPLETE")
    if core["status"] == "CORE_SOURCE_DEFECT":
        labels.append("CORE_SOURCE_DEFECT")
    if endpoints["complete"]:
        if not endpoints["roles"]["source"]["valid_count"]:
            labels.append("NO_EXIT_ENDPOINT")
        if not endpoints["roles"]["target"]["valid_count"]:
            labels.append("NO_ENTRY_ENDPOINT")
    return labels or ["PREFLIGHT_CLEAR"]


def affected_pairs(glosses, rows):
    """Diagnostic prediction only: which ordered pairs a word-level finding is expected to block."""
    groups = {"core_source_defect": set(), "no_exit_endpoint": set(), "no_entry_endpoint": set(), "incomplete": set()}
    for word, row in rows.items():
        labels = row["labels"]
        for other in glosses:
            if "CORE_SOURCE_DEFECT" in labels:
                groups["core_source_defect"] |= {f"{word}__{other}", f"{other}__{word}"}
            if "INCOMPLETE" in labels:
                groups["incomplete"] |= {f"{word}__{other}", f"{other}__{word}"}
            if "NO_EXIT_ENDPOINT" in labels:
                groups["no_exit_endpoint"].add(f"{word}__{other}")
            if "NO_ENTRY_ENDPOINT" in labels:
                groups["no_entry_endpoint"].add(f"{other}__{word}")
    union = set().union(*groups.values())
    return {**{name: {"count": len(pairs), "pair_ids": sorted(pairs)} for name, pairs in groups.items()},
            "any": {"count": len(union), "pair_ids": sorted(union)},
            "unaffected_count": len(glosses) ** 2 - len(union), "denominator": len(glosses) ** 2}


def preflight(root, policy_path):
    root = Path(root).resolve()
    policy = load_policy(policy_path, supported_versions=(2,))
    if policy["endpoints"]["strategy"] != "user_protected_auto_windows_v1":
        raise ValueError("Preflight covers user-protected automatic windows only")
    context = build_pair_context_v2(root, policy)
    glosses = policy["scope"]["expected_glosses"]
    identity = run_identity(context.library, policy)
    result = {"schema_version": 1, "kind": "hospital35_protected_preflight_v1", "identity": identity,
              "policy_hash": json_hash(policy), "protection_file": policy["endpoints"]["protection_file"],
              "protection_bundle_sha256": file_hash(inside(root, policy["endpoints"]["protection_file"])),
              "global_input_blockers": list(context.input_blockers), "window_provenance": "algorithm",
              "formal_acceptance_enabled": False}
    if not context.input_blockers and sorted(context.approvals) != sorted(glosses):
        result["global_input_blockers"].append({"code": "PROTECTION_SCOPE_INCOMPLETE",
                                                "missing": sorted(set(glosses) - set(context.approvals))})
    if result["global_input_blockers"]:
        result.update(status="GLOBAL_INPUT_BLOCKED", words={})
        return result
    rows = {}
    for gloss in glosses:
        started = time.monotonic()
        core = audit_core(context, gloss)
        endpoints = endpoint_roles(context, gloss)
        word = next(w for w in context.library["words"] if w["gloss"] == gloss)
        protection = context.approvals[gloss]
        rows[gloss] = {"gloss": gloss, "motion": word["motion"], "motion_sha256": word["motion_sha256"],
                       "frame_count": word["frames"], "protection_id": protection.protection_id,
                       "protection_sha256": protection.protection_sha256, "core": core, "endpoints": endpoints,
                       "labels": classify(core, endpoints), "wall_time_s": time.monotonic() - started}
        print(json.dumps({"gloss": gloss, "labels": rows[gloss]["labels"]}), flush=True)
    if list(rows) != glosses:
        raise ValueError("Preflight rows differ from the frozen scope")
    counts = Counter(label for row in rows.values() for label in row["labels"])
    result.update(status="COMPLETE" if "INCOMPLETE" not in counts else "INCOMPLETE", words=rows,
                  word_count=len(rows), label_counts=dict(sorted(counts.items())),
                  affected_pairs=affected_pairs(glosses, rows),
                  note="Word-level findings predict pair impacts; they do not replace planning or verification.")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=ROOT / "config/transition_policy_user_protected_hospital35_v1.json")
    parser.add_argument("--output", type=Path, required=True, help="New directory; never reused")
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("Output exists; keep historical evidence and choose a new path")
    started = time.monotonic()
    result = preflight(ROOT, args.policy)
    result["wall_time_s"] = time.monotonic() - started
    args.output.mkdir(parents=True)
    atomic_json(args.output / "preflight.json", result)
    table = ["gloss,labels,core_status,speed_ratio,joint_limit_error,coupling_error,core_min_clearance_mm,"
             "peak_acceleration_rad_s2,peak_jerk_rad_s3,exit_valid,exit_allowed,entry_valid,entry_allowed"]
    for gloss, row in result["words"].items():
        core, metrics = row["core"], row["core"].get("source_audit", {}).get("metrics", {})
        roles = row["endpoints"].get("roles", {})
        table.append(",".join(str(v) for v in (
            gloss, "+".join(row["labels"]), core["status"], metrics.get("speed_ratio"),
            core.get("source_audit", {}).get("joint_limit_error"), core.get("source_audit", {}).get("coupling_error"),
            core.get("geometry", {}).get("min_clearance_mm"), metrics.get("peak_acceleration_rad_s2"),
            metrics.get("peak_jerk_rad_s3"), roles.get("source", {}).get("valid_count"),
            roles.get("source", {}).get("allowed_count"), roles.get("target", {}).get("valid_count"),
            roles.get("target", {}).get("allowed_count"))))
    (args.output / "words.csv").write_text("\n".join(table) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "label_counts": result.get("label_counts"),
                      "affected_pairs": {k: v["count"] if isinstance(v, dict) else v
                                         for k, v in result.get("affected_pairs", {}).items()},
                      "global_input_blockers": result["global_input_blockers"]}, ensure_ascii=False))
    return 0 if result["status"] == "COMPLETE" else 3


if __name__ == "__main__":
    raise SystemExit(main())
