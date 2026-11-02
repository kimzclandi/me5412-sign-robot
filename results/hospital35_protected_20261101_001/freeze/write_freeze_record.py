"""P0-7 freeze record: code/input/policy/environment identities, frozen definitions and test logs.

Usage: write_freeze_record.py FOCUSED_LOG FULL_LOG PREFLIGHT_DIR CASE_MANIFEST
Writes results/hospital35_protected_20261101_001/freeze/freeze.json once (never overwrites).
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path("/home/kingderman/Documents/ME5412-github-latest")
sys.path.insert(0, str(ROOT / "src"))
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

from sign_robot.pair_contract import file_hash, freeze_library, load_policy, read_json, run_identity
from sign_robot.sequence_contract import load_sequence_policy, sequence_code_files, sequence_identity

RUN = "results/hospital35_protected_20261101_001"
PAIR_POLICY = "config/transition_policy_user_protected_hospital35_v1.json"
SEQUENCE_POLICY = "config/sequence_policy_hospital35_v1.json"


def log_record(relative):
    text = (ROOT / relative).read_text()
    summary = [line for line in text.splitlines() if re.search(r"\d+ (passed|failed)", line)]
    exit_line = [line for line in text.splitlines() if line.startswith("exit ")]
    return {"path": relative, "sha256": file_hash(ROOT / relative), "command": text.splitlines()[0],
            "summary": summary[-1] if summary else None, "exit": exit_line[-1] if exit_line else None}


def main(focused, full, preflight_dir, case_manifest):
    pair_policy = load_policy(ROOT / PAIR_POLICY, supported_versions=(2,))
    sequence_policy, _ = load_sequence_policy(ROOT, SEQUENCE_POLICY)
    library, _ = freeze_library(ROOT, pair_policy)
    identity = run_identity(library, pair_policy)
    implementation = sequence_identity(ROOT, sequence_policy, library, identity)
    preflight = read_json(ROOT / preflight_dir / "preflight.json")
    cases = read_json(ROOT / case_manifest)
    batches = f"{RUN}/batches/manifest.json"
    record = {
        "schema_version": 1, "kind": "hospital35_freeze_record_v1",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git": {"branch": subprocess.run(["git", "branch", "--show-current"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
                "head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
                "note": "uncommitted and untracked files are part of the working tree; the code hash covers them"},
        "pair_identity": identity, "sequence_identity": implementation,
        "pair_code_files": library["code_files"], "pair_code_file_count": len(library["code_files"]),
        "sequence_code_file_count": len(sequence_code_files(ROOT, library["code_files"])),
        "environment": library["environment"],
        "inputs": {name: {"path": path, "sha256": file_hash(ROOT / path)} for name, path in (
            ("ods_copy", "data/user_protection/hospital35_20261101/protection_intervals.ods"),
            ("protection_bundle", "config/user_protected_hospital35_v1.json"),
            ("protection_provenance", "config/user_protected_hospital35_v1.provenance.json"),
            ("pair_policy", PAIR_POLICY), ("sequence_policy", SEQUENCE_POLICY),
            ("hospital_mapping", "motions/hospital_v1_motions.json"),
            ("contract", pair_policy["contract"]["path"]))},
        "library_version": library["library_version"], "model_hash": library["model_hash"],
        "frozen_definitions": {"batch_manifest": {"path": batches, "sha256": file_hash(ROOT / batches),
                                                  "batches": len(read_json(ROOT / batches)["batches"])},
                               "case_manifest": {"path": case_manifest, "sha256": file_hash(ROOT / case_manifest),
                                                 "denominator": cases["denominator"], "subbatches": len(cases["subbatches"]),
                                                 "expected_identity": cases["expected_identity"]}},
        "case_manifest_identity_matches": cases["expected_identity"] == {
            "pair_identity_hash": identity["identity_hash"], "sequence_identity_hash": implementation["identity_hash"]},
        "preflight_final": {"path": f"{preflight_dir}/preflight.json", "sha256": file_hash(ROOT / preflight_dir / "preflight.json"),
                            "identity_matches_freeze": preflight["identity"] == identity, "status": preflight["status"],
                            "label_counts": preflight["label_counts"],
                            "affected_pairs_any": preflight["affected_pairs"]["any"]["count"]},
        "tests": {"focused": log_record(focused), "full": log_record(full)},
        "rules_after_freeze": ["no edits to src/sign_robot, tests, identity scripts, docs/README*.md or project_overview.py",
                               "config, policies, bundle and motions unchanged", "a needed code change means a new version and a new run_id"],
        "formal_acceptance_enabled": False,
    }
    path = ROOT / RUN / "freeze/freeze.json"
    with open(path, "x", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"freeze": str(path.relative_to(ROOT)), "pair_identity_hash": identity["identity_hash"],
                      "code_hash": identity["code_hash"], "sequence_identity_hash": implementation["identity_hash"],
                      "pair_code_files": record["pair_code_file_count"], "sequence_code_files": record["sequence_code_file_count"],
                      "case_manifest_identity_matches": record["case_manifest_identity_matches"],
                      "preflight_identity_matches": record["preflight_final"]["identity_matches_freeze"],
                      "tests": {k: (v["summary"], v["exit"]) for k, v in record["tests"].items()}}))


if __name__ == "__main__":
    main(*sys.argv[1:5])
