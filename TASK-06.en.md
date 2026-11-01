# TASK-06: P1-1 Approved-window loading and selection

[中文](TASK-06.md) · [Project state](STATE.en.md)

Date: 2026-10-31 (Asia/Shanghai). Task: **Complete**. Checkout `/home/kingderman/Documents/ME5412-github-latest`, branch `codex/group3-all-pairs-v1`, baseline HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`.

## Changed files and evidence

- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_windows.py`
- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_contract.py`
- `/home/kingderman/Documents/ME5412-github-latest/contracts/all_pairs_v2.json`
- `/home/kingderman/Documents/ME5412-github-latest/config/transition_policy_v2.json`
- `/home/kingderman/Documents/ME5412-github-latest/tests/pair_v2_fixtures.py`
- `/home/kingderman/Documents/ME5412-github-latest/tests/test_pair_windows_v2.py`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-window-approval.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-window-approval.en.md`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-1/approval_state.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-1/pytest_windows_final.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-1/pytest_windows_final.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-1/pytest_windows_initial.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-1/pytest_windows_initial.log`

Also updates this report, its paired translation, both STATE reports and indexes. Before/after SHA-256 values and per-task backups are recorded in `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/TASK-06/changes.json`. Installation is limited to explicit paths and refuses concurrent source changes.

## Decisions, actual commands and results

Implemented external review plus actual-motion hash binding, timezone-aware approval validity, full protected-core preservation and role-specific frame enumeration without legacy trim inheritance. Evidence integrity is not described as human identity verification.

Ran target `.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pair_windows_v2.py tests/test_pair_contract_v2.py tests/test_all_pairs_contract.py` in staging: final exit 0, 72 passed in 0.23s. See P1-1/pytest_windows_final.*. Real input lacks a bundle and stays BLOCKED_INPUT / MISSING_APPROVAL_BUNDLE. The contract gained validity/evidence definitions with the policy hash synchronized. Next: P1-2.

## Deviations

Task scope is unchanged; source assets, v1 policy and historical runs are intact.

## Rollback and final state

Revert only entries in this task's changes.json; restore existing files from the before copy and preserve newly created files first. Never use reset --hard, clean or whole-checkout overwrite. The L2 all-pairs objective remains incomplete; the executor cannot invent approvals.
