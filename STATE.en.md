# Current project state

[中文](STATE.md) · [Next execution handoff](HANDOFF.en.md) · [Latest execution report TASK-28](TASK-28.en.md) · [Previous stage TASK-27](TASK-27.en.md)

Updated: 2026-11-02 (Asia/Shanghai), after round 8 of the nine hospital sentences. Scope: Group 3 word transitions and sequence replay. The "Latest" section is the current state; section 0 is the state after the 2026-11-01 35-word full-library stage, and sections 1–5 the state before that stage. Both are kept as history with their original headings; where they conflict with "Latest", "Latest" applies.

## Latest (2026-11-02): nine hospital sentences, round 8 passes 7/7 numerically

**On 2026-11-01 the user narrowed the scope to nine hospital sentences, with Group 3 owning only the connectors; the 1,225-pair full-library scan stopped (P1-3 at 46/79 batches), and P1-4, the budget retry and the faster scanner were not run. In round 8 all seven multi-word sentences are NUMERICAL_PASS, end at the rest pose, and no connector halts partway.** Rounds, configuration, commands and open items: [TASK-28](TASK-28.en.md).

| Layer | Current fact | Boundary |
|---|---|---|
| Scope | Seven multi-word sentences with 17 word pairs: HELLO YOU APPOINTMENT HAVE, YOU NEED INTERPRETER, PLEASE WAIT DOCTOR COME SOON, YOU HURT WHERE, NOW NURSE BLOOD-DRAW, MEDICINE MORNING NIGHT TAKE, YOU UNDERSTAND; the single words BREATHE-DEEP and THANK-YOU play their source motions | Connectors only (review scope v4); source-motion defects are recorded for Group 2, not counted as failures |
| Result | [Round 8](results/hospital_sentences_20261102_008/README.en.md): 17/17 connectors and 7/7 sentences agree on fresh rechecks; 24/24 protected cores bitwise unchanged; 0 interior stops; 310 frames between cores across the 17 connectors (round 2: 1,717) | Videos not watched by a person |
| Configuration | Pairs `config/transition_policy_hospital_sentences_fast_v5.json`, sequences `config/sequence_policy_hospital_sentences_v7.json`, protection `config/user_protected_hospital35_v2.json` (NURSE [38,75], MORNING [26,37]) | Acceleration-type limits widened with the user's permission to 200 rad/s², 5000 rad/s³ and 5e6 rad²/s⁵; speed caps unchanged |
| Code and tests | Code `1d07d2d`; full suite 1014 passed | Not rerun for this update |
| Git | Public branch `group3/trajectory-planning`: non-raw round-8 snapshot from source `dfe4bacde`, based on clean public commit `86428693` | Updated at the user's explicit request on 2026-11-02; raw stores remain local |
| Formal | PASS_SIM 0; `formal_acceptance_enabled=false` | A numerical pass is not formal, semantic or hardware acceptance |

**To confirm:** someone watches the round-8 videos; sentences still begin directly on the first protected core. Section 0's decision on the 24 source-blocked words is still open but does not block the current scope.

---

> Sections 0–5 below are the history as of 2026-11-01.

## 0. Latest (after execution): 35 words imported and frozen; preflight finds 24 source-blocked words

**The 35-word protection sheet is imported strictly and frozen. The regression under the new protection passes (4/4 pairs, 12/12 sequences). The library-wide scan is running in batches but cannot reach 1,225/1,225, because 24 of the 35 protected cores fail a non-waivable gate in the source motion itself.** Details: [TASK-27](TASK-27.en.md).

