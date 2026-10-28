# Group 3 transition planner, round 6

[中文](transition-planner.md) · **English**

Starting from `group3/transition-planner @ a24af59`, this round applies the **2 mm gate to moving pairs only and reports vendor structural gaps separately**. Nine scripted sentences plus THANK-YOU were replanned: **19 transitions = 16 PASS, 2 source_near, 1 FAILED**. Endpoint classification, absolute / relative floors, minimum clearance and closest pairs all use moving pairs. Static distances remain measured, but cannot alone trigger source_near, FAILED, or block PASS. BREATHE-DEEP and THANK-YOU contain no transitions; this does not certify their word cores as collision-free.

## Deriving static pairs

At construction, `MujocoClearance` reads `motions/hospital_v1_motions.json` and every frame of all 35 referenced motions (4485 frames), accumulating joint extrema across files. A span strictly greater than **1e-9 rad** marks a moving joint; the planner's actual bilateral `retarget.ARM_SUFFIXES` IK contract is included too. Unknown model joints without library evidence remain conservatively moving. The current model has **38 moving joints**. The established 12 constant leg joints and 3 constant waist joints retain model qpos0.

For each body, follow `body_parentid` to world and collect its own and all ancestor moving joint IDs. `derive_static_body_pairs(model, moving_joint_ids)` compares these sets: **equal sets mean no moving joint lies on the kinematic path between the bodies, so their relative pose is static**. The computation uses model topology and motion data, without a handwritten body-pair list. It derives **136 distinct-body static pairs** in this model, containing no arm, wrist, finger or hand bodies. `fixed_mount` versus either hip_pitch_link is static; wrist versus mount is moving even though the mount itself is fixed.

At the constant pose, construction temporarily expands geom / explicit-pair `mj_collision` detection margins to span the scene, retaining native filtering and same-hand exclusions, then measures each detected static geom pair with **`mj_geomDistance`** and deduplicates by geom IDs. This avoids depending on coarse mesh contacts at large detection margins. The **47 eligible geom pairs** are recorded in `vendor_structural_gaps`, with `bodies`, `geoms`, `geom_ids`, `distance_m` and `distance_mm`. Examples:

| Vendor structural gap | Distance mm |
|---|---:|
| fixed_mount / left_hip_pitch_link | +0.701651 |
| fixed_mount / right_hip_pitch_link | +0.719230 |

The 136 topology body pairs and 47 geom pairs surviving native filtering count different things. Full gap lists and derivation provenance appear at report and sentence level, and remain in selected transitions and clearance results. Geometry, masks and MJCF are not permanently edited; `prepare_robot.py` is unchanged.

## Moving-pair distances and search

Signed distances are **positive for separation and negative for penetration**. `PENETRATION_TOLERANCE_M = 0.002`, `ENDPOINT_NEAR_M = 0.002`, **15 rad/s arm** and **10 rad/s finger** limits are unchanged.

| Moving-pair endpoint class | Whole-path and each hub-leg requirement | Passing status |
|---|---|---|
| Both endpoint minima ≥ 2 mm | Minimum clearance ≥ +2 mm | PASS |
| Either endpoint minimum strictly < 2 mm | Minimum clearance ≥ smaller endpoint clearance | source_near |
| No candidate meets its floor | Retain checked candidate with greatest minimum for diagnosis | FAILED |

Exactly 2 mm is not near. FAILED segments retain the `source_near=true` endpoint flag where applicable; `source_near_count` counts relative passes only. `clearance.passed` still means the absolute +2 mm moving-pair check, so near segments also require `status` and `relative_floor_passed`. `min_distance_m`, `closest_pair` / `worst_collision`, `endpoint_clearances_mm` and handoff records never mix in static gaps.

Moving distances retain the R4 numeric query: expand detection margins through 2 mm, 1 cm, 5 cm and 25 cm, then across the scene if needed. Only an eligible **moving pair** can stop expansion; static contacts cannot hide the gated minimum. Read `contact.dist` and restore geom / pair margins in `finally`. Native MuJoCo filtering and the existing same-hand finger / wrist exclusion are unchanged. Separated poses return finite minima and closest body / geom pairs; empty trajectories or models without an eligible moving pair raise errors. Planner poses that change a library-constant joint explicitly reject the now-invalid static classification.

Search still escalates **direct → seven via1 candidates → sixteen via2 candidates → qpos0 hub**, including near endpoints. Passing via1/via2 routes compete on whole-path minimum clearance. Hub is assessed only after all vias fail, on its full path and both legs. An accepted direct path with wrist undershoot can search vias for a replacement passing both height and clearance; height-only search does not escalate to hub. If all routes fail, retain the best diagnostic candidate.

