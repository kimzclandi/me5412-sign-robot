# Nine hospital sentences, round 10: first solve on the new clips clips-v2 (2026-11-02)

[中文](README.md) · **English**

Development evidence only: formal PASS_SIM is 0, `formal_acceptance_enabled=false`, not verified ASL, no human review.
Earlier: round 8 [`../hospital_sentences_20261102_008/README.en.md`](../hospital_sentences_20261102_008/README.en.md) and
round 9 [`../hospital_sentences_20261102_009/README.en.md`](../hospital_sentences_20261102_009/README.en.md), both on the
old clips. Stage record: [TASK-29](../../TASK-29.en.md).

User instructions (chat, 2026-11-02): run the trajectory planning on `group3/clips-v2` with 12 threads; run now, without
first fixing the 34 failing tests; drop NURSE's staged exit. Code `00124363` (no code changes); inputs `make_inputs.py`;
run `run.sh`, 12 pair runs on cpu0-11, 18:31-20:18 (pairs until 19:58, sequences 20:16, videos 20:18).

## Inputs (pair policy `config/transition_policy_hospital_sentences_fast_v7.json`, sequence policy v9)

`fast_v7` is round 8's `fast_v5` with three changes and nothing else:

- **Protection bundle v5** (`config/user_protected_hospital35_v5.json`): NURSE f23-f79, INTERPRETER f19-f40, HURT f37-f57,
  MORNING f26-f37, the rest as before; bound to the clips-v2 hashes.
- **NURSE's staged exit removed.** It was designed for the old NURSE clip (left hand at the lap); the new NURSE ends with
  the left forearm across the chest and the right hand beside the left wrist. MORNING's staged exit is kept.
- **Longer search**, as in round 9: 720 → 1800 s per pair (RRT 240 → 600 s).

Sequence policy `config/sequence_policy_hospital_sentences_v9.json`: round 8's seven multi-word sentences (v7's case list),
pointing at `fast_v7`. The 17 pairs run in 12 batches: the seven pairs that touch a changed word or were hard before get a
run of their own, the other ten share in twos (`make_inputs.py`). Limits, speed caps, selection rule
(`numerical_pass_then_fewest_stops_then_core_gap_v1`) and smooth timing are round 8's.

Identity: pair identity `8c1a2007…`, code hash `5a67cedd…`, policy hash `e0f204e4…`, code commit `00124363`. The tests are
part of the code hash, so these runs can be resumed or rechecked only on this commit with the tests unchanged.

## Result: 7/7 sentences NUMERICAL_PASS on the new clips

- 17/17 pairs have a numerical pass; 17/17 selected connectors agree on fresh rechecks (`selected_recheck_01`-`12`).
- 7/7 sentences NUMERICAL_PASS and 7/7 agree on the fresh sequence recheck (`verify_sequences.log`); 24/24 protected cores
  bitwise unchanged; 17 connector groups; every sentence ends at rest (7 rest tails, 8-10 frames, 0 stops).
- **0 interior full stops**, as in round 8. 16 connectors use the minimum-jerk spline, WAIT→DOCTOR the corner blend.
- **NURSE→BLOOD-DRAW without the staged exit**: a direct 10-frame connector from NURSE f79 (round 8 on the old clip: a
  42-frame staged exit). Its minimum clearance is 4.2 mm.
- Frames between protected cores across the 17 connectors: 310 (round 8) → **263**; connector frames 254 → 215.

| Sentence | Round 8 (old clips) | Round 10 (clips-v2) |
|---|---|---|
| HELLO YOU APPOINTMENT HAVE | 235 fr (7.8 s) | 233 fr (7.7 s) |
| YOU NEED INTERPRETER | 168 fr (5.6 s) | 143 fr (4.7 s) |
| PLEASE WAIT DOCTOR COME SOON | 366 fr (12.2 s) | 366 fr (12.2 s) |
| YOU HURT WHERE | 120 fr (4.0 s); round 9: 109 fr | 109 fr (3.6 s) |
| NOW NURSE BLOOD-DRAW | 271 fr (9.0 s) | 254 fr (8.4 s) |
| MEDICINE MORNING NIGHT TAKE | 164 fr (5.5 s) | 167 fr (5.5 s) |
| YOU UNDERSTAND | 97 fr (3.2 s) | 97 fr (3.2 s) |

- Selected pair connectors: peak jerk 819-1858 rad/s³ (limit 5000), peak acceleration ≤ 130 rad/s² (limit 200), largest
  jerk integral 4.89e6 rad²/s⁵ (HELLO→YOU; limit 5e6).
- The handoff's endpoint issues: NEED→INTERPRETER enters INTERPRETER at f14 (needed: f16 or earlier, so source frames
  f14-18 are kept); HAVE's rest tail leaves at f57, the first frame after the contact span f41-56 (f58 was also tried and
  failed on timing).

