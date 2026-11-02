# Concise instructions for the execution model

[中文](HANDOFF.md) · [Full task plan (Chinese)](PLAN.md)

========== HANDOFF BEGIN ==========

## Project

ME5412 hospital-vocabulary robot motion transitions.

## Task objective

Produce acceptable transitions for all 1,225 ordered pairs in the frozen 35-word vocabulary, including 35 self-pairs. Save trajectories and evidence, verify them independently, validate the specified multiword compositions, and reproduce the results in a fresh environment. The engineering target is L2 simulation acceptance; language understanding and hardware validation are separate.

This is a concise execution specification, not a completion claim or automatic authorization for additional scope. After receiving an execution instruction, follow the tasks in order; PLAN.md defines the detailed inputs, dependencies and completion criteria.

## Current state

Local baseline snapshot dated 2026-10-31; recheck it before starting.

- **Completed:** L1 development scan, word audits, checkpoints, saving and verification. All 1,225 pairs have records, 899 candidates were saved, and all 1,225 records were verified. A previous read-only inspection matched sizes and hashes for 3,378 files in the run manifest.
- **Incomplete:** approved core/window contract, formal quality freeze, general candidates and search, multi-candidate resume, multiword composition, human review, fresh-environment reproduction and hardware validation. Existing two-word checks include self-pairs but do not establish multiword completion.
- **Known issues:** 326 BLOCKED_ENDPOINT, 386 FAILED_SEARCH, 513 FAILED_QUALITY and zero PASS_SIM; 10 problematic endpoint roles, 30 words with clearance issues and 8 with speed issues. The new entry point generates only a direct quintic, and its verifier supports only that representation.
- **Test evidence:** an existing log records 589 passed; this is historical evidence. Report the tests actually run during execution. Twelve full two-word previews passed the numerical checks performed, but are not PASS_SIM; all candidates have playback_eligible=false.
- **Branch/version:** codex/group3-all-pairs-v1; HEAD 2875e499d79b7264b3fe0414318b30ca8aab1f4d; run all_pairs_dev_20261031_v2.
- **Working directory:** /home/kingderman/Documents/ME5412-github-latest. It contains modified and untracked files; restoring HEAD alone loses the current implementation.

## Execution order

1. **[P0-1] Preserve the baseline:** read AGENTS.md and PLAN.md, check structure and write access, and preserve modified/untracked contents and hashes.
2. **[P0-2] Produce per-word issue cards:** include endpoints, source-motion defects, frames, motion hashes, affected pairs and Group 2 decisions.
3. **[P0-3] Audit collision rules:** document filtering, same-hand exclusions, static pairs, sampling scope and stopping conditions.
4. **[P0-4] Define quality metrics:** specify algorithms, units, threshold rationale and pending decisions; keep unapproved policy pending.
5. **[P0-5] Implement the v2 contract:** define piecewise trajectories, boundaries, cores, windows, finger policies, budgets and version dispatch; retain v1.
6. **[P1-1] Implement window selection:** validate motion hashes, approvals, frame ranges and protected cores; reject invalid inputs explicitly.
7. **[P1-2] Implement independent verification:** reconstruct the actual saved curve and check between-frame geometry, word slices, boundaries and quality.
8. **[P1-3] Implement time parameterization:** support nonzero boundary derivatives; resolve and recheck after changing timing.
9. **[P1-4] Implement finger policies:** cover synchronous/early/late timing and finger-only changes while preserving endpoints and couplings.
10. **[P1-5] Integrate deterministic candidates:** unify direct, neutral, IK and retract/approach outputs and failure evidence.
11. **[P1-6] Integrate bounded RRT:** support every valid pair, impose finite work/time budgets, and recheck after postprocessing.
12. **[P1-7] Integrate multi-candidate runs:** retain every attempt, selection rationale, hashes, checkpoints and resume identity.
13. **[P1-8] Freeze inputs and enable formal acceptance:** import real approvals and repaired motions, audit again, and allow PASS_SIM only after complete independent verification.
14. **[P1-9] Run all-pairs acceptance:** use a new run_id for 1,225 pairs; repair by root cause; do not claim final completion while any pair fails.
15. **[P2-1] Verify multiword composition:** check window compatibility for all 42,875 triples and validate the frozen three-word, five-word and repeated-word trajectory set.
16. **[P2-2] Produce videos and human reviews:** link trajectory evidence and distinguish engineering, language and hardware assessments; never fabricate reviews.
17. **[P2-3] Deliver and reproduce:** package resources, bilingual instructions, logs and inventories; reproduce in a newly created environment.

## Execution rules

- Validate each completed task and retain commands, exit codes and logs before starting dependent work; run the full suite after integration.
- Do not expand scope, refactor unrelated modules or use subagents. Serialize edits to shared files.
- Report structural, branch or interface differences before proceeding with affected work. Continue independent work while clarification is pending.
- Do not describe plans or unchecked reports as completed capabilities. Inspect files instead of inventing interfaces.
- Preserve v1, original assets and old runs. Changes to code, inputs, models, environment or policy require a new run_id; do not mix checkpoints.
- Do not alter protected cores, windows or word timing without Group 2 confirmation. The NURSE f80 exception still requires motion-version-bound confirmation.
- Never manufacture passes by changing approved strings, shrinking denominators, dropping collision pairs or relaxing thresholds. Search failure is not proof of infeasibility.
- Independently read and reconstruct trajectories. Sampled acceptance is not continuous collision certification, language understanding or hardware safety.
- Maintain bilingual documentation and indexes under AGENTS.md. Do not push, publish, delete original assets or execute hardware.
- On a blocker, preserve the state and report expected/actual behavior, versions, commands, exit codes, logs and minimal reproduction steps. Continue unaffected tasks.

