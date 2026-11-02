# TASK-25 — v5 lift-off finger arrival: removing the planning timeouts into NOW

[中文](TASK-25.md) · [Current state](STATE.en.md) · [Previous v4 report](TASK-24.en.md)

**v5 implemented and all four pairs rerun: numerical pass 4/4; formal PASS_SIM is still 0.** 812 tests passed (808 after v4 + 4 new). Thresholds, scoring scope and the formal switch are unchanged.

## Root cause

The COME→NOW and NOW→NOW TIMEOUTs were unrelated to collision or budget. NOW's protected core starts at frame 3, so entry can only be frames 1–3 (frame 0 sits on the limit and is already screened out). In those frames 16 finger joints are just leaving their 0 rad lower limit: only 1.5–13 mrad above it and moving upward at 0.13–0.75 rad/s. A single quintic that must arrive near the limit at that velocity first dips through the limit:

| Pair | Transition duration and overshoot |
|---|---|
| COME 132 → NOW 3 | 0.1 s within limits; 0.3 s 0.033 rad over; 1.0 s 0.21 rad over |
| NOW 76 → NOW 3 | ≤0.3 s within limits; 0.5 s 0.019 rad over; 1.0 s 0.15 rad over |

Short durations exceed the acceleration/jerk limits and long ones break the joint limit. After a failure the timer only lengthens the curve, which deepens the overshoot until the 30 s budget runs out. Geometry passed on every attempt.

## v5 change

- New policy `config/transition_policy_user_protected_v5.json` (SHA-256 `4a08faee59d0b1dec77fb5106261a7b2f75d66147278d7646eb51061d198261f`). Compared with v4 it changes only `policy_id` and `endpoints.generator_version` = `protected_cut_search_v3` (keeps v4 edge ranking, adds lift-off arrival).
- `finger_arrival_plan_v1` (`src/sign_robot/pair_fingers.py`) activates only when an independent finger's room to its limit at entry is < 0.4·|v|·minimum duration. It tries earlier frames of the same target word as the staging pose (earliest first) and requires the final segment to stay within joint, speed, acceleration and jerk limits; otherwise it returns `feasible: false`.
- `apply_finger_arrival_v1`: fingers first move smoothly to the staging pose and stop, then a short quintic re-creates the word's original lift-off to the entry state. Arm curves are coefficient-for-coefficient unchanged, endpoint position/velocity/acceleration are unchanged, and coupled joints are recomputed from their drivers. It composes only with the synchronous and late finger strategies (the late phase contract holds); early is unchanged.
- Cut shortlist (v3 generator): entries that need an arrival but have no feasible one rank last; for feasible entries the limit-violation estimate ignores fingers.
- The verifier is unchanged; saved trajectories are still fully recomputed from file by the independent verifier.

Actual plans: NOW entry 3 → stage at frame 0, 0.1 s lift-off (acceleration 24.7, jerk 1328); entry 2 → frame 0, 0.067 s (acceleration 30.0, jerk 2849); entry 1 infeasible; COME entries need none.

## Four-pair results (run `lift_off_arrival_pilot_20261031_001`)

| Pair | Candidates / numerical pass | Selected candidate |
|---|---:|---|
| COME→NOW | 7 / 7 | attempt_00016: rrt_connect, synchronous fingers, cuts COME 132 / NOW 2, 0.067 s lift-off (8 driver fingers); 0.733 s transition; acceleration 21.34, jerk 214.0, integral 61,674; clearance 7.616 mm |
| NOW→NOW | 8 / 8 | attempt_00015: rrt_connect, late fingers, cuts NOW 76 / NOW 3, 0.1 s lift-off; 1.0 s transition; acceleration 28.60, jerk 269.4, integral 162,443; clearance 4.418 mm |
| NOW→COME | 17 / 17 | Same as v4 (attempt_00023, no lift-off needed) |
| COME→COME | 13 / 13 | Same as v4 (attempt_00003, no lift-off needed) |

Full-library denominator 1,225 (1,190 distinct / 35 self): 4 numerical passes awaiting formal approval, 1,221 NOT_RUN, 0 PASS_SIM.

## Commands

```bash
.venv/bin/python scripts/plan_all_pairs.py --library hospital_v1 --include-self --policy config/transition_policy_user_protected_v5.json --run-id lift_off_arrival_pilot_20261031_001 --results-root results/user_protected_lift_off_arrival_20261031_001/runs --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW
```

