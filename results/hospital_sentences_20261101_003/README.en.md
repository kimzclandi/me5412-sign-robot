# Nine hospital sentences, round 3: faster transitions + return to rest (2026-11-01)

[中文](README.md) · **English**

Development evidence only: formal PASS_SIM is 0, `formal_acceptance_enabled=false`, not verified ASL, no human review.
**Superseded by round 4** ([`../hospital_sentences_20261101_004/README.en.md`](../hospital_sentences_20261101_004/README.en.md)),
which reruns the same inputs after a fix to the rest-tail search. Kept as evidence of the failure below.

Code `0b2528d`: pair selection by fewest frames between the protected cores (`numerical_pass_then_core_gap_then_smoothness_v1`)
and a planned return to the library rest pose after the last word (`rest_tail_v1`). Inputs: `make_inputs.py`; run:
`run.sh` (16 pair runs on cpu0-15, 19:56-20:32).

## Result: 6/7 sentences NUMERICAL_PASS

- 17/17 selected pair connectors agree on a fresh recheck (`selected_recheck_*/summary.json`).
- 6 sentences pass the independent sequence recheck, 21/21 protected cores bitwise unchanged (`verify_sequences.log`).
- **YOU NEED INTERPRETER: BLOCKED_DEPENDENCY**. The INTERPRETER rest tail (`sequences/rest_tails/INTERPRETER.json`)
  found nothing: at exit frames 60-61, right after the protected core, the fingers still move fast toward a joint
  limit. Every one of the 25 routes at those two frames timed out at the 6 s duration limit, and together they used
  up the 262144 collision samples before the later, slower frames were reached.
- Fix (round 4): try the two straight routes (direct, via neutral) at every exit frame first, then the detours only
  where they can still win. Same inputs, INTERPRETER: 15-frame direct tail at frame 67.
