"""Frozen retry definitions from the final P1-3 table, by a fixed rule (written once, never overwritten).

Usage: generate_retry_definitions.py PROGRESS_JSON

Rule:
  A     = ordered pairs of two preflight-clear words that ended TIMEOUT without a curve in P1-3;
  cases = the frozen 111 sequence cases that did not have every pair pass in P1-3 and whose failing pairs all lie in A;
  B     = every pair those cases use (re-planned so one pair run can supply the whole sequence).
The retry run plans A | B under the retry-budget policy. Its batch manifest still covers the whole universe:
retry batches (at most 8 pairs) come first and the other pairs sit in "unrun" batches that are never executed.
"""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path("/home/kingderman/Documents/ME5412-github-latest")
sys.path.insert(0, str(ROOT / "src"))
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

from sign_robot.pair_contract import freeze_library, run_identity
from sign_robot.sequence_contract import load_sequence_policy, sequence_identity

RUN = "results/hospital35_protected_20261101_001"
OUT = f"{RUN}/retry_budget_001"
PAIR_POLICY = "config/transition_policy_user_protected_hospital35_retry_budget_v1.json"
BASE_SEQUENCE_POLICY = "config/sequence_policy_hospital35_v1.json"
SEQUENCE_POLICY = "config/sequence_policy_hospital35_retry_budget_v1.json"
RUN_ID = "hospital35_retry_budget_001"


def sha(relative):
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def write_new(relative, value):
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def edges(case):
    words = case.split("__")
    return [f"{a}__{b}" for a, b in zip(words, words[1:])]