```bash
.venv/bin/python scripts/verify_all_pairs.py --run-id lift_off_arrival_pilot_20261031_001 --results-root results/user_protected_lift_off_arrival_20261031_001/runs
```

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider tests
```

Actual: planning + verification took 6 min 29 s, exit 0; log `results/user_protected_lift_off_arrival_20261031_001/run.log`. pytest: 812 passed. New tests in `tests/test_lift_off_arrival_v5.py`.

## Videos

`render_user_protected_pairs.py` refuses a run whose code hash no longer matches. After the run, only `src/sign_robot/project_overview.py` changed (the docs-index hash re-pin), so the four pairs were rerun with the same v5 policy as `lift_off_arrival_pilot_20261031_002`. All 45 saved candidate curves have identical segments and word instances to run 001; only the `identity` field differs, and the selected candidates are the same. Run 001 is unchanged. The first render attempt (an interrupted session) left a partial `videos_interrupted_partial/`; it is kept but not used.

| Pair | Retained original frames | Added transition | Video |
|---|---|---|---|
| COME→NOW | COME [27,132]; NOW [2,76] | 3.500～4.233 s | [MP4](results/user_protected_lift_off_arrival_20261031_001/videos/COME__NOW/comparison.mp4) |
| NOW→NOW | NOW [3,76]; NOW [3,76] | 2.433～3.433 s | [MP4](results/user_protected_lift_off_arrival_20261031_001/videos/NOW__NOW/comparison.mp4) |
| NOW→COME | NOW [3,77]; COME [27,132] | 2.467～3.267 s | [MP4](results/user_protected_lift_off_arrival_20261031_001/videos/NOW__COME/comparison.mp4) |
| COME→COME | COME [27,132]; COME [27,132] | 3.500～4.233 s | [MP4](results/user_protected_lift_off_arrival_20261031_001/videos/COME__COME/comparison.mp4) |

Layout is the same as TASK-22: original row on top, algorithm row below; front view left, side view right. Colours: green=protected, blue=retained, red=cut, yellow=added, gray=hold. Each folder also holds trajectory.json, replay.npz, baseline.npz, trajectory_evidence.csv, independent_verification.json, contact_sheet.png and report.json. The renderer re-runs the independent verifier on each selected curve before drawing; all four passed numerically (`summary.json`: numerical 4, PASS_SIM 0). Unlike TASK-22, no fast-raster wrapper was used, so MuJoCo default render settings apply (shadows and reflections on). Geometry and trajectories are unaffected.

The execution model checked frames around the lift-off for COME→NOW and NOW→NOW. At this resolution the arm moves smoothly through the transition with no visible jumps. The few-mrad finger lift-off is not visible. This is not a human or group-2 review, nor an ASL comprehension check.

```bash
PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 .venv/bin/python scripts/plan_all_pairs.py --library hospital_v1 --include-self --policy config/transition_policy_user_protected_v5.json --run-id lift_off_arrival_pilot_20261031_002 --results-root results/user_protected_lift_off_arrival_20261031_001/runs --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW
```

```bash
PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 .venv/bin/python scripts/verify_all_pairs.py --run-id lift_off_arrival_pilot_20261031_002 --results-root results/user_protected_lift_off_arrival_20261031_001/runs
```

```bash
PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 .venv/bin/python scripts/render_user_protected_pairs.py --run-dir results/user_protected_lift_off_arrival_20261031_001/runs/lift_off_arrival_pilot_20261031_002 --output results/user_protected_lift_off_arrival_20261031_001/videos --pair COME__NOW --pair NOW__NOW --pair NOW__COME --pair COME__COME
```

Actual: render took 38 s, exit 0. Logs are in `run_002_and_render.log` and `render_002.log`. Any later code edit (including a docs-index hash re-pin) will make rendering from run 002 refuse again; then use a new run_id.

## Unverified limits

- Lift-off arrival adds a "pre-shape the hand to NOW's starting shape, then lift" motion before the word; how it looks and whether it stays understandable as ASL has not been checked by a person.
- v3–v5 are development policies (`freeze_status: pending`); the scoring scope, cut rule and arrival rule need cross-review by the three groups.
- Very few scored frames (21–29), so results cover only the region around the transition; collision is sampled, not continuously certified.
- Only the four COME/NOW pairs were run; the other 1,221 pairs are NOT_RUN, and whether other words have similar limit issues is unknown.
- Videos are kinematic replays only; the execution model looked at extracted frames, not a person. No human viewing, multi-word composition, fresh-environment reproduction or hardware run. Nothing committed; old results, original motions and models were not modified.
