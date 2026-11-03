# TASK-29: Switching to Group 2's new clips (clips-v2) and re-setting protection intervals

> **Public delivery, 2026-11-03:** the private round-10 result commit is `ec89a7f`. This requested update publishes its non-raw snapshot on public round-9 parent `83dffbfc`, including clips-v2 dependencies while retaining old results as history. Statements below that round 10 is not committed are superseded. The original run identity and its testing limits are unchanged.

[中文](TASK-29.md) · [Current state](STATE.en.md) · [Handoff](HANDOFF.en.md) · [Previous stage TASK-28](TASK-28.en.md)

Status: **protection bundle v5 is set; round 10 solved the nine sentences on the new clips, 7/7 NUMERICAL_PASS.** Executed 2026-11-02 (Asia/Shanghai). The clip review and bundle v5 came first, without solving, at the user's request; round 10 followed in the evening when the user said start (see "Round 10" below).

**Group 2 published new word clips on `group2/clips-v2` (`85bc230`) and asked Group 3 to continue on a branch made from it. In the new clips NURSE is a new motion and 23 other video-derived words were collision-repaired, all with unchanged frame counts. After watching renders, the user protected NURSE f23–f79, moved INTERPRETER to f19–f40, and kept HAVE and every other interval, giving protection bundle v5. The round-8 and round-9 trajectories on the old clips do not carry over; the nine sentences need re-solving on the new clips.**

Development evidence only: not verified ASL; the renders of the new clips have not been reviewed by anyone else.

## Branch

