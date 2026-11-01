"""Versioned multi-word sequence contract; pair v2 artifacts stay strictly two-word."""
from __future__ import annotations

from pathlib import Path
import re

import numpy as np

from sign_robot.pair_contract import (
    V2_FINGER_STRATEGIES, V2_IDENTITY_KEYS, _v2_fields, _v2_hash, _v2_integer, _v2_number, _v2_vector,
    atomic_json, file_hash, inside, json_bytes, json_hash, load_policy, polynomial_boundary_v2, read_json,
)

SEQUENCE_REPRESENTATION = "user_protected_sequence_v1"
SEQUENCE_POLICY_KIND = "user_protected_sequence_policy_v1"
SEQUENCE_QUALITY_METHOD = "per_transition_region_outside_protected_cores_v1"
AUTO_ENDPOINT_MODE = "user_protected_auto_windows_v1"
BOUNDARY_METHOD = "linear_replay_one_sided_v2"
# Entry points that the pair code hash does not collect automatically.
SEQUENCE_ENTRYPOINTS = ("scripts/plan_sequences.py", "scripts/verify_sequences.py", "scripts/render_sequences.py")
SEQUENCE_IDENTITY_KEYS = ("pair_identity_hash", "sequence_policy_hash", "sequence_code_hash", "identity_hash")
_FINGER_PHASES = {"synchronous": (0.0, 1.0), "early": (0.0, 0.65), "late": (0.35, 1.0)}
_GLOSS = re.compile(r"[A-Z0-9]+(?:-[A-Z0-9]+)*")


def load_sequence_policy(root, path):
    """Load the sequence policy and its hash-bound v5 pair policy."""
    root = Path(root).resolve()
    # Identity binds the policy content, so an absolute test copy is allowed.
    policy = read_json(Path(path) if Path(path).is_absolute() else inside(root, path))
    validate_sequence_policy(policy)
    pair_path = inside(root, policy["pair_policy"]["path"])
    if file_hash(pair_path) != policy["pair_policy"]["sha256"]:
        raise ValueError("Pair policy differs from the sequence policy's frozen hash")
    pair_policy = load_policy(pair_path, supported_versions=(1, 2))
    if pair_policy["endpoints"]["strategy"] != AUTO_ENDPOINT_MODE:
        raise ValueError("Sequences require user-protected automatic windows")
    if pair_policy["formal_acceptance_enabled"] is not False:
        raise ValueError("Sequence development policy cannot run with formal acceptance enabled")
    return policy, pair_policy


def validate_sequence_policy(policy):
    _v2_fields(policy, ("schema_version", "kind", "policy_id", "freeze_status", "pair_policy", "words", "assembly",
                        "quality", "validation", "cases", "case_note", "formal_acceptance_enabled"), "sequence policy")
    if (type(policy["schema_version"]) is not int or policy["schema_version"] != 1
            or policy["kind"] != SEQUENCE_POLICY_KIND or policy["formal_acceptance_enabled"] is not False):
        raise ValueError("Unsupported sequence policy version")
    _v2_hash(policy["pair_policy"]["sha256"], "pair policy hash")
    words = policy["words"]
    _v2_integer(words["minimum"], "minimum words", minimum=2)
    _v2_integer(words["maximum"], "maximum words", minimum=words["minimum"])
    if words["neutral_start_end"] is not False:
        raise ValueError("Implicit neutral start/end is outside this sequence version")
    if policy["quality"]["method"] != SEQUENCE_QUALITY_METHOD:
        raise ValueError("Unknown sequence quality method")
    _v2_integer(policy["assembly"]["max_combinations_per_case"], "combination budget", minimum=1)
    validation = policy["validation"]
    for key in ("max_sampled_poses", "max_native_collision_calls", "max_subdivision_depth"):
        _v2_integer(validation[key], key, minimum=1)
    for key in ("maximum_step_rad", "maximum_time_step_s", "wall_time_s", "protected_relative_timing_tolerance_s"):
        _v2_number(validation[key], key, positive=True)
    if validation["continuous_collision_certified"] is not False:
        raise ValueError("Sampled geometry cannot claim continuous certification")
    cases = policy["cases"]
    if not isinstance(cases, list) or not cases or len(set(cases)) != len(cases):
        raise ValueError("Sequence cases must be a unique, nonempty list")
    for case in cases:
        sequence_glosses(case, policy)
    return policy


