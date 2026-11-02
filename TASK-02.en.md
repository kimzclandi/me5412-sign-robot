# TASK-02: P0-2 per-word issue and confirmation list

[中文](TASK-02.md) · [Project state](STATE.en.md) · [Issue list](docs/group3-all-pairs-word-issues.en.md)

Date: 2026-10-31 (Asia/Shanghai). P0-2: complete. Read `word_audit.json`, `endpoint_blockers.json` and development run `all_pairs_dev_20261031_v2` to generate a 35-word structured issue list and bilingual review templates.

## Changes and decisions

Added paired docs and `results/group3_execution_20261031_001/P0-2/word_issue_manifest.json`. It records 10 endpoint-role issues across 10 words, internal collisions in 30 words, speed excess in 8 words, and 326 unique endpoint-affected pairs with all 35 self-pairs retained. Each word includes motion hash, protected-core hint, original entry/exit frame, issue frames, closest pair, research endpoints and required confirmations. No motion, window or timing changed. Research endpoints including NURSE f80/f81, HURT f66, MEDICINE f73 and INTERPRETER f25 remain pending and must be hash-bound.

## Commands and verification

Working directory: `/home/kingderman/Documents/ME5412-github-latest`. Ran `/home/kingderman/Documents/ME5412-github-latest/.venv/bin/python /tmp/me5412-execution-20261031/generate_p0_2.py`, which writes only to the restored staging tree, and asserted the JSON structure, 35-word count, endpoint count, issue-word counts, motion hashes and affected pairs; exit 0. The hash-guarded installer then wrote the target checkout; exit 0. Backups/manifests are under `results/group3_execution_20261031_001/TASK-02/`. No pytest ran; this task derives frozen evidence and recalculates speed intervals from source arrays. Formal thresholds, protected cores/windows and repaired motions remain second-group dependencies. Geometry evidence provides per-frame clearances and each word's worst pair, not every collision pair at every frame.

## Deviation and state

All P0-2 requested fields are covered. The plan did not prescribe filenames, so paired docs plus structured JSON were used without expanding code scope. P0-2 complete; P0-3 is next; L2 remains incomplete.
