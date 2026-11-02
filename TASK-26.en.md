# TASK-26 — COME/NOW multi-word sequence pilot

[中文](TASK-26.md) · [Current state](STATE.en.md) · [Handoff](HANDOFF.en.md) · [Previous v5 report](TASK-25.en.md)

**All 12 frozen engineering cases pass numerically (12/12). A fresh independent recheck agrees on all 12. Formal PASS_SIM is still 0.** Totals: 44/44 word occurrences have bitwise-unchanged protected poses, 32 connector groups, 8/8 three-word cases and 4/4 five-word stress cases. 836 tests pass (812 + 24 new). Executed 2026-10-31 to 11-01 (Asia/Shanghai), following HANDOFF P0-1 → P1-4.

These are kinematic engineering cases, not ASL sentences and not an independent semantic test set. No person has watched them; nothing ran on hardware.

## Task status

| Task | Status | Evidence |
|---|---|---|
| P0-1 Freeze baseline and cases | Done | `results/sequence_pilot_20261031_001/P0-1/`: git HEAD/status, backups and hashes of files to be edited, run 002 identity check (70 code / 144 input files equal), code-freeze hashes |
| P0-2 Sequence contract and scoring | Done | [sequence_policy_user_protected_v1.json](config/sequence_policy_user_protected_v1.json), `src/sign_robot/sequence_contract.py`; frozen before any sequence was verified |
| P1-1 One slice per occurrence | Done | `src/sign_robot/sequence_assembly.py`, `scripts/plan_sequences.py` |
| P1-2 Independent chain verifier | Done | `src/sign_robot/sequence_verification.py`, `scripts/verify_sequences.py`; does not import the assembler or planners |
| P1-3 Fresh run, 12 cases, videos | Done | `results/sequence_pilot_20261031_001/` |
| P1-4 Review and docs | Done | This report, STATE/HANDOFF, docs index |

## Sequence contract (development v1)

- **Representation:** a separate `user_protected_sequence_v1`. Pair v2 still rejects three words; a test covers this.
  - **Words:** each sequence has 2–5 occurrences. Each occurrence gets a unique ID (`o{position}_{GLOSS}`) and a position number. It starts on the first word's protected core and ends on the last word's; there is no implicit neutral pose.
  - **Edges:** each edge records the source pair run, attempt, candidate file SHA-256 and trajectory hash, plus the exit/entry frames, finger strategy and boundary.
  - **Identities:** two are recorded separately. The pair identity is the candidates' source identity. The sequence identity covers the pair identity, the sequence-policy hash, and code from `src/`, `tests/` and the three new `scripts/*sequences.py` entry points. The pair code hash collects only a fixed script list, so the sequence identity adds the new scripts explicitly; a test checks that changing them changes the identity.
- **Assembly:**
  - **Connectors:** only the pair candidates' connectors are reused. Coefficients and durations are copied, and only the start time shifts.
  - **Slices:** the first word uses the first pair's source slice and the last word the last pair's target slice. A middle word uses one source slice from the incoming entry to the outgoing exit, so its protected core appears once.
  - **Fallback:** if a chain failed, the assembler would try at most 64 combinations of independently passing candidates, ordered by rank sum. It was not needed; every case passed with the first-ranked combination.
- **Scoring (frozen before any results):**
  - **Regions:** each transition is scored over the replay frames strictly between the previous core's end and the next core's start. That is the retained tail, the connector and the retained head. The regions are disjoint, and together they exactly cover the frames outside protected cores (the verifier asserts both).
  - **Per-transition limits:** each transition must meet v5's limits on its own: acceleration 120, jerk 3000, squared-jerk integral 1,000,000, and connector duration ≤ 6 s. Each connector is also checked analytically on its own.
  - **Chain totals:** the total integral is reported only. Limits, coupling, speed, boundaries, finger phases and sampled geometry are checked over the whole chain. Acceleration and jerk inside protected cores stay informational, as in v5.
- **Budget:** the pair budget is kept, except wall time goes from 30 s to 120 s, set before running. Actual worst case: 9,114 poses and 16.2 s.
- **Formal status:** shown separately. `ALGORITHM_WINDOWS_NOT_HUMAN_REVIEWED` is old wording from the automatic-window era. It is listed only under `legacy_formal_wording_not_a_precondition` and is not treated as a precondition on the user's protected intervals.