def sequence_glosses(sequence_id, policy):
    glosses = sequence_id.split("__") if isinstance(sequence_id, str) and sequence_id else []
    if (not policy["words"]["minimum"] <= len(glosses) <= policy["words"]["maximum"]
            or any(_GLOSS.fullmatch(g) is None for g in glosses)):
        raise ValueError(f"Sequence must name {policy['words']['minimum']}-{policy['words']['maximum']} glosses")
    return glosses


def sequence_code_files(root, library_code_files):
    """Pair-collected code plus every sequence entry point; a missing one is an error."""
    root = Path(root).resolve()
    files = dict(library_code_files)
    for relative in SEQUENCE_ENTRYPOINTS:
        path = inside(root, relative)
        if not path.is_file():
            raise ValueError(f"Missing sequence entry point: {relative}")
        files[relative] = file_hash(path)
    return files


def sequence_identity(root, policy, library, pair_identity):
    """Implementation identity, separate from the pair candidates' source identity."""
    value = {"pair_identity_hash": pair_identity["identity_hash"], "sequence_policy_hash": json_hash(policy),
             "sequence_code_hash": json_hash(sequence_code_files(root, library["code_files"]))}
    return {**value, "identity_hash": json_hash(value)}


def _identity(value, keys, label):
    _v2_fields(value, keys, label)
    for key in keys:
        if key.endswith("hash") or key == "environment_id":
            _v2_hash(value[key], f"{label} {key}")
    if json_hash({k: v for k, v in value.items() if k != "identity_hash"}) != value["identity_hash"]:
        raise ValueError(f"{label} hash differs from its content")


def _finger_strategy(strategy):
    _v2_fields(strategy, ("name", "version", "start_fraction", "end_fraction"), "finger strategy")
    if (strategy["name"] not in V2_FINGER_STRATEGIES or type(strategy["version"]) is not int or strategy["version"] != 2
            or (strategy["start_fraction"], strategy["end_fraction"]) != _FINGER_PHASES[strategy["name"]]):
        raise ValueError("Finger phases must match their explicit strategy version")


