# P1-5 deterministic v2 candidate adapters

[中文](group3-deterministic-routes-v2.md) · [Task report](../TASK-10.en.md)

`pair_routes.py` unifies direct, neutral, ik_via1, ik_via2 and retract_approach. Each attempt retains role frames, approval references, route knots/hash, parameters, guide checks, finger strategy, every timed curve/hash, quality/geometry results and shared candidate/pose/node/time budgets.

Only reviewed hash-bound windows are enumerated, then filtered under absolute +2 mm clearance, joint limits and coupling. Legacy hard-coded trims, pair preferences and relative endpoint floors are not inherited. Directions and self occurrences remain separate. Generation never writes PASS_SIM; candidates remain pending independent verification.

Neutral/IK primitives are reused but their complete timed polynomials are resampled. Factory errors are saved before other independent families continue. Retract/approach first densely checks the complete original geometry guides, then uses at most four guide knots each and checks the final curve; these are connector guides, not retimed protected word slices. Guide collisions cannot be hidden by knot reduction.

Wall time is checked at primitive and collision-batch boundaries. A single underlying IK call relies on its finite iterations and is not a hard realtime interruption. Actual all-pairs cost and success still require approved inputs and formal runs.

Actual staging route/timing/verifier/contract command: final exit 0, **73 passed in 12.88s**. Cases include direct/required-detour geometry, invalid endpoints, retract-slice collision, factory-error continuation, candidate-budget stops, self pairs and stable hashes excluding runtime. Real input remains blocked by the missing approval bundle.
