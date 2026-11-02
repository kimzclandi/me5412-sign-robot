# TASK-22 — R1–R7 rerun after the user corrected protected intervals

[中文](TASK-22.md) · [Current state](STATE.en.md)

**Correction implemented and all four pairs rerun; numerical pass 0/4, motion objective remains unmet.** All 799 regression tests passed, and 62 staging engineering checks passed. Engineering delivery and motion acceptance are separate. Formal acceptance remains false.

User wording: “我要更正一下，COME是0.93～4.40s，NOW是0.13～2.53s”. Outward rounding at 30 Hz, zero based and inclusive: COME [27,132] (106 frames, 0.90–4.40 s), NOW [3,76] (74 frames, 0.10–2.533333 s). These supersede [27,141]/[3,102]. Old v1 configurations, TASK-15–21 and runs remain unchanged. v2 is the new input/policy version; protection schema stays 1 and trajectory schema 2. Contract semantics do not change.

Target `/home/kingderman/Documents/ME5412-github-latest`, branch `codex/group3-all-pairs-v1`, HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`. Chat cwd differs from the target. A fresh restored copy of the currently installed repository was used before enumerated installation. Existing automatic-window implementation was already present, so this correction updates necessary inputs, tests and reports without algorithm refactoring.

| Task | Files/models changed | Decision and command/operation | Verification | Deviation |
|---|---|---|---|---|
| R1 | HANDOFF.md/.en.md; new R1 evidence | me5412_preserve_correction.py archives current Git, uncommitted/untracked files and results, then restores a fresh stage | All 8,726 entries match; source unchanged; exit 0 | Baseline is the installed previous delivery, not the stale prior stage |
| R2 | New user_protected_come_now_v2.json and transition_policy_user_protected_v2.json; test_user_protected_correction.py; bilingual docs indexes and two project_overview.py SHAs | Bind new IDs to exact correction and motion hashes; keep contract; freeze identical limits; run window/contract tests | 82 passed, exit 0; versions distinct, legacy approval compatible | No algorithm rewrite; required download-hash updates only |
| R3 | New R3 screening/check evidence; no production changes | screen_user_protected_cuts.py on four real pairs; check_endpoint_screen.py audits every saved boundary state | Valid exit/entry: COME 65/28, NOW 27/3; 19 passed; all exit 0 | Reuse existing screening implementation |
| R4 | New run and R4 analysis; original motions unchanged | plan_all_pairs.py direct→neutral/IK/retract→bounded RRT; same 30 s/128-candidate budget; retime new transitions only | 126 attempts, 342 timing curves plus84 candidate files (426 total); all six families attempted per pair; 43 passed; planning exit 0 | NOW→COME gains 20 eligible candidates; auxiliary analysis error fixed with original failure retained |
| R5 | New R5 independent proofs, source audit and resume evidence | verify_all_pairs.py rebuilds saved curves; recompute intrinsic integral/frame locations; cross-version negatives; completed-resume hash check | 84/84 complete candidate checks, zero numerical passes; two diagnosis-only pairs; 37 passed; all 784 run files unchanged by resume; all exit 0 | Corrected protection still conflicts with quality limits; no deletion, retiming or relaxation |
| R6 | Four video/trajectory/CSV/still/proof exports in videos/; R6/run_analysis.json | Fast raster wrapper calls frozen renderer; reverify displayed curves, compare exported protection and map failures to video time | Four decodable MP4s, 305/305/402/208 frames at 30 Hz; eight bitwise-equal protected instances; 2 passed; all exit 0 | Reuse prior fast raster settings directly; no human approval claimed |
| R7 | Bilingual TASK-22 and STATE; final checklist/diff/commands/report | Full pytest, acceptance.py, baseline-hash-checked installation and installed-source verification | 799 passed in 67.50 s, exit 0; 62 staging checks passed; installed results appended below | Correction increment only; pilot and full-library counts separate |

Metrics below describe the **saved failed diagnostic curves shown in the videos**, not selected solutions. Candidate counts include all eligible candidates and independent candidate reviews. The two zero-candidate pairs additionally have full verification for their displayed diagnostic curve; input diagnosis alone is not full-curve acceptance.

| Pair | Status | Eligible / reviewed | Full acceleration rad/s² | Full jerk rad/s³ | Full squared-jerk integral rad²/s⁵ | Sampled clearance mm |
|---|---|---:|---:|---:|---:|---:|
| COME→NOW | TIMEOUT | 0 / 0 | 206.817407 | 4889.644865 | 42085845.013944 | 7.803863 |
| NOW→COME | FAILED_QUALITY | 20 / 20 | 206.817407 | 4889.644865 | 40424094.846729 | 8.085210 |
| COME→COME | FAILED_QUALITY | 64 / 64 | 97.143139 | 2196.390448 | 5154693.781190 | 8.702362 |
| NOW→NOW | TIMEOUT | 0 / 0 | 206.817407 | 4889.644865 | 79085919.079298 | 4.705174 |

All 84 eligible candidates completed independent boundary, limit, coupling, dense-geometry and protection checks. All failed. Every COME→COME candidate fails the full integral, ranging 5,149,697.094075–5,521,526.772797. Every NOW→COME candidate fails intrinsic source acceleration/jerk/integral, with full integral 40,208,751.485404–40,458,815.416845. The minimum sampled clearance across eligible candidates is 3.490302 mm (>2 mm), without continuous-collision certification. Displayed timeout diagnostics also have connector integral/peak failures; COME→NOW additionally violates analytic connector joint limits. See each independent_verification.json; none is labeled acceptable.

Recomputed cause: COME protected interior f30–129 contributes 1,479,272.694631 squared jerk integral; NOW f6–73 contributes 38,213,419.338553. Each single instance exceeds 1,000,000. These are nonnegative contributions whose three-frame stencils remain entirely inside protection; a connector cannot cancel them. Four-pair lower bounds are 39,692,692.033184, 39,692,692.033184, 2,958,545.389262 and 76,426,838.677107. This conclusion uses the frozen 30-Hz finite-difference/integral definition and unchanged source poses/timing, not a search-completeness claim. Protected joint-limit and coupling errors are zero; internal speed satisfies existing tolerances. NOW source f31/1.033333 s has right_wrist_roll_joint acceleration 206.817407>120; f37/1.233333 s has R_pinky_proximal_joint jerk 4,889.644865>3000. Largest squared-jerk power occurs at COME f56/1.866667 s and NOW f44/1.466667 s. Exact joints/frames and both video-row time mappings are in R5/protected_source_quality.json, protected_coordinate_locations.json, protected_source_lower_bound.json and R6/run_analysis.json.

| 词对 / Pair | 原词保留帧 / Retained original slices | 新增过渡 / Added transition | 视频 / Video |
|---|---|---|---|
| COME→NOW | COME#0 [27,145]; NOW#1 [1,76] | 3.933333～4.233333s (0.300000s) | [MP4](results/user_protected_correction_20261031_001/videos/COME__NOW/comparison.mp4) |
| NOW→COME | NOW#0 [3,77]; COME#1 [23,132] | 2.466667～2.966667s (0.500000s) | [MP4](results/user_protected_correction_20261031_001/videos/NOW__COME/comparison.mp4) |
| COME→COME | COME#0 [27,177]; COME#1 [23,132] | 5.000000～5.300000s (0.300000s) | [MP4](results/user_protected_correction_20261031_001/videos/COME__COME/comparison.mp4) |
| NOW→NOW | NOW#0 [3,82]; NOW#1 [2,76] | 2.633333～2.933333s (0.300000s) | [MP4](results/user_protected_correction_20261031_001/videos/NOW__NOW/comparison.mp4) |

Each folder contains comparison.mp4, trajectory.json, replay.npz, baseline.npz, trajectory_evidence.csv, independent_verification.json, contact_sheet.png and report.json. Original row is above algorithm row; front is left and side is right. The shorter row holds its end without time warping. Green=protected, blue=retained, red=cut, yellow=added, gray=hold. The execution model inspected all four contact sheets using the image tool; this is not human/group-2 review or ASL comprehension. Fast raster settings disable multisampling/shadows/reflections only; geometry, trajectories and verification are unchanged. Wrapper and frozen renderer hashes are in videos/render_configuration.json.

All engineering values match the prior development policy: 2 mm clearance, 15/10 rad/s arm/finger speed, 1e-6 position tolerance, 1e-8 limit/coupling tolerance, 120 rad/s² acceleration, 3000 rad/s³ jerk, 1,000,000 rad²/s⁵ squared jerk integral, 6 s maximum transition and unchanged search/verification budgets. The file SHA was frozen before running in R2/engineering_freeze.json. Formal quality.freeze_status and validation.approval_status remain pending, so formal approval reasons such as QUALITY_THRESHOLDS_NOT_FROZEN remain in evidence. A development hash freeze does not fabricate human review.

The prior round already fixed test date dependence by injecting a test clock; that implementation is retained while production uses real UTC. Fifteen added correction tests cover new bounds, historical version retention, distinct policy identity, old-bundle rejection even after replacing its file hash, two real 106-frame self instances, deletion, forged review, wrong protection reference and retiming. Targeted sets overlap and must not be added together. The full suite actually passed 799 tests.

Actual execution cwd was `/tmp/me5412_corrected_intervals_20261031_001/repository`. The command recorder set `PYTHONDONTWRITEBYTECODE=1`, `MUJOCO_GL=egl`, and OMP/OPENBLAS/MKL/NUMEXPR threads to 1 for tests and formal runs. Use those variables, a fresh results directory and a new run_id with these templates. Existing full-suite tests use temporary 127.0.0.1 services. CLI exit 0 means computation completed; read verification JSON for numerical acceptance.

```bash
.venv/bin/python scripts/screen_user_protected_cuts.py --policy config/transition_policy_user_protected_v2.json --output results/REPRO_NEW_DIR/cuts.json --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW
.venv/bin/python scripts/plan_all_pairs.py --library hospital_v1 --include-self --policy config/transition_policy_user_protected_v2.json --run-id REPRO_NEW_ID --results-root results/REPRO_NEW_DIR/runs --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW
.venv/bin/python scripts/verify_all_pairs.py --run-id REPRO_NEW_ID --results-root results/REPRO_NEW_DIR/runs
.venv/bin/python results/user_protected_correction_20261031_001/R6/fast_render.py --run-dir results/REPRO_NEW_DIR/runs/REPRO_NEW_ID --output results/REPRO_NEW_DIR/videos --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW
.venv/bin/python -m pytest -q -p no:cacheprovider tests
```

Actual commands, cwd, environment, durations, exit codes and logs are in FINAL/commands.json and per-task *.command.json/.log. Planning took 123.559 s, independent candidate verification 593.832 s, rendering 90.227 s. R4/analyze_plan_failed_v1.py tried sorted JSON with a mixed None/string method-count key from endpoint screening and failed with TypeError: '<' not supported between instances of 'str' and 'NoneType', exit 1. Replacing the empty method label with endpoint_screen made analysis_fixed exit 0. The failed script/log remain; no trajectory or threshold changed. A read-only live-progress query also encountered KeyError before method_coverage existed during planning; using get resolved it without affecting the run.

Minimal read-only failure reproduction follows. Expected intrinsic values are COME 1479272.6946308068 and NOW 38213419.33855339 against 1000000. It creates no outputs.

```bash
cd /home/kingderman/Documents/ME5412-github-latest
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
import hashlib, json, numpy as np
from pathlib import Path
p = json.loads(Path('config/transition_policy_user_protected_v2.json').read_text())
b = json.loads(Path(p['endpoints']['protection_file']).read_text())
for r in b['records']:
    path = Path(r['motion'])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == r['motion_sha256']
    with np.load(path, allow_pickle=False) as clip:
        t, x = clip['timestamps_s'], clip['positions']
        for _ in range(3):
            x = np.gradient(x, t, axis=0, edge_order=2)
        a, z = r['protected_core_frames']
        interior = slice(a+3, z-2)
        print(r['gloss'], float(np.trapezoid(np.sum(x[interior]**2, axis=1), x=t[interior])),
              p['quality']['limits']['jerk_integral_rad2_s5'])
