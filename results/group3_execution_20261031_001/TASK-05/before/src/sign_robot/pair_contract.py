"""Frozen inputs and numerical contracts for the all-pairs development scan.

This module has no language-model dependency. JSON hashes describe content;
NPZ file hashes and canonical numerical hashes deliberately have different jobs.
"""
from __future__ import annotations

import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

import numpy as np

from sign_robot.motion import ROOT, validate_motion

STATUSES = (
    "NOT_RUN", "PASS_SIM", "SOURCE_NEAR", "BLOCKED_ENDPOINT", "BLOCKED_INPUT",
    "FAILED_SEARCH", "FAILED_QUALITY", "TIMEOUT", "ERROR",
)
QUALITY_LIMITS = (
    "velocity_jump_arm_rad_s", "velocity_jump_finger_rad_s",
    "acceleration_jump_arm_rad_s2", "acceleration_jump_finger_rad_s2",
    "peak_acceleration_rad_s2", "peak_jerk_rad_s3", "jerk_integral_rad2_s5",
    "maximum_transition_duration_s",
)
MOTION_KEYS = ("timestamps_s", "joint_names", "positions")


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                       separators=(",", ":")) + "\n").encode("utf-8")


def json_hash(value):
    return hashlib.sha256(json_bytes(value)).hexdigest()


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def inside(root, relative):
    """Resolve a package-relative path without escaping its declared root."""
    root, relative = Path(root).resolve(), Path(relative)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Expected a relative path inside {root}: {relative}")
    result = (root / relative).resolve()
    if not result.is_relative_to(root):
        raise ValueError(f"Path escapes {root}: {relative}")
    return result


def atomic_bytes(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.",
                                         suffix=".part", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def atomic_json(path, value):
    atomic_bytes(path, json_bytes(value))


def atomic_motion(path, motion):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.",
                                         suffix=".part", delete=False) as stream:
            temporary = Path(stream.name)
            np.savez_compressed(stream, **{key: motion[key] for key in MOTION_KEYS})
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def read_motion(path):
    with np.load(path, allow_pickle=False) as source:
        result = {key: source[key].copy() for key in MOTION_KEYS}
    validate_motion(result)
    if result["joint_names"].dtype.kind not in "US":
        raise ValueError("Named joints must be strings")
    return result


def canonical_array_hash(motion):
    """UTF-8 joint names, then C-order little-endian float64 time/position arrays."""
    validate_motion(motion)
    digest = hashlib.sha256()
    digest.update(json_bytes({"schema": 1, "joint_names": [str(n) for n in motion["joint_names"]]}))
    for key in ("timestamps_s", "positions"):
        values = np.asarray(motion[key], dtype="<f8", order="C").copy()
        values[values == 0] = 0.0  # Canonicalise negative zero, too.
        digest.update(json_bytes({"field": key, "dtype": "<f8", "shape": list(values.shape)}))
        digest.update(values.tobytes(order="C"))
    return digest.hexdigest()


