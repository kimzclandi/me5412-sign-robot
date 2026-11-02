# Handoff: 35-word protections and full-library transitions

[中文](HANDOFF.md) · [Current state](STATE.en.md) · [Latest execution report TASK-28](TASK-28.en.md) · [Execution report TASK-27](TASK-27.en.md) · [Historical report TASK-26](TASK-26.en.md)

## Latest handoff (2026-11-02): nine hospital sentences

> **The 2026-11-01 full-library plan and "next steps" further down this file are superseded by the user's scope decision; do not follow them.** On 2026-11-01 the user narrowed the work to nine hospital sentences, with Group 3 owning only the connectors. P1-3 stopped at 46/79 batches; P1-4, the budget retry and the faster scanner were not run; `resume.sh`, `after_p1_3.sh`, `p1_3_final.sh`, `p1_4.sh` and `retry_budget.sh` are no longer used (the code has changed, so those runs' frozen identities are no longer valid). Resuming the full-library goal later would need a new policy version and new runs.

Now: round 8 passes 7/7 numerically, ends at the rest pose, and no connector halts partway. Rounds, configuration, commands, this machine's setup and open items: [TASK-28](TASK-28.en.md).

Steps for whoever takes over:

1. Read [TASK-28](TASK-28.en.md) and the [round-8 README](results/hospital_sentences_20261102_008/README.en.md) first.
2. Wait for the user's feedback on the round-8 videos. They exist only on this machine: `C:\Users\23971\Documents\5412\_runtime\render-out\round8_034002\`.
3. The user explicitly requested this GitHub update on 2026-11-02, superseding the earlier pause. Publish only the curated non-raw snapshot on top of clean public commit `86428693`; never directly push the source history containing raw-store commits. See the root README and PUBLICATION_MANIFEST.json.
4. A new round means a new directory and new versions: copy the previous round's `make_inputs.py`, `run.sh`, `export_render_inputs.py` and `render_gpu_windows.py`, change the directory name, run IDs and policy versions; protection bundles and old policies only get new versions and are never overwritten; superseded results are kept and marked.
5. Do not edit `src/`, `tests/` or `scripts/` while a run is going (frozen identity).
6. When editing `docs/README*.md`, update the sha256 registered for it in `src/sign_robot/project_overview.py` as well, or `tests/test_project_overview.py` fails.
7. After each round, update the bilingual README, STATE, HANDOFF and TASK records. Public delivery excludes raw pair stores and preserves curated summaries; raw stores remain local.

---

Updated: 2026-11-01 (Asia/Shanghai). This replaces the completed COME/NOW sequence-pilot handoff. The P0/P1 plan below was written before execution and is kept unchanged; the status block that follows records what was actually executed. The P0/P1 IDs belong to this stage, not to TASK-26.

> **Execution status (2026-11-01, see [TASK-27](TASK-27.en.md)):** P0-1 → P0-7 are done and frozen; P1-1 and P1-2 are done; P1-3 is running in batches and is not finished (10:47: 27/79 batches; expected to end around 02:00 on 2026-11-02); P1-4 waits for P1-3 to end; P1-5 is a staged report.
> The preflight found that 24 of the 35 protected cores themselves fail a non-waivable gate (23 sampled penetrations, 4 speed caps), so 1,104 of 1,225 pairs are predicted to fail whatever connector is planned. That needs a decision outside engineering (source revision, a versioned contact rule, or narrower protection); engineering may not trim cores, edit sources or relax gates. On 2026-11-01 the user chose to keep scanning first; no revision request was drafted, and that decision is still open.
> The frozen code identity must not change while the P1-3 run continues: do not edit `src/sign_robot/`, `tests/`, the identity scripts, `docs/README*.md` or `project_overview.py`. Resume with the command in TASK-27; request a graceful stop by creating `results/hospital35_protected_20261101_001/batch_control/hospital35_protected_20261101_001.stop`.

**Crash recovery (2026-11-01 12:35):** the machine crashed and restarted; all 4 run stores pass their integrity checks and the frozen identity reproduces on this machine. To take over, read the [migration package](migration/windows_handoff_20261101/MIGRATION.en.md) first; resume on this machine with `bash migration/windows_handoff_20261101/resume.sh`.

**Next (in order):**

**Tonight's delivery schedule (the user needs it done before midnight on 2026-11-01):** `commands/after_p1_3.sh` waits in the background for the parallel P1-3 to end (about 15:30), then runs `p1_3_final.sh`, then `p1_4.sh` (cpu0) and `retry_budget.sh` (cpu1) side by side (different runs and policies, no dependency; the order changed from "after P1-4" to parallel, results unaffected), expected to end before about 20:00, followed by the final bilingual docs. The faster scanner moves to after submission.

