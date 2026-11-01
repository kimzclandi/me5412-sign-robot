"""Write a frozen 111-case manifest: 14 sub-batches of at most 8 cases with registered canonical outputs.

Usage: generate_case_manifest.py OUTPUT_JSON CANONICAL_BASE PAIR_RUN_DIR AGGREGATE_DIR
The expected identities are computed from the current (frozen) code and inputs.
"""
import json
import os
from pathlib import Path
import sys

ROOT = Path("/home/kingderman/Documents/ME5412-github-latest")
sys.path.insert(0, str(ROOT / "src"))
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

from sign_robot.pair_contract import file_hash, freeze_library, run_identity
from sign_robot.sequence_contract import load_sequence_policy, sequence_identity

SEQUENCE_POLICY = "config/sequence_policy_hospital35_v1.json"


def main(output, base, pair_run_dir, aggregate_dir):
    policy, pair_policy = load_sequence_policy(ROOT, SEQUENCE_POLICY)
    library, _ = freeze_library(ROOT, pair_policy)
    pair_identity = run_identity(library, pair_policy)
    implementation = sequence_identity(ROOT, policy, library, pair_identity)
    cases = policy["cases"]
    subbatches = [{"subbatch_id": f"s{i // 8 + 1:03d}", "cases": cases[i:i + 8],
                   "canonical_output": f"{base}/s{i // 8 + 1:03d}"} for i in range(0, len(cases), 8)]
    manifest = {"schema_version": 1, "kind": "hospital35_sequence_cases_v1",
                "sequence_policy": {"path": SEQUENCE_POLICY, "sha256": file_hash(ROOT / SEQUENCE_POLICY)},
                "pair_run_dir": pair_run_dir,
                "expected_identity": {"pair_identity_hash": pair_identity["identity_hash"],
                                      "sequence_identity_hash": implementation["identity_hash"]},
                "denominator": len(cases), "groups": {"original_12": cases[:12], "new_99": cases[12:]},
                "subbatches": subbatches,
                "limits": {"max_cases_per_subbatch": 8, "case_budget_s": 600, "soft_wall_time_s": 7200, "min_free_gib": 5,
                           "max_combinations_per_case": policy["assembly"]["max_combinations_per_case"]},
                "aggregate_directory": aggregate_dir,
                "resume_rule": "a resume writes <canonical_output>_resume_NN (01..99) in order and names every earlier output it read",
                "theoretical_full_pass": {"word_instances": 341, "connector_groups": 230},
                "formal_acceptance_enabled": False}
    path = ROOT / output
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8") as stream:
        stream.write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"case_manifest": output, "sha256": file_hash(path), "subbatches": len(subbatches),
                      "pair_identity_hash": pair_identity["identity_hash"],
                      "sequence_identity_hash": implementation["identity_hash"], "code_hash": library["code_hash"]}))


if __name__ == "__main__":
    main(*sys.argv[1:5])
