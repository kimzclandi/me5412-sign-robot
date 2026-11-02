# TASK-04: P0-4 Quality metrics and threshold proposal

[中文](TASK-04.md) · [Project state](STATE.en.md)

Date: 2026-10-31 (Asia/Shanghai). Task: **Complete**. Checkout `/home/kingderman/Documents/ME5412-github-latest`, branch `codex/group3-all-pairs-v1`, baseline HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`.

## Changed files and evidence

- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-quality-metrics.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-quality-metrics.en.md`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-4/analytic_metric_checks.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-4/audit_evidence.py`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-4/quality_audit.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-4/quality_audit.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-4/quality_metrics_recomputed.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-4/quality_threshold_proposal.json`

Also updates this report, its paired translation, both STATE reports and indexes. Before/after SHA-256 values and per-task backups are recorded in `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/TASK-04/changes.json`. Installation is limited to explicit paths and refuses concurrent source changes.

## Decisions and operations

Started from pair_contract boundary derivatives and pair_verification trajectory_metrics. Fixed units, timestamps, finite differences and separate analytic connector calculations. Recomputed 899 candidates and retained per-record values; threshold state remains pending.

## Deviations

Task scope is unchanged; source assets, v1 policy and historical runs are intact.

## Rollback and final state

Revert only entries in this task's changes.json; restore existing files from the before copy and preserve newly created files first. Never use reset --hard, clean or whole-checkout overwrite. The L2 all-pairs objective remains incomplete; the executor cannot invent approvals.

## Actual commands, exits and validation

Ran `.venv/bin/python /tmp/me5412-execution-20261031/audit_p0_4.py` in the target checkout, exit 0; logs quality_audit.log and quality_audit.command.json. All 899 candidates match historical statistics, 35 source-word difference metrics were saved, and three analytic checks pass. A preliminary read-only query used system python3 and failed with ModuleNotFoundError: numpy; the existing .venv interpreter succeeded. No new geometry scan is claimed.
