# Group 3 transition planner, round 13c

[中文](transition-planner.md) · **English**

## Round 13c-f80x: named NURSE:80 exception, smoke PASS / PASS

Departure defaults retain `NURSE:80`, `MEDICINE:73`, `NIGHT:61`, and `HURT:66`, with no DOCTOR override. NURSE on `bcdefc4` / video 39089 has sign=f24–88 and core=f24–102, an inclusive core length of 79. Arrival stays at f24 with no start trim; departure trims **8/79 = 10.126582278481013%**, exceeding the strict 10% cap. The production entry point `source_end_frame` enforces **`trim_frames / core_len <= 0.10`** by default, equivalent to `floor(0.10 * core_len)` whole frames, or 7 frames here for NURSE.

**The sole exception is `TRIM_CAP_EXCEPTIONS = {"NURSE": 80}`**, with the source comment `NURSE exception 10.13%, pending Thomas's confirmation`. Both gloss and departure frame must match exactly to bypass the fraction gate. Removing the exception or making it mismatch causes NURSE:80 to raise `ValueError`; NURSE:79 remains rejected. MEDICINE, NIGHT, and HURT have no exceptions, and all other words retain the strict 10% check. This implementation does not claim Thomas has confirmed the exception or that 8/79 is ≤10%. Integer core/sign bounds always apply. Library assets, metadata, and retained original word samples stay intact.

This worktree's actual `NOW NURSE BLOOD-DRAW` [smoke report](../_scratch/r13c_f80x_smoke/report.json) and [saved-trajectory recheck](../_scratch/r13c_f80x_smoke/verification.json) give **2 transitions = 2 PASS / 0 source_near / 0 failed**:

| Transition | Method / status | Duration s | Minimum signed clearance mm | Source / target clearance mm |
|---|---|---:|---:|---|
| NOW→NURSE | via2 / PASS | 1.033333 | +9.365600 | +9.502134 / +9.365600 |
| NURSE→BLOOD-DRAW | rrt_connect / PASS | 1.000000 | +3.470359 | +9.500561 / +9.500673 |

Neither sampled transition has negative clearance or `source_near` status. `PAIR_VIA_PREFERENCES` still prefers the existing via2 `out+up+forward → out+up+forward` only for NOW→NURSE among candidates passing the original clearance/endpoint gates. `RRT_PAIRS` still contains MEDICINE→MORNING and NURSE→BLOOD-DRAW. Here NURSE→BLOOD-DRAW actually uses minimum-jerk RRT edges after direct, via1/via2, hub, and retract/approach all fail: `rrt_interpolation="minimum_jerk_per_edge"`, `rrt_minimum_duration_s=1.0`, and an actual duration of 1 s. The 0.3 s per-leg floor, 15/8 continuous peak-rate bound, dense edge and timed-sample rechecks, checked fallback on smoothing failure, and one-shot budget remain. MEDICINE retains its original linear edge timing and 0.3 s total floor.

The strict-cap variant's NURSE:81 endpoint measures **−28.426881 mm (left_wrist_pitch_link / torso_link)**. It can be accepted as `source_near` but does not meet absolute +2 mm PASS. Neither via2 nor RRT can remove penetration while retaining that endpoint. This variant obtains the sampled results above using the explicit f80 exception pending confirmation.

