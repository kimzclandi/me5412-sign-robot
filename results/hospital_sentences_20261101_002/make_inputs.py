"""Inputs for the nine hospital sentences, round 2: connector-only v4 + boundary braking (2026-11-01).

Round 1 (results/hospital_sentences_20261101_001) left five pairs without a candidate: at the shortlisted cuts
the source still moved at 8-10 rad/s toward a joint limit, so a connector that must keep that velocity overshoots.
This round adds planner.boundary_braking (stop_and_go_v1: when a route cannot be timed, stop first and start from
rest on entry over a fixed short segment) and brakeable cut pairs interleaved into the shortlist. Every connector
threshold is unchanged; the per-pair wall budget doubles (480 s) and the pairs run on nine cores. Writes, once:
  config/transition_policy_hospital_sentences_braking_v1.json
  config/sequence_policy_hospital_sentences_v2.json
  results/hospital_sentences_20261101_002/batches/
Run from the repository root: .venv/bin/python results/hospital_sentences_20261101_002/make_inputs.py
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PAIR_SOURCE = "config/transition_policy_hospital_sentences_connector_only_v1.json"
SEQUENCE_SOURCE = "config/sequence_policy_hospital_sentences_v1.json"
PAIR_POLICY = "config/transition_policy_hospital_sentences_braking_v1.json"
SEQUENCE_POLICY = "config/sequence_policy_hospital_sentences_v2.json"
SENTENCES = ["HELLO YOU APPOINTMENT HAVE", "YOU NEED INTERPRETER", "PLEASE WAIT DOCTOR COME SOON", "YOU HURT WHERE",
             "BREATHE-DEEP", "NOW NURSE BLOOD-DRAW", "MEDICINE MORNING NIGHT TAKE", "YOU UNDERSTAND", "THANK-YOU"]
# Nine runs; the five round-1 failures each get a run of their own (with one easy pair).
WORKERS = [
    ["NURSE__BLOOD-DRAW"], ["MEDICINE__MORNING", "YOU__UNDERSTAND"], ["PLEASE__WAIT", "COME__SOON"],
    ["WAIT__DOCTOR", "NIGHT__TAKE"], ["YOU__HURT", "MORNING__NIGHT"], ["HELLO__YOU", "YOU__APPOINTMENT"],
    ["APPOINTMENT__HAVE", "YOU__NEED"], ["NEED__INTERPRETER", "DOCTOR__COME"], ["HURT__WHERE", "NOW__NURSE"],
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
    pair["policy_id"] = "group3-hospital-sentences-braking-v1"
    pair["planner"]["budget"]["wall_time_s"] = 480.0
    pair["planner"]["rrt"]["wall_time_s"] = 160.0
    pair["planner"]["boundary_braking"] = {"version": "stop_and_go_v1", "min_speed_rad_s": 0.05,
                                           "limit_fraction": 1.0, "max_frames": 15}
    write_new(ROOT / PAIR_POLICY, pair)

    sequence = json.loads((ROOT / SEQUENCE_SOURCE).read_text(encoding="utf-8"))
    sequence.update(policy_id="group3-hospital-sentences-sequence-v2",
                    pair_policy={"path": PAIR_POLICY, "sha256": sha(ROOT / PAIR_POLICY)})
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
