# Group 3: transition planner, round 2

[中文](transition-planner.md) · **English**

This round edits the existing planner at `bded331` (original base `2656412`) on `group3/transition-planner`. All nine scripted sentences plus THANK-YOU were regenerated locally. Of 19 transitions, **13 are PASS, two are source_collision, and four are FAILED**. These are disjoint counts; `accepted_count` is PASS plus source_collision. A source_collision still contains inherited penetration, and a FAILED path is retained only for diagnosis. The singleton sentences BREATHE-DEEP and THANK-YOU have zero transitions and receive no transition clearance certification.

## Run and local outputs

Run sequentially from the repository root using the existing `.venv` and vendor symlinks. These thread settings keep one heavy process active, at most three threads, and require at least 2 GiB MemAvailable:

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export LP_NUM_THREADS=1 MESA_GLTHREAD=false
.venv/bin/python scripts/plan_transitions.py --all
MUJOCO_GL=egl .venv/bin/python scripts/evaluate_planned_transitions.py --render-comparison
.venv/bin/python -m pytest -q tests/test_plan_transitions.py
.venv/bin/python -m pytest -q
```

The evaluator defaults to `results/planned_transitions/you_hurt_where_baseline_vs_planned_v2.mp4` and copies it to `/workspace/you_hurt_where_baseline_vs_planned_v2.mp4`; `--copy-to` changes the copy path. On macOS omit `MUJOCO_GL=egl`; macOS was not tested here. `--help` lists options. For a single preview, use a separate report so the ten-sentence JSON is preserved:

```bash
MUJOCO_GL=egl .venv/bin/python scripts/plan_transitions.py YOU HURT WHERE --render --report results/planned_transitions/you_hurt_where_preview.json
```

Trajectories use `results/mocap_previews/planned_sentence_<GLOSSES>.npz` with the unchanged `timestamps_s`, `joint_names`, `positions` fields. Local reports, logs, heights, and video live in `results/planned_transitions/`: [JSON](../results/planned_transitions/report.json), [English table](../results/planned_transitions/report.en.md), [Chinese table](../results/planned_transitions/report.md), [planner log](../results/planned_transitions/planner_round2_output.txt), and [v2 video](../results/planned_transitions/you_hurt_where_baseline_vs_planned_v2.mp4). These generated files are ignored; a fresh checkout must regenerate them before those local links work. The planner exits 0 after emitting artifacts even if some transitions are FAILED; inspect report statuses.

## Protocol

- Lookup uses the hospital map, then mocap/video indexes with the baseline ready/poor filters. Interior words keep inclusive `sign_frames`; the first keeps its frame-0 rise and the last its return to neutral. Transition endpoints exactly equal the previous `sign_frames[1]` and next `sign_frames[0]`. Source slices are not edited or resampled.
- Every direct blend and every via leg uses `s(u)=10u³−15u⁴+6u⁵`. Duration is `max(shortest_rate_limited_time, 0.3 s)`, rounded up to integer 30 fps intervals: at least nine intervals per leg, and at least 0.6 s for a two-leg via. Continuous peak velocity is `1.875 × |Δq| / T`. Arm limits stay 15 rad/s, fingers 10 rad/s, including coupled finger joints. Coupled joints are not independent drives.
- `load_model` / `apply_frame` inspect every emitted transition sample, including endpoints, with upstream collision geoms and the existing same-hand adjacency exclusion. The absolute failure threshold stays **`contact.dist < -0.002 m`**. This allows 2 mm penetration; it does not promise a positive 2 mm gap. Null means no detected contacts, not a measured positive separation. Collision masks, rates, and thresholds are unchanged; between-sample continuous collision is unverified.
- When an endpoint is below -2 mm, the whole transition passes as **`source_collision` only if its minimum contact distance is at least the minimum of the two endpoint distances**. A no-contact endpoint does not lower that floor. Any interior worsening must be repaired by a via under the same relative rule, or remains FAILED. `clearance.passed` retains the absolute check; transition `status` carries the relative classification.
- A clearance failure tries the fixed directions `out`, `up`, `forward`, `out+up`, `out+forward`, `up+forward`, `out+up+forward`. Each target is 6.5 cm from the wrist at the endpoint midpoint pose; combination vectors are normalized. Existing shoulder offsets and forward foot geoms confirm robot +Y left, +X forward, +Z up. Outward means +Y for the left hand and -Y for the right. Bounded `G1Retargeter.solve_arms` IK starts each candidate from the same midpoint, softly retaining palm orientation and elbow position. Only arms change; fingers and all other coordinates stay the convex midpoint. Joint limits can prevent fully reaching a target.
- Both complete min-jerk legs are checked for every candidate. The passing via with the largest minimum contact distance wins, using fixed direction order to break ties. No detected contacts rank first but remain null in reports. The chosen `via_direction`, every attempt, endpoint distances, and the selected worst pair with `distance_m` are recorded. If no candidate passes, the least-penetrating failed via is emitted as FAILED.
- Wrist undershoot remains a separate aesthetic check. An already accepted direct path can use the same search to remove undershoot, but is retained with a warning if no via passes both height and collision checks. When clearance itself requires a via, collision acceptance and clearance ranking take priority; any remaining undershoot is reported.

The Group 2 handoff lists each colliding endpoint's word, zero-based source frame from `sign_frames`, body pair, and signed `distance_m`, including bad endpoints on FAILED transitions. It appears per sentence and deduplicated at report level. This run has eight pair records across NURSE frame 24 and DOCTOR frame 89; source motions remain unchanged.

## Results and validation

The two source_collision segments are NOW→NURSE (endpoint floor **-0.032892744 m**) and DOCTOR→COME (**-0.007854003 m**); each complete path equals its endpoint floor. Four segments still fail after all seven directions:

| Transition | Chosen direction | Worst body pair | distance_m |
|---|---|---|---:|
| MEDICINE→MORNING | out+up | left_wrist_yaw_link / torso_link | -0.047320147 |
| NURSE→BLOOD-DRAW | up | R_thumb_proximal / fixed_mount | -0.040771353 |
| COME→SOON | out | R_index_proximal / left_wrist_yaw_link | -0.025966885 |
| NEED→INTERPRETER | out+up | L_thumb_distal / left_hip_roll_link | -0.034908732 |

These failed candidates have substantial penetration and are not execution trajectories. The new fixed search does not resolve every transition.

Saved NPZ files are rechecked for exact endpoints, sampled rates, per-leg minimum duration, and collision classification. The JSON also records input SHA-256 hashes and runtime versions. Sentence duration means frame count / 30; transition/leg duration means intervals / 30. The comparison has baseline on top, planned below, front left and right-side right, at original 30 fps. Baseline YOU HURT WHERE is **9.400 s**, planned **9.033 s**; the shorter row holds its last frame without time warping, and both planned transitions are PASS.

YOU→BUY uses the up via; right-wrist undershoot below the lower endpoint decreases from **0.849769 mm to zero**. Elbow undershoot is zero in both, with the fixed endpoint descent of 8.059297 mm preserved. Inside source YOU, wrist and elbow peak-to-end descents remain **234.348952 mm** and **54.821335 mm**. See local [you_buy_sag.json](../results/planned_transitions/you_buy_sag.json). Archived baseline boundaries have approximately 1e-8 rad differences from today's sources; new planned endpoints are exact.

The focused transition suite has **38 passing tests**, 13 more than round 1. This sandbox's unchanged full baseline is **286 passed, eight failed, 23 errors**; five failures lack `sentence_transformers`, one is the existing project overview failure, and two failures plus 23 errors result from prohibited sockets. The full after run is **299 passed, eight failed, 23 errors**, with **zero new failures or errors**. Full before/after logs and the [failure-set comparison](../results/planned_transitions/pytest_round2_summary.json) are retained locally. A host-capable environment was unavailable; no bypass flags, skips, or dependency fixes were used. These developer checks are not an independent frozen evaluation. Dynamics, hardware execution, ASL meaning, and human comprehension remain unverified; source-word rates/collisions are retained and whole-sentence rates are reported separately.

## Git handoff

`.gitignore` excludes planned NPZ/MP4 files, `results/planned_transitions/`, and comparison MP4s. The requested `git rm --cached` failed because the worktree Git index is on a read-only filesystem. Ignore patterns cannot untrack existing files: the foreman must run the following on the host before committing. `--cached` keeps every file on disk.

```bash
git rm -r --cached -- 'results/mocap_previews/planned_sentence_*.npz' results/planned_transitions/ results/you_hurt_where_baseline_vs_planned.mp4
git add .gitignore src/sign_robot/transitions.py scripts/plan_transitions.py scripts/evaluate_planned_transitions.py tests/test_plan_transitions.py docs/transition-planner.md docs/transition-planner.en.md
git commit -m "feat(group3): add IK via search and source collision handoff"
```

All changes remain unstaged here; no commit or push was made. No files were deleted. `motions/`, `retarget.py`, `ACTION_IDS`, original baseline clips, vendor symlinks, `.venv`, and `_scratch/` are outside this change.
