# Nine hospital sentences, round 7: shorter MORNING/NURSE protection + staged exits (2026-11-02)

[中文](README.md) · **English**

Development evidence only: formal PASS_SIM is 0, `formal_acceptance_enabled=false`, not verified ASL, no human review.
Earlier: round 6 [`../hospital_sentences_20261101_006/README.en.md`](../hospital_sentences_20261101_006/README.en.md).

User instructions (chat, 2026-11-02): delete MORNING's user protection after frame 38; end NURSE's at frame 75 and after
it let the right hand move away quickly first, then straighten the left wrist. Code `129891a`; inputs `make_inputs.py`;
run `run.sh`, 16 pair runs on cpu0-15, 01:17-01:51.

## Changes

- **Protection bundle v2** (`config/user_protected_hospital35_v2.json`): v1 with only two records changed and the
  amendment recorded in each; v1 stays for earlier runs.
  - NURSE: [38, 79] → **[38, 75]**.
  - MORNING: [26, 69] → **[26, 37]**. Asked for 38: between frames 37 and 38 the retargeted right middle/ring fingers
    snap shut at the 10 rad/s cap with 0.8 rad left to their stop. Stopping them already takes a 5-frame brake using
    95 % of the connector's jerk-integral limit (952,146 of 1e6 rad²/s⁵), so no connector could leave from 38 under
    the unchanged thresholds (every NIGHT entry tried). The user chose frame 37.
- **Staged exits** (`planner.staged_exits`, `staged_exit_v1`, pair policy
  `config/transition_policy_hospital_sentences_fast_v4.json`): for a configured word the connector leaves exactly at
  the protected core end through stop-and-go knots that move one joint group at a time, then on to the target entry.
  Stage targets: the rest pose, the target entry, zero, or an IK wrist displacement (`ik:<direction>:<steps>`, 6.5 cm
  per step; only the group's joints are taken). Entries are tried nearest the target core first; generic route
  families and RRT are skipped for these words. Stage options were screened offline for clearance along the knot
  polyline.
  - **NURSE** (selected `right_arm:target + left_upper_arm:ik:out+up+forward:3 + left_wrist:zero`, 4 × 15 frames):
    1) the right arm moves straight to where BLOOD-DRAW needs it, off the left wrist; 2) the left forearm lifts off the
    lap (out + up + forward, about 19.5 cm at the wrist); 3) the left wrist straightens to zero; 4) on to BLOOD-DRAW's
    entry (frame 35). Step 2 was not asked for, but straightening the wrist in place puts the left thumb 52 mm into the
    torso.
  - **MORNING** (selected `right_arm:ik:out+up:2`): from frame 37 a straight route to NIGHT's crossed hands passes
    through the left forearm, so the right hand first moves out and up (13 cm), then both arms cross into NIGHT's
    core start (frame 39); 3-frame brake and 2-frame start segments at the ends.
- Tests `tests/test_staged_exit_v1.py` (11); full suite **1007 passed** (`tests/pytest_full.log`).

## Result: 7/7 sentences NUMERICAL_PASS, each ending at rest

- 17/17 selected connectors and 7/7 sentences agree on fresh rechecks; 24/24 protected cores bitwise unchanged
  (NURSE [38, 75], MORNING [26, 37]); no retained edge flagged.
- NOW NURSE BLOOD-DRAW: 299 replay frames (round 6: 316); NURSE→BLOOD-DRAW connector 60 frames, 61 between cores
  (round 6: 74). Minimum clearance 2.0 mm, exactly at the 2 mm threshold.
