# TASK-12: P1-7 Multi-candidate runner and resume

[中文](TASK-12.md) · [Project state](STATE.en.md)

Date: 2026-10-31 (Asia/Shanghai). Task: **Complete**. Checkout `/home/kingderman/Documents/ME5412-github-latest`, branch `codex/group3-all-pairs-v1`, baseline HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`.

## Changed files and evidence

- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_runner_v2.py`
- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/all_pairs.py`
- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_verification.py`
- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_verification_v2.py`
- `/home/kingderman/Documents/ME5412-github-latest/scripts/plan_all_pairs.py`
- `/home/kingderman/Documents/ME5412-github-latest/scripts/verify_all_pairs.py`
- `/home/kingderman/Documents/ME5412-github-latest/scripts/summarize_all_pairs.py`
- `/home/kingderman/Documents/ME5412-github-latest/tests/test_pair_runner_v2.py`
- `/home/kingderman/Documents/ME5412-github-latest/contracts/all_pairs_v2.json`
- `/home/kingderman/Documents/ME5412-github-latest/config/transition_policy_v2.json`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-multicandidate-runner-v2.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-multicandidate-runner-v2.en.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-v2-contract.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-v2-contract.en.md`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/pytest_runner_initial.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/pytest_runner_initial.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/runner_fault_cases.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/runner_fault_cases.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/runner_fault_cases_v2.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/runner_fault_cases_v2.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/runner_pre_review.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/runner_pre_review.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/runner_summary.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/v1_pipeline_regression.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/v1_pipeline_regression.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/v2_integration_tests.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/v2_integration_tests.log`

Also updates this report, its paired translation, both STATE reports and indexes. Before/after SHA-256 values and per-task backups are recorded in `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/TASK-12/changes.json`. Installation is limited to explicit paths and refuses concurrent source changes.

## Decisions and actual operations

Implemented and tested P1-7 in the restored checkout, preserving the three existing CLIs with explicit schema-2 dispatch for all six method families. Attempts, every resolved timing curve and final candidates are immutable; journals form a previous-file hash chain with a manifest head. Every eligible candidate receives independent review before ranking by actual connector duration, method order, trajectory hash and ID. Missing candidates receive only independent input/endpoint diagnosis. Denominators remain 1,225 / 1,190 / 35 and formal acceptance stays disabled.

Resume checks code/commit, model, motion/approval, policy and environment identity. Complete orphan journals/attempts are recoverable. Completed content is validated and reused. Unfinished replay excludes elapsed time but compares actual saved-curve fingerprints; differing replay is refused with evidence retained, which can happen near a wall deadline. Simulated process interruption is not verified physical power-loss durability.

## Commands, exit codes and validation

Working directory `/tmp/me5412-execution-20261031/restored-baseline`, source checkout `.venv/bin/python`; pytest uses `-q -p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1` and four numerical-library thread variables set to 1. The listed `.command.json` files contain exact argv/cwd/exit/log paths:

- `runner_fault_cases_v2`: exit 0, **38 passed in 11.35s**; identity changes, three interruption points, completed-byte preservation, replay/duplicate refusal, corrupted curves/frozen/review files, false PASS, incomplete proofs, recomputed selection, no-curve diagnosis and budgets.
- `v2_integration_tests`: exit 0, **160 passed in 26.49s**, including the above 38 plus contract/window/verifier/timing/finger/route/search tests.
- `v1_pipeline_regression`: exit 0, **296 passed in 6.32s**, covering all-pairs contract/pipeline, plan_transitions, endpoint gates and RRT.
- Initial `runner_fault_cases`: exit 1, 31 passed / 1 failed. A missing configured approval file correctly returned `INVALID_APPROVAL_INPUT`; the test incorrectly expected `MISSING_APPROVAL_BUNDLE`. The two cases were split and the failure log retained without weakening approval rules.

Synthetic positive cases call the actual independent verifier and read NPZ/review/saved-curve files; freeze/model/clearance boundaries use fixtures. Synthetic reviews were never imported as production approvals. Original motions, cores/windows/timing, v1 policy and historical runs are preserved.

## Current exit

P1-7 implementation and these checks are complete. A small source-checkout development scan will use fresh `handoff_v2_dev_20261031_001` after installation; actual results belong in the final execution report, not a prediction here. P1-8 still requires real group-2 inputs and formal quality/collision approvals. L2 is incomplete.

See the [runner guide](docs/group3-multicandidate-runner-v2.en.md).

## Deviations

Task scope is unchanged; source assets, v1 policy and historical runs are intact.

## Rollback and final state

Revert only entries in this task's changes.json; restore existing files from the before copy and preserve newly created files first. Never use reset --hard, clean or whole-checkout overwrite. The L2 all-pairs objective remains incomplete; the executor cannot invent approvals.