Via1/via2 retain general bilateral offsets, neutral-arm retreat and symmetric serialized retreat families, without word-specific exceptions. IK solves arms only, keeping fingers and other coordinates at convex endpoint interpolation; coupled joints are not independent drives. Each leg uses `s(u)=10u³−15u⁴+6u⁵`, rounds the continuous peak `1.875 × |Δq| / T` upward to 30 fps, and lasts at least **0.3 s / nine intervals**. Source words are neither edited nor resampled. Interior words keep inclusive sign_frames; the first keeps frame-0 rise and the last keeps its neutral return. Transition endpoints remain bit-exact.

## Results and handoff

| Transition | Status / method | Moving endpoint clearances mm | Moving whole-path min mm | Duration s |
|---|---|---|---:|---:|
| MEDICINE → MORNING | FAILED / via2 | −0.809260 / +9.434433 | −42.047690 | 1.100 |
| NOW → NURSE | source_near / direct | +8.813409 / −32.846892 | −32.846892 | 0.300 |
| DOCTOR → COME | source_near / direct | −7.853912 / +9.500549 | −7.853912 | 0.300 |
| NURSE → BLOOD-DRAW | PASS / via2 | +5.952892 / +9.500673 | +5.952892 | 1.000 |
| COME → SOON | PASS / via2 | +9.500621 / +5.476825 | +5.476825 | 0.900 |

**MEDICINE → MORNING actually checked all 25 routes, including hub / neutral.** Direct reaches −56.182729 mm. Hub reaches **−54.852146 mm / FAILED**, with the left/right wrist pair closest. The selected best via2, `neutral_retreat_left+out+forward → hold_left+out+forward`, still reaches only **−42.047690 mm**, below its **−0.809260 mm** relative floor. Its worst pair is `fixed_mount` / `left_wrist_yaw_link` (geoms 3 / 57), transition frame 5: the moving wrist versus mount remains blocked. `hub_attempted`, each attempt's clearance / status / leg_clearance, and the console HUB line explicitly record the attempt.

Deduplicated `source_near_handoff` has **15 moving-body-pair records at 3 word frames**: MEDICINE 119, NURSE 24 and DOCTOR 89. These source-motion issues remain a Group 2 handoff; static mount / hip gaps no longer cause source_near handoff entries. Evaluate rechecks saved endpoints, rates, per-leg durations, numeric moving clearances, statuses and structural-gap consistency for all ten NPZs. Peak sampled transition rates are **14.635394 rad/s arm** and **8.868628 rad/s finger**.

YOU → BUY selects an `out+up` via1, still with zero new right-wrist undershoot below the lower endpoint. Source YOU's inherited wrist / elbow peak-to-end descent of **234.348952 / 54.821335 mm** remains. YOU HURT WHERE lasts **9.033 s planned / 9.400 s baseline**; MEDICINE MORNING NIGHT TAKE lasts **10.267 / 10.067 s**. Sentence duration is frame count / 30; transition and leg durations are interval count / 30.

## Startup, regeneration and v4 videos

