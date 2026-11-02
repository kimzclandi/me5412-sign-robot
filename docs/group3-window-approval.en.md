# P1-1 approved-window loading and selection

[中文](group3-window-approval.md) · [Task report](../TASK-06.en.md)

Added pair_windows.py. `load_window_approvals(root, policy, library)` rereads the actual bundle, motion files and external review documents; checks their hashes/content, motion frame count, window version, unique IDs/words, reviewer field and timezone-aware review/expiry dates. Changing an approved string alone fails. Document consistency does not prove reviewer identity; formal authorized import remains P1-8.

Reviewed core and entry/exit windows are inclusive ranges. Latest entry cannot pass the first protected-core frame; earliest exit cannot precede its last frame. Out-of-range/order errors, insufficient one-sided samples and stale motions fail. Library geometric hints never automatically become semantic approval, and hard-coded legacy trim exceptions are not inherited.

`select_pair_windows` enumerates role-specific frames in stable order by distance from the original sign endpoint, then frame number, and rechecks expiry and motion identity. A→B and B→A are separate, while A→A preserves two occurrences. Endpoint geometry/limits/coupling belong to later candidate and verifier tasks.

The v2 frozen inventory now binds both bundle and referenced review bytes. The contract adds optional valid_until/exceptions and the exact evidence-document format, with its policy hash updated together; v1 and historical assets are unchanged.

Actually ran the window, v2-contract and legacy-contract suites in the restored staging checkout with no pytest cache: final exit 0, 72 passed. The final rerun covers the synchronized contract/policy hashes; counts are not summed. Synthetic approval fixtures exist only in pytest temp directories and are not real group-2 material.

The real policy still has no approval_file and returns MISSING_APPROVAL_BUNDLE. No real approval or PASS_SIM was created. Evidence is under results/group3_execution_20261031_001/P1-1/.