From this worktree's root, use the existing `.venv`, run heavy tasks sequentially, and first check for at least 2 GiB available memory as in the startup section below. Actually executed:

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl PYTHONDONTWRITEBYTECODE=1
.venv/bin/python -m pytest -q tests/test_plan_transitions.py tests/test_transition_endpoint_gate.py tests/test_rrt_connect.py
.venv/bin/python scripts/plan_transitions.py NOW NURSE BLOOD-DRAW --out-dir _scratch/r13c_f80x_smoke --report _scratch/r13c_f80x_smoke/report.json
```

Focused pytest: **248 passed / 0 failed (8.08 s)**, recorded in [_scratch/r13c_f80x_pytest.txt](../_scratch/r13c_f80x_pytest.txt). Tests cover the sole exception, no MEDICINE/NIGHT/HURT exceptions, rejection of excess trims elsewhere, rejection of NURSE:80 without a matching exception, rejection of NURSE:79, and the existing via2/RRT regressions. The existing `verify_saved_sentence` also rechecked this sentence's saved NPZ, endpoints, rates, timing, dense RRT edges, and clearance statuses. `_scratch` contains uncommitted local developer records. No full-batch planning, full pytest, rendering, or push was performed; this round uses local commits only. Developer regression and sampled geometry do not validate continuous collision freedom, word cores, dynamics, hardware, ASL meaning, or actual user comprehension. Historical records follow.

## Round 13b historical record: late arrival and RRT allowlist

`TARGET_START_FRAME_OVERRIDES = {"INTERPRETER": 25}` is the only new frame override. The local [R13b scan](../_scratch/r13b_diagnosis_scan.json) records **−26.745 mm** at INTERPRETER's library sign_start=f24 and **+4.856 mm** at f25. This trims **1/54 = 1.85%** of the inclusive core length from sign_start, below 10%. It affects the stitched arrival endpoint, preserves library assets and metadata, and does not certify the word core.

`target_start_frame(word, overrides=...)` mirrors the departure mechanism: `None` uses the module default and `{}` disables trims. An override must be an integer within `core_frames ∩ sign_frames`, strictly after library sign_start and no later than core_end or sign_end. The first word still starts at f0 and the final word keeps its neutral return. The transition endpoint, following word slice, approach slice `q[:start+1]`, and handoff frame all use the resolved arrival. Reports always record `target_start_frame_overrides`; the evaluator rechecks the saved policy and uses library starts for legacy reports without this field. Departure defaults remain `MEDICINE:73`, `NIGHT:61`, and `HURT:66`.

The gate now uses `RRT_PAIRS = frozenset({("MEDICINE", "MORNING"), ("NURSE", "BLOOD-DRAW")})`. Each allowlisted directed transition may make one arm-only RRT attempt after direct, via1/via2, hub, and retract/approach all fail, including original-slice collisions. The report lists both pairs in `rrt_override.pairs`, replacing the single-pair `rrt_override.glosses`. Seed **5412**, total budget **120 s**, arm **15 rad/s**, finger **10 rad/s**, normal-path **+2 mm** floor, and the monotonic endpoint-attachment gate remain unchanged.

Run this round's focused checks from the repository root:

```bash
.venv/bin/python -m pytest -q tests/test_plan_transitions.py tests/test_transition_endpoint_gate.py tests/test_rrt_connect.py
```

Actual result: **227 passed / 0 failed (4.13 s)**; see local [_scratch/sol_r13b_round1_pytest.txt](../_scratch/sol_r13b_round1_pytest.txt) and the [delivery record](../_scratch/sol_r13b_round1_result.md). These are developer regression checks. This round did not replan the 19 transitions or run full pytest. Updated transition geometry, continuous collision freedom, word cores, dynamics, hardware, ASL meaning, and user comprehension remain unverified. Round 13 and earlier results below are historical and do not describe trajectories after this fix.

## Round 13 historical record: replan after rebasing onto bcdefc4

This round rebases onto Group 2 `bcdefc4`, retaining the planner cherry-picks and excluding the wrist-fix commits. The old `NURSE:57` / `DOCTOR:87` entries used motion frame numbers from before the rebase and were cleared in `ac67b76`. Commit `a2b2379` then added three source-end early-departure overrides based on scans of the current motions:

| Source word and departure frame | Trimmed frames / inclusive core length | Trim percentage | Corresponding transition result |
|---|---:|---:|---|
| MEDICINE:73 | 1/70 | 1.4% | MEDICINE → MORNING: PASS / via2 |
| NIGHT:61 | 3/55 | 5.5% | NIGHT → TAKE: PASS / direct |
| HURT:66 | 4/68 | 5.9% | HURT → WHERE: PASS / direct |

All three departure frames lie within the current `core_frames ∩ sign_frames`, with trims **≤10% of core length**. Overrides affect only the departing source frame during stitching; motion-library assets, metadata and arrival frames stay intact. The old NURSE / DOCTOR overrides remain cleared.

### Round 13 actual results and limits

The pass1 report for ten sentences gives **19 transitions = 17 PASS / 1 source_near / 1 FAILED**. The report is local at `results/planned_transitions/round13/report.json`, is gitignored, and is excluded from this documentation commit. Neither remaining issue is at the departing word's source end, so this round performs no second override round:

| Transition | Status / method | Remaining issue |
|---|---|---|
| NEED → INTERPRETER | source_near / via2 | Near/penetrating INTERPRETER arrival endpoint; not a NEED source-end issue. |
| NURSE → BLOOD-DRAW | FAILED / retract_approach | Defect along the retract/approach path, after the core; NURSE sign_end is already clear. |

Limits remain **15 rad/s for arms, 10 rad/s for fingers, and at least +2 mm moving-pair clearance for PASS**, with the round 9 monotonic endpoint-attachment gate retained. Across the 17 PASS transitions only, the minimum clearance is **2.178434 mm (MORNING → NIGHT)**; the maximum arm rate is **14.49875 rad/s (MORNING → NIGHT)**; the maximum finger rate is **9.502528 rad/s (APPOINTMENT → HAVE)**.

The existing full pytest run actually completed with **477 passed / 6 failed (17.73 s)**. Failed IDs match the six known baseline failures, with no new failures; see local `_scratch/r13_pytest.txt`. The MEDICINE HF jitter proxy check on `bcdefc4` records **PASS, arm_rev=4 / wrist_rev=4**, counting only consecutive-frame velocity sign flips with `|v|>0.1 rad/s` on both sides; see local `_scratch/r13_medicine_jitter.json`. The two remaining issues are diagnosed in local `_scratch/r13_diagnosis.md`. These raw records remain intact. This documentation delivery checked existing reports and logs without rerunning the planner or pytest.

`source_near` passes only the endpoint-relative floor and additional geometry gate and may retain arrival-end penetration; FAILED trajectories are diagnostic only. These are developer regression and sampled geometry checks, not frozen independent evaluation or human review. They do not validate continuous collision freedom, word cores, dynamics, hardware, ASL meaning or user comprehension.

### Round 13 reproduction entry point

From the repository root, use the existing `.venv` and first set the thread environment and `check_mem` (at least 2 GiB available) from the [round 9 startup section](#round-9-startup-and-regeneration) below. Run heavy tasks sequentially. These commands write to a separate `round13_recheck/` directory, preserving this round's `round13/` and historical artifacts. They were not executed during this documentation delivery:

```bash
check_mem && .venv/bin/python scripts/plan_transitions.py --all --out-dir results/planned_transitions/round13_recheck --report results/planned_transitions/round13_recheck/report.json
check_mem && .venv/bin/python scripts/evaluate_planned_transitions.py --report results/planned_transitions/round13_recheck/report.json --out-dir results/planned_transitions/round13_recheck
check_mem && .venv/bin/python -m pytest -q
```

The planner may exit 0 even with failed transitions, so inspect report statuses. The bilingual documentation delivery record is [_scratch/sol_r13_docs_result.md](../_scratch/sol_r13_docs_result.md). Round 9 and earlier records remain below; their results apply only to their original baselines.

## Round 9 historical record

Round 9 adds **endpoint-attached, monotonic exit verification for samples below 2 mm**, in addition to the existing worse-endpoint relative floor. Moving-pair `ENDPOINT_NEAR_M = 0.002 m`, arm 15 rad/s and finger 10 rad/s limits stay unchanged; RRT-Connect was then limited to MEDICINE→MORNING (see the R13c section above for the current two-pair allowlist and timing). Regenerated artifacts use `results/planned_transitions/round9/`; round 8 Step 3 and older raw artifacts remain intact. These are developer geometry checks, not ASL validation. Singleton sentences have no transition checks and do not certify word cores.

## Additional round 9 acceptance rule

Compute the **minimum signed clearance over eligible moving body pairs** at every trajectory sample. Meeting the search floor alone is insufficient for acceptance. If any sample is strictly below 2 mm, all of these conditions must also hold:

1. All samples below 2 mm form exactly one contiguous interval attached to the source or target endpoint whose own clearance is also below 2 mm.
2. Read inward from the attached endpoint: clearance is non-decreasing until the first sample at least 2 mm. Reverse the sample order for target attachment.
3. After the first sample at least 2 mm, the rest of the path never drops below 2 mm again.

The relative floor still guides search; an attempt failing the new gate cannot remain `PASS` or `source_near`. Each segment and attempt records `sub_2mm_frame_intervals` (**transition-local, zero-based, inclusive**) and `sub_2mm_monotonic_ok`. With no samples below 2 mm, intervals are `[]` and this additional gate passes. `sub_2mm_attached_endpoint` identifies source or target attachment; `sub_2mm_first_clear_frame` records the first threshold sample and `sub_2mm_reason` records failures. The evaluator recomputes these values from the full saved trajectory instead of trusting the old report.

If every sample is below 2 mm and no clear frame exists, check the whole path for non-decreasing clearance from an eligible endpoint, with `sub_2mm_first_clear_frame=null`; there is no additional requirement to reach 2 mm. No accepted path in this run uses that edge case.

## Round 9 actual results

Regenerating ten sentences gives **19 transitions = 16 PASS, 3 source_near, 0 FAILED / needs_group2_fix**. All 19 additional gates are `true`, and statuses match `round8_step3`. The [trajectory identity audit](../results/planned_transitions/round9/trajectory_identity.json) verifies bit-exact arrays for all 19 transitions and ten complete sentences. All ten saved NPZ SHA-256 hashes also match the `round8_step3/` files corresponding to `336ed69`. This round adds verification/reporting without changing trajectories. Rendering the same inputs is therefore equivalent across revisions; no heavy round 9 render has been run.

| Transition | Status | Sub-2 mm frame intervals (path-local, inclusive) | Monotonic endpoint-attached check |
|---|---|---|---|
| HELLO → YOU | PASS | [] | true |
| YOU → APPOINTMENT | PASS | [] | true |
| APPOINTMENT → HAVE | PASS | [] | true |
| MEDICINE → MORNING | source_near | [[0, 0]] | true |
| MORNING → NIGHT | PASS | [] | true |
| NIGHT → TAKE | PASS | [] | true |
| NOW → NURSE | source_near | [[7, 9]] | true |
| NURSE → BLOOD-DRAW | PASS | [] | true |
| PLEASE → WAIT | PASS | [] | true |
| WAIT → DOCTOR | PASS | [] | true |
| DOCTOR → COME | source_near | [[0, 1]] | true |
| COME → SOON | PASS | [] | true |
| YOU → BUY | PASS | [] | true |
| BUY → BOOK | PASS | [] | true |
| YOU → HURT | PASS | [] | true |
| HURT → WHERE | PASS | [] | true |
| YOU → NEED | PASS | [] | true |
| NEED → INTERPRETER | PASS | [] | true |
| YOU → UNDERSTAND | PASS | [] | true |

All three near-endpoint segments leave the 2 mm gate after one contiguous run and never re-dip:

- **MEDICINE→MORNING** attaches to the source: f0 **−0.809260 mm** → f1 **+2.757020 mm**. First clear frame is f1; status/method remains `source_near / rrt_connect`.
- **NOW→NURSE** attaches to the target. Reading backward from f9 gives **−32.846892 → −26.332107 → −17.368712 → +8.476263 mm** (f9→f8→f7→f6). First clear frame is f6; status/method remains `source_near / direct`.
- **DOCTOR→COME** attaches to the source: f0→f1→f2 gives **−7.853912 → +1.066278 → +5.074008 mm**. First clear frame is f2; status/method remains `source_near / direct`.

`source_near` retains this endpoint penetration. It passes the relative floor and the new geometry gate, without certifying absolute +2 mm clearance. Inspect the [JSON](../results/planned_transitions/round9/report.json), [generated Chinese table](../results/planned_transitions/round9/report.md), [generated English table](../results/planned_transitions/round9/report.en.md) and [round delivery note](../_scratch/sol_r9_result.md).

The evaluator remeasured endpoints, rates, clearances, the monotonic attachment gate, and existing RRT/original-slice constraints for all ten saved trajectories. Full pytest actually completed with **418 passed, 6 failed (17.79 s)**. The six failed test IDs exactly match the archived baseline six; there are no new failures. The final complete run with working local test servers is logged in [pytest_full_socket_enabled.txt](../results/planned_transitions/round9/pytest_full_socket_enabled.txt). The new batch rendering test uses a mocked renderer and encoder to check order, singletons, endpoint holds, labels, metadata and single-thread encoding options. No MP4 was rendered in this round.

These are developer regression checks, not frozen independent evaluation or human review. Sampling does not certify continuous collision freedom. Word-core speed/collision, dynamics, hardware, ASL meaning and user comprehension remain unverified.

## Round 9 startup and regeneration

Run sequentially from the repository root with the existing `.venv`; do not install `sentence_transformers`. Before every heavy task, use the same memory check for at least 2 GiB available and keep only one heavy process running:

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export LP_NUM_THREADS=1 MESA_GLTHREAD=false MUJOCO_GL=egl
check_mem() {
  awk '/MemAvailable/{ok=$2>=2097152; printf "MemAvailable_KiB=%d ok=%s\n",$2,(ok?"yes":"no"); exit !ok}' /proc/meminfo
}
check_mem && .venv/bin/python scripts/plan_transitions.py --all --out-dir results/planned_transitions/round9 --report results/planned_transitions/round9/report.json
check_mem && .venv/bin/python scripts/evaluate_planned_transitions.py --report results/planned_transitions/round9/report.json --out-dir results/planned_transitions/round9
check_mem && .venv/bin/python -m pytest -q
```

