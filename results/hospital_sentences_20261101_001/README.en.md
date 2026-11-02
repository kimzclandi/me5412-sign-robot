# Nine hospital sentences: connector-only scope (2026-11-01)

[中文](README.md) · **English**

Development evidence only: formal PASS_SIM is 0, `formal_acceptance_enabled=false`, not verified ASL, no human review.

## User decisions

- Only the nine sentences the user gave; the full 1,225-pair scan is no longer pursued (hospital35 P1-3 stopped after
  46/79 batches, see below).
- Group 3 owns only the transition between two word motions. Problems of the source motion itself (collisions,
  over-speed and quality defects inside or around the protected cores) belong to group 2: reported, never gated.

## New versions (old versions unchanged)

| Item | Content |
|---|---|
| Review scope v4 | `CONNECTOR_ONLY_METHOD_V4` (`pair_contract.py`). Gates only the added connector: connector collision, joint limits, couplings, speed; interior finite-difference acceleration/jerk/jerk integral (frames whose 3-frame stencil lies inside the connector); analytic connector extrema; position/velocity/acceleration continuity with the source; protected cores bitwise unchanged. Source-slice findings go to `source_side_findings` (`informational_only`, owner group 2). v2/v3 behaviour unchanged. |
| Pair policy | `config/transition_policy_hospital_sentences_connector_only_v1.json`: the retry-budget policy (240 s per pair, RRT 80 s) + v4; every threshold value unchanged (checked by a test). |
| Sequence policy | `config/sequence_policy_hospital_sentences_v1.json`: the seven multi-word sentences; BREATHE-DEEP and THANK-YOU are single words with no connector. |
| Code | `pair_verification_v2.py`, `sequence_verification.py` (v4 branch); `plan_sequences.py` accepts repeated `--pair-run-dir` (each pair is read from the one run that planned it; single-run behaviour unchanged). |
| Tests | New `tests/test_connector_only_v4.py` (5); full suite **967 passed** (`tests/pytest_full.log`). |

## Results

Four same-identity runs in parallel (WSL2, cpu0-3, 13:54-14:28). Pairs:

| Pair | Run | Attempts | Candidates | Pass | Selected |
|---|---|---|---|---|---|
| HELLO→YOU | 001 | 86 | 25 | 25 | attempt_00033 |
| YOU→APPOINTMENT | 002 | 72 | 3 | 3 | attempt_00063 |
| APPOINTMENT→HAVE | 002 | 73 | 8 | 8 | attempt_00060 |
| YOU→NEED | 002 | 63 | 20 | 20 | attempt_00051 |
| NEED→INTERPRETER | 004 | 121 | 75 | 75 | attempt_00002 |
| PLEASE→WAIT | 003 | 92 | 0 | 0 | — |
| WAIT→DOCTOR | 003 | 78 | 0 | 0 | — |
| DOCTOR→COME | 003 | 129 | 89 | 89 | attempt_00031 |
| COME→SOON | 001 | 112 | 91 | 91 | attempt_00026 |
| YOU→HURT | 001 | 72 | 0 | 0 | — |
| HURT→WHERE | 001 | 120 | 75 | 75 | attempt_00026 |
| NOW→NURSE | 004 | 74 | 16 | 16 | attempt_00009 |
| NURSE→BLOOD-DRAW | 004 | 68 | 0 | 0 | — |
| MEDICINE→MORNING | 001 | 59 | 0 | 0 | — |
| MORNING→NIGHT | 002 | 79 | 7 | 7 | attempt_00023 |
| NIGHT→TAKE | 003 | 82 | 2 | 2 | attempt_00025 |
| YOU→UNDERSTAND | 004 | 86 | 45 | 45 | attempt_00051 |

A fresh independent recheck of all 12 selected candidates agrees (`selected_recheck_00[1-4]/summary.json`).

Sentences (`sequences/summary.json`; recheck `verify_sequences.log`, 3/3 agree):

| Sentence | Status |
|---|---|
| HELLO YOU APPOINTMENT HAVE | NUMERICAL_PASS |
| YOU NEED INTERPRETER | NUMERICAL_PASS |
| YOU UNDERSTAND | NUMERICAL_PASS |
| PLEASE WAIT DOCTOR COME SOON | BLOCKED_DEPENDENCY (PLEASE→WAIT, WAIT→DOCTOR) |
| YOU HURT WHERE | BLOCKED_DEPENDENCY (YOU→HURT) |
| NOW NURSE BLOOD-DRAW | BLOCKED_DEPENDENCY (NURSE→BLOOD-DRAW) |
| MEDICINE MORNING NIGHT TAKE | BLOCKED_DEPENDENCY (MEDICINE→MORNING) |
| BREATHE-DEEP, THANK-YOU | Single words, no connector; the source motion plays as is |

## Why five pairs have no candidate

Planning checks only the connector. Almost every attempt ends `TIMING_MAXIMUM_DURATION_REACHED`: after each failed
timing (mostly `GEOMETRY_AFTER_TIMING_FAILED` collisions on the first connector segment and
`TIMED_CURVE_JOINT_LIMIT_VIOLATION`) the duration grows until it exceeds 6 s. The connector must match the source's
velocity at the cut; while the source is still moving fast, a longer quintic carries further along that velocity, so a
larger budget does not help (the same pairs fail at 240 s as at 30 s; only YOU→APPOINTMENT was solved by budget).
Proposed next version: a short segment that brakes to zero within the acceleration/jerk limits, then the route, and the
mirror on entry. Not implemented.

## Reproduce

```bash
.venv/bin/python results/hospital_sentences_20261101_001/make_inputs.py   # writes only files that do not exist
bash results/hospital_sentences_20261101_001/run.sh
```

## Deviations and unverified limits

- **Videos**: WSL lacks the Noto CJK font hard-coded in `render_sequences.py` (no sudo), so it ran through
  `render_with_windows_font.py` (only the label font becomes Windows Microsoft YaHei; no identity-bound script edited).
  `videos_001/` stopped at a 20-minute timeout: the first two sentences are complete, `videos_001/YOU__UNDERSTAND` is
  partial; the second attempt in `videos_002/` was stopped before the commit at the user's request and is partial too.
  YOU UNDERSTAND has no complete video yet; after the commit it must be rendered from a new run. Videos are not
  committed (user decision). Not watched by a person.
- **Identity**: the runs' `code_commit` is 2875e49 (uncommitted working tree). This directory is committed afterwards;
  the runs cannot be resumed or rechecked on the new HEAD. New runs are needed.
- **hospital35 main scan**: after the WSL move P1-3 stopped at 46/79 batches (plus fresh BATCH_COMPLETE logs for
  rest_018-020). Runs 001/003/004 failed the replay of the pair interrupted by the crash (wall-clock-limited attempts 3+;
  attempts 1-2 bitwise equal); I twice launched in the wrong order, leaving some `BACKLOG_NOT_CLEARED` invocation logs
  (append-only, no results changed); run 002 was stopped gracefully after the user changed scope. The handoff's
  `resume.sh` is refused the same way while a backlog exists. Raw `pair_runs` stay local.
- Sampled collision checks are not a continuous-collision proof; TIMEOUT/no candidate does not prove no connector exists.
