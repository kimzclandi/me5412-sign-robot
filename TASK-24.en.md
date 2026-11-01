# TASK-24 — v4 cut ranking: prefer retained source edges with low jerk

[中文](TASK-24.md) · [Current state](STATE.en.md) · [Previous v3 report](TASK-23.en.md)

**v4 implemented and all four pairs rerun: numerical pass 2/4 (NOW→COME, COME→COME); formal PASS_SIM is still 0.** 808 tests passed (804 after v3 + 4 new). Thresholds, scoring scope and the formal switch are unchanged.

## Problem and change

TASK-23 found that all 58 COME→COME candidates failed. The transition's own integral was small; about 1.84M–1.91M came from the non-protected COME tail kept by the planner. The cut shortlist ranking `endpoint_pairs_v1` sorted by boundary speed before retained length, so it favoured slow late COME frames 177/200.

The user chose “Fix cut ranking”. New version:

- New policy `config/transition_policy_user_protected_v4.json` (SHA-256 `de13b9f4e07378bd0226b837d261738463228887e32cbbfc5c0ba8dff7fcc9a9`). Compared with v3 it changes only `policy_id` and `endpoints.generator_version` = `protected_cut_search_v2`.
- `retained_edge_jerk_v2` (`src/sign_robot/pair_routes.py`) estimates the squared-jerk integral of the original frames kept between the protected core and the cut, using the verifier's 30 Hz finite-difference stencil.
- Under the v2 cut generator the shortlist order is: limit-violation estimate → **retained-edge jerk estimate** → boundary speed → displacement → retained length. The old v1 generator (v2/v3 policies) keeps its order.
- `protected_cut_search_v2` is accepted only with the v3 scoring scope; any other combination is rejected.
- This is only a ranking estimate; saved trajectories are still fully recomputed from file by the independent verifier.

Shortlist comparison (v3 → v4 first-choice cuts): COME→COME (177,23) → (132,27); COME→NOW (145,1) → (132,1); NOW→COME (77,23) → (76,27); NOW→NOW (82,2) → (76,3).

## Four-pair results (run `edge_aware_cuts_pilot_20261031_001`)

| Pair | Status | Candidates / numerical pass | Selected candidate |
|---|---|---:|---|
| NOW→COME | Numerical pass (formal pending) | 17 / 17 | attempt_00023: rrt_connect, late fingers, cuts NOW 77 / COME 27, 0.8 s transition; scoped acceleration 31.71, jerk 317.3, integral 216,253; clearance 8.085 mm |
| COME→COME | Numerical pass (formal pending) | 13 / 13 | attempt_00003: direct, early fingers, cuts COME 132 / COME 27 (both exactly at the protected bounds), 0.733 s transition; acceleration 40.65, jerk 442.6, integral 254,410; clearance 4.711 mm |
| COME→NOW | TIMEOUT | 0 / 0 | Planning wall-time limit; no candidate produced |
| NOW→NOW | TIMEOUT | 0 / 0 | Same as above |

Full-library denominator 1,225 (1,190 distinct / 35 self): 2 numerical passes awaiting formal approval, 2 TIMEOUT, 1,221 NOT_RUN, 0 PASS_SIM.

## Commands

```bash
.venv/bin/python scripts/plan_all_pairs.py --library hospital_v1 --include-self --policy config/transition_policy_user_protected_v4.json --run-id edge_aware_cuts_pilot_20261031_001 --results-root results/user_protected_edge_aware_cuts_20261031_001/runs --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW
```

```bash
.venv/bin/python scripts/verify_all_pairs.py --run-id edge_aware_cuts_pilot_20261031_001 --results-root results/user_protected_edge_aware_cuts_20261031_001/runs
```

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider tests
```

Actual: planning + verification took 5 min 9 s, exit 0; log `results/user_protected_edge_aware_cuts_20261031_001/run.log`. pytest: 808 passed. New tests in `tests/test_edge_aware_cuts_v4.py`. Also: because TASK-23 added rows to `docs/README*.md`, the two pinned index hashes in `src/sign_robot/project_overview.py` were updated.

## Next blocker and unverified limits

- COME→NOW and NOW→NOW time out in planning, independent of scoring and cuts; they need a separate look (RRT/timing wall time, NOW start-segment geometry).
- v3/v4 are development policies (`freeze_status: pending`); the scoring scope and cut rule need cross-review.
- Very few scored frames (NOW→COME 24, COME→COME 21), so results cover only the region around the transition.
- No videos were exported this round; no human viewing, ASL understandability, multi-word composition, fresh-environment reproduction or hardware run.
- Nothing committed to git; v2/v3 results, original motions and models were not modified.
