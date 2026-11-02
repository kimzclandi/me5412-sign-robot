# TASK-03: P0-3 Collision coverage and sampling audit

[中文](TASK-03.md) · [Project state](STATE.en.md)

Date: 2026-10-31 (Asia/Shanghai). Task: **Complete**. Checkout `/home/kingderman/Documents/ME5412-github-latest`, branch `codex/group3-all-pairs-v1`, baseline HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`.

## Changed files and evidence

- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-collision-scope.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-collision-scope.en.md`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-3/audit_evidence.py`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-3/collision_audit.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-3/collision_audit.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-3/collision_inventory.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-3/dense_counterexample_recheck.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-3/pytest_collision_scope.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-3/pytest_collision_scope.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-3/sampling_proposal.json`

Also updates this report, its paired translation, both STATE reports and indexes. Before/after SHA-256 values and per-task backups are recorded in `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/TASK-03/changes.json`. Installation is limited to explicit paths and refuses concurrent source changes.

## Decisions and operations

Inspected MujocoClearance, same_hand, static derivation, all-pairs sampling and current policy. Added paired coverage documentation and a pending v2 sampling proposal without changing filters or v1. Same-hand exclusions cover all same-side finger/wrist pairs; static gaps remain separate, and future changes to constant joints require rejection or fresh classification.

## Actual commands and validation

Ran .venv/bin/python /tmp/me5412-execution-20261031/audit_p0_3.py from this checkout, exit 0: 122 geoms, 136 static body pairs and 47 vendor geom pairs. Reproduced 11/11 saved-curve between-frame counterexamples. See collision_audit.command.json and .log.

Ran .venv/bin/python -m pytest -q tests/test_plan_transitions.py tests/test_transition_endpoint_gate.py, exit 0: 230 passed, one read-only pytest-cache warning. The first output was not persisted; reran to retain complete command/log evidence. These are 230 unique tests, not 460. The second output is in pytest_collision_scope.command.json and .log. Subsequent commands use -p no:cacheprovider.

P0-3 completes the audit, proposal and independent geometry cases; verification budgets are not implemented and formal collision coverage is not approved.

## Deviations

Task scope is unchanged; source assets, v1 policy and historical runs are intact.

## Rollback and final state

Revert only entries in this task's changes.json; restore existing files from the before copy and preserve newly created files first. Never use reset --hard, clean or whole-checkout overwrite. The L2 all-pairs objective remains incomplete; the executor cannot invent approvals.
