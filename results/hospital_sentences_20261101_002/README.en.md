# Nine hospital sentences, round 2: connector-only + boundary braking (2026-11-01)

[中文](README.md) · **English**

Development evidence only: formal PASS_SIM is 0, `formal_acceptance_enabled=false`, not verified ASL, no human review.
Round 1: [`../hospital_sentences_20261101_001/README.en.md`](../hospital_sentences_20261101_001/README.en.md).

## Result: 7/7 sentences NUMERICAL_PASS

| Sentence | Status |
|---|---|
| HELLO YOU APPOINTMENT HAVE | NUMERICAL_PASS |
| YOU NEED INTERPRETER | NUMERICAL_PASS |
| PLEASE WAIT DOCTOR COME SOON | NUMERICAL_PASS |
| YOU HURT WHERE | NUMERICAL_PASS |
| NOW NURSE BLOOD-DRAW | NUMERICAL_PASS |
| MEDICINE MORNING NIGHT TAKE | NUMERICAL_PASS |
| YOU UNDERSTAND | NUMERICAL_PASS |
| BREATHE-DEEP, THANK-YOU | Single words, no connector; the source motion plays as is |

The independent sequence recheck agrees 7/7 and all 24 word occurrences keep their protected cores bitwise
(`verify_sequences.log`). A fresh recheck of the 17 selected connectors agrees for all
(`selected_recheck_0[1-9]/summary.json`).

| Pair | Run | Attempts | Candidates=pass | Selected | Method | Cut (source→target) |
|---|---|---|---|---|---|---|
| NURSE→BLOOD-DRAW | 01 | 94 | 2 | attempt_00087 | rrt_connect | 98→22 |
| MEDICINE→MORNING | 02 | 109 | 20 | attempt_00005 | direct | 86→23 |
| YOU→UNDERSTAND | 02 | 113 | 86 | attempt_00075 | retract_approach | 115→23 |
| COME→SOON | 03 | 131 | 118 | attempt_00050 | neutral | 132→27 |
| PLEASE→WAIT | 03 | 64 | 5 | attempt_00059 | rrt_connect | 85→23 |
| NIGHT→TAKE | 04 | 49 | 5 | attempt_00025 | retract_approach | 97→23 |
| WAIT→DOCTOR | 04 | 82 | 19 | attempt_00006 | direct | 107→23 |
| MORNING→NIGHT | 05 | 50 | 4 | attempt_00034 | rrt_connect | 69→39 |
| YOU→HURT | 05 | 61 | 22 | attempt_00031 | retract_approach | 115→23 |
| HELLO→YOU | 06 | 81 | 47 | attempt_00035 | ik_via2 | 66→45 |
| YOU→APPOINTMENT | 06 | 71 | 25 | attempt_00039 | retract_approach | 116→23 |
| APPOINTMENT→HAVE | 07 | 61 | 24 | attempt_00005 | direct | 163→24 |
| YOU→NEED | 07 | 62 | 33 | attempt_00040 | rrt_connect | 115→30 |
| DOCTOR→COME | 08 | 131 | 109 | attempt_00040 | neutral | 57→26 |
| NEED→INTERPRETER | 08 | 104 | 52 | attempt_00002 | direct | 93→16 |
| HURT→WHERE | 09 | 131 | 96 | attempt_00030 | neutral | 58→51 |
| NOW→NURSE | 09 | 63 | 24 | attempt_00029 | retract_approach | 78→23 |

## What was fixed (commit d1bd7dc)

Round 1's five failing pairs: at the shortlisted cuts the source's finger joints still moved at 8-10 rad/s toward a
joint limit (0.36-0.63 rad left). A connector must keep that velocity, so longer connectors only overshot further into
limits or the body, and a quintic could not stop within the 3000 rad/s³ jerk limit either. Checking every frame showed
that most other cuts in the same user-protection windows stop in 1-3 frames, but the old ranking (preferring cuts next
to the protected core) kept only the worst ones.

- `planner.boundary_braking` (`stop_and_go_v1`, optional): when a route cannot be timed (other than a timeout), stop
  first over a fixed quintic (p0 + v0 T (u − u³ + u⁴/2), monotone, travel v0T/2; clamped at limits, no overshoot while
  travel ≥ 0.4 v0T) and mirror it on entry; retiming lengthens only the middle.
- With braking, the cut shortlist interleaves up to 8 cut pairs that both sides can brake (fewest braking frames first).
- **The second item is what worked**: all 17 selected connectors are plain carry-the-boundary-velocity curves at the
  newly added cuts; the stop segments exist as a fallback and were not selected in this round.
- Every connector threshold is unchanged; 480 s per pair (RRT 160 s); nine runs on cpu0-8 (incl. E-cores),
  15:54-16:22.
- Policies without `boundary_braking` behave byte-identically (tested). New `tests/test_boundary_braking_v1.py` (6);
  full suite **973 passed** (`tests/pytest_full.log`).

## Reproduce

```bash
.venv/bin/python results/hospital_sentences_20261101_002/make_inputs.py   # writes only files that do not exist
bash results/hospital_sentences_20261101_002/run.sh
```

## Limits

- The new cuts lie further from the protected cores, so more source edge is retained (the source belongs to group 2;
  the cores are unchanged).
- Videos: GPU render in `videos_gpu/<sentence>/` (`comparison.mp4` not committed, user decision; `report.json` and
  `contact_sheet.png` committed). Two steps: in WSL, `export_render_inputs.py` reuses the saved independent recheck
  (checking the sequence-file hash) and exports the replay, the original clips and per-frame phase labels; in native
  Windows Python (`_runtime/render-venv`, mujoco 3.15.0), `render_gpu_windows.py` draws them with the same layout,
  cameras, colours and encoder as `render_sequences.py`. GL renderer NVIDIA GeForce RTX 5060; all seven in parallel in
  18 s (the WSL software render took minutes per sentence). The model is a copy of `assets/robot` (MuJoCo cannot open
  `\\wsl.localhost` paths), hash-checked file by file before rendering. Label font Microsoft YaHei. `videos/` is the
  stopped WSL software render and is incomplete. Not watched by a person.
- Sampled collision checks are not a continuous-collision proof. After this directory is committed, these runs cannot
  be resumed or rechecked on the new HEAD.