`--report` explicitly selects the input JSON; `--out-dir` alone does not select the new report. The planner exits 0 even with failed segments, so inspect statuses. Focused unit tests mock clearance sequences for a monotonic exit, a later re-dip below 2 mm, and decreasing clearance within the endpoint run; they do not run a full MuJoCo RRT.

## One comparison video for the complete sentence batch

`--render-all-comparison` reuses the existing renderer to encode **all ten sentences (eight multi-word and two singletons)** into one MP4 in report order, with sentence numbers and gloss labels. Baseline is on top, planned below; front is left and right-side is right. Playback stays at the original 30 fps. Within each sentence the shorter row holds its last frame; both restart at frame zero for the next sentence. Encoding fixes `ffmpeg_params=["-threads", "1"]`. Per-sentence frame intervals in video metadata are **video-local, zero-based, inclusive**, distinct from the transition-local intervals above.

| Order | Sentence | Type |
|---|---|---|
| 1 | HELLO YOU APPOINTMENT HAVE | Multi-word |
| 2 | MEDICINE MORNING NIGHT TAKE | Multi-word |
| 3 | NOW NURSE BLOOD-DRAW | Multi-word |
| 4 | PLEASE WAIT DOCTOR COME SOON | Multi-word |
| 5 | YOU BUY BOOK | Multi-word |
| 6 | YOU HURT WHERE | Multi-word |
| 7 | YOU NEED INTERPRETER | Multi-word |
| 8 | YOU UNDERSTAND | Multi-word |
| 9 | BREATHE-DEEP | Singleton |
| 10 | THANK-YOU | Singleton |

