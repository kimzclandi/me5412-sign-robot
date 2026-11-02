# Next execution handoff: COME/NOW multiword pilot

[中文](HANDOFF.md) · [Current state](STATE.en.md) · [Current v5 report](TASK-25.en.md)

========== HANDOFF BEGIN ==========

Updated: 2026-10-31 (Asia/Shanghai). **These are instructions for the next phase; none of the tasks below has been executed.** This refresh changes only the four Chinese/English STATE and HANDOFF files.

## Project and objective

Project: ME5412 Group 3, transitions between arbitrary vocabulary pairs. The final goal is a suitable transition for any two vocabulary words while preserving their meaningful motion. This phase first tests multiword composition using the existing COME/NOW work.

Objective: reuse the v5 candidate mechanism to generate traceable three- and five-word sequences. Each middle word appears once; every occurrence preserves protected poses, order and relative timing. Independently verify the whole sequence from saved files and export diagnostic replays. **Do not run the remaining 1,221 pairs, enable formal acceptance or operate hardware in this phase.**

## Current state

- Completed: numerical 4/4 ordered pairs; complete independent validation of 45/45 saved candidates; fresh checks of the four selected trajectories; four diagnostic videos and pose/timing comparisons of eight protected occurrences.
- Incomplete: v5 sequence contract, assembly, independent verification and videos; the remaining 1,221 pairs; full-library L2, human semantic viewing, cross-group engineering review, fresh-environment reproduction and hardware.
- Known issues: the summary still labels numerically passing but formally unapproved results `FAILED_QUALITY`; `acceptance_pending()` retains legacy manual-window-review wording. Report numerical and formal status separately; do not turn that wording into a user-approval requirement for cuts. Protected-source smoothness issues remain unchanged.
- Branch: `codex/group3-all-pairs-v1`; HEAD: `2875e499d79b7264b3fe0414318b30ca8aab1f4d`. Modified/untracked files are part of the baseline.
- **Execution directory: `/home/kingderman/Documents/ME5412-github-latest`**. Neither `/home/kingderman/Documents/ME5412` nor its `execution_evidence/thread_acceptance_20261031/repository` is the implementation baseline. The latter is a superseded v2 checkout and must not be installed.
- Code hash: `5d0332c2ac5a87e49288302f1517cad90f897ce2bfd46b999e922c4a9dd864bc`; policy `config/transition_policy_user_protected_v5.json`; current run `lift_off_arrival_pilot_20261031_002` under `results/user_protected_lift_off_arrival_20261031_001/runs/`.
- Test scope: TASK-25 reports 812 passed. The progress review actually rechecked the four selected trajectories and protected media occurrences, not the full suite. The old v2 checkout's 831 passed does not apply.

## Invariants and frozen cases

1. Protection input is `config/user_protected_come_now_v2.json`: COME **0.93–4.40 s / [27,132]**, source `motions/studio_galt_v1/COME.npz`; NOW **0.13–2.53 s / [3,76]**, source `motions/wlasl_video_v1/NOW.npz`. Frames are zero-based, inclusive, 30 Hz, `time_scale=1`; source hashes are in STATE. Do not substitute another COME version.
2. The algorithm owns trimming outside cores, endpoints, transitions and engineering metrics. The user provides indispensable semantic portions. Human viewing, when needed, addresses meaning and misleading added motion, not approval of algorithmic windows.
3. Current selected candidates: COME→NOW `attempt_00016`; NOW→NOW `attempt_00015`; NOW→COME `attempt_00023`; COME→COME `attempt_00003`. Resolve actual candidate paths through the run manifest/checkpoints; do not guess filenames.
4. Freeze eight triples: COME–COME–COME, COME–COME–NOW, COME–NOW–COME, COME–NOW–NOW, NOW–COME–COME, NOW–COME–NOW, NOW–NOW–COME, NOW–NOW–NOW. Stress cases: COME×5, NOW×5, COME–NOW–COME–NOW–COME, NOW–COME–NOW–COME–NOW. These are 12 engineering cases, not asserted ASL sentences or an independent semantic test set.
5. The pilot starts at the first retained source slice and ends at the last. Do not implicitly add neutral start/end motion. Any future neutral-motion requirement needs a separate task and acceptance scope.
6. Keep `formal_acceptance_enabled=false`; use new run IDs and output directories. Preserve old inputs, policies, models, original motions, failure evidence and historical results. After code changes, do not write results to an old run or reuse its identity.