- This branch, `group3/clips-v2`, was made from `group2/clips-v2` at `85bc230`, which already holds round 8's planner code (the non-raw snapshot published to the team repository this morning and merged by Group 2).
- Round 9 (YOU HURT WHERE, HURT from frame 37) existed only on the local source branch `group3/trajectory-planning` and was brought here: the results directory `results/hospital_sentences_20261102_009/` (without raw pair stores), protection bundle v3, policy `fast_v6` and sequence policy `v8`. The project record (TASK-28, STATE, HANDOFF) is a three-way merge of the source branch's round-9 content and the publication edits.
- The meshes in `assets/robot/vendor/` are not tracked and must be copied or fetched separately on another machine.
- `models/all-MiniLM-L6-v2/` (Group 1's sentence-embedding weights, 88 MB) is not tracked either; without it `test_learned_motion` and `test_learning_api` fail.

## User decisions (2026-11-02, in order)

| Decision | Carried out |
|---|---|
| The new clips exist only on `group2/clips-v2`; branch from it (relayed from Group 2) | This branch, `group3/clips-v2` |
| New NURSE protected f23–f80, then changed to f23–f79 (frame 80 is the first frame of the last wrist tap, with the right thumb already on the left wrist; that tap is dropped) | Protection bundle v4 |
| For the other collision-repaired words, first check whether the poses at the old intervals' start and end frames still match | 17 of 23 words identical at both ends; 6 differ at finger level, of which the sentence words are HAVE (end f54) and INTERPRETER (start f30) |
| After renders of these two words: INTERPRETER f19–f40, HAVE keeps f24–f54 | Protection bundle v5 |
| No new trajectory solving for now; upload everything the next solving step needs to `Kingderman/ME5412-Project` | This branch pushed there |
| Evening: start solving on `group3/clips-v2` with 12 threads; run without fixing the failing tests first; drop NURSE's staged exit | Round 10 (`results/hospital_sentences_20261102_010/`) |

## Protection bundle v5 (`config/user_protected_hospital35_v5.json`)

| Word | v3 (old clips) | v5 (clips-v2) |
|---|---|---|
| NURSE | f38–f75 | **f23–f79** |
| INTERPRETER | f30–f60 | **f19–f40** |
| HAVE | f24–f54 | f24–f54 (kept) |
| HURT | f37–f57 | f37–f57 |
| MORNING | f26–f37 | f26–f37 |
| The other 30 words | The user's sheet intervals | Unchanged |

v4 was written from v3 (NURSE replaced, the 24 changed clips re-bound) and v5 from v4 (INTERPRETER replaced); both load with the planner's own loader against this branch's motion library (35/35). The generators, per-frame checks, comparison images and notes are in [`results/clips_v2_review_20261102/`](results/clips_v2_review_20261102/README.en.md).

## What the next solving step needs (all on this branch)

- Code: `src/`, `scripts/` (round 8's planning and verification code, unchanged in this stage); `tests/` fixed for the new clips (see "Tests").
- Clips and library: `motions/` (clips-v2) and `motions/hospital_v1_motions.json`.
- Protection bundle v5 and the starting policies `config/transition_policy_hospital_sentences_fast_v5.json` and `config/sequence_policy_hospital_sentences_v7.json`.
- Round 8's inputs and run scripts ([`results/hospital_sentences_20261102_008/`](results/hospital_sentences_20261102_008/README.en.md): `make_inputs.py`, `run.sh`, `export_render_inputs.py`, `render_gpu_windows.py`) and round 9's single-sentence variant ([`…_009/`](results/hospital_sentences_20261102_009/README.en.md)).
- Steps, the NURSE exit redesign and the known endpoint issues: the top section of [HANDOFF](HANDOFF.en.md).

## Round 10: the nine sentences on the new clips

[Round 10](results/hospital_sentences_20261102_010/README.en.md) ran 18:31–20:18 with 12 pair runs on cpu0–11, code `00124363` unchanged. Pair policy `fast_v7` is `fast_v5` with bundle v5, NURSE removed from `staged_exits` and round 9's longer search (1800 s per pair); sequence policy `v9` has the seven multi-word sentences.

- 17/17 pairs pass numerically and agree on fresh rechecks; 7/7 sentences NUMERICAL_PASS and agree on the fresh sequence recheck; 24/24 protected cores bitwise unchanged; 0 interior stops; every sentence ends at rest.
- NURSE→BLOOD-DRAW passes as a direct 10-frame connector from f79, so the staged exit did not need a redesign. NEED→INTERPRETER enters at f14 and HAVE's rest tail leaves at f57, as the endpoint checks required.
- Frames between protected cores across the 17 connectors: 263 (round 8 on the old clips: 310). MEDICINE→MORNING's minimum clearance is exactly 2.0 mm, as in round 8.
- Not watched by a person. It ran on `00124363` with the old, failing tests (user's choice); the test fix `a1eb6e53` was pushed at 18:48, while round 10 was running. The run can only be resumed or rechecked at `00124363`.

## Not done yet

- Someone watching the round-8, round-9 and round-10 videos.
- A run on the fixed tests (`a1eb6e53` or later) needs a new round with round 10's inputs.
- Committing round 10 (inputs, records and documents); only when the user asks.

## Tests

At the start of this stage the full suite gave 988 passed, 16 failed and 18 errors, identical item by item on an untouched `85bc230` (`group2/clips-v2` as published). After the fix for the new clips on 2026-11-02: **1021 passed, 1 skipped** (exit 0). `src/`, `scripts/` and `config/` are unchanged.

| Cause | Count | Fix |
|---|---|---|
| The tests' old policies point at protection bundles v1–v3, which bind the old clip hashes; the loader rejects them (`STALE_USER_PROTECTION_MOTION`) and later steps fail in turn | 21 | New `tests/clips_v2.py` rebinds an old policy to bundle v5 in memory, other fields unchanged and no policy file rewritten. `test_hospital35_preflight`, `test_connector_only_v4`, `test_rest_tail_v1` and `test_staged_exit_v1` use it; NURSE's staged exit now starts at v5's core end f79 |
| Old NURSE frames and joints written into the tests | 4 | The three tests of the wrist flip after the core use a copy of the old NURSE clip, `tests/data/NURSE_hospital_v1.npz` (23 KB, from git history, hash `f75945f0…`, the one the old policies recorded). The exit-window test uses the new NURSE: it reaches a joint limit at f90–94 and the v2 rules keep only f79 and f86–90 (at f80–85 the right thumb is on the left wrist, too little clearance). `test_all_pairs_pipeline`: the old research endpoints are stale on the new clip (`STALE_INPUT_HASH`); rebound to the current clip they are still only proposed, never scanned |
| Rebuilding v1 from the original sheet no longer matches byte for byte | 3 | Now checks that the rebuild differs from the installed v1 only in `motion_sha256` of the 24 replaced clips (equal to v4's binding) and the hashes that follow; `--check` reports the three v1 files as different (exit 1) and does not rewrite them |
| Reading raw run stores that are not tracked | 1 | Skipped when the file is absent (the one skip) |
| Group 1's learning module | 5 | Not a code problem: the new checkout lacked the MiniLM sentence-embedding weights `models/all-MiniLM-L6-v2/` (not tracked, 88 MB). Passes after copying them from the original checkout; tests unchanged |

Round 10 ran on `00124363`, before this fix (pushed at 18:48, while round 10 was running), so its code hash includes the old tests; a run on the fixed tests needs a new round.

## Unverified limits

- Self-clearance is sampled per frame, not a continuous-collision proof; contact uses the planner's collision scope and the 2 mm threshold.
- The new clips' sign meaning is not certified; the protection intervals are the user's, set from renders.
