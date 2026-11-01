"""Immutable attempt artifacts, chained checkpoints and independent v2 selection."""
from __future__ import annotations

from collections import Counter
import csv
from dataclasses import dataclass
import io
import math
from pathlib import Path

from sign_robot.pair_contract import (
    AUTO_SELECTION_RULES, CORE_GAP_SELECTION_V1, STATUSES, acceptance_pending, atomic_bytes, atomic_json, file_hash, inside,
    json_bytes, json_hash, pair_universe, read_json, read_pair_trajectory,
    run_identity, run_directory, validate_policy_v2,
)
from sign_robot.pair_routes import CandidateAttemptV2, PairWorkBudget, build_pair_context_v2, iter_deterministic_attempts_v2
from sign_robot.pair_search import iter_rrt_attempts_v2
from sign_robot.pair_verification_v2 import verify_missing_candidate_v2, verify_saved_pair_v2


class RunIntegrityError(ValueError):
    pass


class VerificationPaused(RuntimeError):
    """A soft budget stopped before a new candidate review; saved reviews stay, nothing is selected."""
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def _stable_diagnostic(value):
    if isinstance(value, dict):
        return {k: _stable_diagnostic(v) for k, v in value.items() if k not in ("wall_time_s", "runtime_s")}
    if isinstance(value, list):
        return [_stable_diagnostic(v) for v in value]
    return value


def _fingerprint(attempt):
    return json_hash({"diagnostic": _stable_diagnostic(attempt.diagnostic),
                      "candidate_hash": json_hash(attempt.trajectory) if attempt.trajectory is not None else None,
                      "timing_hashes": [json_hash(t) for t in attempt.timing_trajectories]})


def _immutable_json(path, value):
    payload = json_bytes(value)
    if path.exists():
        if path.read_bytes() != payload:
            raise RunIntegrityError(f"Refusing to overwrite a different immutable artifact: {path}")
    else:
        atomic_bytes(path, payload)