## Execution order and atomic tasks

### P0-1 — Freeze the v5 baseline and pilot cases

| Field | Instruction |
|---|---|
| ID / Priority / Name | P0-1 / P0 / Freeze the v5 baseline and pilot cases |
| Purpose | Prevent stale-checkout replacement and establish a reviewable regression baseline. |
| Prerequisites | Read AGENTS.md, STATE.en.md and TASK-25.en.md; confirm the actual execution directory. |
| Operations | Record branch, HEAD and full git status; back up files to be changed with hashes; check run 002's 70 code files, 144 inputs and 607 manifest entries; read selected candidates and protection inputs; freeze the 12 cases, candidate ordering/selection rules, seed and bounded resource budgets. |
| Files/modules | Existing STATE/HANDOFF; run 002 library_manifest.json/manifest.json/checkpoints; v5 policy and protection bundle; planned baseline/case/budget manifests for this phase. |
| Inputs / Outputs | Input: current target and evidence. Output: a new evidence directory, baseline hashes, cases/budgets and differences. |
| Done when | Baseline identity matches, or differences are explained and refrozen; all 12 cases are unique, all four pair sources traceable, and historical files unchanged. |
| Verification | Compare file SHA-256 values; check that the eight triples equal the length-three Cartesian product of the two words; save commands and exit codes. |
| Risk / Rollback | Concurrent changes or the wrong checkout. Preserve the scene, reread changes, discard only unused new manifests and repeat. |
| Parallel | No; all later tasks depend on this one. |

### P0-2 — Define the sequence contract, metric scope and failure states

| Field | Instruction |
|---|---|
| ID / Priority / Name | P0-2 / P0 / Define the sequence contract, metric scope and failure states |
| Purpose | Separate pair passing from whole-sequence passing and give assembly/verification an explicit shared protocol. |
| Prerequisites | P0-1. |
| Operations | Create a new sequence schema/policy without weakening pair v2. Support at least two words and explicitly reject empty/single-word input. Give each occurrence a unique ID. Each connector records source run/candidate/file hash, endpoint occurrences/cuts, finger phase and local timing. Record candidate-source and current sequence-implementation identities separately. Sequence identity must cover the actual new CLI/verifier/render entry points, source, tests, contracts, policies and reference manifests. Existing freeze_library collects selected directories and a fixed script list; do not assume new scripts are automatically hashed. Test explicit coverage and identity changes after mutations. Define time shifts, the 30 Hz grid, identity matching and rejection of missing/duplicate/corrupt inputs. Freeze scoring masks, finite-difference edge handling, integral ownership and budget-exhaustion status. |
| Files/modules | Reference pair_contract.py and pair_verification_v2.py; planned versioned sequence contract/policy and schema tests, with paths registered before implementation. |
| Inputs / Outputs | Input: v5 policy, candidate structure and protection definition. Output: versioned schema/development policy, interface notes and negative contract tests. |
| Done when | All 12 cases are representable, repeated words distinguishable, and pair labels cannot be inherited as sequence passes. Metrics are frozen before observing sequence results. |
| Verification | Reject wrong hashes, duplicate occurrence IDs, missing cores, reversed timing, mismatched source versions and invalid segment types. Pair v2 must still reject three words. |
| Risk / Rollback | Length-dependent integral misclassification or averaging away local peaks. Preserve v5; withdraw only unused new contracts. Post-result policy changes require a new version/run. |
| Parallel | No; P1-1/P1-2 depend on the frozen interface. |

**Required metric decision:** preserve v5's outside-protected-core scoring for every occurrence. The suggested region for each transition is the retained edge after the preceding core, the connector, and the retained edge before the following core. Compute metrics from the reconstructed whole chain; boundary ownership must neither duplicate nor omit scored intervals. Keep existing per-transition peaks, the connector duration cap of 6 s (not a whole-sequence or scoring-region duration cap), and the `1,000,000 rad²/s⁵` integral cap; check each analytic connector separately and report the whole-sequence squared-jerk total separately. P0-2 must express this as a new sequence development policy, not pretend that v5 already defines it. If choosing another global policy, record the engineering basis before running; do not relax limits after seeing failures. Report protected-source internal issues. Whole-chain speed, limits, coupling, boundaries and sampled geometry remain mandatory.