After setting the thread environment and `check_mem` function above, the host can run:

```bash
check_mem && .venv/bin/python scripts/evaluate_planned_transitions.py --report results/planned_transitions/round9/report.json --out-dir results/planned_transitions/round9 --render-all-comparison --artifact-name all9_sentences_baseline_vs_planned_r9 --copy-to /workspace/all9_sentences_baseline_vs_planned_r9.mp4
```

The requested filename retains `all9`; the actual scope is the ten sentences listed above. If the external copy fails on a read-only filesystem, the completed local video stays at `results/planned_transitions/round9/all9_sentences_baseline_vs_planned_r9.mp4`, the JSON records the copy error, and the process exits 1. The host can copy that file. Single-sentence `--render-comparison --comparison-glosses ...` remains available. Omit `MUJOCO_GL=egl` on macOS; macOS was not checked.

## Round 8 Step 3 historical baseline

Round 8 Step 3 added **one arm-only RRT-Connect attempt for MEDICINE→MORNING only**, after every existing route failed, including in-slice collisions. That round's `results/planned_transitions/round8_step3/` run verified **19 transitions = 16 PASS, 3 source_near, 0 failed**, before the round 9 monotonic exit gate existed. MEDICINE→MORNING met its endpoint-relative floor; this does not certify +2 mm clearance or ASL meaning. Its distance/search protocol and historical results are retained below.

