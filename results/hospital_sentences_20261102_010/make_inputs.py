"""Inputs for the nine hospital sentences, round 10: the first solve on Group 2's clips-v2 with protection bundle v5.

User instructions (chat, 2026-11-02): run the trajectory planning on group3/clips-v2 with 12 threads; run now without
first fixing the 34 failing tests (recorded in TASK-29; tests are part of the code identity, so this run is
reproducible only at this commit); drop NURSE's staged exit, which was designed for the old NURSE clip (left hand at the
lap) and does not fit the new NURSE end pose (left forearm across the chest, right hand beside the left wrist).
The pair policy is round 8's fast_v5 with three changes and nothing else:
  - endpoints: protection bundle v5 (NURSE f23-f79, INTERPRETER f19-f40, everything else as v3, which has HURT f37);
  - planner.staged_exits: NURSE removed; MORNING's staged exit (right arm out first) kept;
  - planner budget: round 9's longer search (720 -> 1800 s per pair, RRT 240 -> 600 s), as the handoff allows,
    because round 8's YOU->HURT and HURT->WHERE stopped on the wall-time limit.
The sequence policy is v7's seven multi-word sentences pointing at fast_v7. Writes, once:
  config/transition_policy_hospital_sentences_fast_v7.json
  config/sequence_policy_hospital_sentences_v9.json
  results/hospital_sentences_20261102_010/batches/
Run from the repository root: .venv/bin/python results/hospital_sentences_20261102_010/make_inputs.py
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PAIR_SOURCE = "config/transition_policy_hospital_sentences_fast_v5.json"
SEQUENCE_SOURCE = "config/sequence_policy_hospital_sentences_v7.json"
PROTECTION = "config/user_protected_hospital35_v5.json"
PAIR_POLICY = "config/transition_policy_hospital_sentences_fast_v7.json"
SEQUENCE_POLICY = "config/sequence_policy_hospital_sentences_v9.json"
SENTENCES = ["HELLO YOU APPOINTMENT HAVE", "YOU NEED INTERPRETER", "PLEASE WAIT DOCTOR COME SOON", "YOU HURT WHERE",
             "BREATHE-DEEP", "NOW NURSE BLOOD-DRAW", "MEDICINE MORNING NIGHT TAKE", "YOU UNDERSTAND", "THANK-YOU"]
# Twelve runs (cpu0-11). Pairs that touch a changed word or were hard before get a run of their own; the rest share.
WORKERS = [
    ["NURSE__BLOOD-DRAW"], ["NOW__NURSE"], ["NEED__INTERPRETER"], ["YOU__HURT"], ["HURT__WHERE"],
    ["MEDICINE__MORNING"], ["PLEASE__WAIT"], ["WAIT__DOCTOR", "YOU__UNDERSTAND"], ["MORNING__NIGHT", "HELLO__YOU"],
    ["NIGHT__TAKE", "YOU__NEED"], ["APPOINTMENT__HAVE", "DOCTOR__COME"], ["YOU__APPOINTMENT", "COME__SOON"],
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def main():
    bundle = json.loads((ROOT / PROTECTION).read_text(encoding="utf-8"))
    pair = json.loads((ROOT / PAIR_SOURCE).read_text(encoding="utf-8"))
    pair["policy_id"] = "group3-hospital-sentences-fast-v7"
    pair["endpoints"].update(window_version=bundle["window_version"], protection_file=PROTECTION,
                             protection_bundle_sha256=sha(ROOT / PROTECTION))
    del pair["planner"]["staged_exits"]["words"]["NURSE"]
    pair["planner"]["budget"]["wall_time_s"] = 1800.0
    pair["planner"]["rrt"]["wall_time_s"] = 600.0
    write_new(ROOT / PAIR_POLICY, pair)

    sequence = json.loads((ROOT / SEQUENCE_SOURCE).read_text(encoding="utf-8"))
    sequence.update(policy_id="group3-hospital-sentences-sequence-v9",
                    pair_policy={"path": PAIR_POLICY, "sha256": sha(ROOT / PAIR_POLICY)})
    sequence["case_note"] = sequence["case_note"].replace(
        "round 8 (round 7 with stop-free smooth connectors and sign-level dynamics limits):",
        "round 10 (round 8 on clips-v2 with protection bundle v5, NURSE's staged exit dropped and round 9's longer search):")
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
        "definition": {"sentences": "the 17 ordered pairs of the user's sentences over twelve parallel runs",
                       "rest": "every other pair, universe order; present only so the manifest covers the universe"},
        "batches": entries, "order": [e["batch_id"] for e in entries],
        "limits": {"max_pairs_per_batch": 16, "soft_wall_time_s": 7200, "min_free_gib": 5}})
    print(json.dumps({"runs": len(WORKERS), "sentence_pairs": len(assigned),
                      "manifest_sha256": sha(OUT / "batches/manifest.json")}))


if __name__ == "__main__":
    main()
