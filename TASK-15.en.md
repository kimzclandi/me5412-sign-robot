# TASK-15 — R1 preservation and state audit

[中文](TASK-15.md)

Status: complete. Read-only inspection confirmed the target, branch/HEAD, files, actual library, existing v2 implementation and historical reports. Chat cwd differs from the target. No subagent was created under the current single-agent constraint.

Changed HANDOFF.md and HANDOFF.en.md; added this report and R1 evidence. Corrected stale direct-only and approval-blocker descriptions. PLAN.md and historical tasks remain unchanged. Formal flags remain false/pending.

Archive: `/home/kingderman/Documents/ME5412/execution_evidence/auto_cuts_20261031_001/baseline.tar`, 863,150,080 bytes, SHA-256 `501e2e75d05bad81f93a70e24b76b121370c345f45ee4973dd33ec6ea733d22f`. All 7,585 entries match the restored copy; the source did not change during preservation. Restored workspace: `/tmp/me5412_auto_cuts_20261031_001/repository`. Includes .git, uncommitted/untracked/ignored results, source assets and the external .venv symlink without dereferencing. Restore into a new empty directory and check baseline_inventory.json; restoring HEAD alone is insufficient.

Commands: `python3 /tmp/me5412_preserve_auto.py` exited 0. `.venv/bin/python -m pytest -q -p no:cacheprovider tests` initially exited 1 because sandbox socket access was denied: 724 passed, 2 failed, 23 errors. The identical unchanged baseline then exited 0 with temporary loopback HTTP ports allowed: 749 passed in 43.11s. Both logs remain in results/user_protected_auto_20261031_001/R1/.

Decision: archive first, implement in the restored copy, install only enumerated files after baseline-hash checks. COME binds the actual hospital_v1 201-frame Studio Galt file; the 89-frame WLASL alternative cannot contain the protected interval. Full hashes and the unverified prior displayed-video association are in HANDOFF.en.md.

Deviations: target writes require sandbox installation review, and baseline service tests need temporary local HTTP ports. No tests or numerical limits were weakened.