### P1-1 — Assemble a sequence with each word occurring once

| Field | Instruction |
|---|---|
| ID / Priority / Name | P1-1 / P1 / Assemble a sequence with each word occurring once |
| Purpose | Reuse verified connectors without duplicating middle words by concatenating complete pair clips. |
| Prerequisites | P0-2. |
| Operations | Use run 002's four selected candidates as development fixtures; actual pilot evidence uses candidates reverified in P1-3's new run. Extract only connectors. Use the first edge's source slice for the first word and the last edge's target slice for the last. Each middle word is one original slice from incoming.entry to outgoing.exit. Require entry≤core_start≤core_end≤exit, entry<exit, matching source/protection/joint order/identity, and the sample after entry and before exit within the slice. Renumber occurrences and shift segment times without changing coefficients, durations or source timing. Internal connector subsegment boundaries may be off-grid; complete connectors and source frames must fit the replay grid. On failure, preserve reasons and use the frozen rule to search compatible combinations within that run's verified candidate pool under bounds (run 002 has 45; do not assume the new run has the same count). |
| Files/modules | Existing pair_routes.py:assemble_pair_trajectory_v2, pair_timing.py:boundary_state_v2 and pair_fingers.py; planned sequence assembly, persistence and CLI. Do not pass three words to save_pair_trajectory. |
| Inputs / Outputs | Input: frozen candidates and the new contract. Output: sequence artifacts, per-edge provenance, per-occurrence source mappings and failure logs. |
| Done when | Exactly one source slice per occurrence and one connector group between adjacent words; each occurrence's core appears once; time is contiguous; two-word cases replay equivalently to their original candidates. |
| Verification | Test different middle-NOW ranges, repeated/self words, finger strategies, time shifts, replay equivalence and missing derivative samples. Check that coefficients/source frames/durations are not silently changed. |
| Risk / Rollback | Incompatible endpoints, duplicate boundary samples or incorrect time normalization. Revert only new modules/call sites; retain failed artifacts and original curves. |
| Parallel | Yes, with P1-2 after P0-2; use exclusive file ownership and serialize shared-contract changes. |

Boundary derivatives retain `linear_replay_one_sided_v2`: departure uses the preceding source interval's slope; arrival uses the following interval's slope; the linear source segment's boundary acceleration is zero. Do not claim globally C2 protected motion or certified continuous source derivatives.

Example: selected candidates for COME→NOW→COME imply one middle NOW slice **[2,77]**, with core **[3,76]** appearing once. This is an assembly requirement, not a verified sequence result.

### P1-2 — Independently verify the whole sequence from saved files

| Field | Instruction |
|---|---|
| ID / Priority / Name | P1-2 / P1 / Independently verify the whole sequence from saved files |
| Purpose | Detect middle-occurrence and whole-chain issues beyond pair verification. |
| Prerequisites | P0-2; develop using frozen small fixtures, then integrate after P1-1. |
| Operations | Reload artifacts and source files. Find source_slice by occurrence, not by zipping the first/last segments. Compare every protected occurrence's poses and relative timing. Recompute both connector boundaries' position/one-sided velocity/acceleration, finger phase and analytic extrema. Reconstruct the chain and check all scoring regions, whole-chain speed/limits/coupling and bounded dense geometry sampling. Report numerical_checks_passed, validation_complete, formal status, per-word/per-edge failures and source issues separately. |
| Files/modules | Reference pair_verification_v2.py:_full_replay/_protected_replay_mask/verify_saved_pair_v2; planned sequence verifier/CLI/tests. Carefully reuse private helpers if appropriate; the existing top-level pair verifier is not a sequence verifier. |
| Inputs / Outputs | Input: saved sequence, new policy and original motions/model. Output: artifact-hash-bound independent evidence, whole-chain metrics and per-occurrence protection reports. |
| Done when | Middle occurrences are verified; missing data, identity mismatches and exhausted budgets cannot pass. Tampered middle cores/timing/connectors are rejected. Pair regression behavior is preserved. |
| Verification | Inject missing/changed/retimed middle-core frames, duplicate/swapped occurrences, omitted connectors, changed coefficients/phases, stale hashes and exhausted budgets. Recompute metrics independently of planner-reported values. |
| Risk / Rollback | Shared assembler/verifier assumptions or treating sampled clearance as continuous proof. Construct independent test expectations, preserve the pair path and revert new call sites if needed. |
| Parallel | Yes, with P1-1 after P0-2. A different executor reviews verification logic/tests; integrate serially. |

