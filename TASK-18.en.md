# TASK-18 — R4

[中文](TASK-18.md)

Status: implementation complete; final four-pair outcomes remain pending R5/R6. Automatic outer cuts follow protection bounds. Safety-screened endpoint pairs form an eight-item shortlist. Direct precedes neutral, IK, retract/approach and bounded RRT. Every timing curve, matched p/v/a boundary, analytic quality/limit/coupling and geometry check is saved. Only connectors are solved. Independently passing candidates rank by jerk, acceleration, connector jerk integral and full duration; legacy ranking remains unchanged.

First test run exited 1: 97 passed/3 failed, caused by the false assumption that all real pairs must have a passing direct candidate. Diagnosis found outward-pointing velocities at joint limits and quintic overshoot. Added tangent feasibility checks; tests now verify p/v/a on saved failed curves and retain rejection reasons without making them eligible. Final command: .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_user_protected_routes.py tests/test_user_protected_cuts.py tests/test_pair_routes_v2.py tests/test_pair_search_v2.py tests/test_pair_timing_v2.py tests/test_pair_fingers_v2.py tests/test_pair_runner_v2.py. Exit 0: 104 passed in 29.19s.

Reproduction: R4/diagnose_direct.py; direct_limit_diagnosis command/log exit 0. Initial failed test logs remain intact. Supplemental R3 screen exited 0: valid source/target counts COME→NOW 56/3; NOW→COME 1/28; COME→COME 56/28; NOW→NOW 1/3. See cut_screen_with_tangents.json; original evidence is preserved.

Decisions: direct is not presumed feasible; reject outward-limit tangents only in new mode. Divide the unchanged 30-second budget among route families and reserve bounded search. Eight shortlisted combinations are a work bound, not an infeasibility proof.

Deviations: R3 tangent screening was corrected based on real evidence, and an incorrect success assumption in new tests was fixed. No production threshold or protection was relaxed. Files/hashes are in changes.json.