def validate_sequence_v1(sequence, policy):
    """Structure, ordering and analytic continuity; not geometry or quality."""
    _v2_fields(sequence, ("schema_version", "representation", "sequence_id", "fps", "joint_names", "endpoint_mode",
                          "boundary_method", "word_instances", "edges", "segments", "pair_identity",
                          "sequence_identity"), "sequence")
    if (type(sequence["schema_version"]) is not int or sequence["schema_version"] != 1
            or sequence["representation"] != SEQUENCE_REPRESENTATION or sequence["endpoint_mode"] != AUTO_ENDPOINT_MODE
            or sequence["boundary_method"] != BOUNDARY_METHOD or type(sequence["fps"]) is not int or sequence["fps"] != 30):
        raise ValueError("Unsupported sequence representation")
    json_bytes(sequence)
    names = sequence["joint_names"]
    if (not isinstance(names, list) or len(names) != 53 or len(set(names)) != 53
            or any(not isinstance(n, str) or not n for n in names)):
        raise ValueError("Expected 53 distinct named coordinates")
    _identity(sequence["pair_identity"], V2_IDENTITY_KEYS, "pair identity")
    _identity(sequence["sequence_identity"], SEQUENCE_IDENTITY_KEYS, "sequence identity")
    if sequence["sequence_identity"]["pair_identity_hash"] != sequence["pair_identity"]["identity_hash"]:
        raise ValueError("Sequence identity names a different pair identity")
    glosses = sequence_glosses(sequence["sequence_id"], policy)
    instances = sequence["word_instances"]
    if not isinstance(instances, list) or [w.get("gloss") if isinstance(w, dict) else None for w in instances] != glosses:
        raise ValueError("Word occurrences differ from the ordered sequence identity")
    ids = set()
    for index, word in enumerate(instances):
        _v2_fields(word, ("instance_id", "position", "gloss", "motion_sha256", "source_frames", "protected_core_frames",
                          "protection_id", "protection_sha256", "window_provenance"), "word occurrence")
        if (not isinstance(word["instance_id"], str) or not word["instance_id"] or word["instance_id"] in ids
                or type(word["position"]) is not int or word["position"] != index
                or not isinstance(word["protection_id"], str) or not word["protection_id"]
                or word["window_provenance"] != "algorithm"):
            raise ValueError("Occurrences require unique IDs, ordered positions and protection references")
        ids.add(word["instance_id"])
        _v2_hash(word["motion_sha256"], "motion hash")
        _v2_hash(word["protection_sha256"], "protection hash")
        for key in ("source_frames", "protected_core_frames"):
            if not isinstance(word[key], list) or len(word[key]) != 2:
                raise ValueError("Word frames must be inclusive ranges")
            for frame in word[key]:
                _v2_integer(frame, key)
        entry, exit_ = word["source_frames"]
        c0, c1 = word["protected_core_frames"]
        if not entry <= c0 <= c1 <= exit_ or entry >= exit_:
            raise ValueError("Each occurrence slice must contain its whole protected core once")
        if (index == 0 and entry != c0) or (index == len(instances) - 1 and exit_ != c1):
            raise ValueError("Sequences start and end on protected cores; no implicit neutral")
    edges, segments = sequence["edges"], sequence["segments"]
    if not isinstance(edges, list) or len(edges) != len(instances) - 1 or not isinstance(segments, list):
        raise ValueError("Exactly one connector group is required between neighbouring occurrences")
    previous_end, cursor = 0.0, 0
    for index, word in enumerate(instances):
        if cursor >= len(segments):
            raise ValueError("Missing word slice segment")
        segment = segments[cursor]
        _v2_fields(segment, ("kind", "start_time_s", "end_time_s", "word_instance_id", "source_frames",
                             "interpolation", "time_scale"), "word segment")
        start, end = _v2_number(segment["start_time_s"], "segment start", minimum=0), _v2_number(segment["end_time_s"], "segment end", positive=True)
        if (segment["kind"] != "source_slice_v2" or segment["word_instance_id"] != word["instance_id"]
                or segment["source_frames"] != word["source_frames"] or segment["interpolation"] != "linear"
                or type(segment["time_scale"]) not in (int, float) or segment["time_scale"] != 1.0):
            raise ValueError("Word mapping or original timing changed")
        if not np.isclose(start, previous_end, atol=1e-10, rtol=0) or end <= start:
            raise ValueError("Segments must form a positive, contiguous timeline from zero")
        if not np.isclose(start * 30, round(start * 30), atol=1e-8, rtol=0):
            raise ValueError("Word slices must start on the 30 Hz playback grid")
        if not np.isclose(end - start, (word["source_frames"][1] - word["source_frames"][0]) / 30, atol=1e-10, rtol=0):
            raise ValueError("Word slice duration differs from original replay")
        previous_end, cursor = end, cursor + 1
        if index == len(instances) - 1:
            break
        edge = edges[index]
        _v2_fields(edge, ("edge_index", "from_instance_id", "to_instance_id", "pair_id", "exit_frame", "entry_frame",
                          "segment_indices", "finger_strategy", "planner", "boundary", "source"), "edge")
        following = instances[index + 1]
        if (edge["edge_index"] != index or edge["from_instance_id"] != word["instance_id"]
                or edge["to_instance_id"] != following["instance_id"]
                or edge["pair_id"] != f"{word['gloss']}__{following['gloss']}"
                or edge["exit_frame"] != word["source_frames"][1] or edge["entry_frame"] != following["source_frames"][0]):
            raise ValueError("Edge endpoints differ from their occurrences")
        _finger_strategy(edge["finger_strategy"])
        _v2_fields(edge["source"], ("run_id", "attempt_id", "candidate_file", "candidate_file_sha256",
                                    "candidate_trajectory_hash"), "edge source")
        for key in ("candidate_file_sha256", "candidate_trajectory_hash"):
            _v2_hash(edge["source"][key], key)
        first = cursor
        polynomials = []
        while cursor < len(segments) and isinstance(segments[cursor], dict) and segments[cursor].get("kind") != "source_slice_v2":
            segment = segments[cursor]
            _v2_fields(segment, ("kind", "start_time_s", "end_time_s", "coefficients"), "polynomial segment")
            start, end = _v2_number(segment["start_time_s"], "segment start", minimum=0), _v2_number(segment["end_time_s"], "segment end", positive=True)
            if segment["kind"] != "polynomial_v2" or not isinstance(segment["coefficients"], list) or len(segment["coefficients"]) != 53:
                raise ValueError("Unsupported segment representation or coordinate count")
            if not np.isclose(start, previous_end, atol=1e-10, rtol=0) or end <= start:
                raise ValueError("Segments must form a positive, contiguous timeline from zero")
            for row in segment["coefficients"]:
                _v2_vector(row, 6, "normalized-u quintic coefficients")
            if polynomials:
                left, right = polynomial_boundary_v2(polynomials[-1], "end"), polynomial_boundary_v2(segment, "start")
                if any(not np.allclose(left[k], right[k], atol=1e-7, rtol=0) for k in left):
                    raise ValueError("Connector segments must preserve position, velocity and acceleration continuity")
            polynomials.append(segment)
            previous_end, cursor = end, cursor + 1
        if not polynomials or edge["segment_indices"] != [first, cursor - 1]:
            raise ValueError("Each edge requires its own nonempty connector segment range")
        intervals = (polynomials[-1]["end_time_s"] - polynomials[0]["start_time_s"]) * 30
        if not np.isclose(intervals, round(intervals), atol=1e-8, rtol=0):
            raise ValueError("Each complete connector must fit the 30 Hz playback grid")
        _v2_fields(edge["boundary"], ("start", "end", "method"), "edge boundary")
        if edge["boundary"]["method"] != BOUNDARY_METHOD:
            raise ValueError("Unknown boundary derivative method")
        for endpoint, segment in (("start", polynomials[0]), ("end", polynomials[-1])):
            declared = edge["boundary"][endpoint]
            _v2_fields(declared, ("position", "velocity", "acceleration"), "boundary state")
            actual = polynomial_boundary_v2(segment, endpoint)
            for key in declared:
                if not np.allclose(_v2_vector(declared[key], 53, key), actual[key], atol=1e-7, rtol=0):
                    raise ValueError("Declared boundary differs from saved coefficients")
    if cursor != len(segments):
        raise ValueError("Unexpected trailing segments")
    return sequence


def save_sequence(path, sequence, policy):
    validate_sequence_v1(sequence, policy)
    atomic_json(path, {"schema_version": 1, "sequence": sequence, "sequence_hash": json_hash(sequence)})


def read_sequence(path, policy):
    envelope = read_json(path)
    _v2_fields(envelope, ("schema_version", "sequence", "sequence_hash"), "sequence envelope")
    if type(envelope["schema_version"]) is not int or envelope["schema_version"] != 1:
        raise ValueError("Unsupported sequence envelope")
    if json_hash(envelope["sequence"]) != envelope["sequence_hash"]:
        raise ValueError("Saved sequence integrity mismatch")
    return validate_sequence_v1(envelope["sequence"], policy)