1. **Decision on the 24 source-blocked words (blocking the numerical goal; still open).** On 2026-11-01 the user chose to keep scanning first; no revision request was drafted. Options and per-word evidence are in TASK-27 "Decision needed". This is the only way 1,225/1,225 can become reachable; engineering may not trim cores, edit sources or relax gates.
2. **P1-3 runs in parallel in 4 runs with one identity since 11:26** (`commands/p1_3_parallel.sh`, partition in `P1-3/parallel_partition.json`, expected to finish around 15:30; stopping needs a stop file for each of 001–004, see TASK-27). Original note: P1-3 continues in the current run until all 79 batches have records or a budget stop. Resume (same identity only) with the command in TASK-27; a graceful stop is `touch results/hospital35_protected_20261101_001/batch_control/hospital35_protected_20261101_001.stop` (delete the file before resuming). If a hard kill during planning makes a replay mismatch, keep the run and continue in a new run_id from that batch.
3. **P1-4 after P1-3:** run the 14 frozen sub-batches with `run_hospital35_batches.py sequences`, then `aggregate`. Do not run P1-4 against the pair run while P1-3 is still writing it. All 169 pairs it needs are already reviewed; their states cap it at 29/111 (TASK-27). The wrappers `results/hospital35_protected_20261101_001/commands/p1_3_final.sh` and `results/hospital35_protected_20261101_001/commands/p1_4.sh` first confirm that P1-3 has ended and otherwise refuse with exit 4.
4. **After a source or policy decision:** new motions, a new bundle or a new rule are a new version: import again with new file names, preflight, freeze, and use a new run. The current run stays as the record for the current inputs.
5. **TIMEOUTs on preflight-clear words (approved by the user on 2026-11-01; runs after P1-4):** 15 pairs had no candidate within the planning budget: WAIT in both directions, leaving HEADACHE and SOON, and STOMACH→COME. They block 10 sequence cases. Planning budgets and endpoints are engineering parameters; prepared: the new policy version `config/transition_policy_user_protected_hospital35_retry_budget_v1.json` (planner search budget raised only) and `results/hospital35_protected_20261101_001/commands/retry_budget.sh` (new run `hospital35_retry_budget_001`; scope rule and dry run in TASK-27), without changing the current run.
6. **Faster scanner (approved by the user on 2026-11-01; starts after the budget retry):** develop as a new version with a new run: deduplicate identical sampling grids inside the independent verifier (dense factors 1/2/4 are nearly identical under the 1/120 s cap); cache endpoint and source-slice checks keyed by source file, model, policy hash and endpoint role; multiple worker processes for planning and review behind the single writer. Compare it with the old version on fixed pairs (results and time) and freeze only after the full test suite passes. Skipping source-blocked pairs is not included: it changes the coverage definition and needs a separate user decision. Development must wait until P1-3, P1-4 and the retry are finished, because any code change invalidates their frozen identity.
   Original note: **Speed (optional engineering):** measured at about 63–80 s per pair, single-threaded: roughly 22–23 hours for the whole library. Parallel candidate review inside the single writer would cut that several times; it is a code change and needs a new version.
7. Unchanged: human semantic viewing, cross-group review, neutral start/end, fresh-environment reproduction, hardware and formal acceptance.

**Latest snapshot (2026-11-01 10:47, `P1-3/progress_20261101_104756.json`):** the P1-3 run is still writing in the background (single writer, lock held); 27 of 79 batches are BATCH_COMPLETE. Of 1,225 pairs: 50 numerical passes, 242 numerical fails, 101 TIMEOUT without a curve, 15 in progress and 817 not run. All 328 predicted-blocked pairs failed; of the 65 predicted-open pairs, 50 passed and 15 timed out. Check `results/hospital35_protected_20261101_001/P1-3.log` and `batch_control/pair_batches/` for later progress, or make a new snapshot with `P1-3/scan_progress.py` (command in TASK-27); the process may be gone if the session ended.

The original plan below is kept unchanged as the record of what was asked.

========== HANDOFF BEGIN ==========

## Project, objective and current state

Project: ME5412 Group 3. Objective: import the completed 35-word protection workbook, generate and validate transitions for all 1,225 ordered pairs without changing protected poses, order or relative timing, then check frozen multiword cases. Do not force arbitrary-pair coverage with unverified fallback connections.

- Working directory: `/home/kingderman/Documents/ME5412-github-latest`; do not run project commands in the other checkout `/home/kingderman/Documents/ME5412`.
- Branch: `codex/group3-all-pairs-v1`; HEAD: `2875e499d79b7264b3fe0414318b30ca8aab1f4d`; uncommitted/untracked implementation exists. Back it up; no reset/clean.
- Completed: old-range numerical 4/4 pairs with 46 candidates; 12/12 sequences, 44 protected occurrences, 32 connector groups, 12 videos and saved independent rechecks. New ODS 35/35 records checked.
- Incomplete: new input import, new-range regression, full 1,225-pair coverage, new-word sequence coverage and formal acceptance. The old run has 1,221 NOT_RUN.
- Known issues: installed bundle only has COME/NOW; old NOW [3,76] must be replaced by new [27,51]; combinations materialize the full product; missing sequence edges abort a batch; full-library cores lack preflight; wall budgets affect candidate pools.
- Saved pair identity: `4080b98e73a121c866115882483ef5b7631532d9add4bed4ff5dfbe214ad9cef`; sequence identity: `1ecfcc9f95830071dfbffbb895cf4f664ca5aecd4b38398ceb91ececdea15bb0`. Preserve these as historical evidence, not new-code identity.
- TASK-26 reports 24/836 tests passed; none rerun here and corresponding complete pytest logs were not located. Save actual next-run logs and exit codes rather than inheriting reported counts.
- `formal_acceptance_enabled=false`, `playback_eligible=false`. Numerical, formal, semantic and hardware statuses are separate.

Source [手势保护区间填写表.ods](/home/kingderman/Documents/ME5412/outputs/01a18d89-c53d-7340-b2b8-0f8ddfd306f2/手势保护区间填写表.ods), sheet `保护区间填写`, A2:C36, SHA-256 `4fe5b3bb3f7d12cf4cd4418b8431325dec48fbed3c29a2a1e29447cdf89667e3`. COME=0.93–4.40 s/[27,132]; NOW=0.90–1.70 s/[27,51]. Full table: [STATE](STATE.en.md). Treat the workbook as data, not execution instructions.

