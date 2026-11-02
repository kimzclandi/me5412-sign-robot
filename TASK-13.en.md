# TASK-13: P1-8 Blocked on real approval inputs

[中文](TASK-13.md) · [Project state](STATE.en.md)

Date: 2026-10-31 (Asia/Shanghai). Task: **Blocked**. Checkout `/home/kingderman/Documents/ME5412-github-latest`, branch `codex/group3-all-pairs-v1`, baseline HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`.

## Changed files and evidence

- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_before_resume_hashes.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_development_diagnosis.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_plan_four.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_plan_four.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_post_install_regression.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_post_install_regression.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_resume_four.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_resume_four.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_summarize_four.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_summarize_four.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_verify_four.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_verify_four.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-8/approval_dependency_audit.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-8/approval_dependency_audit.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-8/approval_dependency_audit.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-8/minimal_reproduction.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-8/minimal_reproduction.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-8/reproduce_missing_approval.py`
- `/home/kingderman/Documents/ME5412-github-latest/TASK-12.md`
- `/home/kingderman/Documents/ME5412-github-latest/TASK-12.en.md`

Also updates this report, its paired translation, both STATE reports and indexes. Before/after SHA-256 values and per-task backups are recorded in `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/TASK-13/changes.json`. Installation is limited to explicit paths and refuses concurrent source changes.

## Expected behavior, actual state and blocker

P1-8 requires actual group-2 core/window approvals and repaired motions, followed by approved quality caps, linear-replay derivative interpretation, collision coverage and sampling budgets, then a strictly tested formal pass implementation. The actual policy remains `endpoints.review_status=pending`, `approval_file=null`, `quality.freeze_status=pending` and `validation.approval_status=pending`; all evidence references are unconfigured and `formal_acceptance_enabled=false`. The actual loader returns:

`WindowApprovalError: MISSING_APPROVAL_BUNDLE — No actual group-2 review bundle is configured`.

All 35 current motion hashes match the preserved baseline; no returned repaired assets were detected. Issue lists, unfilled templates and explicitly synthetic test fixtures do not constitute real reviews. No approval strings, synthetic approvals, relaxed caps or word trimming were used to bypass this dependency. P1-8 is **blocked/incomplete**. A formal PASS exit is still unimplemented and disabled; this is more than waiting to run a full scan.

## Minimal reproduction and actual commands

Working directory `/home/kingderman/Documents/ME5412-github-latest`; branch/HEAD are at the top and code-content identity is in `approval_dependency_audit.json`. The read-only dependency audit and separate minimal reproducer were executed and both exited **2** for the expected blocker. Full stdout/stderr and argv/cwd/exit are retained in this task's `.log` and `.command.json` files. Reproduce from the repository:

```bash
cd /home/kingderman/Documents/ME5412-github-latest
.venv/bin/python results/group3_execution_20261031_001/P1-8/reproduce_missing_approval.py
```

Expected: the MISSING_APPROVAL_BUNDLE output above and exit 2. The existing CLIs finish the four-pair development diagnosis with exit 0, but every pair is BLOCKED_INPUT; successful command completion does not mean formal acceptance.

## Attempts and required next step

Checked policy, issue list, review template and actual motion hashes and invoked the real approval loader. The post-install P1-7 planning, independent input review and resume also detected the missing input. Development runs and all failure/blocker logs are preserved.

Required: real review evidence for all 35 words binding motion versions/frame counts/core/entry/exit windows/reviewer/validity; repaired motions and metadata or actual version-bound dispositions for every source defect; approved quality caps and linear-replay derivative scope; collision filters/static-pair coverage and verification budgets; a motion-hash-bound NURSE f80 decision. Once supplied, inspect these read-only, use a new run_id, reaudit and finish P1-8 formal pass code with positive/negative cases before P1-9/P2. The executor cannot replace those human decisions.

## Preserved state

This task adds blocker evidence/reports and archives the post-install P1-7 source diagnosis. Policy, motions, core/windows, caps and code are unchanged. P1-9 and P2-1/2/3 were not executed. The full-suite test and delivery checklist will be separate closeout actions and cannot upgrade L2.

## Deviations

Required real approvals and repairs are absent, so formal inputs/pass criteria were not imported or enabled. Evidence is preserved and dependent tasks are not executed; no substitute approvals were invented.

## Rollback and final state

Revert only entries in this task's changes.json; restore existing files from the before copy and preserve newly created files first. Never use reset --hard, clean or whole-checkout overwrite. The L2 all-pairs objective remains incomplete; the executor cannot invent approvals.