### P1-3 — Run frozen cases and export auditable replays

| Field | Instruction |
|---|---|
| ID / Priority / Name | P1-3 / P1 / Run frozen cases and export auditable replays |
| Purpose | Verify the pilot using actual saved files, whole-chain geometry and protection evidence. |
| Prerequisites | P1-1/P1-2 tests pass. |
| Operations | Freeze final source/test/index identity, then rerun and independently verify the four v5 pairs under a new run ID. Record actual candidates/selections, freeze this candidate manifest, and assemble all eight triples and four five-word stress cases. Save all attempts/failures and independently verify each. Mark exhausted budgets incomplete; fixes require new versions/runs rather than replacing hard cases. Export passing cases as two-view videos labeled by occurrence/protection/cuts/new motion; failed previews must be prominently marked diagnostic failures. Compare all protected occurrences in every video replay. Any later code change makes the run's identity stale: preserve evidence and create a new run. |
| Files/modules | New sequence CLI/verifier/render outputs; reference scripts/render_user_protected_pairs.py (pair-only); existing tests/test_*_v2.py and tests/test_*_v5.py, plus planned sequence tests. |
| Inputs / Outputs | Input: 12 frozen cases and budgets. Output: new runs, per-case JSON/logs/trajectories/videos/protection comparisons, four-pair regression and test logs. |
| Done when | Successful delivery requires numerical passing and complete verification for 8/8 triples and 4/4 stress cases, preservation of all 44 occurrences, passing four-pair regression, focused tests and the full suite. Otherwise retain exact denominators and report incomplete. |
| Verification | Save real CLI arguments/environment/exit codes. Recount the 12 cases, 44 occurrences and 32 connector groups from outputs. Require bitwise-equal protected poses and relative timing error≤1e-12 s. Record sampling coverage/budget. Run focused tests, then the full suite. |
| Risk / Rollback | Long-sequence budget exhaustion, render/trajectory identity mismatch or mistaking visuals for semantic proof. Freeze resource limits and record exhaustion; isolate failed runs without overwriting history. |
| Parallel | No until integration/contract tests pass; later verification/media audits may run in parallel only if they do not write the same run. |

### P1-4 — Review delivery and update state

| Field | Instruction |
|---|---|
| ID / Priority / Name | P1-4 / P1 / Review delivery and update state |
| Purpose | Leave factual, reproducible results for the next executor. |
| Prerequisites | P1-3 has ended, including failed/incomplete outcomes. |
| Operations | Review code differences, saved validations and logs; verify original assets/history hashes; report actual commands, limitations, task states and deviations. Update bilingual STATE/HANDOFF, add a bilingual report using the next unused TASK number and update the index. List source/protection input gaps for the remaining 33 words without expanding runs in this phase. |
| Files/modules | STATE.md/.en.md, HANDOFF.md/.en.md, planned TASK reports, docs/README.md/.en.md; separately record any necessary project_overview.py documentation-index hash maintenance and its effect on code identity. |
| Inputs / Outputs | Input: diffs, run evidence and test/media reports. Output: acceptance matrix, reproducible delivery and next-phase gaps. |
| Done when | Facts and plans are separate; no invented semantic/formal/hardware acceptance; both languages agree, links resolve, and incomplete work has a minimal reproduction. |
| Verification | Audit final file scope/hashes, documentation links and JSON-derived counts. If index maintenance touches code, freeze final code first and rerun/render under a new run ID; never replace an old run's identity. |
| Risk / Rollback | Index maintenance changes code identity, or failures are reported as completion. Restore only backed-up documentation changes while preserving results/audit evidence. |
| Parallel | No; final integration is serial. An independent reviewer can perform a read-only audit. |

## Key files and existing interfaces

