# P1-2 independent v2 verifier

[中文](group3-independent-verifier-v2.md) · [Task report](../TASK-07.en.md)

`pair_verification_v2.py` reconstructs only from the saved v2 integrity envelope, original word NPZ files and declared polynomials. It does not call planners, candidate generators or legacy pass status. It refreshes model/clearance state and checks word slices, approval hashes, boundaries, limits, coupling, speed, quality and dense geometry.

Statuses separate blocked inputs, corrupted contracts, budget `TIMEOUT`, reconstructed collision `FAILED_SEARCH` and completed-but-unaccepted `FAILED_QUALITY`. Each segment is subdivided under 1/120 s and 0.04 rad bounds using analytic speed limits; pose/native-call/time budgets are reserved before queries and progress records retain segment, factor, curve time and worst pair. A finite sample result still declares continuous_collision_certified=false.

Connector extrema and squared-jerk integrals are analytic; source linear replay uses finite differences at 30 Hz, with no continuous-derivative claim. Pending quality/window/collision approvals prevent PASS_SIM.

Actual staging validation used the target `.venv` and no pytest cache: `tests/test_pair_verification_v2.py tests/test_pair_contract_v2.py tests/test_pair_windows_v2.py tests/test_all_pairs_pipeline.py`, final exit 0, **91 passed in 3.39s**. Cases cover valid reconstruction, synthetic between-frame collision, pose/native/time budget stops, motion/approval changes, unknown representation, C2/boundary failures and two self-pair instances. No historical v1 run is upgraded.

The real v2 policy still has no approval_file, so real inputs stop at MISSING_APPROVAL_BUNDLE. P1-2 completes the verifier/diagnostic loop; P1-3 implements boundary derivative/time parameterization next.
