# P1-3 boundary derivatives and time parameterization

[中文](group3-pair-timing-v2.md) · [Task report](../TASK-08.en.md)

`pair_timing.py` reads exact one-sided secant velocities and zero within-interval acceleration from unchanged source clips. It solves normalized quintics for fixed p/v/a and resolves coefficients after every duration increase, rechecking analytic position ranges, speed/acceleration/jerk, squared-jerk integral, coupling and duration. Interior route knots use zero velocity/acceleration for C2 joins.

Durations are quantized at 30 Hz. Every retry stores duration, metrics, reasons and optional geometry evidence. Geometry callbacks run on every freshly solved curve; without a callback, geometry_checked=false and the result is only TIMED_CANDIDATE, still requiring the independent full-clip verifier. No old collision/derivative result or source timing is reused.

Boundary overspeed, out-of-range knots, invalid inputs, finite-attempt exhaustion, maximum duration and wall-clock exhaustion are distinct diagnostics, not a proof of infeasibility. Equal positions with different derivatives may require a nonzero connector; zero distance still retains finite time.

Actually ran the timing/verifier/contract suites in staging with the target `.venv` and no pytest cache: final exit 0, **61 passed in 0.38s**. Cases include nonzero p/v/a, independent saved-file rereading, equal positions/different derivatives, zero distance, short/limited duration, new overshoot after retiming, fresh geometry checks and timeouts. One initial test-side matrix-evaluation orientation error caused 1 failure/52 passes; the test was corrected and logs retained without changing engineering thresholds.