- `src/sign_robot/pair_contract.py`: `load_policy`, `freeze_library`, `run_identity`; `validate_trajectory_v2`, `save_pair_trajectory` and `read_pair_trajectory` strictly handle pairs.
- `src/sign_robot/pair_routes.py`: `assemble_pair_trajectory_v2`; `src/sign_robot/pair_timing.py`: `boundary_state_v2` (one-sided linear-replay derivatives).
- `src/sign_robot/pair_fingers.py`: v5 `finger_arrival_plan_v1` / `apply_finger_arrival_v1`.
- `src/sign_robot/pair_verification_v2.py`: `verify_saved_pair_v2` verifies pairs only; protection masks and boundaries assume first/last words.
- `src/sign_robot/transitions.py:plan_sentence` and `scripts/plan_transitions.py` belong to the legacy multiword pipeline, not completed v5 sequence support.
- **Planned interfaces, not currently present:** sequence schema, assembly/persistence, independent verification, CLI, rendering and sequence tests. Register actual paths/interfaces before implementation. Do not invent existing APIs or merely remove the pair-length check.

## Key commands

These existing entry points have been inspected. Run inspection/tests in the correct target. Sequence CLIs do not exist yet; verify their eventual commands with `--help` and include them in delivery reports.

```bash
cd /home/kingderman/Documents/ME5412-github-latest
git status --short
git branch --show-current
git rev-parse HEAD
sha256sum config/transition_policy_user_protected_v5.json config/user_protected_come_now_v2.json motions/studio_galt_v1/COME.npz motions/wlasl_video_v1/NOW.npz
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/plan_all_pairs.py --help
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/verify_all_pairs.py --help
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pair_contract_v2.py tests/test_user_protected_routes.py tests/test_user_protected_verification.py tests/test_lift_off_arrival_v5.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests
```

The focused command covers only existing pair tests; add the actual new sequence tests. Source and tests enter the code hash. Do not rewrite an old candidate.identity or treat run 002 as a current verification after code changes. Use TASK-25's planning/verification/rendering arguments for four-pair regression, **with a new unique run ID and output directory**. Do not perform write-producing reruns on run 002.

## Execution rules, risks and rollback

- Verify each task before starting its dependents. Report concrete structural differences from the plan and continue unaffected work.
- Use real `gpt-6.1-sol` subagents at `max` effort for scoped implementation/independent review; the root coordinates and performs final review. Avoid recursive delegation and concurrent edits to the same files.
- Keep scope narrow; do not refactor unrelated modules, reset/clean/push, delete historical evidence or change original assets. Preserve user changes; use the tool's normal permission process if the target needs write authorization.
- High risks: duplicated/missing middle occurrences, first/last-only masks, connector timing/normalization mistakes, changed integral scope, stale identities and long-chain budget exhaustion. Negative tests and independent saved-file checks must cover them.
- Human confirmation: semantic preservation and misleading added motion can be reviewed separately; record cross-group engineering review independently. Neither blocks the local formal-off pilot, and neither may be fabricated.
- Irreversible operations: none required. Hardware, publication and overwriting historical results are outside this handoff.
- Rollback only this phase's actual changes/additions. Before restoring a file, verify it still matches the recorded post-install hash and has not been changed by others. Restore backups while retaining failure/command evidence. Do not use whole-repository Git rollback that loses untracked work.
- On a blocker, preserve the new run, input, error, last successful step and minimal reproduction command. TIMEOUT/budget exhaustion is not proof of infeasibility.

## Minimum path and later complete path

Minimum path: P0-1 → P0-2 → P1-1/P1-2 → P1-3's eight-triple checks/replays → P1-4, explicitly marking stress testing unfinished. Complete delivery for this phase adds the four five-word stress cases and all regression checks. Later collect protection inputs for the other 33 words, expand pair coverage and perform semantic/engineering review and fresh-environment reproduction. Full-library and hardware acceptance remain separate; 12 pilot cases cannot establish either.

## Required completion report

1. Changed files, baseline/final identities, preservation of original assets and historical results;
2. Completed/failed/incomplete status of P0-1 through P1-4;
3. Actual commands, environment, elapsed time, budgets and exit codes;
4. Separate counts for eight triples, four stress cases, four-pair regression and tests, plus per-occurrence protection/video evidence;
5. Deviations, policy/contract changes and their reasons;
6. Incomplete work, failure reproduction, residual risks and next requirements.

========== HANDOFF END ==========
