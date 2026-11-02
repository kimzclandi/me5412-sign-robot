# TASK-01: P0-1 baseline preservation

[中文](TASK-01.md) · [Project state](STATE.en.md)

Date: 2026-10-31 (Asia/Shanghai). P0-1: complete. Execution checkout: `/home/kingderman/Documents/ME5412-github-latest`; branch `codex/group3-all-pairs-v1`; HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`. The chat workspace ME5412 is a different checkout.

## Changes and decisions

Added paired TASK-01/STATE reports and an isolated `results/group3_execution_20261031_001` evidence directory; updated both documentation indexes. No code, model, motion, policy or historical run was changed. Preserved the whole checkout, including Git metadata and modified, untracked and ignored content: `/home/kingderman/.codex/visualizations/2026/10/30/01a18e26-94c1-7160-ba35-a119ee7cf0fb/group3-execution-20261031-001/baseline.tar`; SHA-256 `a4c6732f38b25939e407bbbe06c57c9350f7cae98460a07052d976dfd3f29e70`; 858,275,840 bytes. `/home/kingderman/.codex/visualizations/2026/10/30/01a18e26-94c1-7160-ba35-a119ee7cf0fb/group3-execution-20261031-001/baseline-content.json` records 7,052 entries, 6,919 regular files and 845,766,665 content bytes; manifest SHA-256 `3937cca12139306465932570bb4035cae529a806948b4e8e9d309deb42d58481`.

Restore drill: `/tmp/me5412-execution-20261031/restored-baseline`. Types, modes, hashes, sizes, symlink targets and Git status match the source. Future implementation remains serial in the planned checkout; explicit sandbox escalation successfully created its isolated evidence directory. `.venv` is a preserved external symlink to `/home/kingderman/Documents/Codex/2026-10-13/new-chat/me5412-sign-robot/.venv`; its target is not part of this portable snapshot. P2-3 remains necessary.

## Commands and actual verification

Working directory: `/home/kingderman/Documents/ME5412-github-latest`. Read-only inventory used pwd, ls -la, rg --files, git --no-optional-locks status --short --branch, git log -1, and AGENTS/PLAN/HANDOFF reads. Git command arrays, exit codes, outputs and binary patches are under `/home/kingderman/.codex/visualizations/2026/10/30/01a18e26-94c1-7160-ba35-a119ee7cf0fb/group3-execution-20261031-001/commands.json` and git-* files.

`python3 /tmp/me5412-execution-20261031/preserve_baseline.py` initially exited 1 during counting because checkpoints wrap records in an envelope (KeyError: status). The completed archive and restored tree were retained. After inspecting the actual schema, `python3 /tmp/me5412-execution-20261031/preserve_baseline.py --resume-preservation` exited 0 without overwriting the archive. Two earlier read-only python commands exited 127 because only python3 exists; reruns with python3 succeeded. See `/home/kingderman/.codex/visualizations/2026/10/30/01a18e26-94c1-7160-ba35-a119ee7cf0fb/group3-execution-20261031-001/preservation.json`, frozen-input-check.json and repository evidence copies in `results/group3_execution_20261031_001/P0-1/`.

Actually checked 3,378 run files, 4 frozen files, 22 source files, 142 input/model files and 32 summary files; all hashes/sizes match. Recounted 1,225 unique records (1,190 non-self, 35 self), 899 candidates and 1,225 verification files: 326 BLOCKED_ENDPOINT, 386 FAILED_SEARCH, 513 FAILED_QUALITY, zero PASS_SIM. These are integrity checks, not rerun geometry or pytest. The 589 passed entry remains historical evidence.

## Deviations and rollback

The workspace mismatch was reported; unrelated ME5412 content was preserved. Backup lives in the writable session artifact directory, with explicit escalation for target writes. Global user AGENTS requires subagents whereas the summary forbids them; audit_handoff only independently checked paths and completion evidence, with no edits delegated.

P0-1 acceptance passes; L2 is incomplete. Revert only this task's explicit changes.json entries, retaining others' work. Restore baseline into a new empty directory and verify baseline-content.json; never overwrite the original checkout or use reset --hard/clean. Core/window approvals, quality thresholds and collision coverage remain pending human confirmation.
