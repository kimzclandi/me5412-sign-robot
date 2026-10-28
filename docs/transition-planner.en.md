# Group 3: transition planner, round 3

[中文](transition-planner.md) · **English**

This round adds the endpoint gate, dual vias and neutral-hub fallback on `group3/transition-planner` at `98c0970` (original base `2656412`). All nine scripted sentences plus THANK-YOU were regenerated locally: **19 segments = 16 PASS, three source_collision, zero FAILED**. Counts are disjoint; the compatibility field `accepted_count` still sums PASS and source_collision and is not a safe-execution count. Emitted source_collision direct paths are diagnostic only. BREATHE-DEEP and THANK-YOU are singleton sentences with zero transitions and receive no clearance certification of the words themselves.

## Run and local artifacts

Use the existing `.venv` from the repository root, sequentially, without installing `sentence_transformers`. Before each heavy task, confirm `MemAvailable ≥ 2 GiB`; run only one MuJoCo / planner process and at most three threads:

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export LP_NUM_THREADS=1 MESA_GLTHREAD=false MUJOCO_GL=egl
.venv/bin/python -c 'from pathlib import Path; m = int(next(s.split()[1] for s in Path("/proc/meminfo").read_text().splitlines() if s.startswith("MemAvailable:"))); assert m >= 2 * 1024**2; print("MemAvailable GiB:", m / 1024**2)'
.venv/bin/python scripts/plan_transitions.py --all
.venv/bin/python scripts/evaluate_planned_transitions.py
.venv/bin/python -m pytest -q tests/test_plan_transitions.py
.venv/bin/python -m pytest -q
```

For macOS rendering, omit `MUJOCO_GL=egl`; neither macOS nor a host-capable environment was tested this round. Use a separate report for a single preview so the ten-sentence result is preserved:

```bash
MUJOCO_GL=egl .venv/bin/python scripts/plan_transitions.py YOU HURT WHERE --render --report results/planned_transitions/you_hurt_where_preview.json
```

Generated NPZ files use `results/mocap_previews/planned_sentence_<GLOSSES>.npz` and preserve the `timestamps_s`, `joint_names`, `positions` contract. All artifacts below are gitignored; regenerate them after a fresh checkout:

- [report.json](../results/planned_transitions/report.json), [Chinese table](../results/planned_transitions/report.md), [English table](../results/planned_transitions/report.en.md): `method`, `via_direction` / `via_directions`, `min_clearance_mm` and `duration_s` for all 19 segments, per-sentence total duration against baseline, all candidate attempts, and source-frame handoff.
- [fixed_mount_finding.md](../results/planned_transitions/fixed_mount_finding.md): bilingual source locations, generator and runtime mesh / mask evidence.
- [Planner log](../results/planned_transitions/planner_round3_output.txt), [saved-artifact recheck log](../results/planned_transitions/evaluate_round3_output.txt), [before/after test comparison](../results/planned_transitions/pytest_round3_summary.json), [focused test log](../results/planned_transitions/pytest_round3_transitions_final.txt), [full test log](../results/planned_transitions/pytest_round3_after.txt).
- `report_round2.json` / `.md` / `.en.md` preserve the previous reports. `report_round3_initial.json` preserves the initial result with one remaining FAILED before adding serialized retreat. `serialized_neutral_probe.json` and `serialized_outward_probe.json` retain failed and passing general-candidate probes.

The planner exits 0 after successfully writing artifacts even when reports contain FAILED segments; inspect statuses. Sentence duration means frame count / 30; transition and leg duration mean intervals / 30.

## Ordered escalation protocol

1. **Endpoint gate first.** Check both endpoints separately as single frames. The explicit constant **`ENDPOINT_NEAR_M = 0.0 m`** classifies either endpoint minimum `contact.dist` **strictly `< 0.0`** as `source_collision`, records word, zero-based source frame, body pair and distance, and stops via1, via2 and hub search. This includes inherited hard failures below −2 mm and mild negative contacts inside the tolerance. Exactly 0 does not trigger the gate; null means no detected contacts. MEDICINE frame 119 measures **−0.806716 mm** and must also be handed off. This gate is separate from the path's absolute hard-failure line; a detour cannot conceal a source-pose problem.
2. **Direct.** With both endpoints clear, check a direct min-jerk blend. The absolute rule remains **`contact.dist < -PENETRATION_TOLERANCE_M`, `PENETRATION_TOLERANCE_M = 0.002 m`**. It permits up to 2 mm penetration and does not promise a positive 2 mm gap. Check every emitted sample including endpoints. Null is not a measured positive separation.
3. **Rank via1 and via2 together.** If direct clearance fails, evaluate the fixed seven single-via and sixteen dual-via candidates. Choose the passing candidate with the largest minimum contact distance over its **complete path**, retaining candidate order for ties. No-contact candidates rank above detected contacts but still report null. `method="via1"` has `via_direction`; `method="via2"` has two `via_directions`. Each via uses the existing bounded `G1Retargeter.solve_arms` IK without editing `retarget.py`; neither IK targets nor neutral poses are assumed clear.
4. **Hub fallback.** Only when every via1/via2 candidate fails clearance, try source → hub → target. The hub uses the fixed-base model's **`qpos0` values for the named joints**. Check the complete path and both legs independently; all must pass for PASS / `method="hub"`. If it still fails, report `method="FAILED"` and retain the least-penetrating checked candidate, its worst body pair and distance for diagnosis only. All current 19 segments find accepted candidates before hub; real hub paths can fail, while mocked-clearance unit tests cover selection of a passing fallback.

Single vias retain the robot-frame directions `out`, `up`, `forward`, `out+up`, `out+forward`, `up+forward`, `out+up+forward`. Robot +X is forward, +Y left, +Z up; outward is +Y for the left hand and −Y for the right. Normalized vectors request a 6.5 cm wrist displacement. Single-via IK starts at the endpoint joint midpoint with non-arm coordinates held exactly at that midpoint. Joint bounds can prevent reaching the full target.

The sixteen dual-via candidates use no word identity: seven offset the source and target wrist poses in the same direction; three retreat to qpos0 arms then go out, out+up or out+forward; six try serialized retreat symmetrically for either arm. At both serialized knots, the parked arm uses neutral wrist targets plus out / out+up / out+forward displacement. The other arm stays at source for via1 and reaches target for via2, then the parked arm approaches its target. The latter two families use one-/two-thirds source-to-target interpolation for fingers and other non-arm coordinates. Only arms are solved; upstream coupling is retained, and coupled joints are not independent drives.

Every leg uses `s(u)=10u³−15u⁴+6u⁵`, whose continuous peak speed is `1.875 × |Δq| / T`. Round up to 30 fps intervals satisfying the rate limits and **0.3 s / nine intervals** per leg. Via1 / hub take at least 0.6 s and via2 at least 0.9 s. Arm **15 rad/s** and finger **10 rad/s** limits remain unchanged.

`endpoint_floor_m` and `relative_floor_passed` retain the relative-floor diagnostic for inherited endpoints below −2 mm. The new endpoint gate stops search first; interior worsening is never relabelled as a clearance pass. Source_collision still emits and measures a direct diagnostic path. Wrist undershoot remains separate: an already clear direct path may search for a via that passes both height and clearance, retaining the direct path if none does. A purely aesthetic search never escalates to hub.

Source lookup retains hospital-map precedence followed by existing mocap / video ready / poor filters. Interior words keep inclusive `sign_frames`; the first retains its frame-0 rise and the last its neutral return. Source slices are neither edited nor resampled, and transition endpoints match source values bit-for-bit. The existing same-hand finger / wrist adjacency rule is unchanged; no geom exclusion, collision-mask change or `fixed_mount` filtering was added.

## Results and Group 2 handoff

| Previously FAILED segment | Current status / method | Via directions | Duration s | Whole-path minimum mm |
|---|---|---|---:|---:|
| MEDICINE → MORNING | source_collision | No search | 0.433 | −56.182782 |
| NURSE → BLOOD-DRAW | PASS / via2 | up → up | 1.000 | null |
| COME → SOON | PASS / via2 | neutral_retreat_right+out → hold_right+out | 0.900 | null |
| NEED → INTERPRETER | PASS / via2 | out → out | 0.900 | null |

**The −56.183 mm for MEDICINE → MORNING is the retained direct diagnostic path's measurement, not the endpoint gate value or a passing path.** Its trigger is MEDICINE frame 119, left shoulder yaw / torso (−0.807 mm). NOW → NURSE and DOCTOR → COME also retain source_collision; their worst source endpoints are **−32.892744 mm** and **−7.854003 mm**. The handoff contains **10 body-pair records across three word frames** (MEDICINE 119, NURSE 24, DOCTOR 89), includes within-tolerance contacts, and is deduplicated in sentence and aggregate reports. No source motion was changed.

All ten saved NPZ files were rechecked for endpoints, sampled rates, per-leg duration floor, both endpoint gates and collision classification. Inserted transitions peak at **14.635394 rad/s** for arms and **8.868628 rad/s** for fingers. JSON records input SHA-256 hashes, planner-source hash and runtime versions. Local bilingual tables contain every sentence's duration against baseline. YOU HURT WHERE remains **9.033 s** planned versus **9.400 s** baseline. The v2 comparison video was retained and was not refreshed this round. Optionally run `MUJOCO_GL=egl .venv/bin/python scripts/evaluate_planned_transitions.py --render-comparison` to refresh `results/planned_transitions/you_hurt_where_baseline_vs_planned_v2.mp4`; it also copies to `/workspace/you_hurt_where_baseline_vs_planned_v2.mp4` by default, configurable with `--copy-to`.

YOU → BUY still selects the up via, reducing right-wrist undershoot below the lower endpoint from **0.849769 mm** to zero. Source YOU's internal wrist / elbow peak-to-end drops remain **234.348952 / 54.821335 mm**; a planner preserving source frames cannot repair them. See [you_buy_sag.json](../results/planned_transitions/you_buy_sag.json).

### fixed_mount evidence

[scene.xml lines 65–68](../assets/robot/scene.xml) define the wrapper at z=0.79 m; [prepare_robot.py lines 27–31](../scripts/prepare_robot.py) re-parent the imported robot beneath it; [model_info.json](../assets/robot/model_info.json) explicitly records `Fixed mount at z=0.79m`. Directly attached geoms are visual pelvis, visual pelvis_contour_link (both 0/0), and active collision pelvis_contour_link (runtime `contype=1 conaffinity=1`). It is a virtual mounting / fixed-base placeholder rather than an additional real-robot fixture. Its active mesh is still pelvis-contour geometry and **must remain in collision checks**. This round reports evidence without changing the model. The complete runtime table is in local [fixed_mount_finding.md](../results/planned_transitions/fixed_mount_finding.md).

## Actual tests and limitations

The focused suite has **55 passing tests**, covering the strict endpoint gate without via/hub search, real dual-via IK, neutral qpos0, rates / 0.3 s floor, maximum whole-path clearance selection, hub-leg checks and selection, inherited relative-floor diagnostics, fixed-mount collision and source-frame handoff. The full sandbox baseline was **299 passed, eight failed, 23 errors**; after changes it is **316 passed, eight failed, 23 errors**. The same 31 failure / error IDs remain, with **zero new failures or errors**. Five failures are existing learned_motion / learning_api failures without `sentence_transformers`; one is the existing overview failure. Two further failures and 23 errors come from prohibited sockets. The host reference baseline is **324 passed / six failed**; a host-capable run was unavailable, and the sandbox run is not presented as a host run. No dependencies were installed, tests skipped or related modules changed.

These are developer regression checks, not a frozen independent evaluation by reviewers who did not tune the planner. Source_collision and FAILED artifacts are not safe execution trajectories. Source-word rates / collisions remain unchanged, and whole-sentence peaks are reported separately. Between-sample continuous collision, dynamics, hardware execution, ASL meaning and human comprehension remain unverified.

## Git handoff

Generated artifacts remain gitignored. No push or file deletion is authorized or performed. Deliver only the following six code / test / documentation files, also listed locally in `results/planned_transitions/FILE_LIST.txt`. Here `git add` exited 128 because the worktree `index.lock` could not be created on a read-only filesystem ([error log](../results/planned_transitions/git_handoff_round3.txt)). All six changes remain unstaged; no commit or push was attempted. The foreman can commit on the host:

```bash
git add src/sign_robot/transitions.py scripts/plan_transitions.py scripts/evaluate_planned_transitions.py tests/test_plan_transitions.py docs/transition-planner.md docs/transition-planner.en.md
git commit -m "feat(group3): endpoint-near gate, dual-via and hub fallback"
```

`motions/`, `retarget.py`, `ACTION_IDS`, model / collision masks, baseline clips, existing `.venv` / vendor symlinks and `_scratch/` were not changed.