| Pair | Run | Attempts | Pass | Selected | Method | Curve | Cut | Connector fr | Stops | Between cores | Round 8 between | Min clearance |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NURSE→BLOOD-DRAW | 01 | 50 | 20 | attempt_00008 | direct | min_jerk_spline_v1 | 79→35 | 10 | 0 | 11 | 43 | 4.2 mm |
| NOW→NURSE | 02 | 73 | 62 | attempt_00002 | direct | min_jerk_spline_v1 | 51→23 | 10 | 0 | 10 | 14 | 5.9 mm |
| NEED→INTERPRETER | 03 | 92 | 72 | attempt_00014 | direct | min_jerk_spline_v1 | 93→14 | 10 | 0 | 15 | 26 | 6.2 mm |
| YOU→HURT | 04 | 77 | 58 | attempt_00048 | ik_via1 | min_jerk_spline_v1 | 72→37 | 11 | 0 | 11 | 12 | 9.5 mm |
| HURT→WHERE | 05 | 124 | 89 | attempt_00065 | ik_via1 | min_jerk_spline_v1 | 57→51 | 11 | 0 | 11 | 11 | 8.9 mm |
| MEDICINE→MORNING | 06 | 75 | 12 | attempt_00064 | rrt_connect | min_jerk_spline_v1 | 86→25 | 11 | 0 | 29 | 29 | 2.0 mm |
| PLEASE→WAIT | 07 | 57 | 20 | attempt_00028 | ik_via1 | min_jerk_spline_v1 | 66→27 | 22 | 0 | 22 | 22 | 7.7 mm |
| WAIT→DOCTOR | 08 | 72 | 18 | attempt_00012 | neutral | corner_blend_v1 | 84→34 | 32 | 0 | 32 | 32 | 3.4 mm |
| YOU→UNDERSTAND | 08 | 131 | 117 | attempt_00002 | direct | min_jerk_spline_v1 | 72→27 | 9 | 0 | 9 | 9 | 9.0 mm |
| HELLO→YOU | 09 | 115 | 102 | attempt_00002 | direct | min_jerk_spline_v1 | 66→45 | 10 | 0 | 10 | 10 | 9.5 mm |
| MORNING→NIGHT | 09 | 53 | 32 | attempt_00008 | staged_exit | min_jerk_spline_v1 | 37→37 | 14 | 0 | 16 | 13 | 4.0 mm |
| NIGHT→TAKE | 10 | 126 | 90 | attempt_00002 | direct | min_jerk_spline_v1 | 60→51 | 10 | 0 | 10 | 10 | 3.1 mm |
| YOU→NEED | 10 | 55 | 29 | attempt_00042 | rrt_connect | min_jerk_spline_v1 | 72→30 | 8 | 0 | 8 | 8 | 9.1 mm |
| APPOINTMENT→HAVE | 11 | 74 | 42 | attempt_00030 | ik_via1 | min_jerk_spline_v1 | 143→24 | 12 | 0 | 23 | 23 | 9.2 mm |
| DOCTOR→COME | 11 | 116 | 96 | attempt_00002 | direct | min_jerk_spline_v1 | 57→27 | 10 | 0 | 10 | 10 | 8.3 mm |
| COME→SOON | 12 | 131 | 115 | attempt_00002 | direct | min_jerk_spline_v1 | 132→27 | 9 | 0 | 9 | 9 | 8.9 mm |
| YOU→APPOINTMENT | 12 | 63 | 33 | attempt_00032 | neutral | min_jerk_spline_v1 | 72→58 | 16 | 0 | 27 | 29 | 2.8 mm |

`summarize.py` regenerates this table and `summary.json` from the run records.

## Videos

`videos_<sentence>/<sentence>/`: `comparison.mp4` (original clips on top, sequence below; front and side; not committed),
`contact_sheet.png`, `replay.npz`, `baseline.npz`, `report.json`, `independent_verification.json`. Rendered with
`scripts/render_sequences.py` (CPU, EGL), one process per sentence, about 1 minute in total. Not watched by a person.
Interactive replay: `.venv/bin/python play_sentence.py results/hospital_sentences_20261102_010/videos_*/*/replay.npz --loop`
(`play_sentence.py` is a local viewer script, not committed).

## Reproduce

```bash
.venv/bin/python results/hospital_sentences_20261102_010/make_inputs.py   # writes only files that do not exist
bash results/hospital_sentences_20261102_010/run.sh                       # resumes; existing steps are skipped
.venv/bin/python results/hospital_sentences_20261102_010/summarize.py
```

## Deviations and unverified limits

- **Tests not fixed first.** The handoff asks for the full suite to pass on the new clips before solving; at the user's
  request this run used `00124363` as it was (988 passed, 16 failed, 18 errors). The test fix `a1eb6e53` (1021 passed,
  1 skipped) was pushed at 18:48, while this run was going. The tests are part of the code hash, so these runs can only be
  resumed or rechecked at `00124363`; a run on the fixed tests needs a new round.
- **12 runs instead of 16**, at the user's request (12 threads); the pair-to-run split differs from round 8's.
- **NURSE's staged exit was dropped, not redesigned.** A direct connector passed, so no redesign was needed for this round.
- MEDICINE→MORNING's minimum clearance is exactly 2.0 mm (the threshold), as in round 8; YOU→APPOINTMENT 2.8 mm.
- Source-side findings (informational under review scope v4, owner Group 2): retained source frames outside the protected
  cores have sampled penetrations in five sentences, down to −49.1 mm in NOW NURSE BLOOD-DRAW; YOU HURT WHERE and YOU
  UNDERSTAND have none.
- Sentences still start on the first protected core; sampled collision checks are not a continuous-collision proof.
- Raw pair stores (`pair_runs/`) stay local and are not committed.
