# Nine hospital sentences, round 8: stop-free smooth connectors + sign-level dynamics (2026-11-02)

[中文](README.md) · **English**

Development evidence only: formal PASS_SIM is 0, `formal_acceptance_enabled=false`, not verified ASL, no human review.
Earlier: round 7 [`../hospital_sentences_20261102_007/README.en.md`](../hospital_sentences_20261102_007/README.en.md).

User feedback on round 7 (chat, 2026-11-02): the motions are right, but the transitions feel segmented (move, halt, move
again) and are still slower than the signs; acceleration limits may be widened if they are what binds. Code `1d07d2d`;
inputs `make_inputs.py`; run `run.sh`, 16 pair runs on cpu0-15, 02:50-03:39.

## Diagnosis (round 7)

- **Halting**: every route knot was timed rest-to-rest (zero velocity and acceleration), and braking added stop segments
  at the ends. 9 of 17 connectors stopped 1-3 times inside the connector (16 full-body stops), e.g. NURSE→BLOOD-DRAW 3
  (4 × 15 frames), MORNING→NIGHT 3, YOU→HURT 3, PLEASE→WAIT 2.
- **Speed**: for all 17 connectors the attempt just before the passing one failed the jerk-integral limit (1e6 rad²/s⁵);
  peak jerk bound 5, peak acceleration 2. Against the signs' own protected cores (21 sentence words, the verifier's 30 Hz
  finite differences, every joint) the connectors were 5-10× gentler:

| | Sign cores (median / upper quartile) | Round-7 connectors |
|---|---|---|
| peak acceleration | 171 / 211 rad/s² | 23-99 |
| peak jerk | 4283 / 5447 rad/s³ | 607-2336 |
| jerk integral per second | 9.2e6 / 1.26e7 rad²/s⁵ | 3.2e5-2.4e6 |

## Changes (pair policy `config/transition_policy_hospital_sentences_fast_v5.json`, sequence policy v7)

- **`planner.smooth_timing` (`smooth_route_timing_v1`)**, tried before the old stop-at-every-knot quintics:
  - *minimum-jerk spline* (`min_jerk_spline_v1`): one quintic per route segment, passing through every knot; the interior
    velocities and accelerations are solved for the least total squared jerk (continuous to the fourth derivative), so
    the curve never halts at a knot;
  - *corner blend* (`corner_blend_v1`): each segment at constant velocity, consecutive segments blended over
    min(T_i, T_i+1) with a smoothstep velocity change. A joint that holds still in a segment stays exactly still (no
    spline ringing against a joint limit, which is what made the spline fail on the staged NURSE/MORNING routes), and
    the next stage starts while the previous one is still finishing; corners are cut, geometry is rechecked;
  - each with speed-proportional and limit-proportional segment times (the time a segment's joints need under the speed
    cap, and under the speed, peak-acceleration and peak-jerk limits); every schedule starts at the speed-bound total and
    grows all segments together by 1.12× per attempt (whole frames), the shortest passing one of the four is kept;
  - the old stop-and-go quintics and braking remain the fallback (not needed in this round). A lift-off finger arrival
    that does not fit a still-short connector is now one failed attempt instead of aborting the timing; geometry is
    sampled once the analytic gates pass.
- **Selection `numerical_pass_then_fewest_stops_then_core_gap_v1`**: fewest interior full stops (every joint below
  0.05 rad/s at a segment boundary inside the connector) first, then the frames between the protected cores. Rest tails
  use the same key.
- **Limits** (the user allowed widening): peak acceleration 120 → **200** rad/s², peak jerk 3000 → **5000** rad/s³, jerk
  integral 1e6 → **5e6** rad²/s⁵. Each stays within the signs' upper quartile above (5e6 is the upper-quartile rate over
  0.4 s, the shortest connectors); the speed caps (15 arm / 10 finger rad/s) are unchanged. Offline re-timing of round 7's
  17 routes with the same knots chose these over a jerk integral of 1e7, which was only slightly faster.
- Pair budget 480 → 720 s (RRT 160 → 240 s), because each timing call now tries four schedules.
- Tests `tests/test_smooth_timing_v1.py` (7, incl. a recomputation of the sign quartiles); full suite **1014 passed**.

## Result: 7/7 sentences NUMERICAL_PASS, no connector halts

- 17/17 selected connectors and 7/7 sentences agree on fresh rechecks; 24/24 protected cores bitwise unchanged; every
  sentence ends at rest.
- **Interior full stops: 16 → 0** (all 17 connectors and all 7 rest tails). 15 connectors use the spline, 2 the corner
  blend (NURSE→BLOOD-DRAW, WAIT→DOCTOR); the stop-and-go fallback was never needed.
- **Faster**: connector frames 446 → 254; frames between protected cores 563 → 310 (−45 %); rest tails 12-19 → 8-12
  frames. Mean arm speed: connectors 5.0-13.1 rad/s (round 7: 2.7-12.1), rest tails 4.6-8.2 (round 7: 2.2-7.0),
  protected sign cores 1.5-10.5 rad/s.

| Sentence | Round 7 | Round 8 |
|---|---|---|
| HELLO YOU APPOINTMENT HAVE | 271 fr (9.0 s) | 235 fr (7.8 s) |
| YOU NEED INTERPRETER | 198 fr (6.6 s) | 168 fr (5.6 s) |
| PLEASE WAIT DOCTOR COME SOON | 448 fr (14.9 s) | 366 fr (12.2 s) |
| YOU HURT WHERE | 165 fr (5.5 s) | 120 fr (4.0 s) |
| NOW NURSE BLOOD-DRAW | 299 fr (10.0 s) | 271 fr (9.0 s) |
| MEDICINE MORNING NIGHT TAKE | 230 fr (7.7 s) | 164 fr (5.5 s) |
| YOU UNDERSTAND | 107 fr (3.6 s) | 97 fr (3.2 s) |