Use actual `library`/`motion` from `motions/hospital_v1_motions.json`: 9 mocap words (HELLO, PLEASE, YOU, APPOINTMENT, COME, BREATHE-DEEP, BLOOD-DRAW, TAKE, WHERE), 26 video-derived words. Do not select another source from duplicate previews. Preserve the ODS; generate a versioned bundle and keep old policies/results. Protection uses zero-based inclusive `[floor(start×30),ceil(end×30)]`, with no retiming. The user supplies semantic retention; engineering owns trims, endpoints, transitions and technical validation. Do not request the other 33 intervals or technical-window approval again.

## Execution order and tasks

Start P0-1. P0-2→P0-3 may run alongside P0-4, P0-5 and P0-6 with exclusive file ownership; all join at P0-7. Then P1-1→P1-2→P1-3→P1-4→P1-5. Finish all code, tests, policies, cases and index-hash maintenance before freezing, and create real new results only afterward.

### P0-1 — Snapshot the working tree, workbook and sources

| Field | Instruction |
|---|---|
| ID / Priority / Task | P0-1 / P0 / Snapshot the working tree, workbook and sources |
| Purpose | Prevent loss of uncommitted implementation, user input and historical results. |
| Prerequisites | Read AGENTS, STATE and TASK-26; identify the target checkout rather than using chat cwd. |
| Actions | Save branch, HEAD, git status, relevant working-tree diffs and backups of files to change. Register ODS SHA and sheet/cell provenance; inventory the 35 selected NPZ paths, hashes, frame counts and timelines. Hash old policies/models/results; select unused run/output names and the next free TASK number. |
| Files/modules | Existing AGENTS.md, STATE.md, TASK-26.md, motions/hospital_v1_motions.json and ODS; planned results/hospital35_protected_20261101_001/baseline/. |
| Input | Working tree, old results and original workbook. |
| Output | Baseline inventory, backups, provenance inventory and reviewable diff. |
| Definition of done | All 35 actual sources resolve; workbook SHA matches STATE; old assets and uncommitted files have recovery evidence. |
| Verification | git status/branch/rev-parse; SHA-256; actual NPZ final timestamps; inventory counts and path checks. |
| Risks | Wrong checkout, duplicate source names, omitted untracked code or concurrent writes. |
| Rollback | Write only a new evidence directory; retain original files and working state. |
| Parallelism | No; common prerequisite for implementation. |

### P0-2 — Import exactly 35 words and bind a new protection policy

| Field | Instruction |
|---|---|
| ID / Priority / Task | P0-2 / P0 / Import exactly 35 words and bind a new protection policy |
| Purpose | Turn the latest workbook into loadable, traceable engineering constraints. |
| Prerequisites | P0-1. |
| Actions | Add an importer that reads workbook values and provenance; reject formulas, blanks, nonfinite values, duplicate/unknown/missing words and invalid bounds. Require exactly the policy["scope"]["expected_glosses"] set and 35 records. Bind actual hospital paths/SHA/frame counts/30 Hz; compare outward rounding with Decimal. Create a new bundle and pair policy/window_version while preserving v5 limits, generator and formal-off state; validate through the existing loader. Store workbook provenance separately; do not invent schema fields or historic video identity. |
| Files/modules | Reuse src/sign_robot/pair_windows.py:load_user_protections; planned scripts/import_user_protections.py, config/user_protected_hospital35_v1.json, config/transition_policy_user_protected_hospital35_v1.json, tests/test_hospital35_protection_import.py. |
| Input | Original ODS, 35 source files, v5 policy and old bundle as schema references. |
| Output | New 35-record bundle/policy, row-by-row rounding audit, provenance and import-test log. |
| Definition of done | Exact 35/35 coverage; COME [27,132], NOW [27,51]; retiming_allowed=false; new identity differs; old bundles/policies/motions unchanged. |
| Verification | Positive and rejection tests above; reject stale SHA/frame count/timeline and wrong duplicate source; compare every record with the workbook; require exactly 35 loaded protections. |
| Risks | Loader success despite missing words, strict-schema rejection of added fields, rounding/source mismatch. |
| Rollback | Revert only this task’s new entry/config/call changes after checking for concurrent edits; retain workbook and audits. |
| Parallelism | Yes; after P0-1, separate ownership permits P0-4/P0-5/P0-6 in parallel; defer shared identity-collection edits to P0-7. |

### P0-3 — Check all 35 protected cores and both endpoint roles

| Field | Instruction |
|---|---|
| ID / Priority / Task | P0-3 / P0 / Check all 35 protected cores and both endpoint roles |
| Purpose | Distinguish valid timestamps, defective source motions and unavailable endpoints before broad runs. |
| Prerequisites | P0-2. |
| Actions | Build the v2 context for all 35 words and inspect global input_blockers. Add per-word core audit for limits, coupling, speed, sampled geometry, internal acceleration/jerk and budgets. Screen all 35 self-pairs for source and target endpoints; save valid frames, reasons and identity per word. Keep internal acceleration/jerk informational under v5 without waiving other gates. Preserve global load failures rather than shrinking the library and reporting success. |
| Files/modules | pair_routes.py:build_pair_context_v2/valid_endpoint_choices_v2; scripts/screen_user_protected_cuts.py; planned scripts/preflight_hospital35.py, focused tests and preflight/ evidence. |
| Input | New bundle/policy, all source motions and model. |
| Output | 35-row core/endpoint report and blocked-word/affected-pair inventory. |
| Definition of done | Every word has a result and budget-completeness status; no omitted rows or TIMEOUT-as-pass; source defects separated from connector defects. |
| Verification | Check count/set, inject core limit/coupling/speed/geometry defects to test attribution, inspect both endpoint roles and verify source hashes unchanged. |
| Risks | Endpoint screening mistaken for full-core validation; protected defects may prevent some words passing without source revision. |
| Rollback | Retain failure evidence and revert new checker calls if needed; do not trim cores, edit sources or relax thresholds. |
| Parallelism | Yes; after P0-2, independently of P0-4/P0-5/P0-6 with separate files. |

