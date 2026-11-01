# TASK-27: 35-word protection import and library-wide transition run

[中文](TASK-27.md) · [Current state](STATE.en.md) · [Handoff](HANDOFF.en.md) · [Previous TASK-26](TASK-26.en.md)

Status: **staged report (P1-5 interim); P1-3 is still running.** Executed 2026-11-01 (Asia/Shanghai) following the HANDOFF order P0-1 → P0-7 → P1-1 → P1-2 → P1-3. This file was created before the code freeze so the documentation-index hashes could be maintained first; results were filled in after the freeze without touching frozen source, tests or the index.

**The 35 protected intervals are imported strictly and frozen. Under the new protection the regression passes: 4/4 pairs (76/76 candidates) and 12/12 sequences. Fresh rechecks agree, and 44/44 protected instances are unchanged. The preflight, however, shows that 24 of the 35 protected cores fail a non-waivable gate in the source motion itself. Under the current inputs and gates, 1,104 of the 1,225 pairs therefore cannot pass whatever connector is planned. The library-wide scan (P1-3) is running in frozen batches to record the actual results, and going further needs a decision outside engineering.** Tests: 962 passed (836 + 126 new). Formal PASS_SIM is 0.

These are kinematic engineering checks, not ASL sentences or an independent semantic test set. Nobody has watched the videos; nothing ran on hardware; formal PASS_SIM is 0.

## Task status

| Task | Status | Evidence |
|---|---|---|
| P0-1 Freeze baseline, sheet and sources | Done | `baseline/`: branch/HEAD, `git status` (5,672 lines), tracked diff, 31 backed-up files with SHA-256, hash inventory of `results/` (11,546 files), `motions/`, `config/`, `contracts/`, `assets/robot/`; source manifest of the 35 selected motions (9 mocap, 26 video) |
| P0-2 Strict 35-word import | Done | `scripts/import_user_protections.py`; bundle, policy and provenance in `config/`; byte-identical ODS copy in `data/user_protection/hospital35_20261101/` |
| P0-3 Core and endpoint preflight | Done; **24 words source-blocked** | `scripts/preflight_hospital35.py`; `preflight_dev_001/` (development) and `preflight_final/` (frozen code); identical word results |
| P0-4 Batch budgets and single writer | Done | `src/sign_robot/batch_control.py`, `scripts/run_hospital35_batches.py pairs/recheck-pairs` |
| P0-5 Lazy combinations | Done | `sequence_assembly.combinations` |
| P0-6 Per-case blockers and sequence sub-batches | Done | `plan_sequences.py`, `verify_sequences.py`, `render_sequences.py`, `src/sign_robot/sequence_batches.py`, `run_hospital35_batches.py sequences/aggregate` |
| P0-7 Freeze batches, 111 cases, tests, identity | Done | `batches/` (79 files), `config/sequence_policy_hospital35_v1.json`, `sequence_cases/case_manifest.json`, `freeze/freeze.json` |
| P1-1 Four pairs, new protection | Done: 4/4 selected, 76/76 candidates pass, fresh recheck agrees 4/4 | `pair_runs/hospital35_protected_20261101_001/`, `P1-1/` |
| P1-2 Original 12 sequences and videos | Done: 12/12, recheck 12/12, 44/44 protected, 32 connector groups, 12 videos | `sequences_regression_001/`, `videos_regression_001/` |
| P1-3 1,225 pairs in frozen batches | **Running, not finished** (snapshot 10:47: 27/79 batches, 393/1,225 pairs reviewed; below); 1,225/1,225 numerically unreachable under current inputs | `P1-3.log`, `batch_control/`, `P1-3/` |
| P1-4 111 sequences | Not run: waits for P1-3 to end; all 169 pairs it needs are reviewed; upper bound 29/111 | `sequence_cases/case_manifest.json` (frozen) |
| P1-5 Review and bilingual docs | Staged: this report, STATE, HANDOFF, hash checks | `P1-5/` |

Paths without a prefix are under `results/hospital35_protected_20261101_001/`.

## P0-2 Import of the 35 protected intervals

- **Read:** only the stored `office:value` of sheet `保护区间填写`, A1:C36, of the ODS with SHA-256 `4fe5b3bb3f7d12cf4cd4418b8431325dec48fbed3c29a2a1e29447cdf89667e3` (the importer checks the hash first and refuses entity declarations). It rejects formulas, empty or non-numeric cells, non-finite values, a displayed value that differs from the stored one, unknown/duplicate/missing words, anything filled outside A1:C36, and `start ≥ end` or `end` beyond the last frame time.
- **Sources:** each word is bound to the actual `library`/`motion` in `motions/hospital_v1_motions.json` (the file must sit in its declared library and be named after the word), with its SHA-256, frame count and a 30 Hz timeline check.
- **Frames:** zero-based, both ends inclusive, `[floor(start×30), ceil(end×30)]` in Decimal arithmetic; the loader's float rule must give the same frames, otherwise the row is rejected. 35/35 rows agree; every row's rounding audit is in the provenance file.
- **Outputs (never overwritten; `--check` rebuilds them in memory byte for byte):**
  - `config/user_protected_hospital35_v1.json` (35 records, `retiming_allowed=false`, no invented video identities), SHA-256 `d19fec39dcc28dd54fa3d93260dbe0bcbec81062cd190669f74681c5172e3ae0`;
  - `config/transition_policy_user_protected_hospital35_v1.json`, a copy of v5 that changes only `policy_id`, the window version and the bundle path/hash, SHA-256 `d0bc6d9182a72bd1e13106c7732206083ae26acc377f8b60829ed431a5bc59c1`;
  - `config/user_protected_hospital35_v1.provenance.json` (sheet, cells, values, rounding audit, source binding).
