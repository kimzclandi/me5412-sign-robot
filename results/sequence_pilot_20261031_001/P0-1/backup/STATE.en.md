# Current project state

[中文](STATE.md) · [Next execution handoff](HANDOFF.en.md) · [v5 execution report](TASK-25.en.md)

Updated: 2026-10-31 (Asia/Shanghai). This file summarizes the current state. Historical runs remain unchanged; planned work is not completed work.

## 1. Current conclusion

**All four ordered COME/NOW pairs pass numerical checks under the v5 development policy; formal PASS_SIM=0 and the overall goal is incomplete.** All 45 saved candidates have complete, numerically passing saved-file independent validations. The four selected trajectories were independently checked again. Multiword composition, the remaining pairs and formal acceptance are unfinished.

| Pair | Saved candidates / numerical passes | Selected candidate | Retained source frames (zero-based, inclusive) | Transition duration | Minimum sampled clearance |
|---|---:|---|---|---:|---:|
| COME→NOW | 7 / 7 | attempt_00016 | COME [27,132]; NOW [2,76] | 0.733333 s | 7.616 mm |
| NOW→NOW | 8 / 8 | attempt_00015 | NOW [3,76]; NOW [3,76] | 1.000000 s | 4.418 mm |
| NOW→COME | 17 / 17 | attempt_00023 | NOW [3,77]; COME [27,132] | 0.800000 s | 8.085 mm |
| COME→COME | 13 / 13 | attempt_00003 | COME [27,132]; COME [27,132] | 0.733333 s | 4.711 mm |

The full denominator is **1,225 pairs (1,190 non-self + 35 self)**. Only these four were run; **1,221 are NOT_RUN**. `planning_complete=false`, `verification_complete=false` and `L2_complete=false` describe the full-library run, not incomplete verification of these 45 candidates. `formal_acceptance_enabled=false` and `playback_eligible=false`. The current summary still labels the four pairs `FAILED_QUALITY`; read `numerical_checks_passed` separately from formal gate reasons instead of reporting numerical 0/4.

## 2. Current baseline and evidence

- Target: `/home/kingderman/Documents/ME5412-github-latest`. The chat working directory `/home/kingderman/Documents/ME5412` is a different checkout.
- Branch: `codex/group3-all-pairs-v1`; HEAD: `2875e499d79b7264b3fe0414318b30ca8aab1f4d`. Many implementation files are modified or untracked, so HEAD alone cannot reproduce this state.
- Policy: [transition_policy_user_protected_v5.json](config/transition_policy_user_protected_v5.json); generator `protected_cut_search_v3`.
- Current run: `lift_off_arrival_pilot_20261031_002`; [run summary](results/user_protected_lift_off_arrival_20261031_001/runs/lift_off_arrival_pilot_20261031_002/summary.json). Run 002 matches current code, inputs and videos; run 001 remains historical.
- Code collection SHA-256: `5d0332c2ac5a87e49288302f1517cad90f897ce2bfd46b999e922c4a9dd864bc`.
- Raw policy SHA-256: `4a08faee59d0b1dec77fb5106261a7b2f75d66147278d7646eb51061d198261f`; canonical policy hash: `839cbf14ecf37baece107fde30e9cc190501f700943663c6345a5f852e22c850`. These are different hash definitions.
- The 70 code files and 144 inputs in [library_manifest.json](results/user_protected_lift_off_arrival_20261031_001/runs/lift_off_arrival_pilot_20261031_002/library_manifest.json), and 607 entries in [manifest.json](results/user_protected_lift_off_arrival_20261031_001/runs/lift_off_arrival_pilot_20261031_002/manifest.json), were checked against current files and match.

Four diagnostic videos exist: [COME→NOW](results/user_protected_lift_off_arrival_20261031_001/videos/COME__NOW/comparison.mp4), [NOW→NOW](results/user_protected_lift_off_arrival_20261031_001/videos/NOW__NOW/comparison.mp4), [NOW→COME](results/user_protected_lift_off_arrival_20261031_001/videos/NOW__COME/comparison.mp4), and [COME→COME](results/user_protected_lift_off_arrival_20261031_001/videos/COME__COME/comparison.mp4). They are numerical-pass previews with formal acceptance disabled. `videos_interrupted_partial/` is not current delivery evidence.

External progress-review evidence is stored under `/home/kingderman/Documents/ME5412/execution_evidence/thread_acceptance_20261031/`:

- [current_v5_fresh_verification.json](/home/kingderman/Documents/ME5412/execution_evidence/thread_acceptance_20261031/current_v5_fresh_verification.json): the four selected trajectories were actually reverified; numerical pass, validation completeness and protected-core preservation are true, with unchanged identity before and after review.
- [current_v5_media_review.json](/home/kingderman/Documents/ME5412/execution_evidence/thread_acceptance_20261031/current_v5_media_review.json): eight protected occurrences in video replays were compared independently; poses are bitwise identical and relative timing error is below `9e-16 s`.
- [CURRENT_PROGRESS_REVIEW.en.md](/home/kingderman/Documents/ME5412/execution_evidence/thread_acceptance_20261031/CURRENT_PROGRESS_REVIEW.en.md): review scope and limits. These absolute paths are local review evidence; explicitly transfer them for another machine rather than assuming they are included in the repository.

