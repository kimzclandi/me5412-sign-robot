"""Hash-bound reviewed core/window inputs; no implicit legacy trim exceptions."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path

from sign_robot.pair_contract import (
    _v2_fields, _v2_hash, _v2_integer, file_hash, inside, json_hash, read_json,
    read_motion,
)


class WindowApprovalError(ValueError):
    def __init__(self, code, details):
        self.code = code
        self.details = details
        super().__init__(f"{code}: {details}")


@dataclass(frozen=True)
class ApprovedWindow:
    gloss: str
    motion_sha256: str
    frame_count: int
    protected_core_frames: tuple[int, int]
    entry_window_frames: tuple[int, int]
    exit_window_frames: tuple[int, int]
    approval_id: str
    approval_sha256: str
    evidence_path: str
    evidence_sha256: str
    window_version: str
    record_json: str


@dataclass(frozen=True)
class UserProtectedWindow:
    """User protection and computed admissible bounds; never a human review."""
    gloss: str
    motion_sha256: str
    frame_count: int
    protected_core_frames: tuple[int, int]
    entry_window_frames: tuple[int, int]
    exit_window_frames: tuple[int, int]
    protection_id: str
    protection_sha256: str
    window_version: str
    generator_version: str
    record_json: str


def _utc_now():
    return datetime.now(timezone.utc)


def load_window_inputs(root, policy, library, *, now=None):
    if policy["endpoints"]["strategy"] == "user_protected_auto_windows_v1":
        return load_user_protections(root, policy, library)
    return load_window_approvals(root, policy, library, now=now)


def load_user_protections(root, policy, library):
    root = Path(root).resolve()
    config = policy["endpoints"]
    try:
        path = inside(root, config["protection_file"])
        if file_hash(path) != config["protection_bundle_sha256"]:
            raise WindowApprovalError("USER_PROTECTION_BUNDLE_HASH_MISMATCH", str(path))
        bundle = read_json(path)
        _v2_fields(bundle, ("schema_version", "kind", "bundle_id", "window_version", "source_instruction", "records"), "user protection bundle")
        if (type(bundle["schema_version"]) is not int or bundle["schema_version"] != 1
                or bundle["kind"] != "user_protected_intervals_v1" or not bundle["source_instruction"]
                or bundle["window_version"] != config["window_version"]):
            raise WindowApprovalError("INVALID_USER_PROTECTION_VERSION", str(path))
        if not isinstance(bundle["records"], list) or not bundle["records"]:
            raise WindowApprovalError("INVALID_USER_PROTECTION_RECORDS", str(path))
        words = {w["gloss"]: w for w in library["words"]}
        result, ids = {}, set()
        for record in bundle["records"]:
            _v2_fields(record, ("protection_id", "gloss", "motion", "motion_sha256", "frame_count", "fps",
                                "user_interval_text", "user_interval_s", "protected_core_frames", "retiming_allowed",
                                "binding_basis", "prior_video_identity_available"), "user protection record")
            gloss = record["gloss"]
            if gloss not in words or gloss not in policy["scope"]["expected_glosses"]:
                raise WindowApprovalError("UNKNOWN_PROTECTION_GLOSS", str(gloss))
            if (gloss in result or not isinstance(record["protection_id"], str) or not record["protection_id"]
                    or record["protection_id"] in ids):
                raise WindowApprovalError("DUPLICATE_USER_PROTECTION", str(gloss))
            if (record["retiming_allowed"] is not False or type(record["fps"]) is not int or record["fps"] != 30
                    or type(record["prior_video_identity_available"]) is not bool
                    or not isinstance(record["user_interval_text"], str) or not record["user_interval_text"]
                    or not isinstance(record["binding_basis"], str) or not record["binding_basis"]):
                raise WindowApprovalError("INVALID_USER_PROTECTION_SEMANTICS", gloss)
            _v2_hash(record["motion_sha256"], "user-bound motion hash")
            word = words[gloss]
            motion_path = inside(root, record["motion"])
            if (record["motion"] != word["motion"] or record["motion_sha256"] != word["motion_sha256"]
                    or file_hash(motion_path) != record["motion_sha256"]):
                raise WindowApprovalError("STALE_USER_PROTECTION_MOTION", gloss)
            clip = read_motion(motion_path)
            count = _v2_integer(record["frame_count"], "user-bound frame count", minimum=2)
            if count != word["frames"] or count != len(clip["positions"]):
                raise WindowApprovalError("USER_PROTECTION_FRAME_COUNT_MISMATCH", gloss)
            if (not np_all_frame_times_30hz(clip)):
                raise WindowApprovalError("USER_PROTECTION_TIMING_MISMATCH", gloss)
            core = _frame_range(record["protected_core_frames"], count, "user protected core")
            interval = record["user_interval_s"]
            if (not isinstance(interval, list) or len(interval) != 2
                    or any(type(v) not in (int, float) or not math.isfinite(v) for v in interval)
                    or not 0 <= interval[0] <= interval[1] <= float(clip["timestamps_s"][-1])):
                raise WindowApprovalError("INVALID_USER_TIME_RANGE", gloss)
            conservative = (math.floor(interval[0] * 30), math.ceil(interval[1] * 30))
            if core != conservative:
                raise WindowApprovalError("USER_PROTECTION_NOT_CONSERVATIVE", gloss)
            entry, exit_ = (0, min(core[0], count - 2)), (max(core[1], 1), count - 1)
            ids.add(record["protection_id"])
            result[gloss] = UserProtectedWindow(gloss, record["motion_sha256"], count, core, entry, exit_,
                record["protection_id"], json_hash(record), bundle["window_version"], config["generator_version"],
                json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False))
        return result
    except WindowApprovalError:
        raise
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise WindowApprovalError("INVALID_USER_PROTECTION_INPUT", str(exc)) from exc


def np_all_frame_times_30hz(clip):
    # Keep this input loader independent of trajectory generation.
    import numpy as np
    return np.allclose(clip["timestamps_s"], np.arange(len(clip["positions"])) / 30, atol=1e-10, rtol=0)


APPROVAL_FIELDS = (
    "approval_id", "gloss", "motion_sha256", "frame_count", "protected_core_frames",
    "entry_window_frames", "exit_window_frames", "retiming_allowed", "status",
    "reviewer", "reviewed_at", "evidence_path", "evidence_sha256",
)


def approval_review_payload(record):
    """The external review binds all semantics but not its own file hash."""
    return {key: value for key, value in record.items() if key not in ("evidence_path", "evidence_sha256")}


def _aware_time(value, name):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError) as exc:
        raise WindowApprovalError("INVALID_APPROVAL_TIME", name) from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise WindowApprovalError("INVALID_APPROVAL_TIME", f"{name} needs a timezone")
    return result.astimezone(timezone.utc)


def _frame_range(value, count, name):
    if not isinstance(value, list) or len(value) != 2:
        raise WindowApprovalError("INVALID_APPROVAL_RANGE", name)
    for frame in value:
        _v2_integer(frame, name)
    if not 0 <= value[0] <= value[1] < count:
        raise WindowApprovalError("APPROVAL_FRAME_OUT_OF_BOUNDS", name)
    return tuple(value)


def load_window_approvals(root, policy, library, *, now=None):
    """Read actual motions and actual review files, independently of status flags.

    This verifies document integrity and consistency, not a human's identity or
    signature. Formal import must be authorized separately at the P1-8 gate.
    """
    root = Path(root).resolve()
    if policy.get("schema_version") != 2:
        raise WindowApprovalError("UNSUPPORTED_APPROVAL_VERSION", "v2 policy required")
    config = policy["endpoints"]
    if not config.get("approval_file"):
        raise WindowApprovalError("MISSING_APPROVAL_BUNDLE", "No actual group-2 review bundle is configured")
    now = _utc_now() if now is None else now
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise WindowApprovalError("INVALID_APPROVAL_TIME", "comparison time needs a timezone")
    words = {word["gloss"]: word for word in library["words"]}
    try:
        bundle_path = inside(root, config["approval_file"])
        if file_hash(bundle_path) != config["approval_bundle_sha256"]:
            raise WindowApprovalError("APPROVAL_BUNDLE_HASH_MISMATCH", str(bundle_path))
        bundle = read_json(bundle_path)
        _v2_fields(bundle, ("schema_version", "bundle_id", "window_version", "records"), "approval bundle")
        if type(bundle["schema_version"]) is not int or bundle["schema_version"] != 2:
            raise WindowApprovalError("UNSUPPORTED_APPROVAL_VERSION", "bundle schema")
        if not isinstance(bundle["bundle_id"], str) or not bundle["bundle_id"]:
            raise WindowApprovalError("INVALID_APPROVAL_BUNDLE", "a bundle ID is required")
        if bundle["window_version"] != config["window_version"]:
            raise WindowApprovalError("STALE_WINDOW_VERSION", "bundle differs from policy")
        if not isinstance(bundle["records"], list):
            raise WindowApprovalError("INVALID_APPROVAL_BUNDLE", "records must be a list")
        approvals, ids = {}, set()
        for record in bundle["records"]:
            _v2_fields(record, APPROVAL_FIELDS, "approval record", optional=("valid_until", "exceptions"))
            gloss = record["gloss"]
            if not isinstance(gloss, str) or gloss not in words or gloss not in policy["scope"]["expected_glosses"]:
                raise WindowApprovalError("UNKNOWN_APPROVAL_GLOSS", str(gloss))
            if gloss in approvals or record["approval_id"] in ids:
                raise WindowApprovalError("DUPLICATE_APPROVAL", gloss)
            if (record["status"] != "approved" or not isinstance(record["reviewer"], str)
                    or not record["reviewer"].strip() or not isinstance(record["approval_id"], str)
                    or not record["approval_id"].strip() or type(record["retiming_allowed"]) is not bool):
                raise WindowApprovalError("UNAPPROVED_WINDOW", gloss)
            reviewed = _aware_time(record["reviewed_at"], "reviewed_at")
            if reviewed > now:
                raise WindowApprovalError("APPROVAL_FROM_FUTURE", gloss)
            if record.get("valid_until") is not None:
                expires = _aware_time(record["valid_until"], "valid_until")
                if expires < reviewed or now > expires:
                    raise WindowApprovalError("EXPIRED_APPROVAL", gloss)
            _v2_hash(record["motion_sha256"], "reviewed motion hash")
            _v2_hash(record["evidence_sha256"], "review evidence hash")
            word = words[gloss]
            motion_path = inside(root, word["motion"])
            if record["motion_sha256"] != word["motion_sha256"] or file_hash(motion_path) != record["motion_sha256"]:
                raise WindowApprovalError("STALE_MOTION_APPROVAL", gloss)
            count = _v2_integer(record["frame_count"], "approved frame count", minimum=2)
            motion = read_motion(motion_path)
            if count != len(motion["positions"]) or count != word["frames"]:
                raise WindowApprovalError("APPROVAL_FRAME_COUNT_MISMATCH", gloss)
            core = _frame_range(record["protected_core_frames"], count, "protected core")
            entry = _frame_range(record["entry_window_frames"], count, "entry window")
            exit_ = _frame_range(record["exit_window_frames"], count, "exit window")
            if entry[1] > core[0] or exit_[0] < core[1] or entry[1] >= exit_[0]:
                raise WindowApprovalError("WINDOW_REMOVES_PROTECTED_CORE", gloss)
            if entry[1] > count - 2 or exit_[0] < 1:
                raise WindowApprovalError("INSUFFICIENT_BOUNDARY_SAMPLES", gloss)
            evidence_path = inside(root, record["evidence_path"])
            if file_hash(evidence_path) != record["evidence_sha256"]:
                raise WindowApprovalError("APPROVAL_EVIDENCE_HASH_MISMATCH", gloss)
            evidence = read_json(evidence_path)
            _v2_fields(evidence, ("schema_version", "kind", "review"), "approval evidence")
            if (type(evidence["schema_version"]) is not int or evidence["schema_version"] != 2
                    or evidence["kind"] != "group2_core_window_review"
                    or evidence["review"] != approval_review_payload(record)):
                raise WindowApprovalError("APPROVAL_EVIDENCE_CONTENT_MISMATCH", gloss)
            ids.add(record["approval_id"])
            approvals[gloss] = ApprovedWindow(
                gloss, record["motion_sha256"], count, core, entry, exit_, record["approval_id"],
                json_hash(record), record["evidence_path"], record["evidence_sha256"],
                bundle["window_version"], json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False),
            )
        if config["review_status"] == "approved" and set(approvals) != set(policy["scope"]["expected_glosses"]):
            raise WindowApprovalError("INCOMPLETE_FORMAL_APPROVAL_SCOPE", "all 35 words need reviews")
        return approvals
    except WindowApprovalError:
        raise
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise WindowApprovalError("INVALID_APPROVAL_INPUT", str(exc)) from exc


def select_pair_windows(source, target, approvals, library, *, now=None):
    """Enumerate only reviewed endpoints; preserve two occurrences in self-pairs."""
    words = {word["gloss"]: word for word in library["words"]}
    if source not in words or target not in words:
        raise WindowApprovalError("UNKNOWN_GLOSS", f"{source}__{target}")
    selections = {}
    for gloss, role in ((source, "source"), (target, "target")):
        approval = approvals.get(gloss)
        if isinstance(approval, UserProtectedWindow):
            word = words[gloss]
            if approval.motion_sha256 != word["motion_sha256"] or approval.frame_count != word["frames"]:
                raise WindowApprovalError("STALE_USER_PROTECTION_MOTION", gloss)
            window = approval.exit_window_frames if role == "source" else approval.entry_window_frames
            selections[role] = {
                "gloss": gloss, "instance_id": f"{gloss}#{0 if role == 'source' else 1}",
                "allowed_frames": list(range(window[0], window[1] + 1)),
                "protected_core_frames": list(approval.protected_core_frames),
                "motion_sha256": approval.motion_sha256, "frame_count": approval.frame_count,
                "protection_id": approval.protection_id, "protection_sha256": approval.protection_sha256,
                "window_version": approval.window_version, "window_provenance": "algorithm",
                "generator_version": approval.generator_version,
            }
            continue
        if not isinstance(approval, ApprovedWindow):
            raise WindowApprovalError("MISSING_WORD_APPROVAL", gloss)
        current = _utc_now() if now is None else now
        record = json.loads(approval.record_json)
        if current.tzinfo is None or current.utcoffset() is None:
            raise WindowApprovalError("INVALID_APPROVAL_TIME", "selection time needs a timezone")
        if record.get("valid_until") is not None and current > _aware_time(record["valid_until"], "valid_until"):
            raise WindowApprovalError("EXPIRED_APPROVAL", gloss)
        word = words[gloss]
        if approval.motion_sha256 != word["motion_sha256"] or approval.frame_count != word["frames"]:
            raise WindowApprovalError("STALE_MOTION_APPROVAL", gloss)
        window = approval.exit_window_frames if role == "source" else approval.entry_window_frames
        preferred = word["sign_frames"][1 if role == "source" else 0]
        frames = sorted(range(window[0], window[1] + 1), key=lambda frame: (abs(frame - preferred), frame))
        selections[role] = {
            "gloss": gloss, "instance_id": f"{gloss}#{0 if role == 'source' else 1}",
            "allowed_frames": frames, "protected_core_frames": list(approval.protected_core_frames),
            "motion_sha256": approval.motion_sha256, "frame_count": approval.frame_count,
            "approval_id": approval.approval_id, "approval_sha256": approval.approval_sha256,
            "evidence_path": approval.evidence_path, "evidence_sha256": approval.evidence_sha256,
            "window_version": approval.window_version,
        }
    return {"pair_id": f"{source}__{target}", "self_pair": source == target,
            "word_occurrences": 2, **selections}