def main(progress_path):
    progress = json.loads((ROOT / progress_path).read_text(encoding="utf-8"))
    rows = {r["pair_id"]: r for r in progress["rows"]}
    preflight = json.loads((ROOT / RUN / "preflight_final/preflight.json").read_text(encoding="utf-8"))
    clear = [w for w, v in preflight["words"].items() if "PREFLIGHT_CLEAR" in v["labels"]]
    pair_policy = json.loads((ROOT / PAIR_POLICY).read_text(encoding="utf-8"))
    glosses = pair_policy["scope"]["expected_glosses"]
    universe = [f"{s}__{t}" for s in glosses for t in glosses]
    clear_pairs = [p for p in universe if set(p.split("__")) <= set(clear)]
    done = ("NUMERICAL_PASS", "NUMERICAL_FAIL", "NO_CURVE_DIAGNOSIS")
    assert all(rows[p]["state"] in done for p in clear_pairs), "P1-3 has clear-word pairs without a complete review"
    timeouts = [p for p in clear_pairs if rows[p]["state"] == "NO_CURVE_DIAGNOSIS" and rows[p].get("status") == "TIMEOUT"]

    base = json.loads((ROOT / BASE_SEQUENCE_POLICY).read_text(encoding="utf-8"))
    for case in base["cases"]:
        assert all(rows[p]["state"] in done for p in edges(case)), f"{case} depends on a pair without a complete review"
    cases = [c for c in base["cases"]
             if any(rows[p]["state"] != "NUMERICAL_PASS" for p in edges(c))
             and all(p in timeouts for p in edges(c) if rows[p]["state"] != "NUMERICAL_PASS")]
    needed = {p for c in cases for p in edges(c)}
    retry = [p for p in universe if p in set(timeouts) | needed]

    batches, order = [], []
    unrun = [p for p in universe if p not in set(retry)]
    for group, pairs, size in (("retry", retry, 8), ("unrun", unrun, 16)):
        for start in range(0, len(pairs), size):
            batch_id = f"{group}_{start // size + 1:03d}"
            relative = f"{OUT}/batches/{batch_id}.json"
            write_new(relative, {"pair_ids": pairs[start:start + size]})
            batches.append({"batch_id": batch_id, "group": group, "file": relative, "sha256": sha(relative),
                            "pair_count": len(pairs[start:start + size])})
            order.append(batch_id)
    manifest = {"schema_version": 1, "kind": "hospital35_pair_batches_v1",
                "policy": {"path": PAIR_POLICY, "sha256": sha(PAIR_POLICY)},
                "group_counts": {"retry": len(retry), "unrun": len(unrun)}, "pair_universe_count": len(universe),
                "definition": {"retry": "A | B of the retry rule in generate_retry_definitions.py, universe order",
                               "unrun": "every other pair; listed only because the manifest must cover the universe, never executed"},
                "source_progress": {"path": progress_path, "sha256": sha(progress_path)},
                "batches": batches, "order": order,
                "limits": {"max_pairs_per_batch": 8, "soft_wall_time_s": 14400, "min_free_gib": 5}}
    write_new(f"{OUT}/batches/manifest.json", manifest)

    definitions = {"schema_version": 1, "kind": "hospital35_retry_budget_definitions_v1", "run_id": RUN_ID,
                   "pair_policy": {"path": PAIR_POLICY, "sha256": sha(PAIR_POLICY)},
                   "batch_manifest": {"path": f"{OUT}/batches/manifest.json", "sha256": sha(f"{OUT}/batches/manifest.json")},
                   "retry_batches": [b["batch_id"] for b in batches if b["group"] == "retry"],
                   "clear_words": clear, "timeout_pairs": timeouts, "cases": cases,
                   "extra_pairs_for_cases": sorted(needed - set(timeouts)), "retry_pairs": retry,
                   "source_progress": {"path": progress_path, "sha256": sha(progress_path)},
                   "sequence_policy": None, "case_manifest": None, "formal_acceptance_enabled": False}
    if cases:
        policy = {**base, "policy_id": "group3-hospital35-sequence-development-retry-budget-v1",
                  "pair_policy": {"path": PAIR_POLICY, "sha256": sha(PAIR_POLICY)}, "cases": cases,
                  "case_note": ("The frozen hospital35 sequence cases that P1-3 left blocked only by TIMEOUT pairs of "
                                "preflight-clear words, re-run on the retry-budget pair run. Directed engineering coverage only.")}
        write_new(SEQUENCE_POLICY, policy)
        loaded, loaded_pair_policy = load_sequence_policy(ROOT, SEQUENCE_POLICY)
        library, _ = freeze_library(ROOT, loaded_pair_policy)
        pair_identity = run_identity(library, loaded_pair_policy)
        implementation = sequence_identity(ROOT, loaded, library, pair_identity)
        subbatches = [{"subbatch_id": f"s{i // 8 + 1:03d}", "cases": cases[i:i + 8],
                       "canonical_output": f"{OUT}/sequences_001/s{i // 8 + 1:03d}"} for i in range(0, len(cases), 8)]
        case_manifest = {"schema_version": 1, "kind": "hospital35_sequence_cases_v1",
                         "sequence_policy": {"path": SEQUENCE_POLICY, "sha256": sha(SEQUENCE_POLICY)},
                         "pair_run_dir": f"{OUT}/pair_runs/{RUN_ID}",
                         "expected_identity": {"pair_identity_hash": pair_identity["identity_hash"],
                                               "sequence_identity_hash": implementation["identity_hash"]},
                         "denominator": len(cases), "groups": {"retry_cases": cases}, "subbatches": subbatches,
                         "limits": {"max_cases_per_subbatch": 8, "case_budget_s": 600, "soft_wall_time_s": 7200, "min_free_gib": 5,
                                    "max_combinations_per_case": loaded["assembly"]["max_combinations_per_case"]},
                         "aggregate_directory": f"{OUT}/sequences_001/aggregate",
                         "resume_rule": "a resume writes <canonical_output>_resume_NN (01..99) in order and names every earlier output it read",
                         "theoretical_full_pass": {"word_instances": sum(len(c.split("__")) for c in cases),
                                                   "connector_groups": sum(len(edges(c)) for c in cases)},
                         "formal_acceptance_enabled": False}
        write_new(f"{OUT}/sequence_cases/case_manifest.json", case_manifest)
        definitions["sequence_policy"] = {"path": SEQUENCE_POLICY, "sha256": sha(SEQUENCE_POLICY)}
        definitions["case_manifest"] = {"path": f"{OUT}/sequence_cases/case_manifest.json",
                                        "sha256": sha(f"{OUT}/sequence_cases/case_manifest.json"),
                                        "subbatches": [s["subbatch_id"] for s in subbatches]}
    write_new(f"{OUT}/definitions.json", definitions)
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in definitions.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1])
