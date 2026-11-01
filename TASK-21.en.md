# TASK-21 — R7

[中文](TASK-21.md)

Outcome: **engineering implementation and failure evidence delivered; motion goal incomplete, 0/4 numerical passes.** Formal acceptance remains disabled. TASK-15–TASK-20 record R1–R6 files, decisions, commands, verification and deviations. STATE and every new report have matching Chinese/English versions.

| Pair | Planning status | Eligible candidates | Full peak acceleration rad/s² | Full peak jerk rad/s³ | Full squared-jerk integral rad²/s⁵ | Sampled min gap mm |
|---|---|---:|---:|---:|---:|---:|
| COME→NOW | TIMEOUT | 0 | 206.817407 | 4889.644865 | 42109091.946263 | 4.730808 |
| NOW→COME | TIMEOUT | 0 | 206.817407 | 4889.644865 | 40474415.433381 | 4.730808 |
| COME→COME | FAILED_QUALITY | 64 | 97.143139 | 2196.390448 | 5634160.454384 | 8.702362 |
| NOW→NOW | TIMEOUT | 0 | 206.817407 | 4889.644865 | 76503824.684449 | 4.730808 |

Metrics come from independent saved-file verification of the complete displayed diagnostic curves. COME→COME also has 64 eligible planned candidates, all independently reviewed and failed. Other pairs have no eligible candidate and planning timeouts; their videos are diagnostic saved curves. All six route families were actually attempted for every pair. Final checks separately inspect exported protected poses/timing and two self-pair instances.

Blocking cause is intrinsic protected quality: COME frames 30–138 contribute squared jerk 1,850,853.261494 and NOW frames 6–99 contribute 38,239,278.289876, above 1,000,000. NOW also violates acceleration at frame 31/1.033333 s and jerk at frame 37/1.233333 s. The nonnegative contributions lie entirely within protection; changing external cuts or connectors cannot remove them. No limits or original words were retuned. Full frame/joint/time/video attribution is in results/user_protected_auto_20261031_001/R6/protected_source_quality.json and run_analysis.json.

Changed pair_contract.py (explicit new mode/freeze), pair_windows.py (user protection/algorithm provenance/clock), pair_routes.py (screening/shortlist/routes), pair_search.py (cropped timing/shortlist), pair_verification_v2.py (fresh complete-curve/protection/timing/localization), pair_runner_v2.py (applicable independent evidence/smoothness ranking/pilot counts). Added two configs, one contract, two CLIs, fixed-clock fixture and five focused test files. HANDOFF/STATE/seven TASK reports are bilingual; documentation indexes and only two project_overview.py download hashes were synchronized, preserving prior edits. Absolute paths and before/after SHA values are in FINAL/install_manifest.json; text diff FINAL/implementation.patch; per-task before/changes are retained. New evidence lives in results/user_protected_auto_20261031_001 without overwriting history.

