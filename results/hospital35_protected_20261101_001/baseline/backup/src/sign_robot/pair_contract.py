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
FULL_CLIP_METHOD_V2 = "finite_difference_30hz_and_analytic_connector_v2"
# v3 scope: acceleration/jerk limits skip replay frames inside protected cores;
# those cores are checked instead for unchanged poses and relative timing.
TRANSITION_SCOPE_METHOD_V3 = "finite_difference_30hz_outside_protected_cores_and_analytic_connector_v3"
# v2 cut generator ranks cut pairs by the squared-jerk integral of the
# retained non-protected source edges before boundary speed.
EDGE_AWARE_CUT_GENERATOR = "protected_cut_search_v2"
# v3 cut generator keeps v2 ranking and adds lift-off finger arrival for
# target entries whose fingers are leaving a joint limit.
LIFT_OFF_ARRIVAL_GENERATOR = "protected_cut_search_v3"
EDGE_AWARE_CUT_GENERATORS = (EDGE_AWARE_CUT_GENERATOR, LIFT_OFF_ARRIVAL_GENERATOR)
CUT_GENERATOR_VERSIONS = ("protected_cut_search_v1", *EDGE_AWARE_CUT_GENERATORS)
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


def load_policy(path, *, supported_versions=(1,)):
    policy = read_json(path)
    version = policy.get("schema_version")
    if type(version) is not int or version not in supported_versions:
        raise ValueError("Unsupported transition policy schema for this entry point")
    if version == 2:
        return validate_policy_v2(policy)
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
    if policy["schema_version"] == 2:
        register(policy["contract"]["path"], policy["contract"]["sha256"])
        if policy["endpoints"]["strategy"] == "user_protected_auto_windows_v1":
            register(policy["endpoints"]["protection_file"], policy["endpoints"]["protection_bundle_sha256"])
        if policy["endpoints"]["approval_file"] is not None:
            register(policy["endpoints"]["approval_file"], policy["endpoints"]["approval_bundle_sha256"])
            try:
                bundle = read_json(inside(root, policy["endpoints"]["approval_file"]))
                for record in bundle["records"]:
                    register(record["evidence_path"], record["evidence_sha256"])
            except (OSError, KeyError, TypeError, ValueError) as exc:
                errors.append({"code": "INVALID_APPROVAL_BUNDLE", "details": str(exc)})
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
    if policy["schema_version"] == 2:
        code_paths += sorted((root / "tests").glob("*.py"))
        if policy["endpoints"]["strategy"] == "user_protected_auto_windows_v1":
            code_paths += [root / 'scripts' / name for name in
                           ('screen_user_protected_cuts.py','render_user_protected_pairs.py')]
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
    if policy.get("schema_version") == 2:
        reasons = ["V2_FORMAL_ACCEPTANCE_NOT_ENABLED"]
        if policy["quality"]["freeze_status"] != "frozen":
            reasons.append("QUALITY_THRESHOLDS_NOT_FROZEN")
        if policy["validation"]["approval_status"] != "approved":
            reasons.append("COLLISION_SCOPE_NOT_APPROVED")
        if policy["endpoints"]["review_status"] != "approved":
            reasons.append("ALGORITHM_WINDOWS_NOT_HUMAN_REVIEWED" if policy["endpoints"]["strategy"] == "user_protected_auto_windows_v1"
                           else "SEMANTIC_CORE_AND_WINDOWS_UNCONFIRMED")
        return reasons
    reasons = []
    if policy["quality"]["freeze_status"] != "frozen":
        reasons.append("QUALITY_THRESHOLDS_NOT_FROZEN")
    if policy["endpoints"]["review_status"] != "approved":
        reasons.append("SEMANTIC_CORE_AND_WINDOWS_UNCONFIRMED")
    # This baseline has no approved-window/core contract yet, even if someone
    # merely changes the review_status string in a development policy.
    reasons.append("APPROVED_CORE_CONTRACT_NOT_IMPLEMENTED")
    return reasons


