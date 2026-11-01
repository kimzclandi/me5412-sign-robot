# P1-7 multi-candidate runner and resume

[中文](group3-multicandidate-runner-v2.md) · [Execution report](../TASK-12.en.md)

State: the development runner is implemented; formal acceptance remains disabled. The three existing CLIs dispatch by policy/manifest schema. The v1 policy, NPZ format, historical runs and default readers are preserved.

Each v2 run freezes `policy.json`, `contract.json`, `library_manifest.json` and the full `pair_universe.json`. Identity binds actual code content/commit, model assets, motions/metadata, approval files, policy and the dependency environment. Any change requires a new run_id. `--pair` and `--max-pairs` filter execution only; summary denominators remain **1,225 / 1,190 / 35**, with other pairs `NOT_RUN`.

`attempts/PAIR/attempt_NNNNN.json` retains every method, parameter, endpoint, seed, budget and diagnosis. Every resolved timing curve is saved under `timing_attempts/`; eligible final candidates live under `candidates/`. Their hashes and selection eligibility are distinct. Failures and RRT raw/shortcut paths remain in diagnostics. Deterministic routes and RRT share finite per-pair work and wall budgets; timeout/search exhaustion does not prove infeasibility.

Checkpoints append to `checkpoints/PAIR/checkpoint_NNNNN.json`, binding the previous file hash and sequence; the manifest stores the head. After process interruption, recovery can adopt a complete journal not yet registered in the manifest, or a complete attempt not yet checkpointed. Curves written before their attempt can only be reused after identical deterministic replay. An unfinished pair replays its fixed-seed stream and compares logical fingerprints of diagnostics and every actual saved curve, ignoring elapsed-time fields while retaining original bytes. A differing replay is refused and preserved. Wall-driven attempt streams can differ and then require a new run_id with the previous run retained. Completed planning/reviews are validated and reused without recalculation or overwrite. Tests simulate process interruption; physical power-loss storage durability has not been verified.

The independent entry reads every eligible final candidate. Selection requires complete contract, approval, core, original-slice, two-occurrence and full-timeline numerical evidence with matching candidate/run hashes. Ranking uses actual connector duration, `planner.methods` order, canonical trajectory hash and attempt ID. The saved winner is recomputed on load. A numerical development candidate remains `FAILED_QUALITY` and `playback_eligible=false`. Without candidates, the verifier freshly freezes inputs, reads actual approval files and rechecks permitted endpoints within budget; it records `DIAGNOSIS_ONLY`, never a passing curve review.

Exports include a 35×35 `matrix.csv`, 1,225-row `pairs.jsonl`, `summary.json` and a file-hash inventory. The manifest is marked summary-stale before export, allowing an interrupted export to be regenerated without changing planning/review artifacts.

These commands describe the development diagnosis, whose actual results are in the final report. Choose an unused run_id for a new run; only --resume may reuse an existing ID, and version changes also require a new ID. Command completion is not formal acceptance:

```bash
TASK_REPO=/home/kingderman/Documents/ME5412-github-latest
TASK_RUN_ID=handoff_v2_dev_20261031_002
cd "$TASK_REPO"
"$TASK_REPO/.venv/bin/python" scripts/plan_all_pairs.py --include-self \
  --policy config/transition_policy_v2.json --run-id "$TASK_RUN_ID" \
  --pair HELLO__PLEASE --pair PLEASE__HELLO --pair HELLO__HELLO --pair NURSE__NURSE
"$TASK_REPO/.venv/bin/python" scripts/verify_all_pairs.py --run-id "$TASK_RUN_ID"
"$TASK_REPO/.venv/bin/python" scripts/summarize_all_pairs.py --run-id "$TASK_RUN_ID"
"$TASK_REPO/.venv/bin/python" scripts/plan_all_pairs.py --include-self \
  --policy config/transition_policy_v2.json --run-id "$TASK_RUN_ID" --resume \
  --pair HELLO__PLEASE --pair PLEASE__HELLO --pair HELLO__HELLO --pair NURSE__NURSE
```

Actual commands, exit codes, failure and correction logs are under `results/group3_execution_20261031_001/P1-7/`. Test approvals are explicitly synthetic and do not constitute actual group-2 confirmation. Formal acceptance, all 1,225 passes, multiword integration, human evaluation and fresh-environment reproduction remain incomplete.
