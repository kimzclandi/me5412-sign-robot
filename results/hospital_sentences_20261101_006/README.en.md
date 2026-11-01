# Nine hospital sentences, round 6: no IK-flipped source edges (2026-11-01)

[中文](README.md) · **English**

Development evidence only: formal PASS_SIM is 0, `formal_acceptance_enabled=false`, not verified ASL, no human review.
Earlier: round 4 [`../hospital_sentences_20261101_004/README.en.md`](../hospital_sentences_20261101_004/README.en.md)
(faster transitions + return to rest), round 5 (superseded) [`../hospital_sentences_20261101_005/README.en.md`](../hospital_sentences_20261101_005/README.en.md).

User report: in round 4's NOW NURSE BLOOD-DRAW the left hand is abnormally twisted (NURSE frame 81). Code `27b6304` +
`368fc4b`; inputs `make_inputs.py`; run `run.sh`, 16 pair runs on cpu0-15, 22:55-23:32.

## Cause

Not an added connector: the frame was **retained NURSE source motion**. NURSE's protected core ends at frame 79; right
after it the retargeted clip flips the left arm: the shoulder yaw swings from -0.15 to its -2.62 rad stop in about 5
frames at the 15 rad/s cap, the wrist roll sits on its 1.972 rad stop, and the forearm wraps around
(`videos_gpu/source_edge_frames_round5_flags.png`, top row). Round 4's cut kept frames 80-98, so the flip was played.
Frame 79 itself is in self-collision (-10.3 mm), so the connector cannot start there.

## Fix

- `endpoints.retained_edge_screen` = `no_proximal_limit_excursion_v1` (pair policy
  `config/transition_policy_hospital_sentences_fast_v3.json`): every frame of a run in which a shoulder or elbow joint
  has left its protected-core range and reaches a hard stop the core never touches is flagged; such frames, the cut
  frame included, may not be kept outside the core. NURSE: frames 82-116 flagged, the only clean collision-free exit is
  frame 80. Planner cut screening and both independent verifiers gate it (`retained_edge_screen` in the evidence).
  Wrists are not counted: round 5's v1 screen also flagged MEDICINE 73-86 and DOCTOR 28-33, where only a wrist rests on
  its stop; rendered, those poses look like their neighbours, and two sentences were blocked.
- `endpoints.clamped_joint_stop` = `clamped_joint_stop_v1`: at frame 80 the retargeter has clamped the left wrist roll
  on its stop (1.972219 = limit − 1e-6) while the replay slope still runs into it at 0.49 rad/s, so no in-limit
  connector could carry that slope. A joint clamped on its stop whose slope points beyond it (as seen from the
  connector) is taken as resting there (boundary velocity 0). The verifiers accept the velocity step on exactly these
  joints and list them: in this round NURSE→BLOOD-DRAW exit `left_wrist_roll_joint` and HURT→WHERE exit
  `R_thumb_proximal_yaw_joint`.
- Both rules are optional policy fields; earlier policies behave as before. Tests
  `tests/test_retained_edge_screen_v1.py` (8); full suite **996 passed** (`tests/pytest_full.log`).

## Result: 7/7 sentences NUMERICAL_PASS, each ending at rest

- 17/17 selected connectors and 7/7 sentences agree on fresh rechecks; 24/24 protected cores bitwise unchanged; no
  retained edge flagged by the screen in any sentence.
- NOW NURSE BLOOD-DRAW: NURSE now ends at frame 80 (round 4: 98); NURSE→BLOOD-DRAW is a 38-frame RRT connector that
  swings the left arm out around the body to BLOOD-DRAW's start (74 frames between cores, round 4: 92).
  `videos_gpu/NOW__NURSE__BLOOD-DRAW/round4_vs_round6_nurse_exit.png`: from NURSE's core end, every 4 frames, front and
  side; top round 4 (retained flip), bottom round 6.