def load_policy(path):
    policy = read_json(path)
    if policy.get("schema_version") != 1:
        raise ValueError("Unsupported transition policy schema")
    scope = policy["scope"]
    glosses = scope["expected_glosses"]
    if (not glosses or len(set(glosses)) != len(glosses)
            or any(not isinstance(g, str) or not re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", g)
                   for g in glosses)):
        raise ValueError("Policy must freeze a unique, ordered gloss list")
    if scope.get("include_self") is not True:
        raise ValueError("Excluding self-pairs requires a separately versioned scope change")
    if policy["planner"]["method"] != "direct_minimum_jerk_v1":
        raise ValueError("This first-stage runner implements direct_minimum_jerk_v1 only")
    if policy["endpoints"]["strategy"] != "original_sign_frames":
        raise ValueError("This first-stage runner preserves original sign endpoints")
    if policy["endpoints"].get("approved_windows"):
        raise ValueError("Approved window selection is not implemented in this development baseline")
    if policy["fps"] != 30 or policy["joint_count"] != 53:
        raise ValueError("This development contract requires the delivered 30 fps, 53-joint library")
    if policy["planner"].get("max_candidates") != 1:
        raise ValueError("The direct baseline has exactly one candidate per valid pair")
    for proposal in policy["endpoints"]["legacy_research_endpoints"]:
        if (proposal["gloss"] not in glosses or proposal["role"] not in ("source", "target")
                or isinstance(proposal["frame"], bool) or not isinstance(proposal["frame"], int)
                or proposal["frame"] < 0 or not re.fullmatch(r"[0-9a-f]{64}", proposal["motion_sha256"])):
            raise ValueError("A research endpoint requires a valid gloss, role, frame and exact motion hash")
    for value in (policy["fps"], policy["planner"]["minimum_duration_s"],
                  policy["planner"]["wall_time_s"], policy["validation"]["maximum_step_rad"],
                  *policy["constraints"].values()):
        if isinstance(value, bool) or not np.isfinite(value) or value <= 0:
            raise ValueError("Policy thresholds, rates and resource limits must be finite and positive")
    if not isinstance(policy["planner"]["max_collision_samples"], int) or policy["planner"]["max_collision_samples"] < 2:
        raise ValueError("A finite collision-sample work budget is required")
    if policy["validation"]["dense_factors"] != [1, 2, 4]:
        raise ValueError("The first-stage verification contract requires 1x, 2x and 4x sampling")
    if policy["quality"]["derivative_window_frames"] < 3:
        raise ValueError("Boundary derivatives need at least three source samples")
    if policy["quality"]["freeze_status"] not in ("pending", "frozen"):
        raise ValueError("Unknown quality freeze status")
    for key in QUALITY_LIMITS:
        value = policy["quality"]["limits"][key]
        if value is not None and (isinstance(value, bool) or not np.isfinite(value) or value < 0):
            raise ValueError(f"Invalid quality limit: {key}")
        if policy["quality"]["freeze_status"] == "frozen" and value is None:
            raise ValueError(f"A frozen policy cannot omit {key}")
    return policy


def pair_universe(glosses):
    return [{"pair_id": f"{source}__{target}", "source_gloss": source,
             "target_gloss": target, "self_pair": source == target}
            for source in glosses for target in glosses]


def run_directory(results_root, run_id):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", run_id):
        raise ValueError("Invalid run_id")
    return inside(results_root, run_id)


