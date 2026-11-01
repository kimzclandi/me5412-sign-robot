# TASK-20 — R6

[中文](TASK-20.md)

Status: four-pair execution and failure-diagnostic delivery complete; **numerical acceptance failed (0/4)**. No qualifying connector was obtained. Formal acceptance stays false. Source motions, protected intervals and limits remain unchanged.

Run user_protected_pilot_20261031_001: 117 attempts, 64 eligible candidates, all COME→COME. All 64 independent complete-curve reviews failed the squared-jerk integral cap. The other three pairs have planning TIMEOUT, no eligible candidates and saved input diagnoses. Every pair actually attempted direct, neutral, ik_via1, ik_via2, retract_approach and rrt_connect. Bounded failure is not a geometric infeasibility proof.

Each video separately selects a saved failed curve and completes a fresh full-motion saved-file verification: validation_complete=true and numerical_checks_passed=false for all four. These diagnostic curves are not eligible solutions. Their full metrics follow, separate from planner status.

| Pair | Planning status | Eligible candidates | Full peak acceleration rad/s² | Full peak jerk rad/s³ | Full squared-jerk integral rad²/s⁵ | Sampled min gap mm |
|---|---|---:|---:|---:|---:|---:|
| COME→NOW | TIMEOUT | 0 | 206.817407 | 4889.644865 | 42109091.946263 | 4.730808 |
| NOW→COME | TIMEOUT | 0 | 206.817407 | 4889.644865 | 40474415.433381 | 4.730808 |
| COME→COME | FAILED_QUALITY | 64 | 97.143139 | 2196.390448 | 5634160.454384 | 8.702362 |
| NOW→NOW | TIMEOUT | 0 | 206.817407 | 4889.644865 | 76503824.684449 | 4.730808 |

Intrinsic protected-source cause: without any connector, COME frames 30–138 contribute squared jerk 1,850,853.261494 and NOW frames 6–99 contribute 38,239,278.289876, exceeding the frozen 1,000,000 cap. NOW frame 31 (1.033333 s), right wrist roll, acceleration 206.817407 >120; frame 37 (1.233333 s), right proximal pinky, jerk 4,889.644865 >3000. Original difference stencils remain at least three frames inside protection, so external cuts/connectors cannot remove this nonnegative contribution. Reproduce with R6/audit_protected_sources.py. Exit 0 means computation completed; exceeds_frozen_limit=true is failure. Per-instance comparison-video times are in R6/run_analysis.json failure_video_locations.

Videos: results/user_protected_auto_20261031_001/videos_complete/{COME__NOW,NOW__COME,COME__COME,NOW__NOW}/comparison.mp4. Each folder includes trajectory.json, replay.npz, baseline.npz, trajectory_evidence.csv, independent verification, contact_sheet.png and report.json. Original pair above, algorithm below; front left/side right. Common real time, shorter row holds its end. Green protection, blue retained, red cut, yellow added. Persistent FAILED DIAGNOSTIC/not-selected, algorithm-window and kinematic-replay labels.

Command exits: plan_four 0; verify_four 0; resume_four 0; renderer_probe 0; render_four 143 (SIGTERM, cause unknown; first complete video, partial second video and logs preserved); render_four_fast 0. Fast raster export disables shadows/reflections and antialiasing only. Trajectory code, model geometry, collision rules and run identity remain unchanged. R6/fast_render.py and videos_complete/render_configuration.json record provenance; a new output directory preserves earlier output. Exact argv, cwd, timing and logs are in *.command.json and FINAL/commands.json.

Validation: .venv/bin/python -m pytest -q -p no:cacheprovider tests exited 0: 784 passed in 61.04s. Existing HTTP tests use temporary loopback ports. This is the restored workspace, not a newly installed environment. All 790 run-file hashes remain identical after completed resume. Four-pair denominator 4; full library remains 1,225 (1,190 non-self/35 self), 1,221 NOT_RUN, zero PASS_SIM, L2 incomplete. Pending formal quality/collision approval is separate from development values frozen by policy hash.

Changes: real comparison exporter and label tests; automatic-mode code freeze includes both new CLIs. Pre-registered report links and updated only two download SHA literals in project_overview.py, preserving earlier changes. Deviations: tangent screening correction is documented in TASK-18; interrupted rendering led to a separate fast raster output; failed acceptance is retained for review without relaxing limits.