### P0-4 — Add batch budgets and safe checkpoint controls

| Field | Instruction |
|---|---|
| ID / Priority / Task | P0-4 / P0 / Add batch budgets and safe checkpoint controls |
| Purpose | Bound broad scans without selecting from partially verified pools or allowing concurrent run writers. |
| Prerequisites | P0-1; new-policy integration depends on P0-2. |
| Actions | Add a batch driver: at most 16 pairs per batch, default soft wall budget 7,200 s and at least 5 GiB free disk; record final resource limits before execution. Stop at the next immutable attempt/verification checkpoint after exhaustion, retaining incomplete state; do not claim hard real-time cancellation. Forbid selection before all candidates are reviewed. Enforce one writer per run and zero prior verification backlog before a new batch. Record times, resources, commands and exit codes. Retain current planning methods/wall scheduling and explicitly document nondeterministic candidate pools; do not redesign the planner here. |
| Files/modules | src/sign_robot/pair_runner_v2.py:V2RunStore.run_pair/verify_pair/run_scan_v2/verify_run_v2; planned scripts/run_hospital35_batches.py and batch-control tests. |
| Input | Frozen batch format, existing immutable storage and work/time/disk budgets. |
| Output | Checkpoint-aware single-writer driver, resource logs and tests. |
| Definition of done | Budget stops produce no partial selection, loss or overwrite; re-entry handles saved evidence; completed failures are not misrepresented as retryable by resume. |
| Verification | Inject tiny budgets, interruption, low disk, verification backlog and concurrent writers; assert readable saved artifacts, incomplete status, no playback authorization and same-identity resume behavior. |
| Risks | Wall-clock variation can break incomplete-planning fingerprint replay; --max-pairs alone does not cap all candidate cost. |
| Rollback | Retain interrupted directories; on replay mismatch report and start a new version/run, never rewrite fingerprints; revert only the new driver if needed. |
| Parallelism | Yes; after P0-1, parallel with import/sequence work, owning pair_runner_v2.py exclusively; final integration is serial. |

### P0-5 — Generate sequence combinations lazily in the existing order

| Field | Instruction |
|---|---|
| ID / Priority / Task | P0-5 / P0 / Generate sequence combinations lazily in the existing order |
| Purpose | Make the 64-combination limit actually bound generation cost. |
| Prerequisites | P0-1; no new real run required. |
| Actions | Replace full-product sorting in combinations() with lazy enumeration of at most limit entries ordered by (sum(ranks), ranks). Preserve repeated edges, edge order, empty-pool and boundary behavior; do not silently truncate pools or rerank candidates. |
| Files/modules | src/sign_robot/sequence_assembly.py:combinations; tests/test_sequence_v1.py or a planned focused test file. |
| Input | Existing combination-order contract and small-pool reference implementation. |
| Output | Bounded combination function, ordering-equivalence and scale tests. |
| Definition of done | First 64 entries match exactly for small pools; requesting 64 from large pools never materializes the full product; existing sequence tests pass. |
| Verification | Test varied dimensions, unequal sizes, rank ties, repeated edges, empty pools and limit boundaries; inspect generated-state and memory bounds rather than relying only on fragile timing assertions. |
| Risks | Changing tie-break order and violating the existing selection contract. |
| Rollback | Restore only this function change, retain failed-test evidence and leave historical sequences intact. |
| Parallelism | Yes; parallel with P0-2/P0-3/P0-4; coordinate test-file ownership with P0-6. |

### P0-6 — Record per-case blockers and preserve sequence denominators

