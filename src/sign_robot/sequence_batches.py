"""Frozen sequence case manifests and cross-sub-batch aggregation with a fixed denominator.

Each sub-batch has one pre-registered canonical output; a resume writes the next
``<canonical>_resume_NN`` directory and names every earlier output it read.
Aggregation reads only those registered outputs. A case settled as a pass or as
a complete no-pass may be restated later only identically; any other repeat is
a conflict, so results are never chosen by last write or by preference.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from sign_robot.pair_contract import file_hash, inside, json_hash, read_json

MAX_CASES_PER_SUBBATCH = 8
SETTLED = ("NUMERICAL_PASS", "NO_NUMERICAL_PASS_WITHIN_COMBINATION_BUDGET")


class SequenceBatchError(ValueError):
    def __init__(self, code, details=None):
        super().__init__(f"{code}: {details}")
        self.code, self.details = code, details


def load_case_manifest(root, path, expected_sha256, policy_cases):
    """Hash-bound sub-batches: disjoint, at most eight cases each, union equal to the frozen policy cases."""
    manifest_path = inside(root, path)
    if file_hash(manifest_path) != expected_sha256:
        raise SequenceBatchError("CASE_MANIFEST_HASH_MISMATCH", path)
    manifest = read_json(manifest_path)
    if manifest.get("schema_version") != 1 or manifest.get("kind") != "hospital35_sequence_cases_v1":
        raise SequenceBatchError("CASE_MANIFEST_VERSION", path)
    seen, outputs = [], set()
    for subbatch in manifest["subbatches"]:
        cases = subbatch["cases"]
        if not cases or len(cases) > MAX_CASES_PER_SUBBATCH or len(set(cases)) != len(cases):
            raise SequenceBatchError("INVALID_SUBBATCH", subbatch["subbatch_id"])
        if subbatch["canonical_output"] in outputs:
            raise SequenceBatchError("DUPLICATE_CANONICAL_OUTPUT", subbatch["canonical_output"])
        inside(root, subbatch["canonical_output"])
        outputs.add(subbatch["canonical_output"])
        seen.extend(cases)
    groups = [case for group in manifest["groups"].values() for case in group]
    if (len(seen) != len(set(seen)) or sorted(seen) != sorted(policy_cases) or sorted(groups) != sorted(seen)
            or manifest["denominator"] != len(seen)):
        raise SequenceBatchError("SUBBATCHES_DO_NOT_COVER_FROZEN_CASES", len(seen))
    return manifest


def output_chain(root, subbatch):
    """Existing registered outputs of one sub-batch, canonical first, resumes in order without gaps."""
    root = Path(root).resolve()
    chain, base = [], inside(root, subbatch["canonical_output"])
    if not base.exists():
        return chain
    chain.append(base)
    for number in range(1, 100):
        candidate = base.with_name(f"{base.name}_resume_{number:02d}")
        if not candidate.exists():
            break
        chain.append(candidate)
    if any(base.with_name(f"{base.name}_resume_{n:02d}").exists() for n in range(len(chain), 100)):
        raise SequenceBatchError("RESUME_CHAIN_HAS_GAP", subbatch["subbatch_id"])
    return chain


def next_output(root, subbatch):
    chain = output_chain(root, subbatch)
    base = inside(Path(root).resolve(), subbatch["canonical_output"])
    return chain, (base if not chain else base.with_name(f"{base.name}_resume_{len(chain):02d}"))


def _relative(root, path):
    return str(Path(path).resolve().relative_to(Path(root).resolve()))


def aggregate(root, manifest):
    """One row per frozen case; missing results stay NOT_RUN and settled results cannot be replaced."""
    root = Path(root).resolve()
    groups = {case: name for name, cases in manifest["groups"].items() for case in cases}
    rows = {case: {"sequence_id": case, "group": groups[case], "status": "NOT_RUN", "source_output": None}
            for subbatch in manifest["subbatches"] for case in subbatch["cases"]}
    outputs_read = []
    for subbatch in manifest["subbatches"]:
        chain = output_chain(root, subbatch)
        for position, output in enumerate(chain):
            earlier = read_json(output / "manifest.json")
            expected = manifest["expected_identity"]
            if (earlier["sequence_policy_sha256"] != manifest["sequence_policy"]["sha256"]
                    or earlier["pair_identity"]["identity_hash"] != expected["pair_identity_hash"]
                    or earlier["sequence_identity"]["identity_hash"] != expected["sequence_identity_hash"]
                    or earlier["pair_run_dir"] != manifest["pair_run_dir"]):
                raise SequenceBatchError("OUTPUT_IDENTITY_MISMATCH", _relative(root, output))
            if [r["output"] for r in earlier["resume_from"]] != [_relative(root, p) for p in chain[:position]]:
                raise SequenceBatchError("RESUME_SOURCES_DIFFER_FROM_CHAIN", _relative(root, output))
            if not set(earlier["cases"]) <= set(subbatch["cases"]):
                raise SequenceBatchError("OUTPUT_CASES_OUTSIDE_SUBBATCH", _relative(root, output))
            summary_path = output / "summary.json"
            outputs_read.append({"output": _relative(root, output), "manifest_sha256": file_hash(output / "manifest.json"),
                                 "summary_sha256": file_hash(summary_path) if summary_path.exists() else None})
            if not summary_path.exists():
                continue  # Interrupted invocation: its cases stay as they were; files remain for the next resume.
            for record in read_json(summary_path)["cases"]:
                row = rows[record["sequence_id"]]
                current = {"status": record["status"], "selected_attempt": record["selected_attempt"],
                           "selected_output": record.get("selected_output")}
                if row["status"] in SETTLED:
                    previous = {k: row[k] for k in ("status", "selected_attempt", "selected_output")}
                    if current != previous:
                        raise SequenceBatchError("SETTLED_CASE_CONFLICT", record["sequence_id"])
                    continue
                if record["status"] == "NOT_RUN":
                    continue
                row.update(current, source_output=_relative(root, output), record_hash=json_hash(record),
                           blocking_reasons=record.get("blocking_reasons", []), word_count=record["word_count"],
                           numerical_checks_passed=record["numerical_checks_passed"])
    for row in rows.values():
        row["independently_rechecked"] = False
        if row["status"] != "NUMERICAL_PASS":
            continue
        selected = inside(root, row["selected_output"])
        sequence_path = selected / "sequences" / row["sequence_id"] / f"{row['selected_attempt']}.json"
        recheck_path = selected / "independent_recheck" / f"{row['sequence_id']}.json"
        if recheck_path.exists():
            recheck = read_json(recheck_path)
            row["independently_rechecked"] = (recheck["sequence_file_sha256"] == file_hash(sequence_path)
                                              and json_hash(recheck["evidence"]) == recheck["evidence_hash"]
                                              and recheck["evidence"]["numerical_checks_passed"] is True)
            if row["independently_rechecked"]:
                row["word_occurrences"] = recheck["evidence"]["word_occurrences"]
                row["connector_groups"] = recheck["evidence"]["connector_groups"]
    ordered = [rows[case] for subbatch in manifest["subbatches"] for case in subbatch["cases"]]
    totals = {}
    for name in ("all", *manifest["groups"]):
        subset = [r for r in ordered if name == "all" or r["group"] == name]
        passed = [r for r in subset if r["status"] == "NUMERICAL_PASS" and r["independently_rechecked"]]
        totals[name] = {"denominator": len(subset), "status_counts": dict(sorted(Counter(r["status"] for r in subset).items())),
                        "independently_rechecked_pass": len(passed),
                        "planning_pass_without_recheck": sum(r["status"] == "NUMERICAL_PASS" and not r["independently_rechecked"] for r in subset),
                        "blocked_reason_counts": dict(sorted(Counter(x for r in subset for x in r.get("blocking_reasons", [])).items())),
                        "word_occurrences_in_rechecked_passes": sum(r.get("word_occurrences", 0) for r in passed),
                        "connector_groups_in_rechecked_passes": sum(r.get("connector_groups", 0) for r in passed)}
    return {"schema_version": 1, "kind": "hospital35_sequence_aggregate_v1", "denominator": len(ordered),
            "rows": ordered, "totals": totals, "outputs_read": outputs_read, "formal_pass_count": 0,
            "formal_acceptance_enabled": False}
