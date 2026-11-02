# Nine hospital sentences, round 4: faster transitions + return to rest (2026-11-01)

[中文](README.md) · **English**

Development evidence only: formal PASS_SIM is 0, `formal_acceptance_enabled=false`, not verified ASL, no human review.
Earlier: round 2 [`../hospital_sentences_20261101_002/README.en.md`](../hospital_sentences_20261101_002/README.en.md),
round 3 (superseded, rest-tail search fix) [`../hospital_sentences_20261101_003/README.en.md`](../hospital_sentences_20261101_003/README.en.md).

User requests: (1) after a sentence, return to the hands-down starting pose; (2) transitions were clearly slower than the
signs. Code `0b2528d` + `843cd45`; inputs and batches from round 3 (`../hospital_sentences_20261101_003/make_inputs.py`);
run `run.sh`, 16 pair runs on cpu0-15, 20:43-21:18.

## Result: 7/7 sentences NUMERICAL_PASS, each ending at rest

| Sentence | Round 2 frames | Round 4 frames (incl. return to rest) | Return to rest |
|---|---|---|---|
| HELLO YOU APPOINTMENT HAVE | 417 (13.9 s) | 271 (9.0 s) | 15 fr |
| YOU NEED INTERPRETER | 316 (10.5 s) | 201 (6.7 s) | 15 fr |
| PLEASE WAIT DOCTOR COME SOON | 765 (25.5 s) | 441 (14.7 s) | 12 fr |
| YOU HURT WHERE | 291 (9.7 s) | 161 (5.4 s) | 12 fr |
| NOW NURSE BLOOD-DRAW | 405 (13.5 s) | 334 (11.1 s) | 19 fr |
| MEDICINE MORNING NIGHT TAKE | 387 (12.9 s) | 246 (8.2 s) | 17 fr |
| YOU UNDERSTAND | 198 (6.6 s) | 107 (3.6 s) | 15 fr |
| BREATHE-DEEP, THANK-YOU | single words: the whole source clip plays, already starting and ending at rest | | |

- Independent sequence recheck 7/7 agree, 24/24 protected cores bitwise unchanged (`verify_sequences.log`); 17/17
  selected connectors agree on a fresh recheck (`selected_recheck_*/summary.json`).
- Every replay ends at the rest pose: end position error ≤ 1e-14 rad, zero velocity and acceleration
  (`sequences/independent_recheck/<sentence>.json`, `rest_tail`).
- Mean arm speed (norm over shoulder/elbow/wrist): connectors 2.7-12 rad/s, rest tails 2.2-7.0 rad/s, protected sign cores
  1.5-10.5 rad/s. Round 2's connectors were 0.8-6 rad/s.

| Pair | Run | Attempts | Pass | Selected | Method | Cut | Connector fr | Frames between cores | Round 2 |
|---|---|---|---|---|---|---|---|---|---|
| NURSE→BLOOD-DRAW | 01 | 58 | 1 | attempt_00050 | rrt_connect | 98→23 | 60 | 92 | 78 |
| MORNING→NIGHT | 02 | 37 | 4 | attempt_00027 | rrt_connect | 69→39 | 30 | 30 | 30 |
| PLEASE→WAIT | 03 | 67 | 5 | attempt_00059 | rrt_connect | 85→23 | 36 | 59 | 203 |
| NIGHT→TAKE | 04 | 46 | 5 | attempt_00011 | ik_via1 | 60→51 | 24 | 24 | 128 |
| WAIT→DOCTOR | 05 | 82 | 20 | attempt_00074 | rrt_connect | 100→23 | 30 | 57 | 206 |
| MEDICINE→MORNING | 06 | 97 | 16 | attempt_00095 | rrt_connect | 86→26 | 24 | 41 | 95 |
| YOU→HURT | 07 | 40 | 10 | attempt_00008 | ik_via1 | 72→27 | 43 | 43 | 161 |
| YOU→APPOINTMENT | 08 | 46 | 14 | attempt_00045 | rrt_connect | 73→59 | 24 | 35 | 162 |
| YOU→NEED | 09 | 44 | 21 | attempt_00022 | rrt_connect | 72→30 | 24 | 24 | 151 |
| HELLO→YOU | 10 | 59 | 33 | attempt_00002 | direct | 66→45 | 17 | 17 | 47 |
| NOW→NURSE | 11 | 45 | 18 | attempt_00002 | direct | 51→38 | 15 | 15 | 132 |
| NEED→INTERPRETER | 12 | 81 | 39 | attempt_00008 | direct | 93→15 | 19 | 34 | 44 |
| YOU→UNDERSTAND | 13 | 76 | 57 | attempt_00008 | direct | 73→27 | 12 | 13 | 119 |
| HURT→WHERE | 14 | 110 | 71 | attempt_00002 | direct | 58→51 | 17 | 18 | 42 |
| DOCTOR→COME | 15 | 130 | 96 | attempt_00002 | direct | 57→27 | 15 | 15 | 39 |
| APPOINTMENT→HAVE | 16 | 39 | 14 | attempt_00007 | ik_via1 | 143→24 | 30 | 41 | 48 |
| COME→SOON | 16 | 131 | 118 | attempt_00002 | direct | 132→27 | 12 | 12 | 32 |