| Field | Instruction |
|---|---|
| ID / Priority / Task | P0-6 / P0 / Record per-case blockers and preserve sequence denominators |
| Purpose | Prevent failed edges from erasing a batch or inflating success by selecting only runnable cases. |
| Prerequisites | P0-1; integration depends on P0-2/P0-5. |
| Actions | Add per-case dependency checks in existing sequence CLIs/summaries: distinguish missing pair, incomplete planning, incomplete validation and no numerical candidate. Record blocked/not-run cases with fixed denominators. Validate identity before classifying dependencies; corrupt/stale identity still rejects the run. Include sequences in the P0-4 resource driver: at most8 cases per sub-batch, soft7,200 s per sub-batch, soft600 s per case including planning/validation, the existing64-combination cap and5 GiB disk floor. Stop at complete attempt/verification checkpoints; unprocessed cases remain NOT_RUN, interrupted attempts cannot be selected, and already complete passing selections remain valid. Resume in new output directories using same-identity checkpoint inventories that identify processed attempts; retain all retries. Keep P1-2 regression outputs separate; preregister P1-4 canonical outputs for all111 coverage cases, without adding or mixing regression counts. Implement cross-sub-batch aggregation in the new batch driver before freeze: read frozen case/sub-batch inventories and SHAs, use preregistered canonical output references, keep denominator111 and missing cases NOT_RUN. Reject duplicate-case identity/content conflicts; no last-write-wins or best-outcome selection. Update independent summaries so blocked/unverified cases are not passes or universal agreement. Rendering uses valid selections within the sub-batch budget and reports a separate media denominator. |
| Files/modules | scripts/plan_sequences.py, scripts/verify_sequences.py and render_sequences.py if needed; sequence_contract.py/sequence_assembly.py:load_candidate_pools; cross-sub-batch aggregation in the planned driver, focused tests. |
| Input | Frozen cases and complete/missing/failed pools from one pair run. |
| Output | Per-case blockers and total/pass/fail/blocked/not-run counts with tests. |
| Definition of done | Partial edge failure still yields a complete case inventory; each frozen case appears exactly once; no cross-run pools; corrupt identity cannot be downgraded to ordinary blocked status. |
| Verification | Mixed pass/missing/incomplete/no-candidate fixtures, corrupted identity/source-SHA negatives and original12-case compatibility. Inject small case/sub-batch budgets and low disk; test checkpoint stops, NOT_RUN, no partial selection, new-directory recovery, canonical-reference aggregation and conflicting/stale sub-batch SHA rejection; separate renderer and experiment counts. |
| Risks | Swallowing integrity errors or mislabeling blocked as numerical failure/complete validation. |
| Rollback | Revert new reporting/call changes, retain evidence and previous API behavior; never rewrite old results. |
| Parallelism | Yes; after P0-1 parallel with non-sequence work; merge with P0-5 serially and review shared files. |

### P0-7 — Freeze batches, 111 cases, tests and final identity