PY
```

Recommended next step: engineering review of the full-action quality metric versus immutable protection. Any justified input/metric disposition must use a new frozen version and regression run; do not raise limits just to pass. The user need not supply technical parameters. Retaining both original poses/timing and these caps blocks the four-pair numerical objective. The full universe remains 1,225 (1,190 nonself/35 self): only four executed, 2 FAILED_QUALITY, 2 TIMEOUT, 1,221 NOT_RUN and 0 PASS_SIM. Full-library L2, three/multiword compatibility, human cross-review, fresh-environment reproduction and hardware remain unfinished.

Preservation archive: `/home/kingderman/Documents/ME5412/execution_evidence/corrected_intervals_20261031_001/baseline.tar` (894,515,200 bytes), SHA-256 `c7386f1b813e51fbd1df0a787f2d5f3182496095876ee41172601bfd9a098e03`; all 8,726 restored entries match. Bindings remain the 201-frame Studio Galt COME and 104-frame WLASL NOW; complete hashes are in HANDOFF and the new bundle, rechecked this round. The 89-frame alternative COME was not substituted. Earlier displayed-video byte identity remains unavailable and is not invented. Original motions/models, old configurations/contract, TASK-01–21, PLAN.md and historical results remain unchanged. No commit/push/publication; execution remained single agent under the explicit task constraint.

Text diff: FINAL/implementation.patch. Absolute file paths and before/after SHAs: FINAL/changed_files.json and install_manifest.json. Before rollback, preserve this round’s evidence; restore only pre-existing changed files from this round’s archive, and move new configuration/test/report files into a separate preservation folder. Do not reset/clean or overwrite the full tree. Final checks separate engineering completeness from goal_complete=false. Actual installed-source verification is appended below after execution, without calling preparation completion.

Installed-source verification actually completed: all 956 initial delivery files match installation hashes. Final checks in `/home/kingderman/Documents/ME5412-github-latest` exited 0 with 62 engineering checks passing. All 465 original motion/model files and baseline historical results remain unchanged. All eight exported protected instances have bitwise-equal poses and preserved relative timing. See results/user_protected_correction_20261031_001/FINAL/final_acceptance_checklist.json and R7/installed_acceptance.command.json/.log. Numerical result remains 0/4 and goal_complete=false; formal acceptance stays disabled.
