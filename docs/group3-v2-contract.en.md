# P0-5 v2 trajectory and input contract

[中文](group3-v2-contract.md) · [Execution report](../TASK-05.en.md)

State: **complete (contract and rejection logic)**. v2 supplies versioned representation, structural validation and integrity binding; formal core/window, quality and collision approval and PASS_SIM remain disabled.

## Files and dispatch

The v1 policy and NPZ runner remain the default: `load_policy()` accepts schema 1 by default. `config/transition_policy_v2.json` is opt-in through `supported_versions=(1,2)` and keeps formal acceptance disabled with all three approvals pending. `contracts/all_pairs_v2.json` is hash-bound by the policy. `read_pair_trajectory(..., schema_version=1)` reads legacy NPZ; schema 2 reads the integrity envelope and verifies `trajectory_hash`.

## Representation

A candidate has 53 named coordinates at 30 Hz, two explicit word instances (including two self-pair occurrences), ordered segments and boundary states. The first/last segments must preserve original source slices, motion hashes, protected-core hints, approval references and time_scale=1.0. Middle `polynomial_v2` segments store six ascending coefficients per coordinate in normalized u and require position/velocity/acceleration continuity. Multiple connector segments and nonzero boundary derivatives are expressible. Finger strategies are versioned synchronous/early/late phases; coupling and geometry checks are later P1 work.

Identity binds library/model/commit/code/policy/environment hashes. Planner method, seed, candidate/collision/node/segment/attempt counts and wall time are finite. P1-7 connects direct, neutral, ik_via1, ik_via2, retract_approach and rrt_connect through the [multi-candidate development runner](group3-multicandidate-runner-v2.en.md); formal acceptance remains disabled.

## Rejections and validation

Unknown versions/representations/kinds, NaN or boolean values, noncontiguous time, malformed hashes, protected-core loss, missing self occurrences, changed word timing, inconsistent boundary/C2 states, nonpositive budgets, coarser sampling limits, absent approval evidence or formal-acceptance enablement raise explicit errors. A status string cannot create approval.

Ran in the restored staging checkout with the target `.venv`, `-p no:cacheprovider`: `tests/test_pair_contract_v2.py tests/test_all_pairs_contract.py tests/test_all_pairs_pipeline.py`, exit 0, **80 passed**. The suite covers v1 readability, v2 round trips, nonzero boundaries, self pairs, integrity/boundary separation, malformed versions and values, and legacy pipeline behavior. Commands and logs are under `results/group3_execution_20261031_001/P0-5/`.

P0-5 does not modify v1 policy, old results or motion assets and does not present v2 as approved. P1-1 next reads actual approved windows; without them it must return an explicit block.