- Replay frames: HELLO YOU APPOINTMENT HAVE 271, YOU NEED INTERPRETER 198, PLEASE WAIT DOCTOR COME SOON 448,
  YOU HURT WHERE 165, NOW NURSE BLOOD-DRAW 316, MEDICINE MORNING NIGHT TAKE 249, YOU UNDERSTAND 107. Frames between
  protected cores over the 17 pairs: 563 (round 4: 570, round 2: 1717). Connectors' mean arm speed 2.7-12 rad/s;
  selected pair connectors peak jerk 298-787 rad/s³, peak acceleration ≤ 95 rad/s²; rest tails as in round 4.

| Pair | Run | Attempts | Pass | Selected | Method | Cut | Connector fr | Frames between cores | Round 4 |
|---|---|---|---|---|---|---|---|---|---|
| NURSE→BLOOD-DRAW | 01 | 65 | 2 | attempt_00058 | rrt_connect | 80→1 | 38 | 74 | 92 |
| MORNING→NIGHT | 02 | 67 | 4 | attempt_00051 | rrt_connect | 69→39 | 30 | 30 | 30 |
| PLEASE→WAIT | 03 | 63 | 8 | attempt_00055 | rrt_connect | 85→23 | 36 | 59 | 59 |
| NIGHT→TAKE | 04 | 76 | 28 | attempt_00016 | ik_via1 | 60→51 | 24 | 24 | 24 |
| WAIT→DOCTOR | 05 | 55 | 13 | attempt_00047 | rrt_connect | 107→23 | 30 | 64 | 57 |
| MEDICINE→MORNING | 06 | 77 | 13 | attempt_00060 | rrt_connect | 86→23 | 24 | 44 | 41 |
| YOU→HURT | 07 | 38 | 10 | attempt_00008 | ik_via1 | 72→27 | 43 | 43 | 43 |
| YOU→APPOINTMENT | 08 | 46 | 14 | attempt_00045 | rrt_connect | 73→59 | 24 | 35 | 35 |
| YOU→NEED | 09 | 42 | 20 | attempt_00021 | rrt_connect | 72→30 | 24 | 24 | 24 |
| HELLO→YOU | 10 | 57 | 30 | attempt_00002 | direct | 66→45 | 17 | 17 | 17 |
| NOW→NURSE | 11 | 43 | 19 | attempt_00002 | direct | 51→38 | 15 | 15 | 15 |
| NEED→INTERPRETER | 12 | 105 | 69 | attempt_00014 | direct | 93→14 | 15 | 31 | 34 |
| YOU→UNDERSTAND | 13 | 70 | 51 | attempt_00008 | direct | 73→27 | 12 | 13 | 13 |
| HURT→WHERE | 14 | 55 | 26 | attempt_00040 | rrt_connect | 57→51 | 22 | 22 | 18 |
| DOCTOR→COME | 15 | 130 | 91 | attempt_00002 | direct | 57→27 | 15 | 15 | 15 |
| APPOINTMENT→HAVE | 16 | 40 | 14 | attempt_00008 | ik_via1 | 143→24 | 30 | 41 | 41 |
| COME→SOON | 16 | 131 | 115 | attempt_00002 | direct | 132→27 | 12 | 12 | 12 |

The search is wall-clock bounded, so pairs the fix does not touch can still differ slightly from round 4
(WAIT→DOCTOR +7, HURT→WHERE +4, MEDICINE→MORNING +3, NEED→INTERPRETER −3 frames).

## Videos

`videos_gpu/<sentence>/`: `comparison.mp4` (not committed, user decision), `report.json`, `contact_sheet.png`; GPU
render as in round 4 (RTX 5060). Not watched by a person.

## Limits

- Only proximal (shoulder/elbow) flips are screened. MEDICINE→MORNING again keeps MEDICINE frames 73-86, where the left
  wrist yaw rests on its stop; rendered it looked normal, but a person should check. Other source defects (collisions,
  speed inside cores) remain group 2's and are reported, not gated.
- NURSE's protected core itself ends in self-collision (-10.3 mm at frame 79) and on the onset of the flip; that is
  source/protection data, not changed here.
- Sentences still start on the first protected core; sampled collision checks are not a continuous-collision proof;
  after this directory is committed, these runs cannot be resumed or rechecked on the new HEAD.
