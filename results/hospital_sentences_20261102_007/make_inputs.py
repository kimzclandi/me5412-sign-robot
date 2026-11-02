"""Inputs for the nine hospital sentences, round 7: MORNING/NURSE protection ends + NURSE staged exit (2026-11-02).

User instructions (chat, 2026-11-02): MORNING's user protection ends at frame 38 (everything after it is no longer
protected); between frames 37 and 38 the retargeted right middle/ring fingers snap shut at the 10 rad/s cap, which no
connector can stop within the jerk-integral limit, so the user chose frame 37 instead; NURSE's ends at frame 75, and after it the right hand should first move away quickly, then the left wrist
should straighten. This writes protection bundle v2 from v1 with only those two records changed (v1 stays for earlier
runs), and adds planner.staged_exits: NURSE's connector leaves at its core end through stop-and-go knots (right arm
away, left forearm up off the lap, left wrist to zero), then on to the target; MORNING's moves the right arm out first,
because from frame 37 a straight route to NIGHT's crossed hands passes through the left forearm. Everything else is the
round-6 policy unchanged. Writes, once:
  config/user_protected_hospital35_v2.json
  config/transition_policy_hospital_sentences_fast_v4.json
  config/sequence_policy_hospital_sentences_v6.json
  results/hospital_sentences_20261102_007/batches/
Run from the repository root: .venv/bin/python results/hospital_sentences_20261102_007/make_inputs.py
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PAIR_SOURCE = "config/transition_policy_hospital_sentences_fast_v3.json"
PROTECTION_SOURCE = "config/user_protected_hospital35_v1.json"
PROTECTION = "config/user_protected_hospital35_v2.json"
SEQUENCE_SOURCE = "config/sequence_policy_hospital_sentences_v5.json"
PAIR_POLICY = "config/transition_policy_hospital_sentences_fast_v4.json"
SEQUENCE_POLICY = "config/sequence_policy_hospital_sentences_v6.json"
SENTENCES = ["HELLO YOU APPOINTMENT HAVE", "YOU NEED INTERPRETER", "PLEASE WAIT DOCTOR COME SOON", "YOU HURT WHERE",
             "BREATHE-DEEP", "NOW NURSE BLOOD-DRAW", "MEDICINE MORNING NIGHT TAKE", "YOU UNDERSTAND", "THANK-YOU"]
WINDOW_VERSION = "hospital35-user-protection-20261102-v2"
# end time (s), conservative end frame = ceil(end time * 30)
AMENDMENTS = {"MORNING": (1.23, 37), "NURSE": (2.5, 75)}
AMENDMENT_NOTE = ("the user shortened two protections in chat: MORNING ends at frame 37 (asked for 38; the user chose 37 "
                  "after the finger snap at 37-38 was found) and NURSE at frame 75; every other record is unchanged from v1.")
# Same sixteen runs as rounds 3-6 (cpu0-15).
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
    bundle = json.loads((ROOT / PROTECTION_SOURCE).read_text(encoding="utf-8"))
    bundle.update(bundle_id="user-protection-hospital35-20261102-v2", window_version=WINDOW_VERSION,
                  source_instruction=bundle["source_instruction"] + " v2 (2026-11-02): " + AMENDMENT_NOTE)
    for record in bundle["records"]:
        if record["gloss"] in AMENDMENTS:
            end_s, end_frame = AMENDMENTS[record["gloss"]]
            old = record["user_interval_text"]
            record.update(protection_id=f"hospital35-20261102-v2-{record['gloss']}",
                          user_interval_s=[record["user_interval_s"][0], end_s],
                          protected_core_frames=[record["protected_core_frames"][0], end_frame],
                          user_interval_text=f"{record['user_interval_s'][0]}–{end_s} s (user chat 2026-11-02: end at "
                                             f"frame {end_frame}; was {old})",
                          binding_basis=record["binding_basis"] + "; end amended by the user in chat on 2026-11-02")
    write_new(ROOT / PROTECTION, bundle)

    pair = json.loads((ROOT / PAIR_SOURCE).read_text(encoding="utf-8"))
    pair["policy_id"] = "group3-hospital-sentences-fast-v4"
    pair["endpoints"].update(window_version=WINDOW_VERSION, protection_file=PROTECTION,
                             protection_bundle_sha256=sha(ROOT / PROTECTION))
    # Stage options were screened offline for static clearance along the knot polyline (rest-to-rest quintics follow it).
    # NURSE: right hand away first; the left wrist cannot straighten in place (the left thumb would enter the torso by
    # 52 mm), so the left forearm lifts off the lap before the wrist goes to zero. MORNING: from its new core end the
    # right hand would pass through the left forearm on the way to NIGHT's crossed hands, so it moves out first.
    pair["planner"]["staged_exits"] = {"version": "staged_exit_v1", "words": {
        "NURSE": {"stages": [
            {"group": "right_arm", "to": ["rest", "ik:out:2", "ik:out+up:2", "target"]},
            {"group": "left_upper_arm", "to": ["ik:out+up+forward:3", "ik:out+forward:3", "ik:out+up:3"]},
            {"group": "left_wrist", "to": ["zero"]}]},
        "MORNING": {"stages": [
            {"group": "right_arm", "to": ["ik:out:2", "ik:out:3", "ik:out+up:2", "ik:out+up:3"]}]}}}
    write_new(ROOT / PAIR_POLICY, pair)

    sequence = json.loads((ROOT / SEQUENCE_SOURCE).read_text(encoding="utf-8"))
    sequence.update(policy_id="group3-hospital-sentences-sequence-v6",
                    pair_policy={"path": PAIR_POLICY, "sha256": sha(ROOT / PAIR_POLICY)})
    sequence["case_note"] = sequence["case_note"].replace(
        "round 6 (round 3/4 plus the retained-edge screen v2):",
        "round 7 (round 6 with the user's MORNING/NURSE protection ends and NURSE's staged exit):")
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