@dataclass
class V2RunStore:
    root: Path
    run_dir: Path
    policy: dict
    manifest: dict

    @classmethod
    def create(cls, root, policy, context, results_root, run_id, *, resume=False):
        validate_policy_v2(policy)
        if json_hash(context.policy) != json_hash(policy):
            raise RunIntegrityError("Context policy changed; build a fresh context before creating a run")
        run_dir = run_directory(Path(results_root).resolve(), run_id)
        identity = run_identity(context.library, policy)
        if run_dir.exists():
            if not resume:
                raise RunIntegrityError("Run already exists; choose a new run_id or --resume")
            manifest = read_json(run_dir / "manifest.json")
            if manifest.get("identity") != identity or manifest.get("policy_hash") != json_hash(policy):
                raise RunIntegrityError("Code, policy, model, environment or inputs changed; use a new run_id")
            store = cls.load(root, run_dir, recover=True)
            return store
        contract = inside(root, policy["contract"]["path"])
        if file_hash(contract) != policy["contract"]["sha256"]:
            raise RunIntegrityError("Actual contract differs from the v2 policy")
        run_dir.mkdir(parents=True)
        snapshots = {"policy.json": policy, "library_manifest.json": context.library,
                     "pair_universe.json": pair_universe(policy["scope"]["expected_glosses"])}
        for relative, value in snapshots.items():
            atomic_json(run_dir / relative, value)
        atomic_bytes(run_dir / "contract.json", contract.read_bytes())
        manifest = {"schema_version": 2, "run_id": run_id, "identity": identity,
                    "policy_hash": json_hash(policy), "formal_acceptance_enabled": False,
                    "frozen_files": {name: file_hash(run_dir / name) for name in (*snapshots, "contract.json")},
                    "pair_universe_hash": json_hash(snapshots["pair_universe.json"]),
                    "pair_count": 1225, "non_self_count": 1190, "self_count": 35,
                    "heads": {}, "planning_complete": False, "verification_complete": False,
                    "summary_stale": True, "acceptance_pending": acceptance_pending(policy)}
        atomic_json(run_dir / "manifest.json", manifest)
        store = cls(Path(root).resolve(), run_dir, policy, manifest)
        store.verify()
        return store

    @classmethod
    def load(cls, root, run_dir, *, recover=False):
        run_dir = Path(run_dir).resolve()
        manifest = read_json(run_dir / "manifest.json")
        if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 2:
            raise RunIntegrityError("Not a v2 run; use its versioned entry point")
        policy = read_json(run_dir / "policy.json")
        validate_policy_v2(policy)
        store = cls(Path(root).resolve(), run_dir, policy, manifest)
        store.verify()
        if recover:
            store._recover_journals()
            store.verify()
        return store

    def universe(self):
        return pair_universe(self.policy["scope"]["expected_glosses"])

    def _validate_evidence(self, evidence, pair_id, *, diagnosis=False):
        if (type(evidence.get("schema_version")) is not int or evidence["schema_version"] != 2
                or evidence.get("pair_id") != pair_id or evidence.get("status") not in STATUSES
                or evidence["status"] in ("NOT_RUN", "PASS_SIM")
                or evidence.get("playback_eligible") is not False
                or not isinstance(evidence.get("reason_codes"), list)
                or not all(isinstance(code, str) for code in evidence["reason_codes"])):
            raise RunIntegrityError("Invalid independent evidence; formal PASS cannot be imported")
        numeric = evidence.get("numerical_checks_passed")
        if numeric is not None and type(numeric) is not bool:
            raise RunIntegrityError("Independent numerical result must be boolean or incomplete")
        if "identity" in evidence and evidence["identity"] != self.manifest["identity"]:
            raise RunIntegrityError("Independent evidence identity mismatch")
        if diagnosis:
            if (evidence.get("verification_scope") != "no_trajectory_diagnosis" or numeric is not False
                    or evidence.get("validation_complete") is not False
                    or evidence.get("identity") != self.manifest["identity"]):
                raise RunIntegrityError("A no-trajectory diagnosis cannot certify numerical validation")
        elif numeric is True and (evidence.get("identity") != self.manifest["identity"]
                or evidence.get("word_occurrences") != 2
                or evidence["status"] != "FAILED_QUALITY"
                or not all(evidence.get(key) is True for key in
                           ("validation_complete", "artifact_contract_passed",
                            "input_checks_passed" if self.policy["endpoints"]["strategy"] == "user_protected_auto_windows_v1" else "approval_checks_passed",
                            "protected_core_preserved", "original_word_slices_preserved"))):
            raise RunIntegrityError("Numerical-pass claim lacks complete independent evidence")
        if numeric is True and self.policy["endpoints"]["strategy"] == "user_protected_auto_windows_v1":
            if evidence.get("window_provenance") != "algorithm" or evidence.get("approval_checks_passed") is not False:
                raise RunIntegrityError("Algorithm evidence cannot claim human window approval")
            for key in ("peak_jerk_rad_s3", "peak_acceleration_rad_s2", "analytic_connector_jerk_integral_rad2_s5"):
                value = evidence.get("metrics", {}).get(key)
                if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                    raise RunIntegrityError("Automatic candidate selection requires complete smoothness metrics")

    def _validate_record(self, record):
        if json_hash(self.policy) != self.manifest["policy_hash"]:
            raise RunIntegrityError("In-memory policy changed after freezing")
        expected = {p["pair_id"]: p for p in self.universe()}.get(record.get("pair_id"))
        if (expected is None or any(record.get(k) != v for k, v in expected.items())
                or type(record.get("schema_version")) is not int or record["schema_version"] != 2
                or type(record.get("pair_seed")) is not int or record["pair_seed"] < 0
                or record.get("identity") != self.manifest["identity"]
                or record.get("status") not in STATUSES or record.get("status") == "PASS_SIM"
                or record.get("playback_eligible") is not False or record.get("formal_acceptance") is not False):
            raise RunIntegrityError("Invalid v2 pair identity/status; formal PASS cannot be imported")
        if record.get("planning_state") not in ("RUNNING", "COMPLETE"):
            raise RunIntegrityError("Invalid planning-state checkpoint")
        if type(record.get("completed")) is not bool or record["completed"] != (record["planning_state"] == "COMPLETE"):
            raise RunIntegrityError("Checkpoint completion flag differs from its planning state")
        if record["verification_state"] not in ("NOT_RUN", "COMPLETE", "DIAGNOSIS_ONLY"):
            raise RunIntegrityError("Unknown verification state")
        ids = [entry["attempt_id"] for entry in record["attempts"]]
        if ids != [f"attempt_{i:05d}" for i in range(1, len(ids) + 1)]:
            raise RunIntegrityError("Attempt sequence has gaps or duplicates")
        for entry in record["attempts"]:
            self._read_attempt(entry, record["pair_id"])
        candidate_ids = [entry["attempt_id"] for entry in record["attempts"] if entry["candidate_file"]]
        if record["candidate_ids"] != candidate_ids or record["candidate_count"] != len(candidate_ids):
            raise RunIntegrityError("Candidate inventory differs from immutable attempts")
        reviewed = record["verification_state"] != "NOT_RUN"
        if (record.get("independent_review_recorded") is not reviewed
                or reviewed and not record["completed"]):
            raise RunIntegrityError("Independent review state differs from checkpoint completion")
        review_ids = [v["attempt_id"] for v in record["verifications"]]
        if record["verification_state"] == "COMPLETE":
            if not candidate_ids or review_ids != candidate_ids:
                raise RunIntegrityError("Independent reviews must cover every eligible candidate exactly once")
        elif review_ids or record.get("selected_candidate_id") is not None:
            raise RunIntegrityError("Unverified/diagnosis checkpoint cannot select a candidate")
        if record["verification_state"] == "DIAGNOSIS_ONLY":
            if candidate_ids or record["diagnosis_file"] != f"verification/{record['pair_id']}/diagnosis.json":
                raise RunIntegrityError("No-trajectory diagnosis refers to a candidate or an unexpected path")
            path = inside(self.run_dir, record["diagnosis_file"])
            if file_hash(path) != record["diagnosis_file_hash"]:
                raise RunIntegrityError("Independent diagnosis hash mismatch")
            diagnosis = read_json(path)
            evidence = diagnosis["evidence"]
            if (diagnosis["schema_version"] != 2 or diagnosis["identity"] != self.manifest["identity"]
                    or json_hash(evidence) != diagnosis["evidence_hash"]
                    or record["status"] != evidence["status"] or record["reason_codes"] != evidence["reason_codes"]):
                raise RunIntegrityError("Independent diagnosis envelope/status mismatch")
            self._validate_evidence(evidence, record["pair_id"], diagnosis=True)
        for entry in record.get("verifications", []):
            path = inside(self.run_dir, entry["path"])
            if file_hash(path) != entry["sha256"]:
                raise RunIntegrityError("Independent verification artifact hash mismatch")
            envelope = read_json(path)
            attempt = next((a for a in record["attempts"] if a["attempt_id"] == entry["attempt_id"]), None)
            if attempt is None or not attempt["candidate_file"]:
                raise RunIntegrityError("Verification references a nonexistent eligible candidate")
            actual_candidate_hash = file_hash(inside(self.run_dir, attempt["candidate_file"]))
            evidence = envelope["evidence"]
            numerical = evidence.get("numerical_checks_passed") is True
            if (entry["path"] != f"verification/{record['pair_id']}/{entry['attempt_id']}.json"
                    or envelope["schema_version"] != 2 or envelope["identity"] != self.manifest["identity"]
                    or envelope["candidate_hash"] != entry["candidate_hash"]
                    or envelope["candidate_hash"] != actual_candidate_hash
                    or envelope["candidate_file"] != attempt["candidate_file"]
                    or json_hash(envelope["evidence"]) != envelope["evidence_hash"]
                    or entry["status"] != evidence["status"]
                    or entry["numerical_checks_passed"] is not numerical):
                raise RunIntegrityError("Invalid independent verification envelope")
            self._validate_evidence(evidence, record["pair_id"])
            if numerical and (evidence.get("trajectory_file_sha256") != actual_candidate_hash
                    or evidence.get("trajectory_hash") != json_hash(read_pair_trajectory(inside(self.run_dir, attempt["candidate_file"]), schema_version=2))):
                raise RunIntegrityError("Numerical proof is not bound to the saved candidate")
        selected = record.get("selected_candidate_id")
        if selected is not None:
            matches = [v for v in record.get("verifications", []) if v["attempt_id"] == selected]
            if len(matches) != 1 or not matches[0]["numerical_checks_passed"]:
                raise RunIntegrityError("Selected candidate lacks complete numerical verification")
            if record["status"] != "FAILED_QUALITY" or record["reason_codes"] != acceptance_pending(self.policy):
                raise RunIntegrityError("A selected development candidate must retain the pending acceptance status")
        if record["verification_state"] == "COMPLETE" and selected != self._selection_winner(record["verifications"], record["attempts"]):
            raise RunIntegrityError("Saved selection differs from recomputed frozen ranking")

    @staticmethod
    def _with_attempts(record, attempts):
        candidate_ids = [a["attempt_id"] for a in attempts if a["candidate_file"]]
        return {**record, "attempts": attempts, "candidate_count": len(candidate_ids), "candidate_ids": candidate_ids}

    @staticmethod
    def _validate_transition(previous, record):
        if previous is None:
            return
        if (record["pair_id"] != previous["pair_id"] or record["pair_seed"] != previous["pair_seed"]
                or record["attempts"][:len(previous["attempts"])] != previous["attempts"]):
            raise RunIntegrityError("Checkpoint would alter saved attempts or the pair seed")
        if previous["completed"] and any(record.get(key) != previous.get(key) for key in
                ("completed", "planning_state", "attempts", "candidate_count", "candidate_ids", "method_coverage")):
            raise RunIntegrityError("Completed planning cannot be changed by another checkpoint")
        if previous["verification_state"] != "NOT_RUN" and record != previous:
            raise RunIntegrityError("Completed independent evidence cannot be changed")

    def _read_attempt(self, entry, pair_id):
        if entry["attempt_file"] != f"attempts/{pair_id}/{entry['attempt_id']}.json":
            raise RunIntegrityError("Unexpected attempt artifact path")
        path = inside(self.run_dir, entry["attempt_file"])
        if file_hash(path) != entry["attempt_file_hash"]:
            raise RunIntegrityError(f"Attempt integrity mismatch: {path}")
        saved = read_json(path)
        if (saved["schema_version"] != 2 or saved["pair_id"] != pair_id or saved["attempt_id"] != entry["attempt_id"]
                or saved["identity"] != self.manifest["identity"]
                or json_hash(saved["diagnostic"]) != saved["diagnostic_hash"]
                or saved["logical_fingerprint"] != entry["logical_fingerprint"]
                or saved["candidate_file"] != entry["candidate_file"]
                or saved["diagnostic"]["pair_id"] != pair_id
                or saved["diagnostic"]["status"] not in STATUSES or saved["diagnostic"]["status"] == "PASS_SIM"
                or entry["method"] != saved["diagnostic"].get("method")
                or entry["status"] != saved["diagnostic"]["status"]):
            raise RunIntegrityError("Attempt identity/diagnostic differs from its checkpoint")
        eligible = [a["path"] for a in saved["artifacts"] if a["eligible_for_selection"]]
        if eligible != ([] if saved["candidate_file"] is None else [saved["candidate_file"]]):
            raise RunIntegrityError("Eligible artifact list differs from the candidate reference")
        timing, candidate = [], None
        for artifact in saved["artifacts"]:
            if artifact["eligible_for_selection"]:
                expected_path = f"candidates/{pair_id}/{entry['attempt_id']}.json"
            else:
                expected_path = f"timing_attempts/{pair_id}/{entry['attempt_id']}/curve_{len(timing) + 1:04d}.json"
            if artifact["path"] != expected_path or type(artifact["eligible_for_selection"]) is not bool:
                raise RunIntegrityError("Unexpected saved-curve artifact path/order")
            candidate_path = inside(self.run_dir, artifact["path"])
            if file_hash(candidate_path) != artifact["sha256"]:
                raise RunIntegrityError(f"Saved curve integrity mismatch: {candidate_path}")
            trajectory = read_pair_trajectory(candidate_path, schema_version=2)
            if trajectory["identity"] != self.manifest["identity"] or trajectory["pair_id"] != pair_id:
                raise RunIntegrityError("Curve identity differs from its frozen run")
            if artifact["eligible_for_selection"]:
                candidate = trajectory
            else:
                timing.append(trajectory)
        if _fingerprint(CandidateAttemptV2(candidate, saved["diagnostic"], timing)) != saved["logical_fingerprint"]:
            raise RunIntegrityError("Logical attempt fingerprint differs from its actual saved curves")
        return saved

    def _head_record(self, pair_id):
        head = self.manifest["heads"].get(pair_id)
        if head is None:
            return None
        path = inside(self.run_dir, head["path"])
        if file_hash(path) != head["sha256"]:
            raise RunIntegrityError("Checkpoint head hash mismatch")
        envelope = read_json(path)
        if (type(head["sequence"]) is not int or head["sequence"] < 1
                or head["path"] != f"checkpoints/{pair_id}/checkpoint_{head['sequence']:05d}.json"
                or envelope["schema_version"] != 2 or envelope["record"]["pair_id"] != pair_id
                or json_hash(envelope["record"]) != envelope["record_hash"] or envelope["sequence"] != head["sequence"]):
            raise RunIntegrityError("Checkpoint envelope mismatch")
        return envelope["record"]

    def verify(self):
        if (type(self.manifest.get("schema_version")) is not int or self.manifest["schema_version"] != 2
                or self.manifest["run_id"] != self.run_dir.name
                or json_hash(self.policy) != self.manifest["policy_hash"]):
            raise RunIntegrityError("Frozen run identity/policy mismatch")
        if self.manifest.get("formal_acceptance_enabled") is not False:
            raise RunIntegrityError("Formal v2 acceptance is disabled")
        if [self.manifest.get(k) for k in ("pair_count", "non_self_count", "self_count")] != [1225, 1190, 35]:
            raise RunIntegrityError("Frozen denominator mismatch")
        if set(self.manifest["frozen_files"]) != {"policy.json", "library_manifest.json", "pair_universe.json", "contract.json"}:
            raise RunIntegrityError("Frozen input inventory is incomplete")
        for relative, digest in self.manifest["frozen_files"].items():
            if file_hash(inside(self.run_dir, relative)) != digest:
                raise RunIntegrityError(f"Frozen input integrity mismatch: {relative}")
        if file_hash(self.run_dir / "contract.json") != self.policy["contract"]["sha256"]:
            raise RunIntegrityError("Frozen contract differs from the policy")
        if (json_hash(read_json(self.run_dir / "policy.json")) != self.manifest["policy_hash"]
                or read_json(self.run_dir / "pair_universe.json") != self.universe()
                or json_hash(self.universe()) != self.manifest["pair_universe_hash"]):
            raise RunIntegrityError("Frozen policy or full pair universe mismatch")
        library = read_json(self.run_dir / "library_manifest.json")
        if run_identity(library, self.policy) != self.manifest["identity"]:
            raise RunIntegrityError("Frozen library identity mismatch")
        for pair_id, head in self.manifest["heads"].items():
            record = self._head_record(pair_id)
            self._validate_record(record)
            reference = head
            while reference is not None:
                path = inside(self.run_dir, reference["path"])
                if file_hash(path) != reference["sha256"]:
                    raise RunIntegrityError("Checkpoint journal chain is broken")
                envelope = read_json(path)
                if (reference["path"] != f"checkpoints/{pair_id}/checkpoint_{reference['sequence']:05d}.json"
                        or envelope["schema_version"] != 2 or envelope["record"]["pair_id"] != pair_id
                        or envelope["sequence"] != reference["sequence"]
                        or json_hash(envelope["record"]) != envelope["record_hash"]):
                    raise RunIntegrityError("Checkpoint journal envelope is invalid")
                previous = envelope["previous"]
                if ((previous is None) != (reference["sequence"] == 1)
                        or previous is not None and previous["sequence"] != reference["sequence"] - 1):
                    raise RunIntegrityError("Checkpoint journal sequence is broken")
                if previous is not None:
                    prior = read_json(inside(self.run_dir, previous["path"]))["record"]
                    self._validate_transition(prior, envelope["record"])
                reference = previous
        if not self.manifest.get("summary_stale", True):
            for relative, digest in self.manifest.get("files", {}).items():
                if file_hash(inside(self.run_dir, relative)) != digest:
                    raise RunIntegrityError("Summary artifact integrity mismatch")

    def _recover_journals(self):
        directory = self.run_dir / "checkpoints"
        if not directory.exists():
            return
        legal = {p["pair_id"] for p in self.universe()}
        for pair_dir in sorted(directory.iterdir()):
            if pair_dir.name not in legal or not pair_dir.is_dir():
                raise RunIntegrityError("Unexpected pair journal outside the frozen universe")
            current = self.manifest["heads"].get(pair_dir.name)
            expected = 1 if current is None else current["sequence"] + 1
            for path in sorted(pair_dir.glob("checkpoint_*.json")):
                sequence = int(path.stem.split("_")[-1])
                if sequence < expected:
                    continue
                envelope = read_json(path)
                if (sequence != expected or envelope["sequence"] != sequence or envelope["schema_version"] != 2
                        or envelope["record"]["pair_id"] != pair_dir.name
                        or envelope["previous"] != current or json_hash(envelope["record"]) != envelope["record_hash"]):
                    raise RunIntegrityError("Uncommitted checkpoint journal cannot be recovered consistently")
                self._validate_record(envelope["record"])
                prior_record = self._head_record(pair_dir.name)
                self._validate_transition(prior_record, envelope["record"])
                current = {"path": str(path.relative_to(self.run_dir)), "sha256": file_hash(path), "sequence": sequence}
                self.manifest["heads"][pair_dir.name] = current
                self.manifest["summary_stale"] = True
                atomic_json(self.run_dir / "manifest.json", self.manifest)
                expected += 1

    def _commit(self, record):
        self._validate_record(record)
        pair_id = record["pair_id"]
        previous = self.manifest["heads"].get(pair_id)
        self._validate_transition(self._head_record(pair_id), record)
        sequence = 1 if previous is None else previous["sequence"] + 1
        path = self.run_dir / "checkpoints" / pair_id / f"checkpoint_{sequence:05d}.json"
        envelope = {"schema_version": 2, "sequence": sequence, "previous": previous,
                    "record": record, "record_hash": json_hash(record)}
        _immutable_json(path, envelope)
        self.manifest["heads"][pair_id] = {"path": str(path.relative_to(self.run_dir)),
                                           "sha256": file_hash(path), "sequence": sequence}
        self.manifest["summary_stale"] = True
        atomic_json(self.run_dir / "manifest.json", self.manifest)
        return record

    def _base_record(self, source, target, seed):
        return {"schema_version": 2, "pair_id": f"{source}__{target}", "source_gloss": source,
                "target_gloss": target, "self_pair": source == target, "identity": self.manifest["identity"],
                "status": "NOT_RUN", "reason_codes": ["PAIR_PLANNING_INCOMPLETE"],
                "planning_state": "RUNNING", "completed": False, "attempts": [],
                "verification_state": "NOT_RUN", "verifications": [], "selected_candidate_id": None,
                "candidate_count": 0, "candidate_ids": [], "independent_review_recorded": False,
                "pair_seed": int(seed),
                "formal_acceptance": False, "playback_eligible": False}

    def save_attempt(self, pair_id, attempt_id, attempt):
        artifacts = []
        candidate_file = None
        curves = list(attempt.timing_trajectories)
        for index, curve in enumerate(curves, 1):
            relative = f"timing_attempts/{pair_id}/{attempt_id}/curve_{index:04d}.json"
            payload = {"schema_version": 2, "trajectory": curve, "trajectory_hash": json_hash(curve)}
            path = inside(self.run_dir, relative)
            _immutable_json(path, payload)
            artifacts.append({"path": relative, "sha256": file_hash(path), "eligible_for_selection": False})
        if attempt.trajectory is not None:
            candidate_file = f"candidates/{pair_id}/{attempt_id}.json"
            path = inside(self.run_dir, candidate_file)
            _immutable_json(path, {"schema_version": 2, "trajectory": attempt.trajectory,
                                   "trajectory_hash": json_hash(attempt.trajectory)})
            artifacts.append({"path": candidate_file, "sha256": file_hash(path), "eligible_for_selection": True})
        relative = f"attempts/{pair_id}/{attempt_id}.json"
        path = inside(self.run_dir, relative)
        fingerprint = _fingerprint(attempt)
        saved = {"schema_version": 2, "pair_id": pair_id, "attempt_id": attempt_id,
                 "identity": self.manifest["identity"], "diagnostic": attempt.diagnostic,
                 "diagnostic_hash": json_hash(attempt.diagnostic), "logical_fingerprint": fingerprint,
                 "candidate_file": candidate_file, "artifacts": artifacts}
        if path.exists():
            existing = read_json(path)
            if existing["logical_fingerprint"] != fingerprint:
                raise RunIntegrityError("Incomplete attempt replay differs; preserve this run and use a new run_id")
            saved = existing
        else:
            _immutable_json(path, saved)
        return {"attempt_id": attempt_id, "method": saved["diagnostic"].get("method"),
                "status": saved["diagnostic"]["status"], "attempt_file": relative,
                "attempt_file_hash": file_hash(path), "logical_fingerprint": saved["logical_fingerprint"],
                "candidate_file": saved["candidate_file"]}

    def _orphan_attempts(self, record):
        entries = list(record["attempts"])
        directory = self.run_dir / "attempts" / record["pair_id"]
        for path in sorted(directory.glob("attempt_*.json")) if directory.exists() else []:
            saved = read_json(path)
            index = int(saved["attempt_id"].split("_")[-1])
            if index <= len(entries):
                continue
            if index != len(entries) + 1:
                raise RunIntegrityError("Orphan attempts contain a sequence gap")
            entry = {"attempt_id": saved["attempt_id"], "method": saved["diagnostic"].get("method"),
                     "status": saved["diagnostic"]["status"], "attempt_file": str(path.relative_to(self.run_dir)),
                     "attempt_file_hash": file_hash(path), "logical_fingerprint": saved["logical_fingerprint"],
                     "candidate_file": saved["candidate_file"]}
            self._read_attempt(entry, record["pair_id"])
            entries.append(entry)
        if entries != record["attempts"]:
            record = self._with_attempts(record, entries)
            self._commit(record)
        return record

    def run_pair(self, source, target, context, *, seed, max_new_attempts=None):
        if type(seed) is not int or seed < 0:
            raise ValueError("Pair seed must be a nonnegative integer")
        if max_new_attempts is not None and (type(max_new_attempts) is not int or max_new_attempts < 1):
            raise ValueError("Injected attempt limit must be a positive integer")
        if run_identity(context.library, context.policy) != self.manifest["identity"]:
            raise RunIntegrityError("Pair context changed after run initialization")
        pair_id = f"{source}__{target}"
        if pair_id not in {p["pair_id"] for p in self.universe()}:
            raise ValueError("Unknown ordered pair; frozen scope must not change")
        record = self._head_record(pair_id)
        if record is not None:
            self._validate_record(record)
        if record is not None and record["pair_seed"] != int(seed):
            raise RunIntegrityError("Pair seed changed; use a new run_id")
        if record is not None and record["completed"]:
            return record
        if record is None:
            record = self._commit(self._base_record(source, target, seed))
        record = self._orphan_attempts(record)
        budget = PairWorkBudget(context.policy)
        def stream():
            yield from iter_deterministic_attempts_v2(context, source, target, seed=seed, budget=budget)
            if not context.input_blockers:
                yield from iter_rrt_attempts_v2(context, source, target, seed=seed, budget=budget)
        added = 0
        replayed = 0
        for index, attempt in enumerate(stream(), 1):
            replayed = index
            attempt_id = f"attempt_{index:05d}"
            if index <= len(record["attempts"]):
                if record["attempts"][index - 1]["logical_fingerprint"] != _fingerprint(attempt):
                    raise RunIntegrityError("In-progress deterministic replay differs; saved results retained")
                continue
            entry = self.save_attempt(pair_id, attempt_id, attempt)
            record = self._commit(self._with_attempts(record, [*record["attempts"], entry]))
            added += 1
            if max_new_attempts is not None and added >= max_new_attempts:
                raise KeyboardInterrupt("Injected interruption after immutable attempt checkpoint")
        if replayed < len(record["attempts"]):
            raise RunIntegrityError("Replayed stream ended before the saved attempt checkpoint")
        statuses = [a["status"] for a in record["attempts"]]
        candidates = [a for a in record["attempts"] if a["candidate_file"]]
        if context.input_blockers:
            status, reasons = "BLOCKED_INPUT", [b["code"] for b in context.input_blockers]
        elif candidates:
            status, reasons = "FAILED_QUALITY", ["INDEPENDENT_RECHECK_REQUIRED", *acceptance_pending(self.policy)]
        else:
            priority = ["BLOCKED_ENDPOINT", "BLOCKED_INPUT", "TIMEOUT", "ERROR", "FAILED_QUALITY", "FAILED_SEARCH"]
            status = next((s for s in priority if s in statuses), "FAILED_SEARCH")
            reasons = list(dict.fromkeys(reason for entry in record["attempts"]
                                         for reason in self._read_attempt(entry, pair_id)["diagnostic"].get("reason_codes", [])))
        methods = {method: {"attempted": any(a.get("method") == method for a in record["attempts"]),
                            "unattempted_reason": None if any(a.get("method") == method for a in record["attempts"]) else
                            "GLOBAL_INPUT_BLOCKER" if context.input_blockers else "NO_ROUTE_OR_SHARED_BUDGET_EXHAUSTED"}
                   for method in self.policy["planner"]["methods"]}
        return self._commit({**record, "status": status, "reason_codes": reasons, "completed": True,
                             "planning_state": "COMPLETE", "candidate_count": len(candidates),
                             "candidate_ids": [entry["attempt_id"] for entry in candidates],
                             "method_coverage": methods, "selection_reason": "Pending independent candidate review"})

    def verify_pair(self, pair_id, *, should_stop=None):
        record = self._head_record(pair_id)
        if record is None or not record["completed"]:
            raise RunIntegrityError("Cannot independently select from incomplete planning")
        self._validate_record(record)
        if record["verification_state"] in ("COMPLETE", "DIAGNOSIS_ONLY"):
            self._validate_record(record)
            return record
        candidates = [a for a in record["attempts"] if a["candidate_file"]]
        if not candidates:
            evidence = verify_missing_candidate_v2(self.root, record, self.policy)
            relative = f"verification/{pair_id}/diagnosis.json"
            destination = inside(self.run_dir, relative)
            if not destination.exists():
                _immutable_json(destination, {"schema_version": 2, "identity": self.manifest["identity"],
                                              "evidence": evidence, "evidence_hash": json_hash(evidence)})
            else:
                saved = read_json(destination)
                if saved["identity"] != self.manifest["identity"] or json_hash(saved["evidence"]) != saved["evidence_hash"]:
                    raise RunIntegrityError("Invalid orphan independent diagnosis")
                evidence = saved["evidence"]
            self._validate_evidence(evidence, pair_id, diagnosis=True)
            return self._commit({**record, "verification_state": "DIAGNOSIS_ONLY", "independent_review_recorded": True,
                "diagnosis_file": relative, "diagnosis_file_hash": file_hash(destination), "status": evidence["status"],
                "reason_codes": evidence["reason_codes"], "selection_reason": "Fresh input/endpoint diagnosis only; no curve was produced"})
        reviews = []
        for entry in candidates:
            path = inside(self.run_dir, entry["candidate_file"])
            candidate_hash = file_hash(path)
            relative = f"verification/{pair_id}/{entry['attempt_id']}.json"
            destination = inside(self.run_dir, relative)
            if destination.exists():
                saved = read_json(destination)
                if (saved["schema_version"] != 2 or saved["identity"] != self.manifest["identity"]
                        or saved["candidate_hash"] != candidate_hash or saved["candidate_file"] != entry["candidate_file"]
                        or json_hash(saved["evidence"]) != saved["evidence_hash"]):
                    raise RunIntegrityError("Stale independent candidate review")
                evidence = saved["evidence"]
            else:
                reason = should_stop() if should_stop is not None else None
                if reason:
                    raise VerificationPaused(reason)
                evidence = verify_saved_pair_v2(self.root, path, self.policy)
                self._validate_evidence(evidence, pair_id)
                _immutable_json(destination, {"schema_version": 2, "identity": self.manifest["identity"],
                    "candidate_file": entry["candidate_file"], "candidate_hash": candidate_hash,
                    "evidence": evidence, "evidence_hash": json_hash(evidence)})
            numeric = evidence.get("numerical_checks_passed") is True
            self._validate_evidence(evidence, pair_id)
            reviews.append({"attempt_id": entry["attempt_id"], "path": relative, "sha256": file_hash(destination),
                            "candidate_hash": candidate_hash, "numerical_checks_passed": numeric,
                            "status": evidence["status"]})
        positive = [review for review in reviews if review["numerical_checks_passed"]]
        selected, selection_reason = None, "No complete numerical candidate; no playback authorization"
        status, reasons = record["status"], record["reason_codes"]
        if positive:
            selected = self._selection_winner(reviews, record["attempts"])
            selection_reason = "Complete numerical pass, then duration/method/hash among attempted candidates; formal approvals pending"
            status, reasons = "FAILED_QUALITY", acceptance_pending(self.policy)
        elif reviews:
            statuses = [review["status"] for review in reviews]
            status = next((s for s in ("BLOCKED_INPUT", "BLOCKED_ENDPOINT", "FAILED_QUALITY", "FAILED_SEARCH", "TIMEOUT", "ERROR") if s in statuses), "ERROR")
            reasons = ["NO_INDEPENDENT_NUMERICAL_PASS", *acceptance_pending(self.policy)]
        result = {**record, "verifications": reviews, "verification_state": "COMPLETE" if reviews else "DIAGNOSIS_ONLY",
                  "independent_review_recorded": True, "selected_candidate_id": selected,
                  "selection_reason": selection_reason, "status": status, "reason_codes": reasons}
        return self._commit(result)

    def _selection_winner(self, reviews, attempts):
        positive = [review for review in reviews if review["numerical_checks_passed"]]
        if not positive:
            return None
        method_rank = {method: i for i, method in enumerate(self.policy["planner"]["methods"])}
        def score(review):
            entry = next(a for a in attempts if a["attempt_id"] == review["attempt_id"])
            trajectory = read_pair_trajectory(inside(self.run_dir, entry["candidate_file"]), schema_version=2)
            duration = trajectory["segments"][-2]["end_time_s"] - trajectory["segments"][1]["start_time_s"]
            if self.policy["selection_rule"] in AUTO_SELECTION_RULES:
                evidence = read_json(inside(self.run_dir, review["path"]))["evidence"]
                metrics, limits = evidence["metrics"], self.policy["quality"]["limits"]
                gap = ()
                if self.policy["selection_rule"] == CORE_GAP_SELECTION_V1:
                    source, target = trajectory["word_instances"]
                    gap = ((source["source_frames"][1] - source["protected_core_frames"][1]) + round(duration * 30)
                           + (target["protected_core_frames"][0] - target["source_frames"][0]),)
                return (*gap, metrics["peak_jerk_rad_s3"] / limits["peak_jerk_rad_s3"],
                        metrics["peak_acceleration_rad_s2"] / limits["peak_acceleration_rad_s2"],
                        metrics["analytic_connector_jerk_integral_rad2_s5"], trajectory["segments"][-1]["end_time_s"],
                        method_rank.get(trajectory["planner"]["method"], len(method_rank)), json_hash(trajectory),
                        review["attempt_id"])
            return (duration, method_rank.get(trajectory["planner"]["method"], len(method_rank)), json_hash(trajectory),
                    review["attempt_id"])
        return min(positive, key=score)["attempt_id"]

    def summarize(self):
        self.verify()
        records = {pair_id: self._head_record(pair_id) for pair_id in self.manifest["heads"]}
        rows = [{**pair, "status": "NOT_RUN", "reason_codes": [], **records.get(pair["pair_id"], {})} for pair in self.universe()]
        groups = {}
        for label, subset in (("all", rows), ("non_self", [r for r in rows if not r["self_pair"]]), ("self", [r for r in rows if r["self_pair"]])):
            counts = Counter(r["status"] for r in subset)
            groups[label] = {"denominator": len(subset), "status_counts": {s: counts[s] for s in STATUSES},
                             "scanned": sum(r.get("completed", False) for r in subset), "pass_sim_rate": 0.0}
        summary = {"schema_version": 2, "run_id": self.manifest["run_id"], "identity": self.manifest["identity"],
                   "groups": groups, "saved_candidates": sum(r.get("candidate_count", 0) for r in records.values()),
                   "saved_attempts": sum(len(r["attempts"]) for r in records.values()),
                   "verified_records": sum(r.get("independent_review_recorded", False) for r in records.values()),
                   "planning_complete": all(r.get("completed", False) for r in rows),
                   "verification_complete": all(r.get("independent_review_recorded", False) for r in rows),
                   "L2_complete": False, "acceptance_level": "v2_development_pending_real_approvals",
                   "formal_acceptance_enabled": False}
        if self.policy["endpoints"]["strategy"] == "user_protected_auto_windows_v1":
            summary["executed_development_scope"] = {
                "denominator": len(records), "pair_ids": sorted(records),
                "numerical_pass_count": sum(r.get("selected_candidate_id") is not None for r in records.values()),
                "formal_pass_sim_count": 0, "selection_rule": self.policy["selection_rule"], "window_provenance": "algorithm"}
        glosses = self.policy["scope"]["expected_glosses"]
        statuses = {r["pair_id"]: r["status"] for r in rows}
        matrix = io.StringIO(newline="")
        writer = csv.writer(matrix)
        writer.writerow(["source_gloss/target_gloss", *glosses])
        writer.writerows([[source, *[statuses[f"{source}__{target}"] for target in glosses]] for source in glosses])
        self.manifest["summary_stale"] = True
        atomic_json(self.run_dir / "manifest.json", self.manifest)
        atomic_bytes(self.run_dir / "matrix.csv", matrix.getvalue().encode())
        atomic_bytes(self.run_dir / "pairs.jsonl", b"".join(json_bytes(row) for row in rows))
        atomic_json(self.run_dir / "summary.json", summary)
        self.manifest.update(planning_complete=summary["planning_complete"], verification_complete=summary["verification_complete"],
                             summary_stale=False, summary_files={name: file_hash(self.run_dir / name) for name in ("matrix.csv", "pairs.jsonl", "summary.json")})
        self.manifest["files"] = {str(path.relative_to(self.run_dir)): file_hash(path)
                                  for path in sorted(self.run_dir.rglob("*")) if path.is_file() and path.name != "manifest.json"}
        atomic_json(self.run_dir / "manifest.json", self.manifest)
        return summary