### Deriving static pairs

At construction, `MujocoClearance` reads `motions/hospital_v1_motions.json` and every frame of all 35 referenced motions (4485 frames), accumulating joint extrema across files. A span strictly greater than **1e-9 rad** marks a moving joint; the planner's actual bilateral `retarget.ARM_SUFFIXES` IK contract is included too. Unknown model joints without library evidence remain conservatively moving. The current model has **38 moving joints**. The established 12 constant leg joints and 3 constant waist joints retain model qpos0.

For each body, follow `body_parentid` to world and collect its own and all ancestor moving joint IDs. `derive_static_body_pairs(model, moving_joint_ids)` compares these sets: **equal sets mean no moving joint lies on the kinematic path between the bodies, so their relative pose is static**. The computation uses model topology and motion data, without a handwritten body-pair list. It derives **136 distinct-body static pairs** in this model, containing no arm, wrist, finger or hand bodies. `fixed_mount` versus either hip_pitch_link is static; wrist versus mount is moving even though the mount itself is fixed.

At the constant pose, construction temporarily expands geom / explicit-pair `mj_collision` detection margins to span the scene, retaining native filtering and same-hand exclusions, then measures each detected static geom pair with **`mj_geomDistance`** and deduplicates by geom IDs. This avoids depending on coarse mesh contacts at large detection margins. The **47 eligible geom pairs** are recorded in `vendor_structural_gaps`, with `bodies`, `geoms`, `geom_ids`, `distance_m` and `distance_mm`. Examples:

| Vendor structural gap | Distance mm |
|---|---:|
| fixed_mount / left_hip_pitch_link | +0.701651 |
| fixed_mount / right_hip_pitch_link | +0.719230 |

The 136 topology body pairs and 47 geom pairs surviving native filtering count different things. Full gap lists and derivation provenance appear at report and sentence level, and remain in selected transitions and clearance results. Geometry, masks and MJCF are not permanently edited; `prepare_robot.py` is unchanged.

### Moving-pair distances and search

Signed distances are **positive for separation and negative for penetration**. `PENETRATION_TOLERANCE_M = 0.002`, `ENDPOINT_NEAR_M = 0.002`, **15 rad/s arm** and **10 rad/s finger** limits are unchanged.

| Moving-pair endpoint class | Whole-path and each hub-leg requirement | Passing status |
|---|---|---|
| Both endpoint minima ≥ 2 mm | Minimum clearance ≥ +2 mm | PASS |
| Either endpoint minimum strictly < 2 mm | Minimum clearance ≥ smaller endpoint clearance | source_near |
| No candidate meets its floor | Retain greatest-minimum candidate, subject to the slice-stop exception below; the special RRT failure is diagnostic only | FAILED / needs_group2_fix |

Exactly 2 mm is not near. `failed_count` includes `needs_group2_fix`; `needs_group2_fix_count` is its subset. Neither counts as accepted. Failed segments retain the `source_near=true` endpoint flag where applicable; `source_near_count` counts relative passes only. `clearance.passed` still means the absolute +2 mm moving-pair check, so near segments also require `status` and `relative_floor_passed`. `min_distance_m`, `closest_pair` / `worst_collision`, `endpoint_clearances_mm` and handoff records never mix in static gaps.

Moving distances retain the R4 numeric query: expand detection margins through 2 mm, 1 cm, 5 cm and 25 cm, then across the scene if needed. Only an eligible **moving pair** can stop expansion; static contacts cannot hide the gated minimum. Read `contact.dist` and restore geom / pair margins in `finally`. Native MuJoCo filtering and the existing same-hand finger / wrist exclusion are unchanged. Separated poses return finite minima and closest body / geom pairs; empty trajectories or models without an eligible moving pair raise errors. Planner poses that change a library-constant joint explicitly reject the now-invalid static classification.

Search escalates **direct → via1/via2 → qpos0 hub → source retract / target approach (c)**, including near endpoints. Passing vias compete on whole-path minimum, except for the R13c NOW→NURSE passing-route preference above; hub checks its whole route and both legs after all vias fail. Route (c) uses inclusive source `positions[sign_frames[1]:]` and target `positions[:sign_frames[0]+1]`, inserting a minimum-jerk bridge if their neutrals differ. Integer frame subdivisions on each edge preserve every original knot, including neutral and bridge knots, without cutting corners. The whole route lasts at least 0.3 s; each bridge leg also lasts at least 0.3 s.

The table's absolute 2 mm rule applies to direct / via / hub. **Route (c)'s whole route and both original library slices always require minimum clearance ≥ the worse endpoint, even when both endpoints are ≥2 mm.** For example, 8 / 12 mm endpoints with a 3 mm route minimum must FAILED for (c). Each attempt and selected transition report their actual `required_clearance_m`; `clearance.passed` still means only the absolute 2 mm check. Evaluate independently rechecks referenced original slices, so passing saved samples cannot override an in-slice FAILED result.

The `failed_trajectory_policy` exception is explicit: an original (c) slice below its floor reports its library frame and pair and selects retract_approach for diagnosis even when an earlier failed candidate has a greater minimum. Pairs outside the allowlist stop there. **RRT_PAIRS permits MEDICINE→MORNING and NURSE→BLOOD-DRAW to continue to the single RRT attempt described below** (Step 3 originally allowed only the former). Other failed searches retain the greatest-minimum candidate. FAILED and needs_group2_fix outputs are diagnostic only. Moving clearances at or above 9.5 mm display as `>=9.5` (`clearance_capped=true`) in the console and both tables; JSON retains raw measurements. The ~9.50015 mm elbow/wrist_pitch reading is a true mesh gap rechecked using `mj_geomDistance(distmax=1.0)`, not query clipping. An accepted direct path with wrist undershoot can search vias for a replacement passing both height and clearance; height-only search does not escalate to hub.