## Key files

- [Detailed tasks and dependencies](PLAN.md), [Repository instructions](AGENTS.md).
- [Input/version contract](src/sign_robot/pair_contract.py), [Runner](src/sign_robot/all_pairs.py), [Independent verification](src/sign_robot/pair_verification.py).
- [Existing motion primitives](src/sign_robot/transitions.py), [Current policy](config/transition_policy.json), [Motion index](motions/hospital_v1_motions.json).
- [Word audit](word_audit.json), [Endpoint issues](results/group3_all_pairs_startup/endpoint_blockers.json), [Run report](results/group3_all_pairs_startup/final_report.json), [Test log](results/group3_all_pairs_startup/final_pytest.txt).
- [Planning entry point](scripts/plan_all_pairs.py), [Verification entry point](scripts/verify_all_pairs.py), [Summary entry point](scripts/summarize_all_pairs.py), [Existing tests](tests/).

## Key commands

Select commands for the current task; do not blindly run every block. Confirm write access and complete P0-1 before mutations. The local .venv is not a portable delivery environment.

```bash
TASK_REPO=/home/kingderman/Documents/ME5412-github-latest
cd "$TASK_REPO"
git --no-optional-locks status --short --branch
git log -1 --format='%H%n%s'
```

Also run tests added for each task. Existing focused regression tests and the post-integration full suite are:

```bash
"$TASK_REPO/.venv/bin/python" -m pytest -q \
  "$TASK_REPO/tests/test_all_pairs_contract.py" \
  "$TASK_REPO/tests/test_all_pairs_pipeline.py" \
  "$TASK_REPO/tests/test_plan_transitions.py" \
  "$TASK_REPO/tests/test_transition_endpoint_gate.py" \
  "$TASK_REPO/tests/test_rrt_connect.py"

"$TASK_REPO/.venv/bin/python" -m pytest -q "$TASK_REPO/tests"
```

The following demonstrates the **current direct development baseline only**. Confirm the run_id is unused; choose another if it exists, without overwriting. After v2 implementation, select its verified, existing policy path. The current policy cannot produce formal PASS_SIM. Do not feed new trajectory representations to the old verifier.

```bash
TASK_RUN_ID=handoff_direct_baseline_001
"$TASK_REPO/.venv/bin/python" "$TASK_REPO/scripts/plan_all_pairs.py" \
  --library hospital_v1 --include-self \
  --policy "$TASK_REPO/config/transition_policy.json" \
  --run-id "$TASK_RUN_ID"
"$TASK_REPO/.venv/bin/python" "$TASK_REPO/scripts/verify_all_pairs.py" \
  --run-id "$TASK_RUN_ID"
"$TASK_REPO/.venv/bin/python" "$TASK_REPO/scripts/summarize_all_pairs.py" \
  --run-id "$TASK_RUN_ID"
```

The old scripts/plan_transitions.py --all option covers ten fixed sentences, not 1,225 pairs. Development diagnosis may run with approvals pending, but cannot be presented as formal acceptance.

## Acceptance criteria

- Exactly 1,225 unique main records: 1,190 non-self and 35 self-pairs. Each record binds frozen inputs, code, policy and environment.
- Final L2 completion requires **1,225/1,225 PASS_SIM**, with zero blocked, failed, timed-out, erroneous, unrun or SOURCE_NEAR records. Intermediate deliveries that fall short must explicitly say incomplete.
- Accepted candidates have genuine core/window approvals, satisfy frozen limits, couplings, geometry, boundary, speed, acceleration, jerk and duration rules, and pass independent saved-artifact verification.
- Verify A→B, B→A and A→A separately; preserve two occurrences for a self-pair. All 42,875 triple window-compatibility checks and the frozen multiword trajectory tests pass.
- Resume preserves completed results; all evidence is obtainable; fresh-environment reproduction meets frozen tolerances. Report independent tests and remaining limitations.

## Known risks

- Source-motion defects and unapproved windows may prevent any connector from formally passing; Group 3 cannot resolve them through search alone.
- Piecewise curves, finger schedules and postprocessing can introduce between-frame collisions. Pairwise passes do not establish whole-sequence acceptance.
- RRT cost, collision filtering and interpretation of finite-difference derivatives affect conclusions; freeze budgets and verification scope.
- Uncommitted files, ignored result directories and local .venv links can make delivery incomplete.

## Rollback

- Preserve current contents, modified/untracked files and run manifests before editing; maintain a task-specific change list.
- Revert only this task's changes to preserved contents, not others' work. Checking out HEAD alone does not recover the current baseline.
- Explicitly version new code and policies; do not overwrite old results. Keep failed runs and use new directories for new attempts.
- Do not use git reset --hard, git clean or directory-wide replacement. Stop incompatible paths and retain failure evidence.

## Required completion report

1. Changed files: absolute paths and purpose.
2. Every task's status: complete/incomplete/blocked/insufficient evidence, checked against PLAN.md.
3. Actual commands: working directory, version, exit codes and log locations.
4. Test/check results: executed tests, run IDs, 1,225/1,190/35 denominators, status counts, trajectories and verification evidence.
5. Deviations from the plan: reasons, impact and human confirmations.
6. Remaining risks: unverified limitations, external dependencies, minimal failure reproduction steps and rollback procedure.

========== HANDOFF END ==========