def run_scan_v2(root, policy, run_id, results_root, *, resume=False, max_pairs=None, selected_pairs=None, progress=None):
    if max_pairs is not None and (type(max_pairs) is not int or max_pairs < 0):
        raise ValueError("max_pairs must be a nonnegative integer")
    universe = pair_universe(policy["scope"]["expected_glosses"])
    legal = {p["pair_id"] for p in universe}
    if selected_pairs is not None and not set(selected_pairs) <= legal:
        raise ValueError("Unknown pair selection outside the frozen universe")
    context = build_pair_context_v2(root, policy)
    store = V2RunStore.create(root, policy, context, results_root, run_id, resume=resume)
    completed = 0
    for index, pair in enumerate(universe):
        if selected_pairs is not None and pair["pair_id"] not in selected_pairs:
            continue
        current = store._head_record(pair["pair_id"])
        if current is not None and current["completed"]:
            continue
        if max_pairs is not None and completed >= max_pairs:
            break
        record = store.run_pair(pair["source_gloss"], pair["target_gloss"], context, seed=policy["planner"]["seed"] + index)
        completed += 1
        if progress:
            progress(sum(store._head_record(pid)["completed"] for pid in store.manifest["heads"]), 1225, record)
    return store.run_dir, store.summarize()


def verify_run_v2(root, run_dir, *, max_pairs=None, progress=None):
    if max_pairs is not None and (type(max_pairs) is not int or max_pairs < 0):
        raise ValueError("max_pairs must be a nonnegative integer")
    frozen_policy = read_json(Path(run_dir) / "policy.json")
    manifest = read_json(Path(run_dir) / "manifest.json")
    context = build_pair_context_v2(root, frozen_policy)
    if run_identity(context.library, frozen_policy) != manifest["identity"]:
        raise RunIntegrityError("Verifier code, environment or inputs changed; use a new run_id")
    store = V2RunStore.load(root, run_dir, recover=True)
    completed = 0
    for pair in store.universe():
        record = store._head_record(pair["pair_id"])
        if record is None or not record["completed"] or record["verification_state"] != "NOT_RUN":
            continue
        if max_pairs is not None and completed >= max_pairs:
            break
        reviewed = store.verify_pair(pair["pair_id"])
        completed += 1
        if progress:
            progress(completed, len(store.manifest["heads"]), reviewed)
    return store.summarize()


def summarize_run_v2(root, run_dir):
    return V2RunStore.load(root, run_dir).summarize()
