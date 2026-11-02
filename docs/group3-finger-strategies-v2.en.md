# P1-4 constrained finger timing and coupling

[中文](group3-finger-strategies-v2.md) · [Task report](../TASK-09.en.md)

`pair_fingers.py` implements synchronous/early/late versioned strategies on saved polynomial segments. Synchronous retains the original finger route; early compresses it into the first 65%, late into the last 65%. Existing finger knots remain, while the entire arm/fixed-coordinate curve is preserved by exact affine polynomial substitution, not only at samples.

Nonzero boundary derivatives require a short same-pose prefix/tail matching original p/v/a instead of a stationary hold. These extra curves may overshoot or collide, so every timing attempt recalculates analytic metrics and requires fresh geometry.

Coupled children are excluded from drivers and their coefficients restored topologically from parent, multiplier and offset. Cycles, duplicate children, missing joints, nonfinite values and invalid endpoint/derivative coupling fail. Pure-finger changes remain expressible.

Timing applies the strategy before rechecking all connector constraints. The independent verifier rereads phase position/velocity/acceleration from the saved curve at 0.65/0.35, so a label alone is insufficient. Source cores and timing are unchanged.

Actual staging test command covers finger/timing/verifier/contract suites: final exit 0, **81 passed in 0.53s**. Cases cover coupling/endpoints, phase differences, pure fingers, nonzero derivatives, preservation of the full arm curve and intermediate finger knots, crossing collisions and false strategy labels. Initial 5 failures/8 passes came from stale linear-preview and invalid-endpoint fixtures; implementation was unified around polynomials, fixtures corrected, failure logs retained and physical thresholds unchanged.