Actual full test command in the restored /tmp/me5412_auto_cuts_20261031_001/repository workspace:

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider tests
```

Exit 0: 784 passed in 61.04s, including existing temporary loopback HTTP/service tests. Test clock injection removes date dependence while production retains real UTC checks. Negative tests cover removed protection, mismatched versions, lost repeats, forged approval, retiming and tampering; legacy review remains compatible. FINAL/commands.json records commands/exits. Focused final suites have 129/40/104/75 passes with overlap; do not add them. Unchanged baseline actually had 749 passes; the initial socket-restricted failure is preserved.

Reproduce planning/verification from the target using a fresh run ID:

```bash
.venv/bin/python scripts/plan_all_pairs.py --library hospital_v1 --include-self --policy config/transition_policy_user_protected_v1.json --run-id REPRO_NEW_ID --results-root results/user_protected_repro --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW
.venv/bin/python scripts/verify_all_pairs.py --run-id REPRO_NEW_ID --results-root results/user_protected_repro
mkdir -p results/user_protected_repro_diag_001/R6
cp results/user_protected_auto_20261031_001/R6/audit_protected_sources.py results/user_protected_repro_diag_001/R6/
.venv/bin/python results/user_protected_repro_diag_001/R6/audit_protected_sources.py
```

The intrinsic audit formula and original input paths are in R6/audit_protected_sources.py and its saved command/log. Its output is immutable; direct repetition refuses an existing JSON. The commands copy it to a fresh directory at the same depth, preserving ROOT. If that reproduction ID exists, use a new one. Its original-NPZ gradient/integral formula may also be executed read-only. CLI exit 0 means calculation completed, not numerical acceptance. Original SyntaxError, mistaken test-success assumption, np.bool serialization and SIGTERM(143) logs remain with their corrections documented in the atomic reports.

Four comparison.mp4 files are under results/user_protected_auto_20261031_001/videos_complete/<pair>/. Each compares original/algorithm front/side views and marks protection/retained/cut/added/hold phases with persistent FAILED DIAGNOSTIC/not-selected labels. Companion curve JSON, replay/original NPZ, metrics CSV, independent complete verification, contact sheet and hashes are retained. Interrupted shadow rendering remains in videos/. The separate fast raster variant disables shadows/reflections/antialiasing only; geometry, trajectory and collision are unchanged, with explicit wrapper/config hashes. Neither video nor sampled geometry is ASL comprehension, continuous-collision or hardware approval.

Full-library denominator remains 1,225/1,190/35: one FAILED_QUALITY, three TIMEOUT, 1,221 NOT_RUN, zero PASS_SIM. Pilot denominator four, numerical pass zero. All 64 eligible candidates have complete independent reviews; three input diagnoses cannot be presented as curve passes. Four displayed diagnostic curves have additional complete rechecks. Resume leaves all 790 run-file hashes unchanged. A sampled gap over 2 mm does not make a limit/quality-failed complete motion pass.

FINAL/acceptance.py checks frozen values, actual code/model/environment identity, denominators, independent evidence, four decodable videos/hashes, protected exported poses/timing, two instances, baseline assets/history and bilingual reports. Engineering integrity and motion-goal success are distinct; goal_complete stays false. Installed-source verification is separately recorded in FINAL/final_acceptance_checklist.json.

Preservation: /home/kingderman/Documents/ME5412/execution_evidence/auto_cuts_20261031_001/baseline.tar, SHA 501e2e75d05bad81f93a70e24b76b121370c345f45ee4973dd33ec6ea733d22f. All 7,585 entries match the restore. Installation checks every original target hash before changing any enumerated file and refuses concurrent differences. No reset --hard/clean. Rollback first preserves new evidence, then restores listed existing files from before/archive and moves new files aside; do not replace unrelated work. The external .venv symlink remains, so this is not portable fresh-environment reproduction.

Deviations/limits: actual cwd differs from target, so a restored copy was used. COME has two sources; the actual 201-frame Studio Galt library motion is bound, since 89-frame WLASL cannot contain protection. The current handoff lacks the prior displayed-video identity; byte-level association is not invented. Full hashes/binding basis are recorded. R4 corrected R3 outward-limit tangent screening. A separate fast raster export follows interrupted rendering. Required download-hash maintenance does not expand product scope. No raw assets, historical policy, PLAN.md, old runs or formal flags were changed; no forged reviews, denominator reduction or weakened caps. One agent; no hardware, uploads or publication.

Next: planning/execution engineers must resolve protected-source quality versus the current difference/integral definitions with justified versioned decisions, then freeze and regress a new policy. If original protected poses/timing and existing caps are mandatory, these four pairs cannot pass. The user need not supply technical thresholds. Full-library L2, multiword compatibility, human evaluation and fresh-environment reproduction remain incomplete. This is a failure handback, not final goal completion.


Restored-workspace acceptance actually exited 0: 40 engineering delivery checks pass (FINAL/stage_acceptance.json); goal_complete=false and numerical pilot pass remains zero. All four contact sheets were visually inspected by the execution model using image tools for labels and front/side comparisons. This is execution-engineering inspection, not ASL or group-2 approval.

Installed-source verification actually completed: all 977 initial delivery files match installation hashes. Final checks in /home/kingderman/Documents/ME5412-github-latest exited 0, with 40 engineering checks passing. All 465 original motion/model files and baseline historical results are unchanged. All eight exported protected instances have bitwise-equal poses (maximum position error zero) and preserved relative timing. See results/user_protected_auto_20261031_001/FINAL/final_acceptance_checklist.json and R7/installed_acceptance.command.json/.log. Numerical result remains 0/4 and goal_complete=false.