Via1/via2 retain general bilateral offsets, neutral-arm retreat and symmetric serialized retreat families. R13c adds only the NOW→NURSE passing-route preference above, without changing candidate geometry. IK solves arms only, keeping fingers and other coordinates at convex endpoint interpolation; coupled joints are not independent drives. Each leg uses `s(u)=10u³−15u⁴+6u⁵`, rounds the continuous peak `1.875 × |Δq| / T` upward to 30 fps, and lasts at least **0.3 s / nine intervals**. Source words are neither edited nor resampled. Interior words keep inclusive sign_frames; the first keeps frame-0 rise and the last keeps its neutral return. Transition endpoints remain bit-exact.

### One-shot RRT-Connect protocol

The current `RRT_PAIRS` allows MEDICINE→MORNING and NURSE→BLOOD-DRAW; Step 3 originally allowed only the former. Direct, all via1/via2 candidates, hub and retract/approach must fail first. Search connects the resolved source departure pose and target arrival pose without replaying the defective source retract or target approach. Step 3's historical MEDICINE f119 / MORNING f35 are not current endpoints; the override policies above resolve current frames. The failed (c) attempt and its library defects remain in `attempts` and `source_near_handoff`.

- Search exact bilateral `ARM_SUFFIXES`: **14 arm joints**, sampled within finite MuJoCo joint limits. Euclidean nearest/steer, **0.35 rad** step, **0.15** goal bias; RNG is `numpy.random.default_rng(RRT_SEED=5412)`.
- Fingers and every non-arm coordinate are deterministic: derive each knot's progress by clipping its scalar projection onto the arm start→goal vector to [0, 1], then interpolate their source/target coordinates with that weight. Edge timing is linear by default; only new NURSE→BLOOD-DRAW output uses the minimum-jerk timing above along the same geometric edge. No non-arm dimension is searched; coupled fingers are not independent drives.
- Reuse `MujocoClearance` and the same moving-pair/static-gap exclusions. Each edge is checked at **≤0.04 rad per coordinate**. For this source_near pair the entire path must remain **≥−0.0008092600523539207 m**, exactly the worse endpoint. No threshold or rate is relaxed.
- **One attempt, 120 s total cap**: tree search may use at most 96 s, reserving time for smoothing and validation. Monotonic deadlines are checked between queries; native synchronous queries cannot be interrupted mid-call. No seed retry.
- First recheck and rate-scale the unsmoothed reconstructed route. Apply deterministic farthest-first shortcuts that strictly reduce joint-space path length (at most 128 checks; no global optimum claim). Recheck all smoothed edges and exact rate-scaled output. If smoothing/rechecking fails or exhausts its allowance, retain the already checked unsmoothed route.
- MEDICINE retains the original `timescale_to_rate_limits`, exact knots, **15 / 10 rad/s**, **0.3 s** whole-transition minimum and 30 fps. Only new NURSE→BLOOD-DRAW output uses `minimum_jerk_rrt_path` and at least **1 s** in total, with other gates unchanged. Report `min_clearance_m`, mm display, `duration_s`, `rrt_nodes`, `rrt_runtime_s`, `rrt_seed`, `smoothed`, outcome and accepted knots at attempt/segment level.
- No feasible accepted path produces **`needs_group2_fix` / `rrt_connect`**, with no further search. The saved motion is the checked failed (c) diagnostic (`diagnostic_method=retract_approach`), not executable output. Counts exclude it from acceptance. Verification still checks its original library slices.

The implementation choices were recorded before integration in [_scratch/sol_r8_rrt_notes.md](../_scratch/sol_r8_rrt_notes.md), with a Chinese explanation alongside each item.

### Step 3 results and handoff

| MEDICINE→MORNING field | Step 3 actual result |
|---|---:|
| Status / method | source_near / rrt_connect |
| Endpoint clearances mm | −0.809260 / +9.434433 |
| Required floor and saved minimum m | −0.0008092600523539207 |
| Minimum display mm | −0.809260 |
| Transition duration s | 0.466666667 (14 intervals) |
| Tree nodes / seed | 56 / 5412 |
| RRT runtime s | 4.093947754 |
| Smoothed / raw→accepted knots | true / 39→6 |
| Arm / finger peak rad/s | 13.578870 / 2.993295 |

MEDICINE MORNING NIGHT TAKE is now **9.633333 s**, versus baseline **10.066667 s**: delta **−0.433333 s**, previously **+1.600000 s** with the 11.666667 s Step 1 diagnostic. Sentence duration is frame count / 30; transition duration is intervals / 30. The RRT path still reports wrist undershoot; source_near meets only the relative floor and retains the source endpoint penetration.