- **Check:** COME [27,132] and NOW [27,51]; the real loader returns exactly the 35 words; old bundle, v5 policy and the COME/NOW motions are byte-identical to the baseline. The full table is in [STATE](STATE.en.md).

## P0-3 Preflight: 24 of 35 protected cores fail a non-waivable gate in the source itself

The preflight reads only original source samples inside each user-protected core; no planner is involved. Speed, joint limits and coupling are checked as the verifier checks them. Geometry is sampled exactly as the verifier samples word slices (1×/2×/4×, ≤1/120 s, ≤0.04 rad). Both endpoint roles are screened with the real endpoint selector. Acceleration and jerk inside cores stay informational, as in v5. No global input blocker was found, and every row completed within budget (no TIMEOUT).

**Result: 11 words clear, 24 with a source defect, 0 without a usable endpoint.**

- **Clear (11):** COME, DEAF, HEADACHE, NO, NOT, NOW, SOON, STOMACH, WAIT, WHERE, YOU.
- **Sampled clearance below 2 mm inside the protected core (23)**, by contact type:
  - **Resting left hand in the left hip/thigh (8):** LATER, NURSE, PLEASE, THANK-YOU, TOMORROW, UNDERSTAND, YES, YOUR. Penetration reaches −52.0 mm (YES). The left arm is not signing here, so this looks like a retargeting artifact of the idle arm, not part of the sign.
  - **Hand-to-hand contact (9):** APPOINTMENT, BLOOD-DRAW, BREATHE-DEEP, HAVE, INTERPRETER, MEDICINE, MORNING, SORRY, WRITE (down to −49.1 mm, BLOOD-DRAW). Several of these signs touch the other hand by design; the retargeted hands go into each other.
  - **Hand on torso (4):** DOCTOR, HURT, ME, NIGHT (−2.1 to −16.1 mm). ME points at the chest by design.
  - **Near misses, still below 2 mm (2):** HELLO 1.10 mm (right wrist–right hip), NEED 0.25 mm (left wrist–left hip).
- **Speed above the cap inside the core (4):** HELLO 1.304 and PLEASE 1.667 (wrist roll), APPOINTMENT 1.345 (wrist roll), TAKE 1.669 (right middle finger). TAKE fails on speed alone.

Under the frozen v5 gates, every pair containing one of these 24 words is predicted to fail independent verification with `PROTECTED_SOURCE_QUALITY_VIOLATION` or `ORIGINAL_WORD_SLICE_COLLISION`, whatever connector is planned: **1,104 of 1,225 pairs**. Only the 11 × 11 = 121 pairs among clear words remain open. This is a prediction from source data, not a verification result; P1-3 still plans and verifies those pairs. Stills of each defective core at its worst frame are in `preflight_final/worst_frames/` (kinematic renders, viewed only by the execution model).

Per-word preflight (alphabetical; bold marks a failed gate; endpoint counts are valid/candidate frames for the exit and entry roles):

