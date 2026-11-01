"""Join verified pair connectors so every word occurrence is played exactly once."""
from __future__ import annotations

import copy
import itertools
from pathlib import Path

from sign_robot.pair_contract import file_hash, inside, json_hash, read_pair_trajectory
from sign_robot.pair_runner_v2 import V2RunStore
from sign_robot.sequence_contract import AUTO_ENDPOINT_MODE, BOUNDARY_METHOD, SEQUENCE_REPRESENTATION, sequence_glosses

_OCCURRENCE_FIELDS = ("gloss", "motion_sha256", "protected_core_frames", "protection_id", "protection_sha256",
                      "window_provenance")


class SequenceAssemblyError(ValueError):
    def __init__(self, code, details):
        super().__init__(f"{code}: {details}")
        self.code, self.details = code, details


def load_candidate_pools(root, run_dir, pair_ids):
    """Independently passing candidates per pair, in the pair run's own selection order."""
    root = Path(root).resolve()
    store = V2RunStore.load(root, run_dir)
    pools = {}
    for pair_id in pair_ids:
        record = store._head_record(pair_id)
        if record is None or record.get("verification_state") != "COMPLETE":
            raise SequenceAssemblyError("PAIR_NOT_INDEPENDENTLY_VERIFIED", pair_id)
        remaining = [review for review in record["verifications"] if review["numerical_checks_passed"]]
        ranked = []
        while remaining:
            winner = store._selection_winner(remaining, record["attempts"])
            ranked.append(winner)
            remaining = [review for review in remaining if review["attempt_id"] != winner]
        if not ranked or ranked[0] != record["selected_candidate_id"]:
            raise SequenceAssemblyError("PAIR_SELECTION_ORDER_MISMATCH", pair_id)
        pools[pair_id] = []
        for attempt_id in ranked:
            entry = next(a for a in record["attempts"] if a["attempt_id"] == attempt_id)
            path = inside(store.run_dir, entry["candidate_file"])
            trajectory = read_pair_trajectory(path, schema_version=2)
            pools[pair_id].append({"run_id": store.manifest["run_id"], "attempt_id": attempt_id,
                                   "candidate_file": str(path.relative_to(root)), "candidate_file_sha256": file_hash(path),
                                   "trajectory": trajectory})
    return pools


def combinations(pools, pair_ids, limit):
    """Bounded rank combinations: smallest rank sum first, then lexicographic."""
    sizes = [len(pools[pair_id]) for pair_id in pair_ids]
    ranks = sorted(itertools.product(*(range(size) for size in sizes)), key=lambda r: (sum(r), r))
    return ranks[:limit]


def _occurrence(word, instance_id, position, entry, exit_):
    return {"instance_id": instance_id, "position": position, **{k: word[k] for k in _OCCURRENCE_FIELDS},
            "source_frames": [entry, exit_]}


def assemble_sequence(sequence_id, candidates, *, policy, sequence_identity):
    """candidates[i] joins occurrence i to i + 1; coefficients and durations are copied."""
    glosses = sequence_glosses(sequence_id, policy)
    if len(candidates) != len(glosses) - 1:
        raise SequenceAssemblyError("EDGE_COUNT_MISMATCH", sequence_id)
    trajectories = [c["trajectory"] for c in candidates]
    first = trajectories[0]
    for index, trajectory in enumerate(trajectories):
        if trajectory["pair_id"] != f"{glosses[index]}__{glosses[index + 1]}":
            raise SequenceAssemblyError("EDGE_PAIR_MISMATCH", index)
        if (trajectory["identity"] != first["identity"] or trajectory["joint_names"] != first["joint_names"]
                or trajectory.get("endpoint_mode") != AUTO_ENDPOINT_MODE
                or trajectory["boundary"]["method"] != BOUNDARY_METHOD):
            raise SequenceAssemblyError("EDGE_SOURCE_INCONSISTENT", index)
    if sequence_identity["pair_identity_hash"] != first["identity"]["identity_hash"]:
        raise SequenceAssemblyError("PAIR_IDENTITY_MISMATCH", sequence_id)
    instances = []
    for position in range(len(glosses)):
        incoming = trajectories[position - 1]["word_instances"][1] if position else None
        outgoing = trajectories[position]["word_instances"][0] if position < len(trajectories) else None
        if incoming and outgoing and any(incoming[k] != outgoing[k] for k in _OCCURRENCE_FIELDS):
            raise SequenceAssemblyError("OCCURRENCE_REFERENCE_MISMATCH", position)
        word = outgoing or incoming
        c0, c1 = word["protected_core_frames"]
        entry = incoming["source_frames"][0] if incoming else c0
        exit_ = outgoing["source_frames"][1] if outgoing else c1
        if not entry <= c0 <= c1 <= exit_ or entry >= exit_:
            raise SequenceAssemblyError("INCOMPATIBLE_SLICE", {"position": position, "entry": entry, "exit": exit_})
        instances.append(_occurrence(word, f"o{position}_{word['gloss']}", position, entry, exit_))
    segments, edges, frame = [], [], 0
    for position, word in enumerate(instances):
        entry, exit_ = word["source_frames"]
        segments.append({"kind": "source_slice_v2", "start_time_s": frame / 30, "end_time_s": (frame + exit_ - entry) / 30,
                         "word_instance_id": word["instance_id"], "source_frames": [entry, exit_],
                         "interpolation": "linear", "time_scale": 1.0})
        frame += exit_ - entry
        if position == len(trajectories):
            break
        candidate, trajectory = candidates[position], trajectories[position]
        polynomials = trajectory["segments"][1:-1]
        origin = polynomials[0]["start_time_s"]
        duration = polynomials[-1]["end_time_s"] - origin
        intervals = round(duration * 30)
        first_index = len(segments)
        for index, polynomial in enumerate(polynomials):
            shifted = copy.deepcopy(polynomial)
            shifted["start_time_s"] = frame / 30 + (polynomial["start_time_s"] - origin) if index else frame / 30
            shifted["end_time_s"] = ((frame + intervals) / 30 if index == len(polynomials) - 1
                                     else frame / 30 + (polynomial["end_time_s"] - origin))
            segments.append(shifted)
        edges.append({"edge_index": position, "from_instance_id": word["instance_id"],
                      "to_instance_id": instances[position + 1]["instance_id"], "pair_id": trajectory["pair_id"],
                      "exit_frame": exit_, "entry_frame": instances[position + 1]["source_frames"][0],
                      "segment_indices": [first_index, len(segments) - 1],
                      "finger_strategy": copy.deepcopy(trajectory["finger_strategy"]),
                      "planner": copy.deepcopy(trajectory["planner"]),
                      "boundary": copy.deepcopy(trajectory["boundary"]),
                      "source": {"run_id": candidate["run_id"], "attempt_id": candidate["attempt_id"],
                                 "candidate_file": candidate["candidate_file"],
                                 "candidate_file_sha256": candidate["candidate_file_sha256"],
                                 "candidate_trajectory_hash": json_hash(trajectory)}})
        frame += intervals
    return {"schema_version": 1, "representation": SEQUENCE_REPRESENTATION, "sequence_id": sequence_id, "fps": 30,
            "joint_names": list(first["joint_names"]), "endpoint_mode": AUTO_ENDPOINT_MODE,
            "boundary_method": BOUNDARY_METHOD, "word_instances": instances, "edges": edges, "segments": segments,
            "pair_identity": copy.deepcopy(first["identity"]), "sequence_identity": copy.deepcopy(sequence_identity)}