| Layer | Current fact | Boundary |
|---|---|---|
| Inputs | 35/35 records imported strictly from the ODS (`config/user_protected_hospital35_v1.json`); COME [27,132], NOW [27,51]; the import reproduces byte for byte | Semantics not certified; the old COME/NOW bundle stays with the old runs |
| Preflight | 11 words clear; 24 with a source defect inside the protected core (23 sampled penetrations, down to −52.0 mm; 4 speed caps); 0 without endpoints | 1,104/1,225 pairs are predicted to fail whatever connector is planned; 121 remain open. A prediction, not a verification result |
| Freeze | Pair identity `c4624340…`, code `d5e179c2…` (85 files), sequence identity `a3f11715…`; full suite 962 passed, exit 0 | Any code edit while the scan runs makes the identity stale; the driver then stops |
| P1-1 four pairs | 4/4 selected, 76/76 candidates pass numerically, fresh recheck agrees 4/4; protected cores bitwise unchanged | Wall-clock budgets make candidate pools load-dependent |
| P1-2 original 12 sequences | 12/12 numerical passes, fresh recheck agrees 12/12; 44/44 protected instances unchanged, 32 connector groups; 12 videos | COME/NOW engineering cases only, not ASL sentences |
| P1-3 1,225 pairs | Running in the background in frozen batches. Snapshot 10:47: 27/79 batches done; 393 pairs reviewed (50 pass, 242 fail, 101 TIMEOUT with no curve), 15 in progress, 817 not run; all 328 predicted-blocked pairs failed, and 15 of the 65 predicted-open pairs timed out (WAIT, HEADACHE, SOON, STOMACH) | Not finished; split into 4 parallel runs with one identity since 11:26 (one performance core each), expected to end around 15:30; 1,225/1,225 unreachable under current inputs |
| P1-4 111 sequences | Not run: waits for P1-3 to end. All 169 pairs it needs are reviewed; 29/111 cases have every pair passing (upper bound) and 82 will be blocked by a dependency | Frozen case manifest only |
| Budget retry | Approved by the user, runs after P1-4: a new policy that raises only the planner search budget (wall time 30→240 s etc.) and a new run that retries the TIMEOUT pairs between clear words and the affected cases (10:47 dry run: 20 pairs, 10 cases) | Prepared, refusal path tested, not run; may still fail |
| Faster scanner | Approved by the user; developed as a new version after the budget retry: verifier grid deduplication, endpoint/source-slice caching, multiple workers behind the single writer | Not started; does not skip source-blocked pairs |
| Formal | PASS_SIM 0; `formal_acceptance_enabled=false`; `playback_eligible=false` | Numerical success is not formal, semantic or hardware acceptance |

**Decision needed:** each of the 24 words needs a source revision (group 2), a versioned contact rule (policy owner) or narrower protection (user). Engineering may not trim cores, edit sources or relax gates. Per-word frames, body pairs and depths are in TASK-27 and `results/hospital35_protected_20261101_001/preflight_final/`. On 2026-11-01 the user chose to keep scanning first; no revision request was drafted, and the decision is still open.


## 1. Current conclusion

**Under the old COME/NOW configuration, 4/4 pairs and 12/12 engineering sequences pass numerically. The latest 35-word protection workbook is complete and checked, but has not been imported or run.** No further intervals for the other 33 words are needed. Engineering must import, preflight, regress and then expand coverage; formal acceptance remains incomplete.

| Layer | Current fact | Boundary |
|---|---|---|
| User input | 35/35 unique complete words, 70 numeric times; ranges fit selected source motions | Checked does not mean installed or semantically certified |
| Installed configuration | `user_protected_come_now_v2.json` still contains only COME/NOW, with old NOW [3,76] | New NOW [27,51] is not active |
| Latest saved pairs | 4/4 numerical passes; 46/46 candidates have complete passing independent evidence | 1,221 of the 1,225 library pairs remain NOT_RUN |
| Latest saved sequences | 12/12 numerical passes; saved independent recheck agrees for 12/12; 44/44 protected occurrences unchanged; 32 connector groups | Only 8 three-word and 4 five-word COME/NOW engineering cases |
| Media | 12 diagnostic sequence videos; 44/44 protected replay occurrences bitwise equal | No human semantic or cross-group engineering acceptance |
| Tests | TASK-26 reports 24 sequence tests and 836 full-suite tests passed | Not rerun here; corresponding complete pytest output was not located in existing results `.log/.txt` files |
| Formal status | Formal PASS_SIM=0, `formal_acceptance_enabled=false`, `playback_eligible=false` | Numerical success does not establish formal usability or hardware safety |

## 2. Baseline and saved evidence

- Target: `/home/kingderman/Documents/ME5412-github-latest`; chat cwd `/home/kingderman/Documents/ME5412` is a different checkout.
- Branch: `codex/group3-all-pairs-v1`; HEAD: `2875e499d79b7264b3fe0414318b30ca8aab1f4d`. Uncommitted and untracked implementation exists; HEAD alone cannot reproduce this working tree.
- Latest report: [TASK-26](TASK-26.en.md). [TASK-25](TASK-25.en.md) and run 002 remain historical.
- Latest pair run: `sequence_pilot_pairs_20261031_001`; [summary.json](results/sequence_pilot_20261031_001/pair_runs/sequence_pilot_pairs_20261031_001/summary.json).
- Latest sequence [summary](results/sequence_pilot_20261031_001/sequences_001/summary.json), [independent recheck](results/sequence_pilot_20261031_001/sequences_001/independent_recheck/summary.json), and [media summary](results/sequence_pilot_20261031_001/videos/summary.json).
- Active policies: [transition_policy_user_protected_v5.json](config/transition_policy_user_protected_v5.json) and [sequence_policy_user_protected_v1.json](config/sequence_policy_user_protected_v1.json), bound to the old [protection bundle](config/user_protected_come_now_v2.json).
- Pair code-set SHA-256 (74 files): `4080b98e73a121c866115882483ef5b7631532d9add4bed4ff5dfbe214ad9cef`.
- Sequence code-set SHA-256 (77 files): `1ecfcc9f95830071dfbffbb895cf4f664ca5aecd4b38398ceb91ececdea15bb0`.

