# TASK-05: P0-5 v2 trajectory and input contract

[中文](TASK-05.md) · [Project state](STATE.en.md)

Date: 2026-10-31 (Asia/Shanghai). Task: **Complete**. Checkout `/home/kingderman/Documents/ME5412-github-latest`, branch `codex/group3-all-pairs-v1`, baseline HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`.

## Changed files and evidence

- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_contract.py`
- `/home/kingderman/Documents/ME5412-github-latest/config/transition_policy_v2.json`
- `/home/kingderman/Documents/ME5412-github-latest/contracts/all_pairs_v2.json`
- `/home/kingderman/Documents/ME5412-github-latest/tests/test_pair_contract_v2.py`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-v2-contract.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-v2-contract.en.md`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-5/pytest_contract_final.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-5/pytest_contract_final.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-5/pytest_contract_initial.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-5/pytest_contract_initial.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-5/v2_hash_manifest.json`

Also updates this report, its paired translation, both STATE reports and indexes. Before/after SHA-256 values and per-task backups are recorded in `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/TASK-05/changes.json`. Installation is limited to explicit paths and refuses concurrent source changes.

## Decisions and operations

Added strict v2 policy/trajectory validation, explicit schema dispatch, versioned segments and finite budget/approval/identity contracts in pair_contract.py. The default v1 entry point rejects v2 so the legacy runner cannot misread the new representation. Added the v2 policy, declarative contract, positive/negative tests and a hash manifest.

## Deviations

Task scope is unchanged; source assets, v1 policy and historical runs are intact.

## Rollback and final state

Revert only entries in this task's changes.json; restore existing files from the before copy and preserve newly created files first. Never use reset --hard, clean or whole-checkout overwrite. The L2 all-pairs objective remains incomplete; the executor cannot invent approvals.

## Actual validation

In the restored staging checkout, ran target `.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pair_contract_v2.py tests/test_all_pairs_contract.py tests/test_all_pairs_pipeline.py`; final exit 0, 80 passed in 3.19s. After an initial 78-test pass, added nonzero-boundary and real contract-hash freeze cases and reran 80 tests. Both logs are retained. Installation checks each task file hash independently and never rewrites historical runs.
