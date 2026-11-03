"""Inputs for the nine hospital sentences, round 9: YOU HURT WHERE alone, with HURT's protection starting at frame 37.

User instruction (chat, 2026-11-02): HURT starts at frame 37; optimise the sentence YOU HURT WHERE on its own. HURT's
v1/v2 protection [27, 57] began on the retargeted left-arm flip: at frames 29-34 the left shoulder yaw swings at the
15 rad/s cap (left shoulder pitch and wrist pitch near 12-14 rad/s), and round 8's YOU->HURT connector entered exactly at
frame 27, so the flip played. This writes protection bundle v3 from v2 with only HURT's start changed (v2 stays for
earlier runs). The pair policy is round 8's with the new bundle; because this round plans only the sentence's two pairs,
each pair gets a longer search (720 -> 1800 s, RRT 240 -> 600 s): in round 8 both of these pairs stopped on the wall-time
limit (PAIR_WALL_TIME_LIMIT), not on an exhausted route list. Writes, once:
  config/user_protected_hospital35_v3.json
  config/transition_policy_hospital_sentences_fast_v6.json
  config/sequence_policy_hospital_sentences_v8.json
  results/hospital_sentences_20261102_009/batches/
Run from the repository root: .venv/bin/python results/hospital_sentences_20261102_009/make_inputs.py
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PAIR_SOURCE = "config/transition_policy_hospital_sentences_fast_v5.json"
PROTECTION_SOURCE = "config/user_protected_hospital35_v2.json"
PROTECTION = "config/user_protected_hospital35_v3.json"
SEQUENCE_SOURCE = "config/sequence_policy_hospital_sentences_v7.json"
PAIR_POLICY = "config/transition_policy_hospital_sentences_fast_v6.json"
SEQUENCE_POLICY = "config/sequence_policy_hospital_sentences_v8.json"
SENTENCES = ["YOU HURT WHERE"]
WINDOW_VERSION = "hospital35-user-protection-20261102-v3"
# start time (s), conservative start frame = floor(start time * 30): floor(37.2) = 37
AMENDMENTS = {"HURT": (1.24, 37)}
AMENDMENT_NOTE = "the user moved HURT's start to frame 37 in chat; every other record is unchanged from v2."
WORKERS = [["YOU__HURT"], ["HURT__WHERE"]]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def main():
    bundle = json.loads((ROOT / PROTECTION_SOURCE).read_text(encoding="utf-8"))
    bundle.update(bundle_id="user-protection-hospital35-20261102-v3", window_version=WINDOW_VERSION,
                  source_instruction=bundle["source_instruction"] + " v3 (2026-11-02): " + AMENDMENT_NOTE)
    for record in bundle["records"]:
        if record["gloss"] in AMENDMENTS:
            start_s, start_frame = AMENDMENTS[record["gloss"]]
            old = record["user_interval_text"]
            record.update(protection_id=f"hospital35-20261102-v3-{record['gloss']}",
                          user_interval_s=[start_s, record["user_interval_s"][1]],
                          protected_core_frames=[start_frame, record["protected_core_frames"][1]],
                          user_interval_text=f"{start_s}–{record['user_interval_s'][1]} s (user chat 2026-11-02: start at "
                                             f"frame {start_frame}; was {old})",
                          binding_basis=record["binding_basis"] + "; start amended by the user in chat on 2026-11-02")
    write_new(ROOT / PROTECTION, bundle)

    pair = json.loads((ROOT / PAIR_SOURCE).read_text(encoding="utf-8"))
    pair["policy_id"] = "group3-hospital-sentences-fast-v6"
    pair["endpoints"].update(window_version=WINDOW_VERSION, protection_file=PROTECTION,
                             protection_bundle_sha256=sha(ROOT / PROTECTION))
    # Two pairs only, one core each: a longer search instead of round 8's 720 s, which both pairs ran out of.
    pair["planner"]["budget"]["wall_time_s"] = 1800.0
    pair["planner"]["rrt"]["wall_time_s"] = 600.0
    write_new(ROOT / PAIR_POLICY, pair)

    sequence = json.loads((ROOT / SEQUENCE_SOURCE).read_text(encoding="utf-8"))
    sequence.update(policy_id="group3-hospital-sentences-sequence-v8", cases=["YOU__HURT__WHERE"],
                    pair_policy={"path": PAIR_POLICY, "sha256": sha(ROOT / PAIR_POLICY)})
    sequence["case_note"] = sequence["case_note"].replace(
        "round 8 (round 7 with stop-free smooth connectors and sign-level dynamics limits):",
        "round 9 (YOU HURT WHERE only: round 8 with HURT's protection starting at frame 37 and a longer pair search):")
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
        "definition": {"sentences": "the 2 ordered pairs of YOU HURT WHERE, one batch per parallel run",
                       "rest": "every other pair, universe order; present only so the manifest covers the universe"},
        "batches": entries, "order": [e["batch_id"] for e in entries],
        "limits": {"max_pairs_per_batch": 16, "soft_wall_time_s": 7200, "min_free_gib": 5}})
    print(json.dumps({"runs": len(WORKERS), "sentence_pairs": len(assigned),
                      "manifest_sha256": sha(OUT / "batches/manifest.json")}))


if __name__ == "__main__":
    main()