| Word | Protected frames | Preflight | Speed ratio | Core min clearance mm | Worst contact | Exit valid/candidates | Entry valid/candidates |
|---|---|---|---:|---:|---|---:|---:|
| APPOINTMENT | [69,132] | **clearance+speed** | **1.345** | **-8.89** | L wrist–R wrist f74 | 39/55 | 49/70 |
| BLOOD-DRAW | [36,165] | **clearance** | 0.963 | **-49.09** | L wrist–R wrist f65 | 34/51 | 33/37 |
| BREATHE-DEEP | [42,84] | **clearance** | 0.456 | **-12.44** | L finger–R wrist f77 | 43/55 | 40/43 |
| COME | [27,132] | clear | 0.974 | 9.36 | R finger–R wrist f27 | 65/69 | 28/28 |
| DEAF | [33,57] | clear | 0.383 | 6.72 | R finger–torso f44 | 54/57 | 32/34 |
| DOCTOR | [34,57] | **clearance** | 1.000 | **-2.44** | L wrist–torso f43 | 55/64 | 34/35 |
| HAVE | [24,54] | **clearance** | 1.000 | **-19.20** | R finger–L wrist f41 | 33/50 | 24/25 |
| HEADACHE | [27,75] | clear | 1.000 | 2.69 | R finger–torso f60 | 37/54 | 27/28 |
| HELLO | [27,66] | **clearance+speed** | **1.304** | **1.10** | R hip–R wrist f29 | 42/48 | 28/28 |
| HURT | [27,57] | **clearance** | 1.000 | **-4.14** | L wrist–torso f33 | 20/59 | 26/28 |
| INTERPRETER | [30,60] | **clearance** | 1.000 | **-14.83** | L finger–R finger f31 | 41/42 | 17/31 |
| LATER | [27,51] | **clearance** | 1.000 | **-4.16** | L hip–L wrist f33 | 15/31 | 27/28 |
| ME | [30,75] | **clearance** | 0.730 | **-2.09** | R finger–torso f71 | 56/60 | 30/31 |
| MEDICINE | [27,69] | **clearance** | 1.000 | **-34.04** | R finger–L wrist f32 | 36/49 | 15/28 |
| MORNING | [26,69] | **clearance** | 1.000 | **-25.77** | L finger–R wrist f44 | 20/54 | 26/27 |
| NEED | [30,93] | **clearance** | 0.487 | **0.25** | L hip–L wrist f40 | 19/49 | 29/31 |
| NIGHT | [39,60] | **clearance** | 1.000 | **-16.15** | L wrist–torso f42 | 8/43 | 12/40 |
| NO | [21,105] | clear | 1.000 | 3.63 | L finger–L hip f83 | 37/49 | 21/22 |
| NOT | [27,69] | clear | 1.000 | 2.48 | L finger–L hip f35 | 28/42 | 17/28 |
| NOW | [27,51] | clear | 1.000 | 9.25 | R finger–torso f27 | 52/53 | 27/28 |
| NURSE | [38,79] | **clearance** | 1.000 | **-45.78** | L finger–L hip f78 | 28/48 | 35/39 |
| PLEASE | [27,66] | **clearance+speed** | **1.667** | **-23.52** | L hip–L wrist f43 | 26/43 | 28/28 |
| SOON | [27,87] | clear | 1.000 | 3.57 | L finger–L hip f42 | 27/63 | 27/28 |
| SORRY | [21,168] | **clearance** | 0.916 | **-14.07** | L finger–R wrist f166 | 10/20 | 21/22 |
| STOMACH | [33,75] | clear | 0.897 | 5.00 | L finger–L hip f42 | 19/37 | 25/34 |
| TAKE | [51,78] | **speed** | **1.669** | 9.50 | R elbow–R wrist f60 | 25/38 | 48/52 |
| THANK-YOU | [17,87] | **clearance** | 1.000 | **-30.06** | L hip–L wrist f28 | 11/28 | 17/18 |
| TOMORROW | [24,66] | **clearance** | 0.665 | **-30.86** | L hip–L wrist f24 | 43/47 | 14/25 |
| UNDERSTAND | [27,78] | **clearance** | 1.000 | **-10.77** | L hip–L wrist f28 | 37/47 | 27/28 |
| WAIT | [27,84] | clear | 0.821 | 9.11 | R finger–torso f52 | 46/47 | 27/28 |
| WHERE | [51,81] | clear | 0.539 | 8.81 | L hip–L wrist f58 | 46/55 | 48/52 |
| WRITE | [27,69] | **clearance** | 1.000 | **-34.32** | L finger–R wrist f32 | 36/63 | 12/28 |
| YES | [18,69] | **clearance** | 1.000 | **-52.00** | L finger–L hip f20 | 24/46 | 15/19 |
| YOU | [45,72] | clear | 0.261 | 9.50 | R finger–L wrist f60 | 66/71 | 42/46 |
| YOUR | [33,73] | **clearance** | 1.000 | **-46.55** | L finger–L hip f36 | 54/60 | 32/34 |

## P0-4/P0-6 Batch and sequence control

- **Pairs:** one run, one writer (an advisory lock outside the run directory). Each frozen batch has at most 16 pairs, a soft 7,200 s wall clock and a 5 GiB free-disk floor. Budgets are checked only before a new pair plan and before a new candidate review, so a stop is soft. A started step is never killed, and nothing is selected until every candidate of the pair is reviewed. A new batch starts only when no earlier pair is left planned but unreviewed. Completed failures are not retried on resume. Planning keeps v5's wall-clock schedule, so candidate pools still depend on machine load.
- **Stop and drift:** creating `batch_control/<run-id>.stop`, or sending SIGTERM, stops at the next breakpoint. Before each new step the driver also recomputes the code/input identity. A mid-run edit stops the run (`IDENTITY_CHANGED_DURING_RUN`) instead of saving ERROR reviews (see "Deviations").
- **Sequences:** each case first checks its pair dependencies: `PAIR_NOT_PLANNED`, `PAIR_PLANNING_INCOMPLETE`, `PAIR_VERIFICATION_INCOMPLETE`, `PAIR_NO_NUMERICAL_CANDIDATE`. A blocked case is recorded as `BLOCKED_DEPENDENCY` and the run goes on; a corrupt or stale pair run still stops everything.
  - Sub-batches have at most 8 cases, with a 600 s soft budget per case (planning plus verification), a 7,200 s soft wall clock, 64 combinations and a 5 GiB floor. Unstarted cases are `NOT_RUN`, and an interrupted attempt is never selected.
  - A resume writes `<canonical>_resume_NN`, names every earlier output it read, keeps earlier passing selections and skips completely verified attempts. All earlier files stay.
- **Aggregation:** reads only the pre-registered canonical outputs and their resume chain, with a fixed denominator of 111. A case settled as a pass or a complete no-pass may be restated only identically; any other repeat is rejected (no last-write-wins, no picking the best). A pass counts only with a matching independent recheck. The original 12 and the new 99 are counted separately. The P1-2 regression output is kept apart and never added in.
- **Combinations:** generated lazily by rank sum. The first 64 equal the old sorted full product item for item (tested on 300 random shapes, and on five pools whose full product has 10³⁰ tuples, without building it).

## P0-7 Freeze

- **Batches** (`batches/manifest.json`, SHA-256 `fb7c56187f6a1edded67b3c701fde6746a3c87d49eeff62af303ca19231ebf19`): mutually exclusive, union = the 1,225-pair universe, each ≤16. They are regression 4 (1 batch), the other 33 self pairs (3 batches), 132 hub pairs (for each other word w: COME→w, w→COME, NOW→w, w→NOW; 9 batches), and the 1,056 other ordered pairs in universe order (66 batches).
- **Sequence policy** `config/sequence_policy_hospital35_v1.json` (SHA-256 `a37615d852d8db7fcdbdb1fb8c589cc7c21eec33bf9783bc5daa1f27fd4420a6`):
  - Bound to the new pair policy by hash, with the old 2–5 word limits and the old numerical and validation budgets.
  - 111 cases: the original 12, plus `COME__w__NOW`, `NOW__w__COME` and `w__w__w` for each of the 33 other words.
  - A full pass would be 341 word instances and 230 connector groups.
  - `sequence_cases/case_manifest.json` (SHA-256 `3e453cfdb89281a2258db7b3719c8d18b9f261bab8d88d4872837d2457bbe8ab`) splits the cases into 14 sub-batches and records the expected identities.