- MEDICINE MORNING NIGHT TAKE: 230 replay frames (round 6: 249); MORNING→NIGHT connector 43 frames (round 6: 30, but
  MORNING's core is now 32 frames shorter).
- Other sentences: HELLO YOU APPOINTMENT HAVE 271, YOU NEED INTERPRETER 198, PLEASE WAIT DOCTOR COME SOON 448,
  YOU HURT WHERE 165, YOU UNDERSTAND 107 (same as round 6). Pair connectors' peak jerk 298-787 rad/s³, peak
  acceleration ≤ 95 rad/s²; rest tails as in round 4.
- `clamped_joint_stop_v1` acted only at HURT→WHERE's exit (`R_thumb_proximal_yaw_joint`); NURSE no longer needs it.

| Pair | Run | Attempts | Pass | Selected | Method | Cut | Connector fr | Frames between cores | Round 6 |
|---|---|---|---|---|---|---|---|---|---|
| NURSE→BLOOD-DRAW | 01 | 47 | 15 | attempt_00023 | staged_exit | 75→35 | 60 | 61 | 74 |
| MORNING→NIGHT | 02 | 53 | 31 | attempt_00004 | staged_exit | 37→39 | 43 | 43 | 30 |
| PLEASE→WAIT | 03 | 68 | 8 | attempt_00058 | rrt_connect | 85→23 | 36 | 59 | 59 |
| NIGHT→TAKE | 04 | 81 | 28 | attempt_00018 | ik_via1 | 60→51 | 24 | 24 | 24 |
| WAIT→DOCTOR | 05 | 58 | 13 | attempt_00049 | rrt_connect | 107→23 | 30 | 64 | 64 |
| MEDICINE→MORNING | 06 | 80 | 13 | attempt_00062 | rrt_connect | 86→23 | 24 | 44 | 44 |
| YOU→HURT | 07 | 43 | 13 | attempt_00008 | ik_via1 | 72→27 | 43 | 43 | 43 |
| YOU→APPOINTMENT | 08 | 50 | 15 | attempt_00047 | rrt_connect | 73→59 | 24 | 35 | 35 |
| YOU→NEED | 09 | 47 | 24 | attempt_00022 | rrt_connect | 72→30 | 24 | 24 | 24 |
| HELLO→YOU | 10 | 65 | 34 | attempt_00002 | direct | 66→45 | 17 | 17 | 17 |
| NOW→NURSE | 11 | 48 | 19 | attempt_00002 | direct | 51→38 | 15 | 15 | 15 |
| NEED→INTERPRETER | 12 | 117 | 79 | attempt_00014 | direct | 93→14 | 15 | 31 | 31 |
| YOU→UNDERSTAND | 13 | 78 | 59 | attempt_00008 | direct | 73→27 | 12 | 13 | 13 |
| HURT→WHERE | 14 | 60 | 30 | attempt_00004 | direct | 57→51 | 22 | 22 | 22 |
| DOCTOR→COME | 15 | 130 | 94 | attempt_00002 | direct | 57→27 | 15 | 15 | 15 |
| APPOINTMENT→HAVE | 16 | 42 | 15 | attempt_00008 | ik_via1 | 143→24 | 30 | 41 | 41 |
| COME→SOON | 16 | 131 | 116 | attempt_00002 | direct | 132→27 | 12 | 12 | 12 |

## Videos

`videos_gpu/<sentence>/`: `comparison.mp4` (not committed, user decision), `report.json`, `contact_sheet.png`.
`NOW__NURSE__BLOOD-DRAW/round6_vs_round7_nurse_exit.png` and `MEDICINE__MORNING__NIGHT__TAKE/round6_vs_round7_morning_exit.png`:
from the core end, every 4 frames, front and side, round 6 top, round 7 bottom. `source_frames_morning_night_nurse.png`:
source frames around the new cuts. This render ran on the Intel Arc B390 integrated GPU (Windows did not hand the GL
context to the RTX 5060 this time), 97-230 s per sentence instead of about 12 s; same script and output format. Not
watched by a person.

## Limits

- NURSE's staged exit takes 2 s (four stop-and-go segments of 0.5 s); each stage is timed to the shortest duration that
  passes every gate, so "quickly" means the minimum allowed by the limits, not a separately tuned speed.
- NOW NURSE BLOOD-DRAW's minimum clearance is exactly 2.0 mm.
- Sentences still start on the first protected core; sampled collision checks are not a continuous-collision proof;
  after this directory is committed, these runs cannot be resumed or rechecked on the new HEAD.
