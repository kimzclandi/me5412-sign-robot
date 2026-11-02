"""Inputs for the nine hospital sentences under connector-only scope (2026-11-01, user decision).

The user scoped group 3 to the transitions between two word motions only: source-motion defects belong to group 2
and must not fail a connector. This writes, once (files are never overwritten):
  config/transition_policy_hospital_sentences_connector_only_v1.json  pair policy: the retry-budget policy
      (240 s per pair) with quality.full_clip_method = connector-only v4; every connector limit is unchanged
  config/sequence_policy_hospital_sentences_v1.json  the seven multi-word sentences, same sequence limits
  results/hospital_sentences_20261101_001/batches/  sentence pairs in four batches (one per parallel run), then
      the rest of the 1,225-pair universe in 16-pair batches that are not run (the manifest must cover it)
Run from the repository root: .venv/bin/python results/hospital_sentences_20261101_001/make_inputs.py
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PAIR_SOURCE = "config/transition_policy_user_protected_hospital35_retry_budget_v1.json"
SEQUENCE_SOURCE = "config/sequence_policy_hospital35_v1.json"
PAIR_POLICY = "config/transition_policy_hospital_sentences_connector_only_v1.json"
SEQUENCE_POLICY = "config/sequence_policy_hospital_sentences_v1.json"
SENTENCES = ["HELLO YOU APPOINTMENT HAVE", "YOU NEED INTERPRETER", "PLEASE WAIT DOCTOR COME SOON", "YOU HURT WHERE",
             "BREATHE-DEEP", "NOW NURSE BLOOD-DRAW", "MEDICINE MORNING NIGHT TAKE", "YOU UNDERSTAND", "THANK-YOU"]
# Pairs with no candidate under the 30 s budget are spread over the four runs first.
WORKERS = [
    ["YOU__HURT", "HURT__WHERE", "MEDICINE__MORNING", "HELLO__YOU", "COME__SOON"],
    ["YOU__APPOINTMENT", "APPOINTMENT__HAVE", "MORNING__NIGHT", "YOU__NEED"],
    ["PLEASE__WAIT", "WAIT__DOCTOR", "NIGHT__TAKE", "DOCTOR__COME"],
    ["NURSE__BLOOD-DRAW", "NEED__INTERPRETER", "NOW__NURSE", "YOU__UNDERSTAND"],
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def main():
    pair = json.loads((ROOT / PAIR_SOURCE).read_text(encoding="utf-8"))
    pair["policy_id"] = "group3-hospital-sentences-connector-only-v1"
    pair["quality"]["full_clip_method"] = "connector_only_interior_fd_and_analytic_connector_v4"
    write_new(ROOT / PAIR_POLICY, pair)

    sequence = json.loads((ROOT / SEQUENCE_SOURCE).read_text(encoding="utf-8"))
    cases = ["__".join(s.split()) for s in SENTENCES if len(s.split()) >= 2]
    sequence.update(policy_id="group3-hospital-sentences-sequence-v1",
                    pair_policy={"path": PAIR_POLICY, "sha256": sha(ROOT / PAIR_POLICY)}, cases=cases,
                    case_note="The user's nine hospital sentences (2026-11-01). Single-word BREATHE-DEEP and THANK-YOU "
                              "need no connector and are not cases. Connector-only scope: source-motion findings are "
                              "reported, never gated. Not verified ASL; no human review.")
    write_new(ROOT / SEQUENCE_POLICY, sequence)

    needed = [f"{a}__{b}" for s in SENTENCES for a, b in zip(s.split(), s.split()[1:])]
    assigned = [p for worker in WORKERS for p in worker]
    if sorted(assigned) != sorted(set(needed)) or len(assigned) != len(set(assigned)):
        raise SystemExit("worker assignment must cover the sentence pairs exactly once")
    glosses = pair["scope"]["expected_glosses"]
    universe = [f"{a}__{b}" for a in glosses for b in glosses]
    rest = [p for p in universe if p not in assigned]
    groups = [("sentences", f"sentences_{i + 1:03d}", w) for i, w in enumerate(WORKERS)]
    groups += [("rest", f"rest_{i // 16 + 1:03d}", rest[i:i + 16]) for i in range(0, len(rest), 16)]
    entries = []
    for group, batch_id, pairs in groups:
        path = OUT / "batches" / f"{batch_id}.json"
        write_new(path, {"pair_ids": pairs})
        entries.append({"batch_id": batch_id, "group": group, "file": str(path.relative_to(ROOT)),
                        "sha256": sha(path), "pair_count": len(pairs)})
    write_new(OUT / "batches/manifest.json", {
        "schema_version": 1, "kind": "hospital35_pair_batches_v1",
        "policy": {"path": PAIR_POLICY, "sha256": sha(ROOT / PAIR_POLICY)},
        "group_counts": {"sentences": len(assigned), "rest": len(rest)}, "pair_universe_count": len(universe),
        "definition": {"sentences": "the 17 ordered pairs of the user's sentences, one batch per parallel run",
                       "rest": "every other pair, universe order; present only so the manifest covers the universe"},
        "batches": entries, "order": [e["batch_id"] for e in entries],
        "limits": {"max_pairs_per_batch": 16, "soft_wall_time_s": 7200, "min_free_gib": 5}})
    print(json.dumps({"cases": cases, "sentence_pairs": len(assigned), "batches": len(entries),
                      "manifest_sha256": sha(OUT / "batches/manifest.json")}))


if __name__ == "__main__":
    main()