- **Identity** (`freeze/freeze.json`): pair identity `c4624340015d9015ecc99231a969c1ab8b9f21aa0dc4844b4159747f59e21941`, code hash `d5e179c27f447ad88208cabd9cd0e171535437fa43d03d42b7a6c77079250468` (85 files), sequence identity `a3f11715bfcd12417d1133d9a27bdb438b14494ef372497c80ad765e5389db6a` (88 files), environment `599c49bedf2ffe0a5b933a1b518ec13510d906b7a14b0cd3c3a632851223d835`. The final preflight and the case manifest carry the same identity.
- **Tests (saved logs and exit codes):** focused 222 passed, exit 0 (`freeze/pytest_focused_final.log`); full suite **962 passed**, exit 0 (`freeze/pytest_full_candidate_002.log`); 11 `--help` checks exit 0 (`freeze/cli_help.log`). The 126 new tests:
  - `test_hospital35_protection_import.py` (29): real-sheet byte equality, every rejection above, stale/wrong same-name sources.
  - `test_hospital35_preflight.py` (7): injected limit/coupling/speed/geometry defects attributed, accel/jerk informational, budget exhaustion INCOMPLETE, global blocker not shrunk.
  - `test_hospital35_batches.py` (9): soft stops between pairs and between reviews, disk floor, backlog gate, no retry of completed failures, second writer refused, frozen batch tampering/overlap/gaps/oversize, stop file and identity drift.
  - `test_sequence_combinations.py` (57) and `test_sequence_blockers.py` (17): order equality, bounded memory, dependency states, budgets, resume checkpoint, aggregation conflicts/chains/identity, the recheck never counting blocked cases.
  - `test_hospital35_freeze.py` (7): batch union/exclusivity, 111/341/230, the new scripts in the code identity with a tamper negative.
- **Pre-freeze smoke** (`smoke_pre_freeze_002/`, development only): the real driver on the regression batch (4/4 selected, 74/74 candidates passing), a no-op resume, a fresh recheck (4/4 agree), sequence sub-batch s001 (8/8 pass, recheck 8/8), a blocked sub-batch (8 `BLOCKED_DEPENDENCY`), a sequence resume (8 retained), aggregation (111 rows) and one video. Code identity was then confirmed unchanged before freezing.

## P1-1 Four pairs under the new protection (run `hospital35_protected_20261101_001`)

The batch driver planned `regression_001` and independently reviewed every saved candidate before selecting (437 s, exit 0, log `batch_control/pair_batches/regression_001/invocation_001.json`). A separate fresh `verify_saved_pair_v2` recheck of each selection (`P1-1/selected_recheck/`) agrees 4/4. Protected cores are bitwise unchanged: COME [27,132], NOW [27,51].

| Pair | Attempts | Candidates / numerical pass | Selected (method, fingers) | Kept source frames | Transition s | Peak acc. | Peak jerk | Region integral | Clearance mm |
|---|---:|---:|---|---|---|---:|---:|---:|---:|
| COME→NOW | 31 | 20 / 20 | attempt_00009 (neutral, early) | COME [27,132] → NOW [27,51] | 3.500–5.367 | 25.70 | 233.5 | 237,120 | 3.993 |
| NOW→COME | 27 | 18 / 18 | attempt_00013 (ik_via2, synchronous) | NOW [27,51] → COME [27,132] | 0.800–2.367 | 29.67 | 279.0 | 322,229 | 9.251 |
| COME→COME | 23 | 13 / 13 | attempt_00003 (direct, early) | COME [27,132] → COME [27,132] | 3.500–4.233 | 40.65 | 442.6 | 254,410 | 4.711 |
| NOW→NOW | 36 | 25 / 25 | attempt_00010 (neutral, early) | NOW [27,51] → NOW [27,51] | 0.800–2.667 | 25.69 | 246.8 | 294,056 | 3.993 |

