"""Inputs for the nine hospital sentences, round 5: retained-edge screen (2026-11-01).

Round 4 (results/hospital_sentences_20261101_004) passed 7/7, but the user saw a twisted left hand in
NOW NURSE BLOOD-DRAW: the NURSE cut kept source frames 80-98, where the retargeted clip flips the left shoulder yaw
to its -2.62 rad stop at the 15 rad/s cap. Two more kept edges press an arm joint on a limit their protected core never
touches (MEDICINE frames 73-86, DOCTOR frames 28-33). This round adds endpoints.retained_edge_screen
(no_new_arm_limit_contact_v1): such frames may not be kept strictly between a protected core and its cut, so the
connector replaces them. NURSE's only clean exit is then frame 80, where the retargeter has clamped the left wrist roll
on its stop while the replay slope still runs into it; endpoints.clamped_joint_stop (clamped_joint_stop_v1) takes such
a joint as resting on its stop at the cut. Everything else is the round-4 policy unchanged. Writes, once:
  config/transition_policy_hospital_sentences_fast_v2.json
  config/sequence_policy_hospital_sentences_v4.json
  results/hospital_sentences_20261101_005/batches/
Run from the repository root: .venv/bin/python results/hospital_sentences_20261101_005/make_inputs.py
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PAIR_SOURCE = "config/transition_policy_hospital_sentences_fast_v1.json"
SEQUENCE_SOURCE = "config/sequence_policy_hospital_sentences_v3.json"
PAIR_POLICY = "config/transition_policy_hospital_sentences_fast_v2.json"
SEQUENCE_POLICY = "config/sequence_policy_hospital_sentences_v4.json"
SENTENCES = ["HELLO YOU APPOINTMENT HAVE", "YOU NEED INTERPRETER", "PLEASE WAIT DOCTOR COME SOON", "YOU HURT WHERE",
             "BREATHE-DEEP", "NOW NURSE BLOOD-DRAW", "MEDICINE MORNING NIGHT TAKE", "YOU UNDERSTAND", "THANK-YOU"]
# Same sixteen runs as round 3/4 (cpu0-15).
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
    pair["policy_id"] = "group3-hospital-sentences-fast-v2"
    pair["endpoints"]["retained_edge_screen"] = "no_new_arm_limit_contact_v1"
    pair["endpoints"]["clamped_joint_stop"] = "clamped_joint_stop_v1"
    write_new(ROOT / PAIR_POLICY, pair)

    sequence = json.loads((ROOT / SEQUENCE_SOURCE).read_text(encoding="utf-8"))
    sequence.update(policy_id="group3-hospital-sentences-sequence-v4",
                    pair_policy={"path": PAIR_POLICY, "sha256": sha(ROOT / PAIR_POLICY)})
    sequence["case_note"] = sequence["case_note"].replace(
        "round 3:", "round 5 (round 3/4 plus the retained-edge screen):")
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