# v2 is opt-in. Legacy CLI callers deliberately keep load_policy's (1,) default
# until a runner and verifier for this representation are implemented together.
V2_REPRESENTATION = "piecewise_polynomial_v2"
V2_METHODS = ("direct", "neutral", "ik_via1", "ik_via2", "retract_approach", "rrt_connect")
V2_FINGER_STRATEGIES = ("synchronous", "early", "late")
V2_IDENTITY_KEYS = ("library_version", "model_hash", "code_commit", "code_hash", "policy_hash", "environment_id", "identity_hash")


def _v2_number(value, label, *, minimum=None, positive=False):
    if type(value) not in (int, float) or not np.isfinite(value):
        raise ValueError(f"{label} must be a finite number, not a boolean")
    if (minimum is not None and value < minimum) or (positive and value <= 0):
        raise ValueError(f"{label} is outside its permitted range")
    return value


def _v2_integer(value, label, *, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{label} must be an integer >= {minimum}")
    return value


def _v2_hash(value, label):
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{label} requires a lowercase SHA-256")
    return value


def _v2_fields(value, required, label, *, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise ValueError(f"{label} fields differ from the versioned contract")


def _v2_vector(value, count, label):
    if not isinstance(value, list) or len(value) != count:
        raise ValueError(f"{label} must have {count} coordinates")
    for item in value:
        _v2_number(item, label)
    return np.asarray(value, dtype=float)


def validate_work_budget_v2(budget):
    counts = ("max_candidates", "max_collision_samples", "max_nodes", "max_segments", "max_time_attempts")
    _v2_fields(budget, (*counts, "wall_time_s"), "work budget")
    for name in counts:
        _v2_integer(budget[name], name, minimum=1)
    _v2_number(budget["wall_time_s"], "wall_time_s", positive=True)
    return budget


def validate_policy_v2(policy):
    """Validate finite development proposals, without creating human approval."""
    _v2_fields(policy, ("schema_version", "policy_id", "fps", "joint_count", "scope", "contract", "planner",
                       "constraints", "endpoints", "validation", "quality", "finger_strategies",
                       "selection_rule", "formal_acceptance_enabled", "pending_decisions"), "v2 policy")
    if type(policy["schema_version"]) is not int or policy["schema_version"] != 2:
        raise ValueError("Expected v2 policy")
    json_bytes(policy)  # Reject non-JSON and nonfinite values anywhere.
    scope = policy["scope"]
    glosses = scope["expected_glosses"]
    if (scope.get("library") != "hospital_v1" or scope.get("include_self") is not True
            or not isinstance(glosses, list) or len(glosses) != 35
            or any(not isinstance(g, str) or re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", g) is None for g in glosses)
            or len(set(glosses)) != 35):
        raise ValueError("v2 requires all 35 frozen hospital words including self-pairs")
    if type(policy["fps"]) is not int or policy["fps"] != 30 or type(policy["joint_count"]) is not int or policy["joint_count"] != 53:
        raise ValueError("v2 requires 30 Hz and 53 named coordinates")
    if policy["formal_acceptance_enabled"] is not False:
        raise ValueError("Formal v2 acceptance is not implemented; keep it disabled")
    _v2_fields(policy["contract"], ("path", "sha256"), "contract reference")
    inside(ROOT, policy["contract"]["path"])
    _v2_hash(policy["contract"]["sha256"], "contract hash")
    planner = policy["planner"]
    _v2_fields(planner, ("method", "methods", "seed", "minimum_duration_s", "budget", "rrt"), "planner")
    if planner["method"] != "multi_candidate_v2" or planner["methods"] != list(V2_METHODS):
        raise ValueError("Unknown or incomplete v2 method dispatch")
    _v2_integer(planner["seed"], "seed")
    _v2_number(planner["minimum_duration_s"], "minimum duration", positive=True)
    validate_work_budget_v2(planner["budget"])
    rrt = planner["rrt"]
    _v2_fields(rrt, ("step_rad", "edge_resolution_rad", "goal_bias", "wall_time_s"), "RRT")
    for key in ("step_rad", "edge_resolution_rad", "wall_time_s"):
        _v2_number(rrt[key], key, positive=True)
    _v2_number(rrt["goal_bias"], "goal_bias", minimum=0)
    if rrt["goal_bias"] > 1 or rrt["wall_time_s"] > planner["budget"]["wall_time_s"]:
        raise ValueError("RRT bias/time must fit the pair budget")
    constraints = policy["constraints"]
    required = ("min_clearance_m", "position_tolerance_rad", "joint_limit_tolerance_rad", "coupling_tolerance_rad",
                "arm_speed_rad_s", "finger_speed_rad_s", "fixed_joint_speed_rad_s", "speed_tolerance_rad_s")
    _v2_fields(constraints, required, "constraints")
    for key, value in constraints.items():
        _v2_number(value, key, positive=True)
    if constraints["min_clearance_m"] < 0.002 or constraints["arm_speed_rad_s"] > 15 or constraints["finger_speed_rad_s"] > 10:
        raise ValueError("v2 cannot relax the delivered clearance or speed caps")
    endpoints = policy["endpoints"]
    automatic = endpoints["strategy"] == "user_protected_auto_windows_v1"
    auto_fields = ("protection_file", "protection_bundle_sha256", "generator_version") if automatic else ()
    _v2_fields(endpoints, ("strategy", "window_version", "review_status", "approval_file", "approval_bundle_sha256", *auto_fields), "endpoints")
    if endpoints["strategy"] not in ("approved_core_windows_v2", "user_protected_auto_windows_v1") or endpoints["review_status"] not in ("pending", "approved"):
        raise ValueError("Unsupported endpoint contract")
    if automatic:
        if (endpoints["review_status"] != "pending" or endpoints["approval_file"] is not None
                or endpoints["approval_bundle_sha256"] is not None or endpoints["generator_version"] not in CUT_GENERATOR_VERSIONS):
            raise ValueError("Algorithm windows cannot claim human approval")
        inside(ROOT, endpoints["protection_file"])
        _v2_hash(endpoints["protection_bundle_sha256"], "user protection bundle hash")
    if not isinstance(endpoints["window_version"], str) or not endpoints["window_version"]:
        raise ValueError("An endpoint-window version is required")
    if endpoints["approval_file"] is not None:
        inside(ROOT, endpoints["approval_file"])
        _v2_hash(endpoints["approval_bundle_sha256"], "approval bundle hash")
    elif endpoints["approval_bundle_sha256"] is not None or endpoints["review_status"] == "approved":
        raise ValueError("Approval requires an actual hash-bound bundle")
    validation = policy["validation"]
    _v2_fields(validation, ("dense_factors", "maximum_step_rad", "maximum_time_step_s", "max_sampled_poses",
                            "max_native_collision_calls", "max_subdivision_depth", "wall_time_s", "approval_status",
                            "approval_evidence", "continuous_collision_certified", "scope"), "validation")
    if (validation["dense_factors"] != [1, 2, 4] or validation["continuous_collision_certified"] is not False
            or validation["scope"] != "native_moving_non_same_hand_v2"
            or validation["approval_status"] not in ("pending", "approved")):
        raise ValueError("Unknown or incomplete collision coverage")
    for key in ("maximum_step_rad", "maximum_time_step_s", "wall_time_s"):
        _v2_number(validation[key], key, positive=True)
    if validation["maximum_step_rad"] > 0.04 or validation["maximum_time_step_s"] > 1 / 120:
        raise ValueError("v2 sampling cannot coarsen the proposed grid")
    for key in ("max_sampled_poses", "max_native_collision_calls", "max_subdivision_depth"):
        _v2_integer(validation[key], key, minimum=1)
    quality = policy["quality"]
    _v2_fields(quality, ("freeze_status", "limits", "approval_evidence", "boundary_method", "full_clip_method"), "quality")
    if (quality["freeze_status"] not in ("pending", "frozen")
            or quality["boundary_method"] != "linear_replay_one_sided_v2"
            or quality["full_clip_method"] not in (FULL_CLIP_METHOD_V2, TRANSITION_SCOPE_METHOD_V3)):
        raise ValueError("Unknown v2 metric definition")
    if quality["full_clip_method"] == TRANSITION_SCOPE_METHOD_V3 and not automatic:
        raise ValueError("Transition-only quality scope requires user-protected cores")
    if automatic and endpoints["generator_version"] in EDGE_AWARE_CUT_GENERATORS and quality["full_clip_method"] != TRANSITION_SCOPE_METHOD_V3:
        raise ValueError("Edge-aware cut ranking is defined only for transition-only quality scope")
    _v2_fields(quality["limits"], QUALITY_LIMITS, "quality limits")
    for key, value in quality["limits"].items():
        _v2_number(value, key, minimum=0)
    if quality["freeze_status"] == "frozen" and not quality["approval_evidence"]:
        raise ValueError("Frozen quality requires approval evidence")
    if validation["approval_status"] == "approved" and not validation["approval_evidence"]:
        raise ValueError("Approved collision scope requires approval evidence")
    selection_rule = "numerical_pass_then_smoothness_total_duration_v1" if automatic else "numerical_pass_then_duration_method_hash_v2"
    if (policy["finger_strategies"] != list(V2_FINGER_STRATEGIES)
            or policy["selection_rule"] != selection_rule):
        raise ValueError("Unknown finger or candidate-selection version")
    return policy


def polynomial_boundary_v2(segment, endpoint):
    """Read declared normalized-u coefficients; no planner is invoked."""
    if endpoint not in ("start", "end"):
        raise ValueError("Polynomial endpoint must be start or end")
    coefficients = np.asarray(segment["coefficients"], dtype=float)
    duration = segment["end_time_s"] - segment["start_time_s"]
    u = 0.0 if endpoint == "start" else 1.0
    result = {}
    for order, name in enumerate(("position", "velocity", "acceleration")):
        derivative = np.polynomial.polynomial.polyder(coefficients, m=order, axis=1)
        result[name] = (derivative @ (u ** np.arange(derivative.shape[1])) / duration**order).tolist()
    return result


def validate_trajectory_v2(trajectory):
    """Structural and mathematical v2 validation; not geometry or approval."""
    required = ("schema_version", "representation", "pair_id", "fps", "joint_names", "word_instances",
                "segments", "finger_strategy", "planner", "boundary", "identity")
    _v2_fields(trajectory, required, "trajectory", optional=("endpoint_mode",))
    automatic = trajectory.get("endpoint_mode") == "user_protected_auto_windows_v1"
    if "endpoint_mode" in trajectory and not automatic:
        raise ValueError("Unknown endpoint mode")
    if type(trajectory["schema_version"]) is not int or trajectory["schema_version"] != 2 or trajectory["representation"] != V2_REPRESENTATION:
        raise ValueError("Unsupported saved trajectory representation")
    json_bytes(trajectory)
    names = trajectory["joint_names"]
    if (not isinstance(names, list) or len(names) != 53 or any(not isinstance(n, str) or not n for n in names)
            or len(set(names)) != 53 or type(trajectory["fps"]) is not int or trajectory["fps"] != 30):
        raise ValueError("Expected 53 distinct named coordinates at 30 Hz")
    identity = trajectory["identity"]
    _v2_fields(identity, V2_IDENTITY_KEYS, "trajectory identity")
    if not isinstance(identity["library_version"], str) or not identity["library_version"].startswith("hospital_v1@"):
        raise ValueError("A frozen hospital library identity is required")
    _v2_hash(identity["library_version"].split("@", 1)[1], "library hash")
    for key in ("model_hash", "policy_hash", "code_hash", "environment_id", "identity_hash"):
        _v2_hash(identity[key], key)
    if not isinstance(identity["code_commit"], str) or re.fullmatch(r"[0-9a-f]{40}", identity["code_commit"]) is None:
        raise ValueError("A concrete Git commit is required in v2 provenance")
    if json_hash({k: v for k, v in identity.items() if k != "identity_hash"}) != identity["identity_hash"]:
        raise ValueError("Trajectory identity hash differs from its content")
    instances = trajectory["word_instances"]
    if not isinstance(instances, list) or len(instances) != 2:
        raise ValueError("A pair must retain two explicit word instances")
    ids = set()
    for word in instances:
        reference_fields = ("protection_id", "protection_sha256", "window_provenance") if automatic else ("approval_id", "approval_sha256")
        _v2_fields(word, ("instance_id", "gloss", "motion_sha256", "source_frames", "protected_core_frames", *reference_fields), "word instance")
        reference_id = "protection_id" if automatic else "approval_id"
        reference_hash = "protection_sha256" if automatic else "approval_sha256"
        if automatic and word["window_provenance"] != "algorithm":
            raise ValueError("Algorithm windows cannot claim human approval")
        if (not isinstance(word["instance_id"], str) or not word["instance_id"] or word["instance_id"] in ids
                or not isinstance(word["gloss"], str) or re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", word["gloss"]) is None
                or not isinstance(word[reference_id], str) or not word[reference_id]):
            raise ValueError("Word instances require unique IDs, glosses and approval references")
        ids.add(word["instance_id"])
        for key in ("motion_sha256", reference_hash):
            _v2_hash(word[key], key)
        for key in ("source_frames", "protected_core_frames"):
            frames = word[key]
            if not isinstance(frames, list) or len(frames) != 2:
                raise ValueError("Word frames must be inclusive ranges")
            for frame in frames:
                _v2_integer(frame, key)
        s, e = word["source_frames"]
        c0, c1 = word["protected_core_frames"]
        if not 0 <= s <= c0 <= c1 <= e or s == e:
            raise ValueError("Mapped word slices must preserve the entire protected core")
    if trajectory["pair_id"] != "__".join(w["gloss"] for w in instances):
        raise ValueError("Pair identity differs from its ordered word occurrences")
    planner = trajectory["planner"]
    _v2_fields(planner, ("method", "method_version", "seed", "budget"), "trajectory planner")
    if planner["method"] not in V2_METHODS or type(planner["method_version"]) is not int or planner["method_version"] != 2:
        raise ValueError("Unsupported v2 candidate method/version")
    _v2_integer(planner["seed"], "seed")
    validate_work_budget_v2(planner["budget"])
    strategy = trajectory["finger_strategy"]
    _v2_fields(strategy, ("name", "version", "start_fraction", "end_fraction"), "finger strategy")
    if strategy["name"] not in V2_FINGER_STRATEGIES or type(strategy["version"]) is not int or strategy["version"] != 2:
        raise ValueError("Unsupported finger strategy")
    start = _v2_number(strategy["start_fraction"], "finger start", minimum=0)
    end = _v2_number(strategy["end_fraction"], "finger end", positive=True)
    expected = {"synchronous": (0.0, 1.0), "early": (0.0, 0.65), "late": (0.35, 1.0)}[strategy["name"]]
    if not 0 <= start < end <= 1 or (start, end) != expected:
        raise ValueError("Finger phases must match their explicit strategy version")
    segments = trajectory["segments"]
    if not isinstance(segments, list) or not 3 <= len(segments) <= planner["budget"]["max_segments"] + 2:
        raise ValueError("A finite nonempty connector and two word slices are required")
    previous_end = 0.0
    polynomials = []
    for index, segment in enumerate(segments):
        kind = segment.get("kind") if isinstance(segment, dict) else None
        _v2_number(segment.get("start_time_s") if isinstance(segment, dict) else None, "segment start", minimum=0)
        _v2_number(segment.get("end_time_s"), "segment end", positive=True)
        start, end = segment["start_time_s"], segment["end_time_s"]
        if not np.isclose(start, previous_end, atol=1e-10, rtol=0) or end <= start:
            raise ValueError("Segments must form a positive, contiguous timeline from zero")
        previous_end = end
        if index in (0, len(segments) - 1):
            _v2_fields(segment, ("kind", "start_time_s", "end_time_s", "word_instance_id", "source_frames",
                                 "interpolation", "time_scale"), "word segment")
            word = instances[0 if index == 0 else 1]
            if (kind != "source_slice_v2" or segment["word_instance_id"] != word["instance_id"]
                    or segment["source_frames"] != word["source_frames"] or segment["interpolation"] != "linear"
                    or type(segment["time_scale"]) not in (int, float) or segment["time_scale"] != 1.0):
                raise ValueError("Word mapping or original timing changed")
            for frame in segment["source_frames"]:
                _v2_integer(frame, "segment source frame")
            if not np.isclose(end - start, (word["source_frames"][1] - word["source_frames"][0]) / 30, atol=1e-10, rtol=0):
                raise ValueError("Word slice duration differs from original replay")
        else:
            _v2_fields(segment, ("kind", "start_time_s", "end_time_s", "coefficients"), "polynomial segment")
            if kind != "polynomial_v2" or not isinstance(segment["coefficients"], list) or len(segment["coefficients"]) != 53:
                raise ValueError("Unsupported segment representation or coordinate count")
            for row in segment["coefficients"]:
                _v2_vector(row, 6, "normalized-u quintic coefficients")
            if polynomials:
                left, right = polynomial_boundary_v2(polynomials[-1], "end"), polynomial_boundary_v2(segment, "start")
                if any(not np.allclose(left[k], right[k], atol=1e-7, rtol=0) for k in left):
                    raise ValueError("Connector segments must preserve position, velocity and acceleration continuity")
            polynomials.append(segment)
    _v2_fields(trajectory["boundary"], ("start", "end", "method"), "boundary")
    intervals = (polynomials[-1]["end_time_s"] - polynomials[0]["start_time_s"]) * 30
    if not np.isclose(intervals, round(intervals), atol=1e-8, rtol=0):
        raise ValueError("The complete connector must fit the 30 Hz playback grid")
    if trajectory["boundary"]["method"] != "linear_replay_one_sided_v2":
        raise ValueError("Unknown boundary derivative method")
    for endpoint, segment in (("start", polynomials[0]), ("end", polynomials[-1])):
        declared = trajectory["boundary"][endpoint]
        _v2_fields(declared, ("position", "velocity", "acceleration"), "boundary state")
        actual = polynomial_boundary_v2(segment, endpoint)
        for key in declared:
            vector = _v2_vector(declared[key], 53, key)
            if not np.allclose(vector, actual[key], atol=1e-7, rtol=0):
                raise ValueError("Declared boundary differs from saved coefficients")
    return trajectory


def save_pair_trajectory(path, trajectory):
    validate_trajectory_v2(trajectory)
    atomic_json(path, {"schema_version": 2, "trajectory": trajectory, "trajectory_hash": json_hash(trajectory)})


def read_pair_trajectory(path, *, schema_version):
    """Explicit dispatch: existing v1 NPZ, or integrity-bound v2 polynomial JSON."""
    if type(schema_version) is not int:
        raise ValueError("An explicit integer trajectory schema is required")
    if schema_version == 1:
        return read_motion(path)
    if schema_version != 2:
        raise ValueError("Unsupported saved trajectory version")
    envelope = read_json(path)
    _v2_fields(envelope, ("schema_version", "trajectory", "trajectory_hash"), "trajectory envelope")
    if type(envelope["schema_version"]) is not int or envelope["schema_version"] != 2:
        raise ValueError("Unsupported trajectory envelope")
    if json_hash(envelope["trajectory"]) != envelope["trajectory_hash"]:
        raise ValueError("Saved v2 trajectory integrity mismatch")
    return validate_trajectory_v2(envelope["trajectory"])