"Frames between cores" = retained source after the first core + connector + retained source before the second core.
Total 570 frames (19.0 s) against 1717 (57.2 s) in round 2. NURSE→BLOOD-DRAW is longer than in round 2: the search
is wall-clock bounded and this run found a single passing candidate for it.

## What changed

- **Selection rule** `numerical_pass_then_core_gap_then_smoothness_v1` (pair policy
  `config/transition_policy_hospital_sentences_fast_v1.json`, otherwise identical to `braking_v1`): among candidates
  that pass the independent recheck, take the fewest frames between the two protected cores; peak jerk, peak
  acceleration and jerk integral only break ties. The old rule ranked by peak jerk first, which always favours a long,
  slow connector (round 2 selected up to 180 frames where 36 passed). Every connector threshold is unchanged; the
  selected connectors stay below peak jerk 3000 rad/s³ and peak acceleration 120 rad/s².
- **Return to rest** `rest_tail_v1` (sequence policy `config/sequence_policy_hospital_sentences_v3.json`,
  `assembly.rest_tail`): the rest pose is the first frame that all 35 library clips share bitwise (the retargeted
  hands-down pose: elbows 0.25 rad, thumbs slightly in; not MuJoCo qpos0). After the last word, exit frames in its exit
  window are tried in order; the route families and quintic timing are the pair planner's, ending with zero velocity and
  acceleration. The fewest frames from the core end to rest win. Search: straight routes (direct, via neutral) at every
  exit frame first, detours only where the frame bound lets them win. All seven tails chose a direct route.
- The independent verifier checks the tail like any connector (hash-bound planning record
  `sequences/rest_tails/<word>.json`, fresh rest pose from all library clips, boundary, analytic limits, interior FD
  quality, dense collision) and reports it as `rest_tail`.
- New tests `tests/test_rest_tail_v1.py` (15); full suite **988 passed** (`tests/pytest_full.log`).

## Videos

`videos_gpu/<sentence>/`: `comparison.mp4` (not committed, user decision), `report.json`, `contact_sheet.png`. Same
two-step GPU render as round 2 (`export_render_inputs.py` in WSL, `render_gpu_windows.py` on Windows, RTX 5060, all
seven in 16 s); the tail is labelled "ADDED return to rest / 新增回到初始姿态". Not watched by a person.

## Limits

- The faster motion is closer to the limits than round 2: selected pair connectors peak jerk 171-787 rad/s³ (round 2:
  1-500), peak acceleration ≤ 95 rad/s² (round 2: ≤ 63); the rest tails' analytic peak jerk is 561-1986 rad/s³
  (NOW NURSE BLOOD-DRAW highest), acceleration ≤ 66 rad/s². All stay under 3000 rad/s³ and 120 rad/s²; whether the
  motion looks natural needs a human look at the videos.
- Sentences still start on the first word's protected core, not from rest (not requested; the same tail mechanism could
  be mirrored for a start-from-rest head).
- Sampled collision checks are not a continuous-collision proof. After this directory is committed, these runs cannot
  be resumed or rechecked on the new HEAD.