## Fresh pair run `sequence_pilot_pairs_20261031_001`

| Pair | Candidates / numerical pass | Selected | Compared with run 002 |
|---|---:|---|---|
| COME→NOW | 7 / 7 | attempt_00016 | Same selection, identical curves |
| NOW→NOW | 8 / 8 | attempt_00015 | Same selection, identical curves |
| NOW→COME | **18 / 18** | **attempt_00013** | **Differs.** Run 002 had 17/17 and selected attempt_00023 |
| COME→COME | 13 / 13 | attempt_00003 | Same selection, identical curves |

**Deviation:** NOW→COME attempt_00013 (ik_via2) hit `TIMING_WALL_TIME_LIMIT` in run 002 after 16.1 s of its 30 s wall-clock budget. This time it completed, became an 18th candidate, and was ranked first by the frozen selection rule. **Pair candidate pools therefore depend on machine load through wall-clock budgets**, so a rerun is not guaranteed to be identical. The sequences use this fresh run's verified candidates; run 002 is unchanged.

## Twelve sequences `sequences_001`

All passed on attempt_0001 (every edge at rank 0) and were independently rechecked again. The values below are the worst case over each sequence's transition regions. Clearance is sampled, not continuous.

| Sequence | Duration s | Peak acc. | Peak jerk | Region integral | Analytic connector integral | Clearance mm |
|---|---:|---:|---:|---:|---:|---:|
| COME–COME–COME | 11.967 | 40.65 | 442.6 | 254,409 | 469,770 | 4.711 |
| COME–COME–NOW | 10.933 | 40.65 | 442.6 | 254,409 | 824,671 | 4.711 |
| COME–NOW–COME | 12.600 | 31.83 | 315.3 | 253,347 | 824,671 | 7.616 |
| COME–NOW–NOW | 10.133 | 28.60 | 269.4 | 162,442 | 824,671 | 4.418 |
| NOW–COME–COME | 12.567 | 40.65 | 442.6 | 254,409 | 469,770 | 4.711 |
| NOW–COME–NOW | 11.533 | 31.83 | 315.3 | 253,347 | 824,671 | 7.616 |
| NOW–NOW–COME | 11.767 | 31.83 | 315.3 | 253,347 | 580,753 | 4.418 |
| NOW–NOW–NOW | 9.300 | 28.60 | 269.4 | 162,442 | 580,753 | 4.418 |
| COME×5 | 20.433 | 40.65 | 442.6 | 254,409 | 469,770 | 4.711 |
| NOW×5 | 16.167 | 28.60 | 269.4 | 162,442 | 580,753 | 4.418 |
| COME–NOW–COME–NOW–COME | 21.700 | 31.83 | 315.3 | 253,347 | 824,671 | 7.616 |
| NOW–COME–NOW–COME–NOW | 20.633 | 31.83 | 315.3 | 253,347 | 824,671 | 7.616 |

- **Fresh recheck:** `independent_recheck/summary.json` reports 12 cases, 12 numerical passes, 44 occurrences, 44 unchanged protected instances, 32 connector groups and agreement with planning on all 12.
- **Protected timing:** the maximum relative timing error of any protected instance is 3.1e-15 s, within the 1e-12 s gate.
- **Per-transition metrics:** these match the corresponding pair results. The finite-difference stencil only reaches into the unchanged protected cores, so chaining does not change any transition's own numbers.
- **Chain total integral:** the highest total is 1,017,639 for COME×5. It is reported, not gated.

## Videos

All 12 are in `results/sequence_pilot_20261031_001/videos/<sequence>/comparison.mp4`. The top row shows the full original clips concatenated; the bottom row shows the sequence, with front and side views. Labels show the occurrence number, protected/kept/cut/added parts and the transition number. The renderer reruns the independent verifier first and checks protected instances against the replay used to draw the video: 44/44 are bitwise equal.

The execution model looked at the COME–NOW–COME–NOW–COME contact sheet. The labels and core end frames are correct (COME f132, NOW f76). This is not a human or group-2 review, nor an ASL comprehension check.

## Commands (all exit 0; 857 s total)

```bash
cd /home/kingderman/Documents/ME5412-github-latest
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
```