def environment_record():
    packages = {}
    for name in ("numpy", "scipy", "mujoco", "Pillow", "imageio", "imageio-ffmpeg"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    result = {"python": platform.python_version(), "implementation": platform.python_implementation(),
              "system": platform.system(), "machine": platform.machine(), "packages": packages,
              "threads": {name: os.environ.get(name) for name in
                          ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")}}
    return {**result, "environment_id": json_hash(result)}


def freeze_library(root, policy):
    """Hash delivered inputs, including actual mesh bytes, without importing an encoder."""
    root = Path(root).resolve()
    path = root / "motions/hospital_v1_motions.json"
    library = read_json(path)
    words = library["glosses"]
    if [word["gloss"] for word in words] != policy["scope"]["expected_glosses"]:
        raise ValueError("Library gloss order/scope differs from the frozen policy")
    if library["fps"] != policy["fps"]:
        raise ValueError("Library fps differs from the policy")
    info = read_json(root / "assets/robot/model_info.json")
    inventory, errors, clips, entries = {}, [], {}, []

    def register(relative, expected=None):
        target = inside(root, relative)
        actual = file_hash(target) if target.is_file() else None
        inventory[str(relative)] = {"sha256": actual, "bytes": target.stat().st_size if actual else None}
        if actual is None:
            errors.append({"code": "MISSING_RESOURCE", "path": str(relative)})
        elif expected is not None and actual != expected:
            errors.append({"code": "RESOURCE_HASH_MISMATCH", "path": str(relative)})
        return actual

    register("motions/hospital_v1_motions.json")
    vocab = "data/mocap/" + library["vocab_file"]
    register(vocab, library["vocab_sha256"])
    for relative in ("assets/robot/scene.xml", "assets/robot/imported.xml", "assets/robot/g1_fixed.urdf",
                     "assets/robot/model_info.json", "assets/robot/upstream_manifest.json",
                     "motions/studio_galt_v1/index.json", "motions/wlasl_video_v1/index.json",
                     "config/transition_development_pairs.json"):
        register(relative)
    for asset in read_json(root / "assets/robot/upstream_manifest.json")["files"]:
        register("assets/robot/vendor/" + asset["file"], asset["sha256"])
    # Hash the actual file dependencies named by the scene, too. An added mesh
    # must not silently escape the upstream manifest's frozen inventory.
    scene = ET.parse(root / "assets/robot/scene.xml").getroot()
    compiler = scene.find("compiler")
    for node in scene.iter():
        if node.tag == "include":
            errors.append({"code": "UNSUPPORTED_SCENE_INCLUDE", "path": node.get("file")})
        filename = node.get("file")
        if filename:
            asset_dir = ""
            if compiler is not None and node.tag in ("mesh", "texture"):
                asset_dir = compiler.get("meshdir" if node.tag == "mesh" else "texturedir", "")
            relative = str(Path("assets/robot") / asset_dir / filename)
            if relative not in inventory:
                register(relative)
    for word in words:
        entry = dict(word)
        issues = []
        if not word.get("motion_ready") or not word.get("motion"):
            entry.update(input_errors=["MOTION_NOT_READY"], motion_sha256=None, metadata_sha256=None)
            entries.append(entry)
            continue
        motion_path = inside(root, word["motion"])
        entry["motion_sha256"] = register(word["motion"])
        entry["metadata_sha256"] = register(str(Path(word["motion"]).with_suffix(".json")))
        try:
            motion = read_motion(motion_path)
            if len(motion["joint_names"]) != policy["joint_count"]:
                raise ValueError("Unexpected joint count")
            if not np.allclose(np.diff(motion["timestamps_s"]), 1 / policy["fps"], rtol=0, atol=1e-10):
                raise ValueError("Expected the frozen sampling period")
            c0, c1 = word["core_frames"]
            s0, s1 = word["sign_frames"]
            if any(isinstance(f, bool) or not isinstance(f, int) for f in (c0, c1, s0, s1)) or not (
                    0 <= c0 <= s0 < s1 <= c1 < len(motion["positions"])):
                raise ValueError("Invalid core/sign frame hints")
            clips[word["gloss"]] = motion
            entry.update(frames=len(motion["positions"]), canonical_array_hash=canonical_array_hash(motion))
        except (OSError, KeyError, ValueError, TypeError) as exc:
            issues.append(f"INVALID_MOTION: {exc}")
        entry["input_errors"] = issues
        entries.append(entry)
    names = next((clip["joint_names"].tolist() for clip in clips.values()), [])
    for gloss, clip in clips.items():
        if clip["joint_names"].tolist() != names:
            errors.append({"code": "JOINT_ORDER_MISMATCH", "gloss": gloss})
    code_paths = sorted((root / "src/sign_robot").glob("*.py")) + [
        root / "scripts" / name for name in
        ("plan_all_pairs.py", "verify_all_pairs.py", "summarize_all_pairs.py", "freeze_all_pairs_inputs.py")]
    code_files = {str(p.relative_to(root)): file_hash(p) for p in code_paths if p.is_file()}
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True,
                            capture_output=True, check=False).stdout.strip() or "unversioned"
    model_files = {p: item for p, item in inventory.items() if p.startswith("assets/robot/")}
    environment = environment_record()
    result = {"schema_version": 1, "library": policy["scope"]["library"], "words": entries,
              "word_count": len(words), "pair_count": len(words) ** 2,
              "non_self_pair_count": len(words) * (len(words) - 1), "self_pair_count": len(words),
              "joint_names": names, "couplings": info["couplings"],
              "independent_joint_names": [n for n in names if n not in {c["child"] for c in info["couplings"]}],
              "files": inventory, "model_hash": json_hash(model_files),
              "input_errors": errors, "code_commit": commit, "code_files": code_files,
              "code_hash": json_hash(code_files), "environment": environment}
    result["library_version"] = policy["scope"]["library"] + "@" + json_hash(
        {"words": entries, "files": inventory, "joint_names": names, "couplings": info["couplings"]})
    return result, clips


def run_identity(library, policy):
    value = {"library_version": library["library_version"], "model_hash": library["model_hash"],
             "code_commit": library["code_commit"], "code_hash": library["code_hash"],
             "policy_hash": json_hash(policy), "environment_id": library["environment"]["environment_id"]}
    return {**value, "identity_hash": json_hash(value)}


def rate_limits(names, policy):
    limits = policy["constraints"]
    return np.array([limits["finger_speed_rad_s"] if str(n).startswith(("L_", "R_")) else
                     limits["arm_speed_rad_s"] if any(s in str(n) for s in ("shoulder", "elbow", "wrist")) else
                     limits["fixed_joint_speed_rad_s"] for n in names])


def coordinate_errors(positions, names, model, couplings):
    positions = np.asarray(positions)
    index = {str(n): i for i, n in enumerate(names)}
    lower = np.array([model.joint(str(n)).range[0] for n in names])
    upper = np.array([model.joint(str(n)).range[1] for n in names])
    limited = np.array([bool(model.joint(str(n)).limited[0]) for n in names])
    errors = np.maximum(np.maximum(lower - positions, positions - upper), 0)[:, limited]
    coupling = [np.abs(positions[:, index[c["child"]]] - c["offset"] -
                       c["multiplier"] * positions[:, index[c["parent"]]]) for c in couplings]
    return {"joint_limit_error": float(errors.max(initial=0)),
            "coupling_error": float(np.max(coupling)) if coupling else 0.0}


def boundary_derivatives(clip, frame, side, window):
    start, end = (max(0, frame - window + 1), frame + 1) if side == "source" else (
        frame, min(len(clip["positions"]), frame + window))
    t = clip["timestamps_s"][start:end] - clip["timestamps_s"][frame]
    if len(t) < 3:
        raise ValueError("Insufficient one-sided boundary derivative samples")
    fit = np.linalg.lstsq(np.column_stack([np.ones(len(t)), t, t * t]),
                          clip["positions"][start:end], rcond=None)[0]
    return {"velocity": fit[1].tolist(), "acceleration": (2 * fit[2]).tolist(),
            "frames": [start, end - 1], "method": "one-sided quadratic least squares; no filter",
            "units": {"velocity": "rad/s", "acceleration": "rad/s^2"}}


def quintic_samples(a, b, intervals, *, factor=1):
    u = np.linspace(0, 1, intervals * factor + 1)[:, None]
    q = a + (10 * u**3 - 15 * u**4 + 6 * u**5) * (b - a)
    q[0], q[-1] = a, b
    return q


def linear_dense(q, factor, maximum_step_rad):
    pieces = [q[:1]]
    for left, right in zip(q, q[1:]):
        count = max(factor, int(np.ceil(np.max(np.abs(right - left)) / maximum_step_rad)))
        pieces.append(np.linspace(left, right, count + 1)[1:])
    return np.vstack(pieces)


def acceptance_pending(policy):
    reasons = []
    if policy["quality"]["freeze_status"] != "frozen":
        reasons.append("QUALITY_THRESHOLDS_NOT_FROZEN")
    if policy["endpoints"]["review_status"] != "approved":
        reasons.append("SEMANTIC_CORE_AND_WINDOWS_UNCONFIRMED")
    # This baseline has no approved-window/core contract yet, even if someone
    # merely changes the review_status string in a development policy.
    reasons.append("APPROVED_CORE_CONTRACT_NOT_IMPLEMENTED")
    return reasons
