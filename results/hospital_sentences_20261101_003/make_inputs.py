"""Inputs for the nine hospital sentences, round 3: faster transitions + return to rest (2026-11-01).

Round 2 (results/hospital_sentences_20261101_002) passed 7/7, but its selection rule preferred the lowest peak jerk,
which picks long, slow connectors (up to 180 frames). The user asked for (1) transitions about as fast as the signs and
(2) a return to the hands-down starting pose after each sentence. This round changes only the selection rule
(fewest frames between the two protected cores, smoothness as tie-break) and adds a planned rest tail per sentence.
Planner, thresholds and budgets are the round-2 braking policy unchanged. Writes, once:
  config/transition_policy_hospital_sentences_fast_v1.json
  config/sequence_policy_hospital_sentences_v3.json
  results/hospital_sentences_20261101_003/batches/
Run from the repository root: .venv/bin/python results/hospital_sentences_20261101_003/make_inputs.py
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PAIR_SOURCE = "config/transition_policy_hospital_sentences_braking_v1.json"
SEQUENCE_SOURCE = "config/sequence_policy_hospital_sentences_v2.json"
PAIR_POLICY = "config/transition_policy_hospital_sentences_fast_v1.json"
SEQUENCE_POLICY = "config/sequence_policy_hospital_sentences_v3.json"
SENTENCES = ["HELLO YOU APPOINTMENT HAVE", "YOU NEED INTERPRETER", "PLEASE WAIT DOCTOR COME SOON", "YOU HURT WHERE",
             "BREATHE-DEEP", "NOW NURSE BLOOD-DRAW", "MEDICINE MORNING NIGHT TAKE", "YOU UNDERSTAND", "THANK-YOU"]
# Sixteen runs on cpu0-15; the four pairs with the fewest round-2 passes come first (cpu0-3), and two
# pairs with many round-2 passes share the last run.
WORKERS = [
    ["NURSE__BLOOD-DRAW"], ["MORNING__NIGHT"], ["PLEASE__WAIT"], ["NIGHT__TAKE"], ["WAIT__DOCTOR"],
    ["MEDICINE__MORNING"], ["YOU__HURT"], ["YOU__APPOINTMENT"], ["YOU__NEED"], ["HELLO__YOU"], ["NOW__NURSE"],
    ["NEED__INTERPRETER"], ["YOU__UNDERSTAND"], ["HURT__WHERE"], ["DOCTOR__COME"], ["APPOINTMENT__HAVE", "COME__SOON"],
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
    pair["policy_id"] = "group3-hospital-sentences-fast-v1"
    pair["selection_rule"] = "numerical_pass_then_core_gap_then_smoothness_v1"
    write_new(ROOT / PAIR_POLICY, pair)

    sequence = json.loads((ROOT / SEQUENCE_SOURCE).read_text(encoding="utf-8"))
    sequence.update(policy_id="group3-hospital-sentences-sequence-v3",
                    pair_policy={"path": PAIR_POLICY, "sha256": sha(ROOT / PAIR_POLICY)})
    sequence["assembly"]["rest_tail"] = {"version": "rest_tail_v1", "rest_pose": "library_first_frame_v1",
                                         "max_exit_frames": 60}
    sequence["case_note"] = (
        "The user's nine hospital sentences (2026-11-01), round 3: the pair run selects the candidate with the fewest "
        "frames between the two protected cores, and every case ends with a planned return to the library rest pose "
        "(hands down). Single-word BREATHE-DEEP and THANK-YOU need no connector and are not cases. Connector-only "
        "scope: source-motion findings are reported, never gated. Not verified ASL; no human review.")
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
    print(json.dumps({"runs": len(WORKERS), "sentence_pairs": len(assigned),
                      "manifest_sha256": sha(OUT / "batches/manifest.json")}))


if __name__ == "__main__":
    main()