**Test evidence:** [TASK-25](TASK-25.en.md) records 812 passing tests. The progress review and this documentation refresh did not rerun the full 812-test suite. The old isolated v2 checkout's 831 tests and 0/4 result do not describe current v5; that checkout was not installed into the target and must not overwrite it.

## 3. User-protected inputs and responsibilities

Use the corrected [user_protected_come_now_v2.json](config/user_protected_come_now_v2.json). Earlier intervals are historical only.

| Word | User-required interval | Conservative 30 Hz core | Actual source motion | Total frames / SHA-256 |
|---|---|---|---|---|
| COME | 0.93–4.40 s | [27,132], 106 frames | [studio_galt_v1/COME.npz](motions/studio_galt_v1/COME.npz) | 201 / `75d6455408ce6584043baedbd0e049cbeabcad534eda65ef561d2c7293b477a4` |
| NOW | 0.13–2.53 s | [3,76], 74 frames | [wlasl_video_v1/NOW.npz](motions/wlasl_video_v1/NOW.npz) | 104 / `2d494c13fdf1b44bb11e97004e7b212ea5c45b7b0f8d0b972bd3589ae63e15e3` |

Preserve protected poses, order and relative timing. Repeated words are distinct occurrences, each with its full core. Engineering owns trimming outside the core, endpoint selection, timing and transitions; use `window_provenance=algorithm` and do not ask the user to approve technical windows. The user supplies semantic preservation requirements and, when needed, judges whether added motion changes meaning. The byte identity of the previously displayed original video remains unavailable. Current motion binding is verified, but complete video-to-motion provenance must not be invented.

## 4. Scope of numerical passing

v3–v5 use `finite_difference_30hz_outside_protected_cores_and_analytic_connector_v3`: acceleration, jerk and squared-jerk integral are scored outside protected cores, including new connectors and retained optional source edges, alongside analytic connector checks. Whole-motion speed, joint limits, coupling, boundaries and sampled collision remain checked. Protected cores are checked for unchanged poses and timing.

v4 ranks endpoints to avoid noisy optional source edges. v5 adds `finger_arrival_plan_v1` / `apply_finger_arrival_v1` in [pair_fingers.py](src/sign_robot/pair_fingers.py), reaching an earlier handshape before a brief lift-off into NOW to address the entry joint-limit problem. Protected source motion is unchanged.

The 4/4 result is not a pass under the old v2 whole-clip smoothness scope. Acceleration/jerk exceedances inside NOW's protected source remain reported source issues and are informational under the current policy. Only 21–29 frames are scored. Collision uses finite sampling under `native_moving_non_same_hand_v2`, not a proof of continuous clearance or all contact pairs. ASL comprehension, cross-group engineering review, reproduction in a fresh environment and hardware validation remain unfinished.

`acceptance_pending()` retains legacy wording about manual review of automatic windows. This requires later clarification of engineering status; it is not a request for the user to approve algorithmic cuts, and does not authorize invented approvals or enabling formal acceptance.

## 5. Next phase: multiword pilot (not executed)

Freeze **all eight ordered three-word sequences** over COME/NOW, verify the middle occurrence with both incoming and outgoing connections, then expand the vocabulary. Passing individual pairs does not establish that a longer sequence passes.

`pair_contract.validate_trajectory_v2` accepts only two occurrences. `pair_routes.assemble_pair_trajectory_v2` and `pair_verification_v2.verify_saved_pair_v2` assume first/last words. The legacy `transitions.plan_sentence` follows a different pipeline and is not evidence of v5 sequence support. Introduce a versioned sequence contract, assembler and independent verifier; do not concatenate whole pair videos or inherit pair validation labels.

See [HANDOFF.en.md](HANDOFF.en.md) for executable tasks: freeze the baseline and sequence metric policy; assemble each middle word once from its original source slice; verify every occurrence and boundary and recheck the whole chain; cover eight triples and repeated-word stress cases; deliver a new run, videos and bilingual reports. These tasks, the remaining 1,221 pairs and full-library L2 are unfinished. Semantic protection inputs for the other 33 words can be collected subsequently and do not block this two-word engineering pilot.

## 6. History (not the current state)

| Version | Historical result | Main change | Report |
|---|---|---|---|
| Corrected v2 | 0/4 numerical passes | Corrected cores; original whole-clip scoring failed | [TASK-22](TASK-22.en.md) |
| v3 | 1/4 numerical passes | Scoring outside protected cores | [TASK-23](TASK-23.en.md) |
| v4 | 2/4 numerical passes | Rank cuts by retained-edge jerk | [TASK-24](TASK-24.en.md) |
| Current v5 | 4/4 numerical passes, formal 0 | Finger lift-off arrival | [TASK-25](TASK-25.en.md) |

TASK-15–21 concern earlier intervals. Historical FINAL checklists prove only their associated run's checks, not acceptance of current v5 or future sequences.