- Selected pair connectors: peak jerk 819-2058 rad/s³ (limit 5000), peak acceleration ≤ 134 rad/s² (limit 200), largest
  jerk integral 4.89e6 rad²/s⁵ (limit 5e6).
- NURSE keeps its choreography without halting: the right hand drops away from the left wrist first, the left forearm
  lifts and the wrist straightens, then BLOOD-DRAW (42 frames, round 7: 60 with 3 stops).
- `clamped_joint_stop_v1` acted at PLEASE→WAIT's exit (`left_wrist_roll_joint`) and HURT→WHERE's exit
  (`R_thumb_proximal_yaw_joint`).

| Pair | Run | Attempts | Pass | Selected | Method | Curve | Cut | Connector fr | Stops | Between cores | Round 7 (fr / stops / between) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NURSE→BLOOD-DRAW | 01 | 20 | 4 | attempt_00016 | staged_exit | corner_blend_v1 | 75→35 | 42 | 0 | 43 | 60 / 3 / 61 |
| MORNING→NIGHT | 02 | 53 | 40 | attempt_00002 | staged_exit | min_jerk_spline_v1 | 37→39 | 13 | 0 | 13 | 43 / 3 / 43 |
| PLEASE→WAIT | 03 | 35 | 4 | attempt_00010 | ik_via1 | min_jerk_spline_v1 | 66→27 | 22 | 0 | 22 | 36 / 2 / 59 |
| NIGHT→TAKE | 04 | 82 | 58 | attempt_00002 | direct | min_jerk_spline_v1 | 60→51 | 10 | 0 | 10 | 24 / 1 / 24 |
| WAIT→DOCTOR | 05 | 34 | 7 | attempt_00006 | neutral | corner_blend_v1 | 84→34 | 32 | 0 | 32 | 30 / 1 / 64 |
| MEDICINE→MORNING | 06 | 41 | 7 | attempt_00038 | rrt_connect | min_jerk_spline_v1 | 86→25 | 11 | 0 | 29 | 24 / 1 / 44 |
| YOU→HURT | 07 | 40 | 15 | attempt_00015 | ik_via1 | min_jerk_spline_v1 | 72→27 | 12 | 0 | 12 | 43 / 3 / 43 |
| YOU→APPOINTMENT | 08 | 41 | 21 | attempt_00026 | ik_via2 | min_jerk_spline_v1 | 72→59 | 19 | 0 | 29 | 24 / 0 / 35 |
| YOU→NEED | 09 | 37 | 20 | attempt_00027 | rrt_connect | min_jerk_spline_v1 | 72→30 | 8 | 0 | 8 | 24 / 1 / 24 |
| HELLO→YOU | 10 | 83 | 68 | attempt_00002 | direct | min_jerk_spline_v1 | 66→45 | 10 | 0 | 10 | 17 / 0 / 17 |
| NOW→NURSE | 11 | 32 | 15 | attempt_00004 | direct | min_jerk_spline_v1 | 51→38 | 14 | 0 | 14 | 15 / 0 / 15 |
| NEED→INTERPRETER | 12 | 53 | 43 | attempt_00014 | direct | min_jerk_spline_v1 | 93→14 | 10 | 0 | 26 | 15 / 0 / 31 |
| YOU→UNDERSTAND | 13 | 73 | 63 | attempt_00002 | direct | min_jerk_spline_v1 | 72→27 | 9 | 0 | 9 | 12 / 0 / 13 |
| HURT→WHERE | 14 | 66 | 43 | attempt_00028 | ik_via1 | min_jerk_spline_v1 | 57→51 | 11 | 0 | 11 | 22 / 0 / 22 |
| DOCTOR→COME | 15 | 86 | 69 | attempt_00002 | direct | min_jerk_spline_v1 | 57→27 | 10 | 0 | 10 | 15 / 0 / 15 |
| APPOINTMENT→HAVE | 16 | 32 | 19 | attempt_00013 | ik_via1 | min_jerk_spline_v1 | 143→24 | 12 | 0 | 23 | 30 / 1 / 41 |
| COME→SOON | 16 | 95 | 84 | attempt_00002 | direct | min_jerk_spline_v1 | 132→27 | 9 | 0 | 9 | 12 / 0 / 12 |

## Videos and charts

`videos_gpu/<sentence>/`: `comparison.mp4` (not committed, user decision), `report.json`, `contact_sheet.png`.
`MEDICINE__MORNING__NIGHT__TAKE/arm_speed_round7_vs_round8.png` and `NOW__NURSE__BLOOD-DRAW/arm_speed_round7_vs_round8.png`:
arm speed over time, round 7 above and round 8 below, gray bands for the added transitions, dots for interior full stops.
`NOW__NURSE__BLOOD-DRAW/round7_vs_round8_nurse_exit.png`: NURSE's exit every 5 frames. Rendered on the Intel Arc B390
integrated GPU again (setting `SHIM_MCCOMPAT` for the render process did not move it to the RTX 5060), 94-231 s per
sentence; same script and output format. Not watched by a person.

## Limits

- Faster and smoother is within, not beyond, the signs' own upper-quartile dynamics; whether it looks natural needs a
  person to watch the videos. The largest connector jerk integral (4.89e6) is close to the new limit.
- MEDICINE MORNING NIGHT TAKE's minimum clearance is exactly 2.0 mm (the threshold).
- The corner blend cuts corners, so the two blended connectors do not pass exactly through their stage knots; their
  geometry is checked on the actual curve.
- Sentences still start on the first protected core; sampled collision checks are not a continuous-collision proof;
  after this directory is committed, these runs cannot be resumed or rechecked on the new HEAD.
