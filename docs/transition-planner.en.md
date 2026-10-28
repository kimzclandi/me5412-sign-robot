# Group 3: transition planner delivery

[中文](transition-planner.md) · **English**

Starting from `group3/transition-planner` at `2656412`, this delivery adds joint-space minimum-jerk transitions and local acceptance artifacts. All ten sentences were generated. Of 19 transitions, 13 pass collision checks and six remain **FAILED** after one via-point retry. Failed trajectories are retained for diagnosis and must not be used as safe execution trajectories. The singleton sentences `BREATHE-DEEP` and `THANK-YOU` have no transitions; zero checks does not certify their word motions.

## Run

Run from the repository root using the existing `.venv` and `assets/robot/vendor` symlinks:

```bash
export PATH="$HOME/.local/bin:$PATH"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export LP_NUM_THREADS=1 MESA_GLTHREAD=false MUJOCO_GL=egl
.venv/bin/python scripts/plan_transitions.py YOU BUY BOOK
.venv/bin/python scripts/plan_transitions.py --all
.venv/bin/python scripts/evaluate_planned_transitions.py --render-comparison
.venv/bin/python scripts/plan_transitions.py YOU HURT WHERE --render --report results/planned_transitions/you_hurt_where_preview.json
.venv/bin/python -m pytest -q tests/test_plan_transitions.py
.venv/bin/python -m pytest -q
```

Run sequentially; each rendering task uses one encoding thread. On macOS, omit `MUJOCO_GL=egl`; macOS was not tested in this delivery. `--help` describes arguments; `--out-dir` changes the trajectory directory and `--report` changes the report path. A single-sentence run replaces the default `report.json`, so generate the complete acceptance report with `--all` and use the separate report filename above for an individual render. The CLI returns 0 when artifact emission completes, even if segments are FAILED; inspect report status instead of interpreting exit code as collision acceptance.

Default trajectories are `results/mocap_previews/planned_sentence_<GLOSSES>.npz`, with the existing `timestamps_s`, `joint_names`, `positions` fields. `--render` adds an MP4 with the same stem. Original `sentence_*.npz`, motion data, `retarget.py`, `ACTION_IDS`, and vendor assets are untouched. This delivery uses local commits only; nothing is pushed.

## Method and boundaries

- Lookup uses the hospital map first, then the mocap and video indexes, with the same ready/poor filtering as `stitch_baseline.py`. Lowercase glosses are accepted; unknown words raise an error.
- Interior words retain inclusive `sign_frames`. The first starts at frame 0, retaining its rise; the last runs through its return to neutral, matching the baseline. Transition endpoints exactly equal the previous `sign_frames[1]` and next `sign_frames[0]`. Word slices are neither resampled nor modified.
- Interpolation is `s(u)=10u³−15u⁴+6u⁵`, with at least three time intervals (two interior samples) at 30 fps. Continuous peak velocity is `1.875 × |Δq| / T`, which determines the shortest safe integer duration. Shoulder/elbow/wrist joints use 15 rad/s and L_/R_ finger joints use 10 rad/s, including coupled joints; coupled joints are not independent drives. Other joints keep the fixed poses in the source clips.
- Repository `load_model` / `apply_frame` check every emitted transition sample, endpoints included, using upstream collision geoms. Same-hand finger/wrist mesh adjacency is excluded exactly as in `summarize_library.py`. The task's explicit rule fails `contact.dist < -0.002 m`: **this allows up to 2 mm penetration and does not guarantee a positive 2 mm gap**. No contacts is recorded as null minimum contact distance, not a fabricated positive clearance. Collision masks and thresholds are unchanged; continuous collision between samples is unverified.
- On failure, exactly one deterministic joint-space via is added: endpoint midpoint, with both shoulder pitches decreased by 0.35 rad and elbows increased by 0.15 rad, clipped to model limits. Each leg uses its shortest rate-safe quintic; velocity and acceleration are zero at their junction. A colliding retry is emitted with FAILED reasons; there is no further search.
- A separate wrist-height check detects undershoot below the lower endpoint and may use the same single via to remove it. If an initially clear direct path has a via that fails either height or collision checks, the direct path is retained with a WARNING. Attempt and final PASS/FAILED refer to collision status; height results are separate. The CLI prints warnings.

Only inserted transitions receive the rate/collision checks. Source-word rate excesses and penetration are retained; whole-sentence peak rates are recorded separately as `sentence_peak_rates`. This is an offline kinematic candidate preview. Dynamics, hardware execution, ASL meaning, and human comprehension remain unverified. Software tests are not represented as independent user review.

## Results and checks

Per-sentence counts, durations, and all failure reasons are in the [English table](../results/planned_transitions/report.en.md) and [raw JSON](../results/planned_transitions/report.json); see [planner_output.txt](../results/planned_transitions/planner_output.txt) for CLI output. Duration consistently means frame count / 30; the final timestamp is `(frame count−1)/30`. The report includes SHA-256 hashes of source motions, model, and indexes, plus endpoint/rate verification against the saved NPZ artifacts.

Failed segments are `MEDICINE→MORNING`, `NOW→NURSE`, `NURSE→BLOOD-DRAW`, `DOCTOR→COME`, `COME→SOON`, and `NEED→INTERPRETER`. For example, `DOCTOR→COME` already penetrates by 7.854 mm at its fixed start, which a via cannot change. `NURSE→BLOOD-DRAW` still penetrates by 2.006 mm after retry and therefore remains failed.

`YOU→BUY` right-wrist transition undershoot, measured below the lower endpoint, decreases from **0.849769 mm to zero**. Elbow undershoot is zero in both. The elbow still descends 8.059297 mm from start to end, which is the fixed endpoint height difference. Inside the source YOU clip, wrist peak-to-end descent is **234.348952 mm**, and elbow descent is **54.821335 mm**; both versions preserve these. Removing that visible descent would require separate authorization to cut earlier or change the specified boundaries, and is not claimed here. Full heights and metrics are in [you_buy_sag.json](../results/planned_transitions/you_buy_sag.json). The archived baseline BUY boundary differs from the current word library by approximately 1e-8 rad; metrics use the archive unchanged, while new planned boundaries remain exactly equal.

The [comparison video](../results/planned_transitions/you_hurt_where_baseline_vs_planned.mp4) is also copied to `/workspace/you_hurt_where_baseline_vs_planned.mp4`. The top row is baseline and bottom row planned; columns are front and right-side views. Both play at their original 30 fps; the shorter planned row holds its final frame, without time warping. Baseline duration is 9.400 s and planned duration 8.967 s; both planned transitions pass these collision checks.

Test results and the before/after failure-set comparison are in [pytest_summary.json](../results/planned_transitions/pytest_summary.json). This environment's complete baseline is 261 passed, eight failed, and 23 errors: five missing `sentence_transformers` failures, one existing `test_project_overview` failure, and two failures plus 23 errors from the sandbox prohibition on creating sockets. The user's 286 passed/six failed baseline came from another environment. Actual before/after logs are preserved, and new failures are assessed by comparing the same environment's failure sets.

All **25 new tests pass** (0.23 s). The full suite after the change reports **286 passed, eight failed, and 23 errors** (3.88 s), with **zero new failures or errors** against the local before run. No failing tests were skipped, patched, or hidden with bypass flags.

Local `git add` failed because the filesystem containing `.git/worktrees/wt-transitions/index.lock` is read-only. No commit was created; all delivery files remain unstaged for the foreman to commit on the host. Nothing was pushed. Existing `.venv`, `assets/robot/vendor`, and `_scratch/` are unchanged and are outside this delivery.