**Compared with the old pilot run** (`sequence_pilot_pairs_20261031_001`, NOW [3,76]): COME→COME is identical (same selection and metrics, since COME's protection did not change). The three NOW pairs now have more candidates (20/18/25 versus 7/18/8) and different selections; with the shorter NOW core, both connectors leave or enter NOW exactly at its core boundary. All three are new results under the new protection, not reused. All pass the frozen v5 limits; formal status stays pending.

## P1-2 The original 12 sequences under the new protection (`sequences_regression_001`)

The 12 original cases were selected explicitly from the new 111-case policy. They used only candidates from the same new pair run (all four edges `READY`). All 12 passed on attempt_0001 (every edge at rank 0), and a separate fresh recheck agrees on all 12. Values are the worst case over each sequence's transition regions; clearance is sampled, not continuous.

| Sequence | Duration s | Peak acc. | Peak jerk | Region integral | Analytic connector integral | Clearance mm |
|---|---:|---:|---:|---:|---:|---:|
| COME–COME–COME | 11.967 | 40.65 | 442.6 | 254,410 | 469,770 | 4.711 |
| COME–COME–NOW | 10.400 | 40.65 | 442.6 | 254,410 | 469,770 | 3.993 |
| COME–NOW–COME | 11.233 | 29.67 | 279.0 | 322,229 | 485,712 | 3.993 |
| COME–NOW–NOW | 8.833 | 25.70 | 246.8 | 294,056 | 504,454 | 3.993 |
| NOW–COME–COME | 10.100 | 40.65 | 442.6 | 322,229 | 485,712 | 4.711 |
| NOW–COME–NOW | 8.533 | 29.67 | 279.0 | 322,229 | 485,712 | 3.993 |
| NOW–NOW–COME | 8.533 | 29.67 | 279.0 | 322,229 | 504,454 | 3.993 |
| NOW–NOW–NOW | 6.133 | 25.69 | 246.8 | 294,056 | 504,454 | 3.993 |
| COME×5 | 20.433 | 40.65 | 442.6 | 254,410 | 469,770 | 4.711 |
| NOW×5 | 11.467 | 25.69 | 246.8 | 294,056 | 504,454 | 3.993 |
| COME–NOW–COME–NOW–COME | 18.967 | 29.67 | 279.0 | 322,229 | 485,712 | 3.993 |
| NOW–COME–NOW–COME–NOW | 16.267 | 29.67 | 279.0 | 322,229 | 485,712 | 3.993 |

- **Recheck** (`independent_recheck/summary.json`): 12 cases, 12 rechecked, 12 numerical passes, 12 agree with planning. 44 word instances, all 44 protected instances unchanged, 32 connector groups. The largest relative timing error is 3.2e-15 s (limit 1e-12 s).
- **Shorter NOW:** NOW now keeps only [27,51] (25 frames instead of 74), so sequences with NOW are shorter than in TASK-26 (for example NOW×5: 11.467 s instead of 16.167 s).
- **Videos** (`videos_regression_001/<sequence>/comparison.mp4`): 12 rendered; media denominator 12 of 12 cases. The top row is the original clips, the bottom row the sequence, front and side. The renderer reruns the independent verifier first and compares protected instances against the replay used for the video: 44/44 are bitwise equal. The execution model looked at the NOW–COME–NOW–COME–NOW contact sheet: the labels show the new core ends (NOW f51, COME f132). This is not a human, group-2 or ASL comprehension review.

## P1-3 Library-wide batches (running)

The driver works through the 79 frozen batches in order in the same run (`P1-3.log`; one append-only log per batch invocation in `batch_control/pair_batches/<batch>/`). It plans each pair, reviews every candidate independently and only then selects. It stops at the first batch that does not complete. Measured throughput (batch wall time ÷ pairs, single-threaded): about 63 s per pair in the self group, 80 s in the hub group and 64 s in the rest group. The 40–50 h estimated at handoff from "about 30 s of planning plus about 4.5 s per candidate review" was too pessimistic. At the rest-group rate the remaining 52 batches (832 pairs) need about 15 h, finishing around 02:00 on 2026-11-02; batches took 600–1,770 s each, so the end may come hours earlier or later. **It is not finished.** The snapshot below was taken while it ran; pairs not yet reached are `NOT_RUN`.

**Parallel from 11:26 (no code change):** at the user's request to speed up, run 001 was stopped gracefully at a breakpoint at 11:24 (inside rest_017, exit 3) and the 50 open frozen batches were dealt round-robin in manifest order to 4 runs: 001 continues its slice (including rest_017) and 002–004 are new. Code, policy, environment and identity are identical, each run still has a single writer, and each is pinned to its own performance core (cpu0–3; planning has a wall-clock budget, and the 3.3–3.7 GHz efficiency cores would yield fewer candidates). Pair seeds depend only on the position in the frozen batch, not on the run. The partition is in `P1-3/parallel_partition.json` (13/13/12/12 batches); the command is `commands/p1_3_parallel.sh`. Expected to finish around 15:30 (instead of about 02:00).
- **Deviation from the HANDOFF:** it asks for "the same new run"; the 1,225 pairs now sit in 4 runs with one identity. The final table is merged by `P1-3/scan_progress_multi.py` (each pair in at most one run, identities must match), and rechecks run per run. P1-4 is unaffected: all 169 pairs of the 111 cases are in run 001.
- **Comparability:** with all 4 performance cores busy they run at about 4.4 GHz instead of about 4.8 GHz single-core, so about 8% less work fits into the 30 s planning budget; candidate counts and TIMEOUT rates per group will be compared at the end. Snapshot before the split: `P1-3/progress_20261101_presplit.json` (441 pairs with records).

**Snapshot 2026-11-01 10:47** (read-only, `P1-3/progress_20261101_104756.json`, made with `P1-3/scan_progress.py`; the first snapshot from 03:32 is kept in `P1-3/progress_20261101_033213.json`):

| Group | Pairs | Numerical pass | Numerical fail | No curve (TIMEOUT, diagnosis only) | Planned, review pending | Planning running | Not run |
|---|---:|---:|---:|---:|---:|---:|---:|
| Regression | 4 | 4 | 0 | 0 | 0 | 0 | 0 |
| Self | 33 | 6 | 15 | 12 | 0 | 0 | 0 |
| Hub | 132 | 27 | 78 | 27 | 0 | 0 | 0 |
| Rest | 1,056 | 13 | 149 | 62 | 14 | 1 | 817 |
| **All** | **1,225** | **50** | **242** | **101** | **14** | **1** | **817** |

- **Batches:** 27 of 79 ended BATCH_COMPLETE (regression_001, self_001–003, hub_001–009, rest_001–014), with no budget stop so far; rest_015 is running. The driver has run for 7 h 37 min at 1.8 GB RSS; the pair run takes 926 MB, with 100 GB of disk free.
- **Prediction check (393 pairs with a complete independent review):** all 328 predicted-blocked pairs failed; none passed unexpectedly. Of the 65 predicted-open pairs, 50 passed and 15 had no candidate within the planning budget (TIMEOUT). The preflight checks only protected cores and endpoints and plans no connector, so "predicted open" is necessary, not sufficient.
- **The 15 TIMEOUTs fall on 4 preflight-clear words:** all 12 reviewed WAIT pairs have no curve; the 7 with clear words are WAIT–WAIT, COME→WAIT, WAIT→COME, NOW→WAIT, WAIT→NOW, NO→WAIT and YOU→WAIT. HEADACHE and SOON can be entered (COME/NOW/NO→HEADACHE and COME/NOW/NO/YOU→SOON pass) but not left (HEADACHE→COME, HEADACHE→NOW, HEADACHE–HEADACHE, SOON→COME, SOON→NOW, SOON–SOON), plus YOU→HEADACHE. STOMACH has only STOMACH→COME. A TIMEOUT is not a proof that no connector exists.
- **Failure reasons** (counted per pair; a pair can have several): `ORIGINAL_WORD_SLICE_COLLISION` 220, `FULL_CLIP_SPEED_VIOLATION` 79, `PROTECTED_SOURCE_QUALITY_VIOLATION` 78, peak acceleration 28, jerk integral 28, peak jerk 20.

Execution coverage (every pair planned and independently reviewed, with failures allowed) and the numerical goal (1,225/1,225 usable connections) are separate. The numerical goal is out of reach under the current inputs and gates (P0-3). The scan records the actual failures rather than assuming them.

## P1-4 111 sequences (not run)

The 111 cases and their 14 sub-batches are frozen (`sequence_cases/case_manifest.json`). They have not been run: P1-3 is still writing the pair run, and loading candidate pools first verifies the whole run, so they run after P1-3 ends (the HANDOFF prerequisite for P1-4 is also that P1-3 has finished or stopped at an explicit budget checkpoint). The 111 cases use only 169 pairs, all in the regression, self and hub groups, and by 10:47 every one had a complete independent review, so the dependency states are already fixed:

- **29 of 111 cases have every pair passing numerically:** the original 12; `COME__w__NOW`, `NOW__w__COME` and `w__w__w` for each of NO, YOU, DEAF, NOT and WHERE (15 cases); and `COME__STOMACH__NOW` and `STOMACH__STOMACH__STOMACH`. This is an upper bound: sequence-level combination and verification can still fail.
- **10 cases are blocked only by TIMEOUT pairs of preflight-clear words:** 3 each for HEADACHE, WAIT and SOON, plus `NOW__STOMACH__COME` (STOMACH→COME). Recovering them is an engineering matter (planning budget or endpoints) and needs a new policy version and a new run; the current run is not changed.
- **72 cases contain a source-blocked word.**

The preflight bound of 39/111 therefore drops to 29/111; the other 82 cases are expected to end as `BLOCKED_DEPENDENCY` (`PAIR_NO_NUMERICAL_CANDIDATE`). A full pass (341 word instances, 230 connector groups) is not reachable under the current inputs.

### Approved budget retry (after P1-4)

On 2026-11-01 the user approved retrying the TIMEOUT pairs between clear words with a larger, versioned budget once P1-4 has finished. Prepared:

- **New policy** `config/transition_policy_user_protected_hospital35_retry_budget_v1.json` (SHA-256 `bcef2e84…`), copied from the frozen policy by `retry_budget_001/generate_retry_policy.py` with only the planner search budget raised: `wall_time_s` 30→240, `rrt.wall_time_s` 10→80, `max_collision_samples` 32,768→262,144, `max_nodes` 4,096→16,384, `max_time_attempts` 12→48. `max_candidates` (128), validation budgets, endpoints, protection and every gate are unchanged; the old policy and run are untouched. Checked with the frozen code: the code hash and environment equal the freeze record and only the policy hash differs; the frozen identity still reproduces.
- **Scope rule (frozen once on the final P1-3 table):** A = pairs of two clear words that ended TIMEOUT without a curve; cases = those of the 111 that did not fully pass and whose failing pairs all lie in A; B = every pair those cases use (re-planned so one pair run can supply each whole sequence). The new run `hospital35_retry_budget_001` plans A ∪ B; the batch manifest still covers the universe, with the other pairs in `unrun` batches that are never executed. A dry run on the 10:47 snapshot gave 15 TIMEOUT pairs + 5 extra pairs = 20 pairs (3 batches) and 10 cases, and the frozen loaders accepted the generated manifests (`retry_budget_001/dryrun_20261101_1047/`, dry run only).
- **Why it may still fail:** the WAIT–WAIT diagnosis shows that besides wall-time limits, the geometric RRT paths failed timing because the finger arrival does not fit inside the connector. A larger budget is a fair retry, not a guaranteed fix; the result is kept either way.

## Commands

All commands run from the repository root with this environment (the thread variables are part of the run identity):

```bash
cd /home/kingderman/Documents/ME5412-github-latest
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
```

Import (exit 0) and byte-for-byte check (exit 0, `MATCH`):

```bash
.venv/bin/python scripts/import_user_protections.py --ods data/user_protection/hospital35_20261101/protection_intervals.ods --expected-sha256 4fe5b3bb3f7d12cf4cd4418b8431325dec48fbed3c29a2a1e29447cdf89667e3
```

```bash
.venv/bin/python scripts/import_user_protections.py --ods data/user_protection/hospital35_20261101/protection_intervals.ods --expected-sha256 4fe5b3bb3f7d12cf4cd4418b8431325dec48fbed3c29a2a1e29447cdf89667e3 --check
```

Preflight with the frozen code (exit 0, 43 s):

```bash
.venv/bin/python scripts/preflight_hospital35.py --output results/hospital35_protected_20261101_001/preflight_final
```

Tests (full suite: 962 passed, exit 0, 118 s):

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider tests
```

P1-1 regression batch (exit 0, 437 s), then the fresh recheck of the selections (exit 0):

```bash
.venv/bin/python scripts/run_hospital35_batches.py pairs --batch-manifest results/hospital35_protected_20261101_001/batches/manifest.json --batch-manifest-sha256 fb7c56187f6a1edded67b3c701fde6746a3c87d49eeff62af303ca19231ebf19 --batch regression_001 --run-id hospital35_protected_20261101_001 --results-root results/hospital35_protected_20261101_001/pair_runs --control-dir results/hospital35_protected_20261101_001/batch_control
```

```bash
.venv/bin/python scripts/run_hospital35_batches.py recheck-pairs --run-dir results/hospital35_protected_20261101_001/pair_runs/hospital35_protected_20261101_001 --output results/hospital35_protected_20261101_001/P1-1/selected_recheck
```

P1-2 (each exit 0); the plan command lists the 12 original cases with `--case` (see `commands/p1_2.sh`):

```bash
.venv/bin/python scripts/plan_sequences.py --sequence-policy config/sequence_policy_hospital35_v1.json --pair-run-dir results/hospital35_protected_20261101_001/pair_runs/hospital35_protected_20261101_001 --output results/hospital35_protected_20261101_001/sequences_regression_001 --case COME__COME__COME --case COME__COME__NOW --case COME__NOW__COME --case COME__NOW__NOW --case NOW__COME__COME --case NOW__COME__NOW --case NOW__NOW__COME --case NOW__NOW__NOW --case COME__COME__COME__COME__COME --case NOW__NOW__NOW__NOW__NOW --case COME__NOW__COME__NOW__COME --case NOW__COME__NOW__COME__NOW
```

```bash
.venv/bin/python scripts/verify_sequences.py --run-dir results/hospital35_protected_20261101_001/sequences_regression_001
```

```bash
.venv/bin/python scripts/render_sequences.py --run-dir results/hospital35_protected_20261101_001/sequences_regression_001 --output results/hospital35_protected_20261101_001/videos_regression_001
```

P1-3, all frozen batches in order. The same command resumes; it is valid only while the frozen identity is unchanged:

```bash
.venv/bin/python scripts/run_hospital35_batches.py pairs --batch-manifest results/hospital35_protected_20261101_001/batches/manifest.json --batch-manifest-sha256 fb7c56187f6a1edded67b3c701fde6746a3c87d49eeff62af303ca19231ebf19 --run-id hospital35_protected_20261101_001 --results-root results/hospital35_protected_20261101_001/pair_runs --control-dir results/hospital35_protected_20261101_001/batch_control
```

Graceful stop at the next breakpoint (delete the file before resuming):

```bash
touch results/hospital35_protected_20261101_001/batch_control/hospital35_protected_20261101_001.stop
```

Parallel continuation (4 runs, each pinned to a performance core; the same command resumes):

```bash
bash results/hospital35_protected_20261101_001/commands/p1_3_parallel.sh
```

Graceful stop of all parallel runs:

```bash
for n in 1 2 3 4; do touch results/hospital35_protected_20261101_001/batch_control/hospital35_protected_20261101_00$n.stop; done
```

Read-only progress snapshot while it runs (the output file must be new):

```bash
.venv/bin/python results/hospital35_protected_20261101_001/P1-3/scan_progress.py results/hospital35_protected_20261101_001/pair_runs/hospital35_protected_20261101_001 results/hospital35_protected_20261101_001/batches/manifest.json results/hospital35_protected_20261101_001/preflight_final/preflight.json results/hospital35_protected_20261101_001/P1-3/progress_$(date +%Y%m%d_%H%M%S).json
```

P1-4 after P1-3 (once per sub-batch `s001`…`s014`, then aggregate):

```bash
.venv/bin/python scripts/run_hospital35_batches.py sequences --sequence-policy config/sequence_policy_hospital35_v1.json --case-manifest results/hospital35_protected_20261101_001/sequence_cases/case_manifest.json --case-manifest-sha256 3e453cfdb89281a2258db7b3719c8d18b9f261bab8d88d4872837d2457bbe8ab --subbatch s001 --control-dir results/hospital35_protected_20261101_001/batch_control
```

```bash
.venv/bin/python scripts/run_hospital35_batches.py aggregate --sequence-policy config/sequence_policy_hospital35_v1.json --case-manifest results/hospital35_protected_20261101_001/sequence_cases/case_manifest.json --case-manifest-sha256 3e453cfdb89281a2258db7b3719c8d18b9f261bab8d88d4872837d2457bbe8ab
```

Alternatively run the wrappers `commands/p1_3_final.sh` (final snapshot and a fresh recheck of every selected candidate) and then `commands/p1_4.sh` (the 14 sub-batches, the aggregate, then videos of the passing cases; a rerun skips completed sub-batches). Both refuse with exit 4 while P1-3 has not ended; the refusal path was tested.

The budget retry after P1-4 (generates the definitions once, then runs the retry pairs, the recheck, the affected cases, the aggregate and videos; refuses with exit 4 until P1-3 and P1-4 are done, refusal path tested):

```bash
bash results/hospital35_protected_20261101_001/commands/retry_budget.sh
```

The evidence scripts (baseline, frozen-definition, case-manifest and freeze-record generators, comparison, worst-frame stills) are saved next to their outputs; the shell wrappers are in `commands/`.

## Files

New inputs and policies (frozen): `data/user_protection/hospital35_20261101/protection_intervals.ods`, `config/user_protected_hospital35_v1.json`, `config/user_protected_hospital35_v1.provenance.json`, `config/transition_policy_user_protected_hospital35_v1.json`, `config/sequence_policy_hospital35_v1.json`.

New code: `scripts/import_user_protections.py`, `scripts/preflight_hospital35.py`, `scripts/run_hospital35_batches.py`, `src/sign_robot/batch_control.py`, `src/sign_robot/sequence_batches.py`. Changed: `src/sign_robot/pair_contract.py`, `pair_runner_v2.py`, `sequence_assembly.py`, `scripts/plan_sequences.py`, `verify_sequences.py`, `render_sequences.py`, `src/sign_robot/project_overview.py` (docs-index hashes only), `docs/README.md`/`.en.md` (one row). Six new test files.

Evidence under `results/hospital35_protected_20261101_001/`:

| Folder | Contents |
|---|---|
| `baseline/` | P0-1 baseline, backups, hash inventories, source manifest |
| `import/` | importer help, write and `--check` logs, import test log |
| `preflight_dev_001/` | development preflight (before freeze; diagnosis only) |
| `preflight_final/` | preflight with the frozen code; `worst_frames/` stills |
| `batches/` | 79 frozen batch files and `manifest.json` |
| `sequence_cases/` | frozen 111-case manifest (14 sub-batches) |
| `freeze/` | test logs, CLI help log, generators, `freeze.json` |
| `smoke_pre_freeze/` | invalidated development smoke (see its INVALIDATED.md) |
| `smoke_pre_freeze_002/` | clean development smoke before the freeze |
| `pair_runs/hospital35_protected_20261101_001/` | the single new pair run (P1-1 and P1-3) |
| `batch_control/` | limits, locks, per-batch invocation logs |
| `P1-1/` | fresh recheck of the four selections, comparison with the old run |
| `sequences_regression_001/`, `videos_regression_001/` | P1-2 sequences, recheck and videos |

## Decision needed (outside engineering)

**User choice on 2026-11-01: keep scanning.** No source-revision request was drafted; how to handle the 24 words is still open, and the options below are unchanged.

Under the frozen inputs and v5 gates, "any two words connect" cannot reach 1,225/1,225, because 24 protected cores fail before any connector is planned. Engineering may not trim cores, edit sources or relax gates. One of these needs an owner's decision. Evidence per word (frames, body pairs, depth, speeding joint) is in `preflight_final/preflight.json`, `words.csv` and `worst_frames/`.

1. **Source revision (group 2):** re-export the 24 motions so the protected cores keep their meaning without penetration or speed spikes. For example, move the resting left arm off the hip (8 words), keep two-hand and torso contacts at ≥2 mm instead of inside the body, and cap the wrist/finger spikes (HELLO, PLEASE, APPOINTMENT, TAKE). New files change the source hashes, so the protected intervals would then be confirmed on the new files.
2. **Versioned contact rule (policy owner):** a new policy version that defines which contacts inside protected cores belong to a sign (for example designated hand–hand or hand–torso pairs) and how they are gated. This changes the collision scope and needs explicit approval; it was not done here.
3. **Narrower protection (user):** only where the defect lies outside the semantic part. The idle-arm contacts cover most of each core, so this rarely helps.
4. **Accept the gap for now:** keep the 11 clear words as the numerically usable subset and let the scan continue to record failures.

## Deviations from the HANDOFF

- **No subagents:** the HANDOFF suggests `gpt-6.1-sol` subagents. None were started; this session does not spawn agents unless the user asks, so the main executor did all implementation, tests and review.
- **First full test run stopped:** I stopped it to make the soft wall clock per batch instead of per invocation. Its partial log was replaced. The two complete candidate runs are kept (960 and then 962 passed).
- **First smoke invalidated:** during its review step I edited `batch_control.py`. From then on every review correctly failed with an identity mismatch (ERROR), and the later steps refused the stale run. Those files are kept and marked `smoke_pre_freeze/INVALIDATED.md`. This led to the drift guard; the clean repeat is `smoke_pre_freeze_002/`.
- **P1-1 commands:** P1-1 used the frozen batch driver (`pairs --batch regression_001`) rather than `plan_all_pairs.py` + `verify_all_pairs.py`. It uses the same runner and seeds, plus locking, budgets and logs.
- **Known limitation:** if `--resume-from` points at tampered earlier outputs, `plan_sequences.py` stops after creating an empty output directory. Aggregation then fails loudly on the missing manifest rather than silently.

## Unverified limits

- Nobody has watched the videos or stills. Whether transitions mislead, and whether the cases stay understandable, is not checked; they are not ASL sentences.
- Formal PASS_SIM is 0. The policies are development policies pending cross-group review.
- Collision is sampled, not continuous. Derivatives inside protected cores are not certified as continuous.
- The P1-3 full-library scan is incomplete (see above). P1-4's 111 cases have not been run because they depend on P1-3.
- Wall-clock planning budgets make candidate pools depend on machine load, and reruns are not bit-identical.
- There is no neutral start/end pose, no hardware run and no reproduction in a fresh environment. Nothing is committed to git.