```bash
.venv/bin/python scripts/plan_all_pairs.py --library hospital_v1 --include-self --policy config/transition_policy_user_protected_v5.json --run-id sequence_pilot_pairs_20261031_001 --results-root results/sequence_pilot_20261031_001/pair_runs --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW --quiet
```

```bash
.venv/bin/python scripts/verify_all_pairs.py --run-id sequence_pilot_pairs_20261031_001 --results-root results/sequence_pilot_20261031_001/pair_runs
```

```bash
.venv/bin/python scripts/plan_sequences.py --pair-run-dir results/sequence_pilot_20261031_001/pair_runs/sequence_pilot_pairs_20261031_001 --output results/sequence_pilot_20261031_001/sequences_001
```

```bash
.venv/bin/python scripts/verify_sequences.py --run-dir results/sequence_pilot_20261031_001/sequences_001
```

```bash
.venv/bin/python scripts/render_sequences.py --run-dir results/sequence_pilot_20261031_001/sequences_001 --output results/sequence_pilot_20261031_001/videos
```

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_sequence_v1.py
```

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider tests
```

The log is in `results/sequence_pilot_20261031_001/P1-3.log`, with tables in `P1-3_tables.txt`.

- **Tests:** 24 sequence tests, 836 in the full suite.
  - **Contract:** 12 cases, pair-policy hash binding, rejection of empty, single-word and over-long input, and pair v2 still rejecting three words.
  - **Assembly:** a middle core appears once, connectors are copied unchanged, a two-word sequence replays identically to its pair, repeated words get distinct IDs, and reference mismatches are rejected.
  - **Rejection:** 8 malformed-contract cases, plus tampered connectors (including a contract-valid edit), stale candidate hashes, replaced candidates, stale code identity, wrong protection, retiming, a corrupt envelope, and budget exhaustion reported as TIMEOUT rather than a pass.
- **Identity:** the frozen pair code hash is `4080b98e73a121c866115882483ef5b7631532d9add4bed4ff5dfbe214ad9cef` (74 files). The sequence code hash is `1ecfcc9f95830071dfbffbb895cf4f664ca5aecd4b38398ceb91ececdea15bb0`. Any later code edit, including a docs-index re-pin, makes this run stale.

## Files

- **New:** `config/sequence_policy_user_protected_v1.json`, `src/sign_robot/sequence_{contract,assembly,verification}.py`, `scripts/{plan,verify,render}_sequences.py`, `tests/test_sequence_v1.py`, and TASK-26 in both languages.
- **Changed:** the docs index (one row in each language), the two docs-index hashes in `project_overview.py` (re-pinned before the code freeze), and STATE/HANDOFF in both languages.
- **Unchanged:** originals, the v5 policy, the protection bundle, models and historical results are not modified. The SHA-256 values of COME/NOW, the v5 policy and the protection bundle match P0-1. Backups are in `P0-1/backup/`.

## Unverified limits

- No person has watched the sequences. Whether the added transitions mislead, and whether the 12 cases stay understandable, is not checked. They are not ASL sentences.
- Formal PASS_SIM is 0. The v5 and sequence policies are development policies pending cross-review by the three groups.
- Collision is sampled, not continuous. Derivatives inside protected cores are not certified as continuous.
- Only COME/NOW were run. The other 33 words have no protected intervals, so their 1,221 pairs and any sequences using them are not run.
- There is no neutral start/end pose, no hardware run and no reproduction in a fresh environment.
- Wall-clock planning budgets make pair candidate pools depend on machine load, as the NOW→COME result above shows.
- Nothing is committed to git.

## Next step: protection inputs needed for the other 33 words

Each word needs a user-supplied protected interval (start and end seconds, or frames at 30 Hz, inclusive) for its current motion file before the 1,225-pair scan can extend beyond COME/NOW. Sources (all `motion_ready`):

- `motions/studio_galt_v1/`: HELLO, PLEASE, YOU, APPOINTMENT, BREATHE-DEEP, BLOOD-DRAW, TAKE, WHERE
- `motions/wlasl_video_v1/`: THANK-YOU, SORRY, YES, NO, YOUR, ME, DEAF, DOCTOR, NURSE, INTERPRETER, MEDICINE, STOMACH, HEADACHE, HAVE, NEED, WAIT, HURT, UNDERSTAND, WRITE, NOT, SOON, LATER, TOMORROW, MORNING, NIGHT

None were run in this round.
