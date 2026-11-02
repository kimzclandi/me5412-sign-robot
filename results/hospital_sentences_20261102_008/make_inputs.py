"""Inputs for the nine hospital sentences, round 8: stop-free smooth connectors + sign-level dynamics (2026-11-02).

User feedback on round 7 (chat, 2026-11-02): the motions are right, but the transitions feel segmented (they move, halt,
move again) and are still slower than the signs; the acceleration limits may be widened if they are what binds.
Round 7: 9 of 17 connectors stopped at interior route knots (1-3 full stops each: every knot was rest-to-rest), and the
jerk-integral limit bound the timing of all 17. This round changes three things and nothing else:
  - planner.smooth_timing (smooth_route_timing_v1): a minimum-jerk spline through the route knots and a constant-velocity
    route with smoothstep corner blends are tried first (two segment-proportion rules each), the shortest that passes is
    kept; the stop-at-every-knot quintics and braking remain the fallback.
  - selection_rule numerical_pass_then_fewest_stops_then_core_gap_v1: fewest interior full stops first, then core gap.
  - quality.limits: peak acceleration 120 -> 200 rad/s^2, peak jerk 3000 -> 5000 rad/s^3, jerk integral
    1e6 -> 5e6 rad^2/s^5. The signs' own protected cores (the 21 sentence words, same 30 Hz finite differences as the
    verifier, every joint) have upper quartiles of 211 rad/s^2, 5447 rad/s^3 and 1.26e7 rad^2/s^5 per second: a
    connector may now be as dynamic as an upper-quartile sign, not more (5e6 is that rate over 0.4 s). Speed caps stay.
  - planner budget: 480 -> 720 s per pair (RRT 160 -> 240 s), because each timing call now tries four schedules.
Protection bundle v2 and the staged exits are round 7's. Writes, once:
  config/transition_policy_hospital_sentences_fast_v5.json
  config/sequence_policy_hospital_sentences_v7.json
  results/hospital_sentences_20261102_008/batches/
Run from the repository root: .venv/bin/python results/hospital_sentences_20261102_008/make_inputs.py
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PAIR_SOURCE = "config/transition_policy_hospital_sentences_fast_v4.json"
SEQUENCE_SOURCE = "config/sequence_policy_hospital_sentences_v6.json"
PAIR_POLICY = "config/transition_policy_hospital_sentences_fast_v5.json"
SEQUENCE_POLICY = "config/sequence_policy_hospital_sentences_v7.json"
SENTENCES = ["HELLO YOU APPOINTMENT HAVE", "YOU NEED INTERPRETER", "PLEASE WAIT DOCTOR COME SOON", "YOU HURT WHERE",
             "BREATHE-DEEP", "NOW NURSE BLOOD-DRAW", "MEDICINE MORNING NIGHT TAKE", "YOU UNDERSTAND", "THANK-YOU"]
LIMITS = {"peak_acceleration_rad_s2": 200.0, "peak_jerk_rad_s3": 5000.0, "jerk_integral_rad2_s5": 5000000.0}
# Same sixteen runs as rounds 3-7 (cpu0-15).
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
    pair["policy_id"] = "group3-hospital-sentences-fast-v5"
    pair["selection_rule"] = "numerical_pass_then_fewest_stops_then_core_gap_v1"
    pair["planner"]["smooth_timing"] = {"version": "smooth_route_timing_v1", "growth": 1.12, "minimum_total_frames": 7}
    pair["quality"]["limits"].update(LIMITS)
    # Every timing call now tries four stop-free schedules before the stop-and-go fallback; a longer pair budget
    # keeps the number of explored routes per pair near round 7's (RRT keeps its third of the budget).
    pair["planner"]["budget"]["wall_time_s"] = 720.0
    pair["planner"]["rrt"]["wall_time_s"] = 240.0
    write_new(ROOT / PAIR_POLICY, pair)

    sequence = json.loads((ROOT / SEQUENCE_SOURCE).read_text(encoding="utf-8"))
    sequence.update(policy_id="group3-hospital-sentences-sequence-v7",
                    pair_policy={"path": PAIR_POLICY, "sha256": sha(ROOT / PAIR_POLICY)})
    sequence["case_note"] = sequence["case_note"].replace(
        "round 7 (round 6 with the user's MORNING/NURSE protection ends and NURSE's staged exit):",
        "round 8 (round 7 with stop-free smooth connectors and sign-level dynamics limits):")
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
