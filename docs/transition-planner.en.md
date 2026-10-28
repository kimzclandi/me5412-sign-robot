# Group 3: transition planner, round 4

[中文](transition-planner.md) · **English**

This round implements **`ENDPOINT_NEAR_M = 0.002`, full near-source search and numeric clearance** on `group3/transition-planner` at `3eccb06` (original base `2656412`). All nine scripted sentences plus THANK-YOU were regenerated and rechecked: **19 segments = zero PASS, 18 source_near, one FAILED**. The three statuses are disjoint; `accepted_count` sums PASS and source_near and only counts satisfaction of the applicable planning condition. BREATHE-DEEP and THANK-YOU are singleton sentences with zero transitions and receive no clearance certification of the words themselves.

There are no normal PASS segments because numeric distance measurement finds an unchanged `fixed_mount` / `left_hip_pitch_link` gap of approximately **+0.701652 mm** at every boundary pose, below 2 mm. Neither this body nor any other geom was excluded. The 18 segments meet the endpoint-relative condition; they do not claim absolute +2 mm clearance.

## Run, regenerate and inspect local artifacts

Use the existing `.venv` from the repository root without installing `sentence_transformers`. Run heavy tasks sequentially, check `MemAvailable ≥ 2 GiB` before each, use at most three threads and only one heavy process at a time:

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export LP_NUM_THREADS=1 MESA_GLTHREAD=false MUJOCO_GL=egl
check_mem() {
  .venv/bin/python -c 'from pathlib import Path; m = int(next(s.split()[1] for s in Path("/proc/meminfo").read_text().splitlines() if s.startswith("MemAvailable:"))); assert m >= 2 * 1024**2; print("MemAvailable GiB:", m / 1024**2)'
}
check_mem && .venv/bin/python scripts/plan_transitions.py --all
check_mem && .venv/bin/python scripts/evaluate_planned_transitions.py
check_mem && .venv/bin/python scripts/evaluate_planned_transitions.py --render-comparison --comparison-glosses YOU HURT WHERE --artifact-name you_hurt_where_baseline_vs_planned_v3 --copy-to /workspace/you_hurt_where_baseline_vs_planned_v3.mp4
check_mem && .venv/bin/python scripts/evaluate_planned_transitions.py --render-comparison --comparison-glosses MEDICINE MORNING NIGHT TAKE --artifact-name medicine_morning_baseline_vs_planned_v3 --copy-to /workspace/medicine_morning_baseline_vs_planned_v3.mp4
check_mem && .venv/bin/python -m pytest -q tests/test_plan_transitions.py
check_mem && .venv/bin/python -m pytest -q
```

Omit `MUJOCO_GL=egl` for macOS rendering; neither macOS nor a host environment with permitted sockets was tested this round. Give a single-sentence preview its own report to preserve the ten-sentence aggregate:

```bash
check_mem && .venv/bin/python scripts/plan_transitions.py YOU HURT WHERE --render --report results/planned_transitions/you_hurt_where_preview.json
```

The planner exits 0 after writing artifacts even when there are FAILED segments; read their statuses. Planned NPZs are `results/mocap_previews/planned_sentence_<GLOSSES>.npz`, and baselines are `sentence_<GLOSSES>.npz` in the same directory. Both use `timestamps_s`, `joint_names`, `positions`. Sentence duration is frame count / 30; transition and leg duration is intervals / 30.

The following artifacts are all gitignored and must be regenerated after a fresh checkout:

- [report.json](../results/planned_transitions/report.json), [Chinese table](../results/planned_transitions/report.md), [English table](../results/planned_transitions/report.en.md): `status`, `method`, `source_near`, `endpoint_clearances_mm`, `min_clearance_mm`, `closest_pair` / `worst_collision`, `duration_s`, via directions and complete attempts for all 19 segments. Closest pairs include bodies and geom names or IDs; clearance is always finite and numeric.
- [YOU HURT WHERE v3](../results/planned_transitions/you_hurt_where_baseline_vs_planned_v3.mp4), also copied to `/workspace/you_hurt_where_baseline_vs_planned_v3.mp4`.
- [MEDICINE MORNING NIGHT TAKE v3](../results/planned_transitions/medicine_morning_baseline_vs_planned_v3.mp4), also copied to `/workspace/medicine_morning_baseline_vs_planned_v3.mp4`. Its FAILED transition is diagnostic replay only.
- [Planner log](../results/planned_transitions/planner_round4_adaptive_output.txt), [saved-artifact recheck](../results/planned_transitions/evaluate_round4_output.txt), [test comparison](../results/planned_transitions/pytest_round4_summary.json), [focused tests](../results/planned_transitions/pytest_round4_transitions_final.txt), [full tests](../results/planned_transitions/pytest_round4_after.txt).
- The [R3 archive](../results/planned_transitions/round3_archive/report.json) preserves the previous reports, ten planned NPZs and sag record; original v1/v2 videos and historical experiment logs remain. The first attempt using a uniform 25 cm detection margin was interrupted for slow performance; `planner_round4_output.txt` is retained. The final implementation expands detection progressively.

Videos show baseline on top and planned below, with front views on the left and right-side views on the right. Playback uses original 30 fps; the shorter row holds its last frame. `render_comparison` derives the baseline from supplied glosses, reads the planned NPZ from its report, and takes a separate artifact name. CLI options are `--comparison-glosses`, `--artifact-name`, `--copy-to`. Both video metadata entries are retained in aggregate `comparison_videos`.

## Signed distance and acceptance conditions

Use one convention for MuJoCo collision surfaces: **positive means separation, negative means penetration**. `PENETRATION_TOLERANCE_M = 0.002 m` remains unchanged. A normal path requires **`min_distance_m >= PENETRATION_TOLERANCE_M`**, or at least +2 mm clearance.

| Endpoint class | Required condition for the complete path and each hub leg | Accepted status |
|---|---|---|
| Both endpoint minima ≥ `ENDPOINT_NEAR_M` | Whole-path minimum ≥ +0.002 m | `PASS` |
| Either endpoint minimum strictly < `ENDPOINT_NEAR_M = 0.002 m` | Whole-path minimum ≥ the smaller endpoint clearance | `source_near` |
| Every candidate fails the applicable condition | Retain the checked candidate with greatest minimum clearance for diagnosis only | `FAILED` |

Exactly 2 mm is not near. Positive gaps below 2 mm, mild −0.8 mm contacts and deeper inherited penetrations are near. `source_near=true` is retained on FAILED segments too; `method` always identifies the accepted or diagnostic route as `direct` / `via1` / `via2` / `hub`. `source_near_count` counts only accepted source_near statuses, separately from `failed_count`. On near segments, `endpoint_floor_m` is the worse endpoint and `relative_floor_passed` states whether the selected route meets it. New reports no longer use the name `source_collision`.

Raw `clearance.passed` always describes the absolute +2 mm check. Use `status` and `relative_floor_passed` for relative acceptance of near segments; source_near can therefore coexist with `clearance.passed=false`.

### Numeric distance without original contacts

At every emitted sample, `MujocoClearance` first computes the original model's kinematics, then temporarily raises geom and explicit-pair detection margins for `mj_collision`: start at 2 mm, expand if needed to 1 cm, 5 cm, 25 cm, then the current geom-center span plus 1 m. Once an eligible non-same-hand pair is measured, omitted farther pairs cannot lower the minimum. `contact.dist` is the surface distance; the detection margin is neither subtracted nor used as the acceptance threshold.

A `finally` block restores original geom / pair margins after every query. The MJCF, contype / conaffinity, native MuJoCo pair filtering and existing same-hand finger / wrist exclusion remain unchanged; `fixed_mount` is retained. Separated poses with no original contacts still return finite `min_distance_m` and a closest body / geom pair; a 1.2 m separated-sphere test covers expansion beyond 25 cm. Empty trajectories or models with no eligible non-same-hand pair raise an explicit error instead of inventing a distance or returning null. Round 4 values use this consistent detection process and must not be mixed with R3 measurements.

## Search order for every segment

1. Measure both endpoints to choose the absolute or relative floor; **do not stop search**. Check the direct min-jerk path including both boundaries and accept if it meets the applicable floor.
2. If direct fails, evaluate the existing seven via1 candidates, then sixteen via2 candidates, including neutral-retreat and symmetric serialized retreat. Rank passing via1/via2 paths by greatest whole-path minimum clearance, retaining candidate order for ties.
3. If every via fails, check source → `qpos0` hub → target. Use original named-joint values from the fixed-base model's neutral pose. Check the whole path and both legs separately against the same floor; never assume the hub is clear.
4. If all fail, report FAILED with the best diagnostic route's worst body / geom pair, frame and clearance. Never accept a worsening direct path as source_near.

A direct path already meeting clearance may search vias to remove wrist undershoot. Only a candidate passing both height and clearance can replace it; otherwise retain direct with a warning. A height-only search does not escalate to hub.

Via1 retains robot-frame `out`, `up`, `forward` and combined directions: +X forward, +Y left, +Z up, normalized to request 6.5 cm wrist displacement. Via2 retains endpoint-direction offsets, neutral-arm retreat and serialized parking of either arm while the other moves, with no word-specific exceptions. The existing bounded `G1Retargeter.solve_arms` solves arms only; other coordinates retain midpoint or one-/two-thirds convex interpolation. Upstream coupling remains intact, and coupled joints are not independent drives.

Every leg uses `s(u)=10u³−15u⁴+6u⁵`, with continuous peak speed `1.875 × |Δq| / T`, rounded up to 30 fps intervals and at least **0.3 s / nine intervals** per leg. Arm **15 rad/s** and finger **10 rad/s** limits remain unchanged. Source motions are neither edited nor resampled. Interior words retain inclusive `sign_frames`; the first keeps its frame-0 rise and the last its neutral return. Transition endpoints match source values bit-for-bit.

## Results and Group 2 handoff

| Segment | Status / method | Via directions | Duration s | Endpoint clearances mm | Whole-path minimum mm |
|---|---|---|---:|---|---:|
| MEDICINE → MORNING | FAILED / via2 | neutral_retreat_left+out+forward → hold_left+out+forward | 1.100 | −0.809260 / +0.701652 | −42.047690 |
| NURSE → BLOOD-DRAW | source_near / via2 | up → up | 1.000 | +0.701652 / +0.701652 | +0.701652 |
| COME → SOON | source_near / via2 | neutral_retreat_right+out → hold_right+out | 0.900 | +0.701652 / +0.701652 | +0.701652 |
| NEED → INTERPRETER | source_near / via2 | out → out | 0.900 | +0.701652 / +0.701652 | +0.701652 |

MEDICINE → MORNING checks **25 complete routes: one direct, seven via1, sixteen via2, one hub**. Direct measures **−56.182729 mm**, hub **−54.852146 mm**, and even the best via2 is **−42.047690 mm**, below its **−0.809260 mm** relative floor. Output and video explicitly mark it FAILED diagnostic replay. The best route's worst pair is `fixed_mount` / `left_wrist_yaw_link` (geom 3 / 57), at transition-local frame 5.

`source_near_handoff` is deduplicated in sentence and aggregate reports: **83 body-pair records across 34 word frames**, each with word, zero-based source frame, pair and `clearance_mm`, including near endpoints of FAILED segments. Fixed-base / hip gaps remain at all boundaries. Additional source problems are MEDICINE frame 119 at approximately −0.809260 mm, NURSE frame 24 at −32.846892 mm and DOCTOR frame 89 at −7.853912 mm. Source motions were not changed.

All ten saved NPZs were actually rechecked for endpoints, rates, leg duration, numeric clearance and classification. Inserted transitions peak at **14.635394 rad/s** for arms and **8.868628 rad/s** for fingers. JSON records input SHA-256 hashes, planner-source hash and runtime versions. YOU HURT WHERE is **9.033 s** planned versus **9.400 s** baseline; MEDICINE MORNING NIGHT TAKE is **10.267 s** planned versus **10.067 s** baseline.

YOU → BUY still selects the up via, reducing right-wrist undershoot below the lower endpoint from **0.849769 mm** to zero. Source YOU's internal wrist / elbow peak-to-end drops remain **234.348952 / 54.821335 mm**; see [you_buy_sag.json](../results/planned_transitions/you_buy_sag.json).

`fixed_mount` remains the z=0.79 m fixed-base wrapper whose active pelvis-contour collision mesh must be retained. Source definitions and runtime evidence are in [fixed_mount_finding.md](../results/planned_transitions/fixed_mount_finding.md). Only temporary query margins are expanded; model files and collision masks are unchanged.

## Actual tests and limitations

The final focused suite has **88 passing tests**, covering numeric separated clearance, the normal +2 mm floor, strict near classification, relative near-source passes and complete search after relative failure, via1/via2/hub route identity, FAILED segments excluded from accepted counts while retaining handoff, rates, the 0.3 s floor, real IK, same-hand exclusion and fixed_mount checks.

The full suite was **316 passed, eight failed, 23 errors** before changes and **349 passed, eight failed, 23 errors** afterward. **All 31 failure / error IDs are identical, with zero new failures or errors.** Six are the existing learned_motion / learning_api / overview failures in the task's supplied host reference; two further failures and 23 errors come from prohibited sandbox sockets. A host-capable run was unavailable and is not claimed. Full ID sets are in [pytest_round4_summary.json](../results/planned_transitions/pytest_round4_summary.json). No dependencies were installed, tests skipped or those modules changed.

Both v3 videos were actually decoded and checked at **30 fps, 960×1088**, with **282 / 308 frames** respectively. Their designated `/workspace` copies have identical SHA-256 hashes; a MEDICINE failure frame was visually confirmed to show `FAILED`. All **309 recursively checked clearance results are finite and have a closest body / geom pair**; see [round4_artifact_audit.json](../results/planned_transitions/round4_artifact_audit.json). The renderer measured three threads; available memory exceeded 2 GiB before every heavy task.

These are developer regression checks, not a frozen independent review by people who did not tune the planner. source_near only means no worse than the source endpoints and can retain substantial penetration; FAILED is diagnostic only. Source-word rates / collisions remain, and whole-sentence peaks are reported separately. Between-sample continuous collision, dynamics, hardware execution, ASL meaning and human comprehension remain unverified.

## Git handoff

Deliver only `src/sign_robot/transitions.py`, `scripts/plan_transitions.py`, `scripts/evaluate_planned_transitions.py`, `tests/test_plan_transitions.py`, this English document and its Chinese counterpart, also listed in [FILE_LIST.txt](../results/planned_transitions/FILE_LIST.txt). Generated artifacts are not staged. No push or file deletion is performed. If read-only `.git` prevents staging / committing, leave changes unstaged for the foreman to commit on the host:

```bash
git add src/sign_robot/transitions.py scripts/plan_transitions.py scripts/evaluate_planned_transitions.py tests/test_plan_transitions.py docs/transition-planner.md docs/transition-planner.en.md
git commit -m "feat(group3): near-source search with numeric clearance"
```

`motions/`, `retarget.py`, `ACTION_IDS`, original model / collision masks, baseline clips, existing `.venv` / vendor symlinks and `_scratch/` remain unchanged.
