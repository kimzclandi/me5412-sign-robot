# TASK-23 — v3 quality scope: score transitions only, check protected cores for invariance

[中文](TASK-23.md) · [Current state](STATE.en.md) · [Previous v2 report](TASK-22.en.md)

**v3 implemented and all four pairs rerun: numerical pass 1/4 (NOW→COME); formal PASS_SIM is still 0.** 804 tests passed (799 existing + 5 new). Formal acceptance stays false and no threshold changed.

## Decision and reason

On 2026-10-31 the user chose “Score transitions only”. TASK-22 showed that the protected original words themselves exceed the quality limits (NOW f6–73 squared-jerk integral 38,213,419 > 1,000,000, f31 acceleration 206.8 > 120, f37 jerk 4889.6 > 3000; COME f30–129 integral 1,479,273 > 1,000,000). Since original words may not be modified, whole-clip scoring made every transition fail.

## v3 definition

- New policy `config/transition_policy_user_protected_v3.json` (SHA-256 `d0b0209e54a5d5c366285afd78a7bca9ce67f84f90c291c8f7a6eb9c181e9612`). Compared with v2 it changes only `policy_id` and `quality.full_clip_method` = `finite_difference_30hz_outside_protected_cores_and_analytic_connector_v3`. Every threshold, constraint, budget, endpoint rule and the formal switch are unchanged.
- Peak acceleration, peak jerk and squared-jerk integral are computed only on replay frames **outside protected cores** (the transition plus non-protected source edges the algorithm keeps). The integral sums only intervals whose two endpoints are both scored. Finite-difference stencils still read up to 2–3 protected frames at each boundary, so junction discontinuities are still counted.
- Acceleration/jerk defects inside protected cores are still written to `protected_source_audit`, marked `excluded_from_quality_gate`, and no longer fail the pair. Speed, joint-limit and coupling defects inside cores still fail.
- Speed, limits, coupling, collision (+2 mm), boundary continuity, finger phase, bitwise-equal protected poses and unchanged relative timing are still checked on the whole clip. Unscoped whole-clip metrics are kept in `full_clip_unscoped_metrics` for reference only.
- v3 is accepted only with `user_protected_auto_windows_v1`; human-window policies reject it. The v2 path is numerically bit-identical.

Code: `src/sign_robot/pair_contract.py`, `src/sign_robot/pair_verification_v2.py`; tests `tests/test_transition_scope_v3.py`. The planner is unchanged.

## Four-pair results (run `transition_scope_pilot_20261031_001`)

| Pair | Status | Candidates / numerical pass | Notes |
|---|---|---:|---|
| NOW→COME | Numerical pass (formal pending) | 20 / 20 | Selected attempt_00002: direct, synchronous fingers, cuts NOW 77 / COME 23, 0.5 s transition; scoped acceleration 44.78, jerk 786.5, integral 586,690; clearance 8.085 mm |
| COME→COME | FAILED_QUALITY | 58 / 0 | All fail only on the integral; best 1,908,672. Split: the transition itself is about 0.7k–290k; about 1.84M–1.91M comes from the non-protected COME tail kept by the planner (frames 133→177/200) |
| COME→NOW | TIMEOUT | 0 / 0 | Planning timed out (RRT/timing wall-time limit); unrelated to scoring scope |
| NOW→NOW | TIMEOUT | 0 / 0 | Same as above |

The full-library denominator remains 1,225 (1,190 distinct / 35 self): 1 numerical pass awaiting formal approval, 1 FAILED_QUALITY, 2 TIMEOUT, 1,221 NOT_RUN, 0 PASS_SIM.

## Next blocker found

The cut shortlist ranking `endpoint_pairs_v1` (`src/sign_robot/pair_routes.py`) sorts by boundary speed before retained length, so it favours slow late COME frames and keeps a jerky original tail. Changing it is a new planner version and was not done this round. The two TIMEOUTs need a separate look at planning budget or routes.

## Commands

```bash
.venv/bin/python scripts/plan_all_pairs.py --library hospital_v1 --include-self --policy config/transition_policy_user_protected_v3.json --run-id transition_scope_pilot_20261031_001 --results-root results/user_protected_transition_scope_20261031_001/runs --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW
```

```bash
.venv/bin/python scripts/verify_all_pairs.py --run-id transition_scope_pilot_20261031_001 --results-root results/user_protected_transition_scope_20261031_001/runs
```

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider tests
```

Actual: planning + verification took 11 min 32 s, exit 0; log `results/user_protected_transition_scope_20261031_001/run.log`. pytest: 804 passed in 77.53s.

## Unverified limits

- v3 is a development policy (`freeze_status: pending`), not a frozen formal acceptance agreed by the three groups; the scope change needs cross-review.
- NOW→COME has only 19 scored frames (180 protected frames excluded), so the result covers only the region around the transition.
- No videos were exported this round; no human viewing, ASL understandability, multi-word composition, fresh-environment reproduction or hardware run.
- Nothing committed to git; v2 results, original motions and models were not modified.