Read-only checks in this refresh matched 74 pair code files and 144 input files against the frozen inventory; 615 pair-manifest entries and the bindings of 46 candidate verifications; 12 sequence artifacts and saved planning/recheck references; and 60 media files plus 12 source references. Trajectory/physical verification was not recomputed. Inspecting saved evidence and rerunning validation are distinct evidence levels.

| Pair | Candidates / numerical passes | Selected |
|---|---:|---|
| COME→NOW | 7 / 7 | attempt_00016 |
| NOW→NOW | 8 / 8 | attempt_00015 |
| NOW→COME | 18 / 18 | attempt_00013 |
| COME→COME | 13 / 13 | attempt_00003 |

The library denominator is **1,225=1,190 non-self+35 self pairs**. `planning_complete=false`, `verification_complete=false`, and `L2_complete=false` describe whole-library completion. The four formal classifications remain `FAILED_QUALITY`; inspect `numerical_checks_passed` and formal-gate reasons together rather than reporting numerical 0/4.

Saved sequence rechecks report a maximum relative timing error of `3.1086244689504383e-15 s` (≤3.11e-15 s), below `1e-12 s`. All 12 passed on the first candidate combination. These are kinematic engineering cases, not ASL sentences.

Compared with historical run 002, NOW→COME changed from 17 candidates/attempt_00023 to 18 candidates/attempt_00013; the other three selected candidates stayed the same. A candidate previously interrupted by the wall-clock budget completed in this run. **Machine load can change candidate pools; replanning is not guaranteed to reproduce the same selection bitwise.** Saved-artifact identity checks and numerical rechecks remain separate reproducible operations.

## 3. Latest protection input: checked, not imported

Source [手势保护区间填写表.ods](/home/kingderman/Documents/ME5412/outputs/01a18d89-c53d-7340-b2b8-0f8ddfd306f2/手势保护区间填写表.ods); sheet `保护区间填写`; A1:C1 contains word/start seconds/end seconds, A2:C36 contains 35 records. SHA-256: `4fe5b3bb3f7d12cf4cd4418b8431325dec48fbed3c29a2a1e29447cdf89667e3`. This is an external local file: carry it and verify its hash on another machine rather than assuming Git contains it.

Checked: 35 unique complete words in hospital-map order; 70 numeric values without formulas or blanks; all satisfy `0≤start<end≤actual final-frame time`. Selected NPZ timelines equal `np.arange(n)/30`. The current contract maps outward to zero-based inclusive `[floor(start×30),ceil(end×30)]`; all 35 mappings agree with Decimal arithmetic. Checks concern selected NPZ sources, not independent certification of every preview-container duration or historical video-byte identity.

| Word | Old-run protection | Latest workbook | Next action |
|---|---|---|---|
| COME | 0.93–4.40 s → [27,132], 106 frames | 0.93–4.40 s → [27,132], 106 frames | Preserve interval in new bundle |
| NOW | 0.13–2.53 s → [3,76], 74 frames | **0.90–1.70 s → [27,51], 25 frames** | New policy/run; rerun 4 pairs and 12 sequences |
| Other 33 | No installed user protection | All supplied and checked | Import and preflight all words |

COME source SHA-256: `75d6455408ce6584043baedbd0e049cbeabcad534eda65ef561d2c7293b477a4`; NOW source SHA-256: `2d494c13fdf1b44bb11e97004e7b212ea5c45b7b0f8d0b972bd3589ae63e15e3`. **Old 4/4 and 12/12 results do not validate the latest ranges. Even unchanged COME must be bound into the new bundle/policy identity.**

Duplicate names are resolved by actual `library` and `motion` fields in [hospital_v1_motions.json](motions/hospital_v1_motions.json), not `planned_source` or the first matching preview. The 9 mocap words are HELLO, PLEASE, YOU, APPOINTMENT, COME, BREATHE-DEEP, BLOOD-DRAW, TAKE, WHERE; the other 26 use `motions/wlasl_video_v1/`. HELLO therefore uses `motions/studio_galt_v1/HELLO.npz`.

The following is a checked transcription, not installed configuration. Compare the original ODS and next automated import row by row.

