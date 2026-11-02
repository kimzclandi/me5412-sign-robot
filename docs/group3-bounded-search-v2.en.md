# P1-6 general bounded RRT

[中文](group3-bounded-search-v2.md) · [Task report](../TASK-11.en.md)

`pair_search.py` has no gloss-pair allowlist. The finite space includes limited arm joints and independent L_/R_ fingers. Coupled children are reconstructed and their limits tighten parent bounds; fixed non-actuated coordinates cannot change. Full endpoint limits/coupling are checked first.

Fixed-seed bidirectional RRT-Connect uses node, collision-pose, candidate and cooperative wall-clock budgets. Edges use at most 0.04 rad coordinate steps. Equal arms with different fingers retain an actual search dimension, avoiding the old arm-progress degeneracy. Failure means not found within finite work, never mathematical infeasibility.

Raw/shortcut paths, control names/bounds, hashes, seed and budgets are retained. Every shortcut edge and final timed/finger curve is rechecked; failed shortcuts retain a raw fallback. A checked linear raw path is not a final curve or formal PASS; independent verification remains required.

Actual staging command covers new search, legacy RRT, timing and route suites: final exit 0, **56 passed in 13.34s**. Cases cover seeded obstacle detours, pure fingers, coupled limits, tiny work/time budgets, fixed-coordinate rejection, no old allowlist and faulty-shortcut/raw fallback. Initial new-test clock-sequence and fixed-coordinate fixture errors were corrected with failed logs retained. No real matrix was run and all formal approvals remain pending.