| Field | Instruction |
|---|---|
| ID / Priority / Task | P0-7 / P0 / Freeze batches, 111 cases, tests and final identity |
| Purpose | Ensure regression and expansion use one tested version. |
| Prerequisites | P0-2 through P0-6 completed and reviewed; P0-3 diagnostics classified. |
| Actions | Freeze disjoint 4+33+132+1056 pair groups below (≤16 per batch). Create a sequence policy with original 12+new 99=111 cases, binding the new pair-policy file SHA while retaining 2–5 words and existing numerical/validation limits. Record root blockers, batch resources and stops. Include new import/preflight/batch/cross-sub-batch aggregation scripts in code identity. Complete required bilingual TASK indices and project_overview.py hash maintenance first. Run focused and full tests with stdout/stderr/commands/exit codes, rerun all35-word preflight checks under the final code and confirm matching input/code identity (earlier P0-3 output is development diagnosis only), then freeze code, tests, policies, inputs, environment and case-list SHAs. |
| Files/modules | pair_contract.py:freeze_library/run_identity; sequence_contract.py:sequence_identity; planned config/sequence_policy_hospital35_v1.json, batches/*.json, case_manifest.json; tests, docs/README.md/.en.md and src/sign_robot/project_overview.py. |
| Input | All reviewed implementation, 35-word protections, batches and case definitions. |
| Output | Complete test logs, code/input identity, frozen 1225-pair inventory and 111-case sequence policy. |
| Definition of done | No duplicate/missing pairs; exactly 111 cases; tests pass and new script changes alter identity; formal flags off and thresholds unchanged; no later code/test/index-hash edits. |
| Verification | Assert union/intersections, case/occurrence counts and script-hash tamper rejection; focused then full pytest; CLI --help; diff review and recomputed freeze inventory. |
| Risks | Late index/hash maintenance invalidating runs; treating historical test counts as the new acceptance target. |
| Rollback | Before freeze restore task-scoped backups; after freeze retain runs and create a new version for required code changes, never rewrite identities. |
| Parallelism | No; final integration, testing and identity freeze are serial. |

### P1-1 — Rerun four regression pairs with the new protection ranges

| Field | Instruction |
|---|---|
| ID / Priority / Task | P1-1 / P1 / Rerun four regression pairs with the new protection ranges |
| Purpose | Validate the new NOW range and full bundle against baseline transitions. |
| Prerequisites | P0-7; the full35-word context has no global input/binding/loading blocker. Report per-word source-quality failures separately from global loading errors. |
| Actions | Create a unique pair run for COME__NOW, NOW__COME, COME__COME, NOW__NOW. Independently review all saved candidates before selection; save a fresh verify_saved_pair_v2 recheck for each selected candidate rather than rerunning a CLI that skips COMPLETE records. Record counts, selection and differences from historical results. |
| Files/modules | scripts/plan_all_pairs.py, scripts/verify_all_pairs.py; pair_verification_v2.py:verify_saved_pair_v2; new pair_runs/. |
| Input | Final frozen new policy/identity and 4 pair IDs. |
| Output | Candidates, complete validations, fresh selected rechecks and logs for 4 pairs. |
| Definition of done | Progress gate: 4/4 numerical passes with complete validation and preserved cores, formal still 0; otherwise record blockers and failures, never substitute historical results. |
| Verification | Recompute denominators, passes and candidate counts from saved JSON; verify new policy/bundle SHA, COME/NOW cores and source hashes; require fresh recheck agreement. |
| Risks | Changed ranges alter outcomes, wall-clock effects alter pools, or old identity is reused incorrectly. |
| Rollback | Retain failed new run; fixes require a new version/run, not overwritten history or altered user cores. |
| Parallelism | No; one run writer, then validation, then fresh recheck. |

### P1-2 — Regress 12 sequences and render comparison videos

| Field | Instruction |
|---|---|
| ID / Priority / Task | P1-2 / P1 / Regress 12 sequences and render comparison videos |
| Purpose | Validate assembly, whole-chain checks and displayed replay under the new NOW range. |
| Prerequisites | P1-1 passes. |
| Actions | Explicitly select the original 12 cases from the new sequence policy, using only the new single pair run. Plan, independently recheck and render two-view videos with occurrence/protected/retained/cut/added labels. Compare protected poses and timing in the actual video replay per occurrence. |
| Files/modules | scripts/plan_sequences.py, verify_sequences.py, render_sequences.py; new sequences_regression_001/ and videos_regression_001/. |
| Input | New sequence policy, completely verified pools for 4 pairs and 12 case IDs. |
| Output | Trajectories, independent rechecks, core comparisons, videos and logs for 12 cases. |
| Definition of done | 12/12 numerical passes, 44/44 protected occurrences bitwise unchanged, relative timing≤1e-12 s, 32 connector groups; 12 identity-matched videos; formal 0. |
| Verification | Independent saved-file rechecks and JSON counts; middle cores appear once and repeated words have distinct occurrences; labels use COME f132 and NOW f51; inspect contact sheets. |
| Risks | Omitting --case attempts 111 cases prematurely; old NOW f76 videos may be reused incorrectly. |
| Rollback | Retain failures and new output; never overwrite old sequence/recheck/media directories; do not advance the expansion gate on failure. |
| Parallelism | No; depends on pair regression, then planning→verification→rendering serially. |

### P1-3 — Cover all 1,225 pairs in frozen batches

| Field | Instruction |
|---|---|
| ID / Priority / Task | P1-3 / P1 / Cover all 1,225 pairs in frozen batches |
| Purpose | Measure engineering coverage of arbitrary ordered word pairs against the full denominator. |
| Prerequisites | P1-2 passes; budgets, preflight and batches are frozen. |
| Actions | Expand the same new run with 33 remaining self pairs, 132 directed hub edges, then 1056 other non-self edges. Each batch≤16: plan→independent validation→summary→clear backlog→next. Resume only unfinished same-identity work; --resume does not retry completed failures. Retain failures, source blockers, TIMEOUT and NOT_RUN; no concurrent run writers. |
| Files/modules | Existing plan_all_pairs.py/verify_all_pairs.py/summarize_all_pairs.py, P0-4 driver, batches/*.json and the same pair_runs/. |
| Input | Frozen batches, new 35-word protections and one final code/model/environment identity. |
| Output | 1225-row matrix, resource logs, candidates/validations and failure-cause table. |
| Definition of done | Full-path coverage requires planning and independent review records for all 1225 pairs, allowing explicit failures/diagnoses. Universal numerical usability separately requires 1225/1225 numerical passes. Report all shortfalls; scan completion is not universal success. |
| Verification | Reconcile denominators 1225/1190/35; report planned, NOT_RUN, numerical pass/fail, validation incomplete, DIAGNOSIS_ONLY and formal 0; check all-candidate review and frozen-batch union. |
| Risks | Runtime/disk growth, many pairs affected by source defects, no-candidate diagnosis mistaken for trajectory success, verifier processes old backlog first. |
| Rollback | Stop at a safe checkpoint and retain complete/incomplete evidence; algorithm/budget changes require new version/run, not a swapped policy. |
| Parallelism | No; one serial run writer; read-only review of sealed output may run concurrently. |

### P1-4 — Execute the frozen 111-case sequence coverage

| Field | Instruction |
|---|---|
| ID / Priority / Task | P1-4 / P1 / Execute the frozen 111-case sequence coverage |
| Purpose | Check middle occurrences, repeated words and bidirectional combinations across the vocabulary. |
| Prerequisites | P1-3 completed or explicitly stopped at a budget checkpoint; required edge states known; P0-6 blocker reporting available. |
| Actions | Process all 111 frozen cases in new outputs without dropping blocked cases; report original 12 and added 99 separately. Run sub-batches of≤8 within P0-6 case/sub-batch/disk budgets, using separate outputs; aggregate by frozen recovery rules and IDs, deduplicate and retain NOT_RUN. Independently recheck successes and record failed/missing dependencies. Report media coverage separately and provide new-word videos for later semantic viewing. Use pools from one pair run. |
| Files/modules | New sequence policy/case_manifest, extended sequence CLIs, independent_recheck, videos and coverage aggregation. |
| Input | 111 frozen cases, verified pools and failure states from the same run. |
| Output | 111-case status table, per-occurrence protection evidence and sequence/media inventories. |
| Definition of done | All 111 cases have status; if all pass, totals are 341 occurrences and 230 connector groups, protected poses unchanged and timing≤1e-12 s. Blocked/failed cases preclude a 111/111 pass claim. |
| Verification | Check 12+33×3=111, 44+99×3=341, 32+99×2=230; reconcile artifacts, independent evidence and media with frozen denominators; rerun middle/repeated-word tamper regressions as needed. |
| Risks | Targeted engineering coverage is not all 35³ triples, all five-word chains or ASL sentences; pools may still be costly. |
| Rollback | Retain failed/blocked sub-batches and complete the aggregate without replacing hard cases; code/policy changes require a new version, not overwritten batches. |
| Parallelism | No by default; serialize sub-batches within resource limits; sealed results may receive parallel read-only review. |

### P1-5 — Review delivery evidence and update bilingual state

| Field | Instruction |
|---|---|
| ID / Priority / Task | P1-5 / P1 / Review delivery evidence and update bilingual state |
| Purpose | Deliver auditable progress, failure causes and next actions. |
| Prerequisites | Earlier execution finished or reached an explicit blocker/budget checkpoint. |
| Actions | Independently review diffs, logs, JSON, core/media comparisons and test exit codes; verify unchanged old assets/workbook/historical runs. Complete preregistered bilingual TASK, STATE/HANDOFF and actual commands; do not edit frozen source/tests/index hashes at this stage. Record semantic, cross-group and formal-acceptance gaps without inventing human review. |
| Files/modules | Preregistered TASK-XX.md/.en.md, STATE.md/.en.md, HANDOFF.md/.en.md and new-run evidence; leave TASK-26 historical. |
| Input | Execution diffs, all success/failure logs, final hash inventory, tests and rechecks. |
| Output | Bilingual execution report, acceptance matrix, remaining work and reproduction commands. |
| Definition of done | Separate facts/plans, old/new versions and numerical/formal status; bilingual numbers match; every incomplete item has denominator/reason/minimal reproduction; protections and historical assets remain intact. |
| Verification | Final scope/hash audit, document-link checks and fresh aggregation from saved JSON; independent review rather than relying solely on executor claims. |
| Risks | Scan completion mislabeled universal usability, videos mislabeled hardware readiness, old test reports mislabeled current runs. |
| Rollback | Restore only this task’s documentation changes after checking post-write hashes; retain all execution evidence; no reset/clean. |
| Parallelism | No; root integrates the final result, with delegated read-only review. |


## Frozen coverage and acceptance

| Stage | New pairs | Cumulative | Frozen definition |
|---|---:|---:|---|
| Regression | 4 | 4 | Four COME/NOW ordered pairs |
| Other self pairs | 33 | 37 | Each other word with itself |
| Directed hub edges | 132 | 169 | For every other w: COME→w, w→COME, NOW→w, w→NOW |
| Other non-self pairs | 1,056 | 1,225 | 33×32 ordered pairs among remaining words; policy order, 66 batches of 16 |

Pair files use `{"pair_ids":["SOURCE__TARGET", ...]}`; split the 33 and 132 groups into batches of at most 16 too. All four groups must be disjoint and cover the full universe. Freeze cases before viewing results: original 12 plus `COME__w__NOW`, `NOW__w__COME`, `w__w__w` for each remaining w, adding 99 for 111 total. Complete success would comprise 341 occurrences and 230 connector groups; do not count blocked/not-run occurrences as protected checks. This is targeted engineering coverage only.

Each protected occurrence must retain bitwise-identical poses, order and relative timing within 1e-12 s. Each middle occurrence uses one source slice covering its whole core; connector coefficients/durations are copied unchanged with only shifted start time. Retain v5 per-transition limits: acceleration120 rad/s², jerk3000 rad/s³, squared-jerk integral1,000,000 rad²/s⁵, connector≤6 s. Whole-chain limits/speed/coupling/boundaries/sampled geometry still apply. Internal core acceleration/jerk and chain-total integral remain informational; do not change scoring to obtain passes.

Acceptance has two levels: **execution coverage** permits explicit failed diagnoses but requires fixed denominators and independent records; **numerical completion of the user goal** requires valid connections for 1,225/1,225 pairs. If short, deliver actual gaps and a next-version failure-repair plan without claiming arbitrary-pair success. Formal acceptance stays separately disabled.

## Key files, interfaces and commands

Existing: `pair_windows.py:load_user_protections`, `pair_contract.py:freeze_library/run_identity`, `pair_routes.py:build_pair_context_v2`, `pair_runner_v2.py:V2RunStore`, three `src/sign_robot/sequence_*.py` modules and `scripts/{plan,verify,render}_sequences.py`. `load_candidate_pools` accepts one run; do not mix historical/new runs. `freeze_all_pairs_inputs.py` still uses the v1 path and cannot preflight the new protection policy unchanged; this plan adds a v2 preflight entry.

Import/preflight/batch entry points and configurations marked “planned” above do not exist yet. Implement them and inspect `--help`; do not invent runnable interfaces. These templates use existing CLIs; new configs/outputs are only valid after P0. If a run name is occupied, register a new name in P0-1 and update every reference consistently. The new policy contains 111 cases, so regression explicitly lists 12 `--case` flags.

```bash
cd /home/kingderman/Documents/ME5412-github-latest
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
git status --short
git branch --show-current
git rev-parse HEAD
.venv/bin/python scripts/plan_all_pairs.py --help
.venv/bin/python scripts/verify_all_pairs.py --help
.venv/bin/python scripts/plan_sequences.py --help
.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_user_protected_windows.py tests/test_user_protected_correction.py tests/test_pair_runner_v2.py tests/test_lift_off_arrival_v5.py tests/test_sequence_v1.py
.venv/bin/python -m pytest -q -p no:cacheprovider tests
```

```bash
.venv/bin/python scripts/plan_all_pairs.py \
  --library hospital_v1 --include-self \
  --policy config/transition_policy_user_protected_hospital35_v1.json \
  --run-id hospital35_protected_20261101_001 \
  --results-root results/hospital35_protected_20261101_001/pair_runs \
  --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW
.venv/bin/python scripts/verify_all_pairs.py \
  --run-id hospital35_protected_20261101_001 \
  --results-root results/hospital35_protected_20261101_001/pair_runs --max-pairs 4
```

```bash
.venv/bin/python scripts/plan_sequences.py \
  --sequence-policy config/sequence_policy_hospital35_v1.json \
  --pair-run-dir results/hospital35_protected_20261101_001/pair_runs/hospital35_protected_20261101_001 \
  --output results/hospital35_protected_20261101_001/sequences_regression_001 \
  --case COME__COME__COME --case COME__COME__NOW \
  --case COME__NOW__COME --case COME__NOW__NOW \
  --case NOW__COME__COME --case NOW__COME__NOW \
  --case NOW__NOW__COME --case NOW__NOW__NOW \
  --case COME__COME__COME__COME__COME \
  --case NOW__NOW__NOW__NOW__NOW \
  --case COME__NOW__COME__NOW__COME \
  --case NOW__COME__NOW__COME__NOW
.venv/bin/python scripts/verify_sequences.py \
  --run-dir results/hospital35_protected_20261101_001/sequences_regression_001
.venv/bin/python scripts/render_sequences.py \
  --run-dir results/hospital35_protected_20261101_001/sequences_regression_001 \
  --output results/hospital35_protected_20261101_001/videos_regression_001
```

```bash
.venv/bin/python scripts/plan_all_pairs.py \
  --library hospital_v1 --include-self \
  --policy config/transition_policy_user_protected_hospital35_v1.json \
  --run-id hospital35_protected_20261101_001 \
  --results-root results/hospital35_protected_20261101_001/pair_runs \
  --resume --pairs-file results/hospital35_protected_20261101_001/batches/rest_001.json \
  --max-pairs 16
.venv/bin/python scripts/verify_all_pairs.py \
  --run-id hospital35_protected_20261101_001 \
  --results-root results/hospital35_protected_20261101_001/pair_runs --max-pairs 16
.venv/bin/python scripts/summarize_all_pairs.py \
  --run-id hospital35_protected_20261101_001 \
  --results-root results/hospital35_protected_20261101_001/pair_runs
```


Add actual new import, preflight, budget, enumeration and blocker tests to focused validation. Execute commands through the P0-4 budget driver and record stdout/stderr and exit codes. Use the `rest_001` template only after the 33-self and 132-hub groups. Batch verification has no `--pairs-file`: clear prior backlog first and set `--max-pairs` to the actual new pending count. Repeated verification skips COMPLETE and does not replace P1-1 fresh selected rechecks. Never overwrite old outputs; another sequence recheck also needs a new evidence location or output, after inspecting actual script behavior.

## Rules, risks, human decisions and rollback

- Validate each task before its dependents. Report concrete structure differences first while continuing unaffected work. Keep planned work separate from completion; no scope expansion or unrelated refactors.
- Use real `gpt-6.1-sol`, `max` subagents for scoped implementation/testing/read-only review; root integrates. No recursive delegation, concurrent file edits or multiple writers to one run.
- Preserve source motions, models, original ODS, old policies and historical runs. No reset/clean/push, publishing or hardware. Version strategy/budget changes; never rewrite old identities, overwrite failures or inherit historical pass flags.
- High risks: wrong source/frame, global input blockers, core defects, combination explosion, partial-pool selection, wall-clock replay mismatch, late index changes invalidating identity, and counting only assemblable cases. P0 tests and denominator audits must cover these.
- Human decisions concern real semantic ambiguity, required protected-source changes or final cross-group/semantic review; provide exact words, frames, videos and evidence. Engineering owns endpoints, budgets and transition parameters. Do not request technical-window approval or pretend development runs satisfy formal human review.
- Irreversible operations: none required. Historical deletion, original-asset changes, publishing/merging and hardware are outside this handoff.
- Roll back per-file from P0-1 backups only after confirming current files still match task post-write hashes. Revert only task changes; retain failed runs, inputs, logs, last successful checkpoints and minimal reproduction commands. TIMEOUT is not proof of infeasibility.

## Minimum viable and full paths

Minimum: P0-1–P0-7→P1-1→P1-2→interim P1-5. This delivers bound 35-word input, full-word preflight, resource/failure handling and genuine new-range 4-pair/12-sequence regression, not full-library completion. Full path continues P1-3→P1-4→final P1-5 for all1,225 pairs and111 frozen sequences. Repair failed edges in a new version based on actual causes; do not guarantee first-pass success. More than2–5 words, neutral, semantic acceptance and hardware require subsequent independent tasks.

## Required completion report

1. Changed/added files and hashes proving original assets unchanged.
2. Every task’s completed, failed, blocked or not-run status and reason.
3. Actual commands, parameters, branch/HEAD/working-tree identity, environment, output paths and exit codes.
4. Raw focused/full test logs, independent rechecks, fixed denominators, numerical/formal status and per-word protection/media checks.
5. Deviations, budget stops, candidate changes, missing/diagnosis records and minimal reproduction.
6. Remaining risks, specific human judgments needed and next-stage recommendations.

## Plan self-review

Resolved omissions: no waiting for the 35-word input; new NOW invalidates reuse of old results; sequence support already exists; exact35 coverage, core preflight, Cartesian-product cost, per-case blockers, budgets and index hashes all precede final freeze. Focus tests on formulas/wrong sources, unfixable protected defects, repeated middle occurrences, partial verification recovery, integrity failures not downgraded to blockers, and saved-evidence inspection versus genuine revalidation. STATE retains unverified risks; this plan promises neither universal success, continuous collision certification nor semantic correctness.

========== HANDOFF END ==========