Use the existing `.venv` from the repository root; do not install `sentence_transformers`. Run heavy tasks sequentially with at most three threads and one heavy process, checking `MemAvailable ≥ 2 GiB` before each:

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export LP_NUM_THREADS=1 MESA_GLTHREAD=false MUJOCO_GL=egl
check_mem() {
  .venv/bin/python -c 'from pathlib import Path; m = int(next(s.split()[1] for s in Path("/proc/meminfo").read_text().splitlines() if s.startswith("MemAvailable:"))); assert m >= 2 * 1024**2; print("MemAvailable GiB:", m / 1024**2)'
}
check_mem && .venv/bin/python scripts/plan_transitions.py --all
check_mem && .venv/bin/python scripts/evaluate_planned_transitions.py
check_mem && .venv/bin/python scripts/evaluate_planned_transitions.py --render-comparison --comparison-glosses YOU HURT WHERE --artifact-name you_hurt_where_baseline_vs_planned_v4 --copy-to /workspace/you_hurt_where_baseline_vs_planned_v4.mp4
check_mem && .venv/bin/python scripts/evaluate_planned_transitions.py --render-comparison --comparison-glosses MEDICINE MORNING NIGHT TAKE --artifact-name medicine_morning_baseline_vs_planned_v4 --copy-to /workspace/medicine_morning_baseline_vs_planned_v4.mp4
check_mem && .venv/bin/python -m pytest -q tests/test_plan_transitions.py
```

Omit `MUJOCO_GL=egl` on macOS; macOS was not tested this round. The planner exits 0 after writing a report even when a segment FAILED, so read statuses. If an external copy fails, evaluate preserves the local video and report, records `copy_requested` / `copy_error`, and exits 1. Give single-sentence previews a separate `--report` to preserve the ten-sentence report. The default artifact stem now uses v4; this task explicitly selects both stems with `--artifact-name`.

- [report.json](../results/planned_transitions/report.json), [Chinese table](../results/planned_transitions/report.md), [English table](../results/planned_transitions/report.en.md): all 19 segments' method, source_near, moving endpoint / whole-path clearance, closest pair, duration_s, status and hub records, plus a separate vendor gap list. JSON also includes SHA-256 for all 35 derivation motion inputs and runtime versions.
- [YOU HURT WHERE v4](../results/planned_transitions/you_hurt_where_baseline_vs_planned_v4.mp4); requested copy `/workspace/you_hurt_where_baseline_vs_planned_v4.mp4`.
- [MEDICINE MORNING NIGHT TAKE v4](../results/planned_transitions/medicine_morning_baseline_vs_planned_v4.mp4); requested copy `/workspace/medicine_morning_baseline_vs_planned_v4.mp4`. The failed transition retains its diagnostic label.
- Planned NPZs use `results/mocap_previews/planned_sentence_<GLOSSES>.npz`; baselines use `sentence_<GLOSSES>.npz` in the same directory, with the timestamps_s / joint_names / positions contract.
- [Round 6 planner log](../results/planned_transitions/planner_round6_output.txt), [YOU HURT WHERE verification / render log](../results/planned_transitions/evaluate_round6_you_hurt_where.txt), [MEDICINE verification / render log](../results/planned_transitions/evaluate_round6_medicine_morning.txt).
- [Pre-round-6 round4 archive](../results/planned_transitions/round4_before_round6_archive/report.json) preserves the previous report and ten planned NPZs. Earlier v1/v2/v3 videos, raw experiments and failure records remain.

Both videos use `render_comparison`: baseline on top, planned below, front on the left and right-side view on the right; original 30 fps, with the shorter row holding its last frame and no time warping. File, copy status and video metadata live in report `comparison_videos`. These results and videos are gitignored and require regeneration after a new checkout.

## Actual checks and unverified limits

Final focused pytest: **94 passed (2.98 s)**; see the [test log](../results/planned_transitions/pytest_round6_transitions_final.txt). Tests cover existing R4 constraints plus aggregate library span at 1e-9, inclusion of planner IK joints, arbitrary-name topology derivation, both mount / hip vendor gaps, static contacts neither dominating gates nor ending distance expansion early, and forced left-wrist / mount 1 mm and −3 mm violations still failing and trying hub. Foreman will run full pytest on the host. This round does not claim a host full-suite pass and does not install the missing semantic-model dependency.

Both v4 videos were fully decoded and checked: **30 fps, 960×1088, 282 / 308 frames**. Video frame 124 of MEDICINE was visually confirmed to display FAILED. All **309 clearance results** have finite values and closest pairs from the moving set; see the [artifact audit](../results/planned_transitions/round6_artifact_audit.json). The second render sampled a peak of **3 main-process threads**; preflight memory exceeded 2 GiB before heavy tasks. See the [resource record](../results/planned_transitions/medicine_morning_round6_resources.json).

This managed sandbox mounts `/workspace` read-only. Both requested external copies were actually denied; local videos are complete and `copy_requested` / `copy_error` are recorded. Render commands exited 1 because copying failed. The host still needs to run:

```bash
cp results/planned_transitions/you_hurt_where_baseline_vs_planned_v4.mp4 /workspace/you_hurt_where_baseline_vs_planned_v4.mp4
cp results/planned_transitions/medicine_morning_baseline_vs_planned_v4.mp4 /workspace/medicine_morning_baseline_vs_planned_v4.mp4
```

These are developer regression checks, not frozen independent review by non-tuners. PASS only means sampled moving pairs meet +2 mm. source_near is endpoint-relative and may retain substantial penetration; FAILED is diagnostic only. Vendor structural gaps describe geometry under the stated constant-joint condition and do not certify hardware structural safety. Word-core speed / collision, continuous inter-sample collision, dynamics, hardware execution, ASL meaning and actual user comprehension remain unverified.

## Git handoff

Deliver code, scripts, tests and paired documentation only; do not stage generated outputs, push, or delete files. If read-only `.git` prevents staging / committing, leave changes unstaged and let foreman use [FILE_LIST](../results/planned_transitions/FILE_LIST.txt) on the host:

```bash
git add src/sign_robot/transitions.py scripts/plan_transitions.py scripts/evaluate_planned_transitions.py tests/test_plan_transitions.py docs/transition-planner.md docs/transition-planner.en.md
git commit -m "feat(group3): moving-pair clearance gate and vendor structural gaps"
```

`motions/`, `retarget.py`, `ACTION_IDS`, `scripts/prepare_robot.py`, vendor geometry and collision masks are unchanged.