The [scope audit](../results/planned_transitions/round8_step3/scope_audit.json) checks all **18 other transitions** are bit-exact with Step 1, including method, status, duration, clearance and peak rates. All nine other complete sentences are bit-exact. Ten saved NPZs verify endpoints, rates, floors, accepted RRT knots/non-arm policy/dense edges and vendor-gap consistency. Source-word cores remain untouched.

The Group 2 list remains **identical to Step 1: 17 moving-pair records at 5 word frames**: **MEDICINE f119, MEDICINE f145, MORNING f28, NURSE f24, DOCTOR f89**. RRT does not repair these library defects. The failed (c) attempt still records MEDICINE retract f119–159, MORNING approach f0–35, with f145 `left_wrist_yaw_link / fixed_mount` at −67.599238 mm and f28 `R_thumb_proximal / left_wrist_yaw_link` at −44.832 mm. Static mount/hip gaps remain separate.

### Step 3 historical artifacts

Current regeneration uses the separate `round9/` commands above and preserves these historical directories.

- Step 3 [JSON](../results/planned_transitions/round8_step3/report.json), [Chinese table](../results/planned_transitions/round8_step3/report.md), [English table](../results/planned_transitions/round8_step3/report.en.md), [scope audit](../results/planned_transitions/round8_step3/scope_audit.json), [focused pytest](../results/planned_transitions/round8_step3/pytest.txt).
- [MEDICINE v6 comparison](../results/planned_transitions/round8_step3/medicine_morning_baseline_vs_planned_v6.mp4), with comparison metadata/copy status in JSON. Baseline on top, planned below; front left, right-side right, original 30 fps, shorter row holds its last frame without time warping. Actual video checks are in [artifact_audit.json](../results/planned_transitions/round8_step3/artifact_audit.json).
- Step 3 NPZs are `results/planned_transitions/round8_step3/planned_sentence_<GLOSSES>.npz`, using `timestamps_s / joint_names / positions`. Logs and concise bilingual outcome are in [_scratch/sol_r8_rrt_result.md](../_scratch/sol_r8_rrt_result.md).
- Historical [Step 1 JSON](../results/planned_transitions/round8_step1/report.json) retains 16 PASS / 2 source_near / 1 FAILED and its slice-stop diagnosis. [MEDICINE v5](../results/planned_transitions/medicine_morning_baseline_vs_planned_v5.mp4), [YOU HURT WHERE v4](../results/planned_transitions/you_hurt_where_baseline_vs_planned_v4.mp4), root Round 7 reports, [round4 archive](../results/planned_transitions/round4_before_round6_archive/report.json), older videos and raw records remain intact. Generated plans/videos are gitignored and require regeneration after a new checkout.

### Step 3 actual checks and unverified limits

Focused pytest: **120 passed (4.29 s)**. Checks cover fixed seed stability, exact arm-only indexing and deterministic non-arm behavior, relative-floor acceptance, timeout→needs_group2_fix without retry, authorized direction only, skipping RRT after earlier success, and smoothing recheck failure with safe fallback, alongside the existing transition regressions. Full pytest and commit are left to the host; no push.

These are developer regression checks, not frozen independent evaluation or ASL/user review. PASS certifies only sampled moving pairs at +2 mm. source_near is endpoint-relative and may retain penetration; FAILED/needs_group2_fix are diagnostic only. Sampling does not certify continuous collision freedom; shortcut smoothing does not ensure acceleration continuity. Word-core speed/collision, dynamics, hardware, ASL meaning, real-user comprehension and macOS remain unverified. Vendor gaps certify no hardware safety.

v6 fully decoded as **302 frames, 30 fps, 960×1088**; frame 124 was visually confirmed to display `source_near`. The external copy was actually denied with `[Errno 30] Read-only file system`; rendering exits 1 solely for that copy failure. The local video and verification are complete. Host copies it:

```bash
cp results/planned_transitions/round8_step3/medicine_morning_baseline_vs_planned_v6.mp4 /workspace/medicine_morning_baseline_vs_planned_v6.mp4
```

No staging, commit or push was attempted. `motions/`, `retarget.py`, `ACTION_IDS`, `scripts/prepare_robot.py`, vendor geometry and collision masks are unchanged. Host reviews the [FILE_LIST](../results/planned_transitions/round8_step3/FILE_LIST.txt), runs full pytest and commits.
