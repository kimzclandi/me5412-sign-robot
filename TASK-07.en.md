# TASK-07: P1-2 independent v2 verifier

[中文](TASK-07.md) · [Project state](STATE.en.md)

Date: 2026-10-31 (Asia/Shanghai). Task: **Complete**. Checkout `/home/kingderman/Documents/ME5412-github-latest`, branch `codex/group3-all-pairs-v1`, baseline HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`.

## Changed files and evidence

- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_verification_v2.py`
- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_verification.py`
- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_contract.py`
- `/home/kingderman/Documents/ME5412-github-latest/contracts/all_pairs_v2.json`
- `/home/kingderman/Documents/ME5412-github-latest/config/transition_policy_v2.json`
- `/home/kingderman/Documents/ME5412-github-latest/tests/test_pair_verification_v2.py`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-independent-verifier-v2.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-independent-verifier-v2.en.md`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-2/pytest_verifier_final.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-2/pytest_verifier_final.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-2/pytest_verifier_initial.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-2/pytest_verifier_initial.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-2/pytest_verifier_reviewed.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-2/pytest_verifier_reviewed.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-2/pytest_verifier_reviewed_final.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-2/pytest_verifier_reviewed_final.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-2/verifier_contract_hashes.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-2/verifier_evidence_summary.json`

Also updates this report, its paired translation, both STATE reports and indexes. Before/after SHA-256 values and per-task backups are recorded in `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/TASK-07/changes.json`. Installation is limited to explicit paths and refuses concurrent source changes.

## Decisions, actual commands and results

Added an independent saved-file verifier with no planner dependency. It reconstructs source slices and polynomial segments under the v2 contract, checks hashes/approvals/slices first, then analytic quality and bounded native geometry. Budget exhaustion is TIMEOUT and never pass. The v2 contract verifier dispatch and policy hash were synchronized.

Final staging command: `.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pair_verification_v2.py tests/test_pair_contract_v2.py tests/test_pair_windows_v2.py tests/test_all_pairs_pipeline.py`, exit 0, 91 passed in 3.39s. After an initial 89 pass, added endpoint/progress/hash, analytic-extrema and self-pair cases and fixed a floating-point tolerance; the final 91-test output is retained. Real input remains blocked by the missing approval bundle.

This matches the plan: independent reconstruction, between-frame sampling, source slices, boundaries, quality and budgets are implemented; real approvals and formal PASS remain P1-8.

## Deviations

Task scope is unchanged; source assets, v1 policy and historical runs are intact.

## Rollback and final state

Revert only entries in this task's changes.json; restore existing files from the before copy and preserve newly created files first. Never use reset --hard, clean or whole-checkout overwrite. The L2 all-pairs objective remains incomplete; the executor cannot invent approvals.