| Word | Start s | End s | Inclusive core frames |
|---|---:|---:|---|
| HELLO | 0.9 | 2.2 | [27,66] |
| PLEASE | 0.9 | 2.17 | [27,66] |
| THANK-YOU | 0.57 | 2.9 | [17,87] |
| SORRY | 0.7 | 5.57 | [21,168] |
| YES | 0.63 | 2.3 | [18,69] |
| NO | 0.7 | 3.5 | [21,105] |
| YOU | 1.53 | 2.37 | [45,72] |
| YOUR | 1.1 | 2.43 | [33,73] |
| ME | 1 | 2.5 | [30,75] |
| DEAF | 1.1 | 1.9 | [33,57] |
| DOCTOR | 1.15 | 1.87 | [34,57] |
| NURSE | 1.27 | 2.63 | [38,79] |
| INTERPRETER | 1 | 2 | [30,60] |
| APPOINTMENT | 2.3 | 4.4 | [69,132] |
| MEDICINE | 0.9 | 2.3 | [27,69] |
| STOMACH | 1.1 | 2.5 | [33,75] |
| HEADACHE | 0.9 | 2.47 | [27,75] |
| HAVE | 0.83 | 1.8 | [24,54] |
| NEED | 1 | 3.1 | [30,93] |
| WAIT | 0.9 | 2.8 | [27,84] |
| COME | 0.93 | 4.4 | [27,132] |
| HURT | 0.9 | 1.9 | [27,57] |
| BREATHE-DEEP | 1.4 | 2.8 | [42,84] |
| BLOOD-DRAW | 1.2 | 5.5 | [36,165] |
| TAKE | 1.7 | 2.6 | [51,78] |
| UNDERSTAND | 0.9 | 2.6 | [27,78] |
| WRITE | 0.9 | 2.3 | [27,69] |
| NOT | 0.9 | 2.27 | [27,69] |
| NOW | 0.9 | 1.7 | [27,51] |
| SOON | 0.9 | 2.9 | [27,87] |
| LATER | 0.9 | 1.7 | [27,51] |
| TOMORROW | 0.83 | 2.2 | [24,66] |
| MORNING | 0.87 | 2.27 | [26,69] |
| NIGHT | 1.3 | 2 | [39,60] |
| WHERE | 1.7 | 2.67 | [51,81] |

## 4. Existing implementation and expansion gaps

- `src/sign_robot/pair_windows.py:load_user_protections` already accepts arbitrary valid records and checks individual bindings, but does not enforce exactly 35 words. Add exact-set coverage checks at import.
- Pair planning, independent validation, incremental scanning and real-geometry endpoint screening exist. So do `sequence_contract.py`, `sequence_assembly.py`, `sequence_verification.py` and three sequence CLIs. Do not rebuild basic sequence support.
- `sequence_assembly.combinations()` materializes the entire Cartesian product before taking 64 entries. Its current limit does not bound enumeration memory. Larger pools require bounded order-preserving enumeration and equivalence tests.
- Sequence planning currently aborts all requested cases if any pair pool is unavailable. Expansion needs per-case missing/incomplete/no-numerical-candidate records and a fixed denominator. Corrupt identity must still reject the run.
- Protected-core joint limits, speed, coupling and sampled geometry have not been checked across all 35 words. Valid times do not imply valid motions; never trim protected frames or retime them to hide source defects.
- `--max-pairs` caps newly processed pairs, not all candidate-validation cost within each pair. Use batches, budgets and checkpoints. Existing COMPLETE verifications are skipped; rerunning the batch verifier is not a fresh independent recheck.

Current numerical policy scores retained margins and new transitions outside protected cores, and checks analytic connectors. Per-transition limits are 120 rad/s², 3000 rad/s³, 1,000,000 rad²/s⁵ and connector≤6 s. Protected-core acceleration/jerk are informational; whole-chain joint limits, speed, coupling, boundaries and sampled geometry still apply. Results do not certify global derivative continuity or continuous collision freedom.

## 5. Next stage and responsibilities

Follow [HANDOFF](HANDOFF.en.md): snapshot → strict 35-word import → full-word preflight → bounded combinations and blocked-case reporting → freeze all code/policies/cases → new 4-pair and 12-sequence regression → bounded coverage of 1,225 pairs → fixed 111-case sequence coverage and review. These new stages have not been executed.

The user identifies semantically indispensable motion; engineering owns trimming elsewhere, endpoints, timing, transitions and technical validation, with `window_provenance=algorithm`. Do not ask the user to certify technical windows. A real conflict between source defects and protected meaning requires specific word/frame evidence and a source-revision request, not silently altered user input.

Still incomplete: new import/results, remaining library coverage, human semantic viewing, cross-group engineering review, neutral start/end, fresh-environment reproduction, hardware and formal acceptance. Development numerical results cannot replace those independent acceptance steps. Formal flags remain off; this refresh performs no commit, publication or hardware action.
