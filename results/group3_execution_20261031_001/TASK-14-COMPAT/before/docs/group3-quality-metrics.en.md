# P0-4 quality metrics and threshold approval sheet

[中文](group3-quality-metrics.md) · [Execution report](../TASK-04.en.md)

Formal freeze: **pending**. This task makes “smooth” reproducible with metrics, units and directions. It does not modify transition_policy.json or create PASS_SIM.

## Metric contract

| Metric | Algorithm and scope | Unit | Direction / limitation |
|---|---|---|---|
| `velocity_jump_*` | One-sided five-frame quadratic least-squares boundary velocity versus the connector's declared zero endpoint velocity; max absolute value per arm/finger | rad/s | Lower is better; source replay corners are not hidden by the connector model |
| `acceleration_jump_*` | Same boundary fit versus zero connector acceleration | rad/s² | Lower is better; not proof of continuous source derivatives |
| `peak_acceleration` | `gradient(gradient(q,t),t)` over the full saved trajectory at actual timestamps, `edge_order=2` | rad/s² | Lower is better; includes discrete word-boundary effects |
| `peak_jerk` | One more timestamp-aware gradient of acceleration | rad/s³ | Lower is better; continuous jerk at linear-replay knots is undefined |
| `jerk_integral` | `trapezoid(sum(jerk²), t)` over the saved trajectory | rad²/s⁵ | Lower is better; finite-difference energy, not dynamics cost |
| `analytic_connector_*` | Analytic derivative extrema and squared-jerk integral per quintic segment; recompute after retiming | Corresponding SI angular units | Lower is better; never reuse stale values |
| `maximum_transition_duration_s` | Last minus first connector timestamp | s | Must be below a frozen cap; budget exhaustion is TIMEOUT |
| position/limit/coupling errors | Recompute saved arrays; max absolute or out-of-range errors | rad | Independent contract; metadata alone is insufficient |

Boundary fits use actual source `[frame-window+1, frame]` and target `[frame, frame+window-1]` times; too few samples fail. Every result stores time base, window and method. Discrete jerk is never described as a continuous physical guarantee.

## Development recomputation

All 899 saved candidates were rebuilt through the metric functions; every p50/p95/p99/max matches the existing quality_development_metrics.json. Key values are in the paired Chinese table and in quality_metrics_recomputed.json. They are observed development data, not held-out acceptance or threshold approval. Analytic connector statistics are saved separately.

## Pending threshold proposal

`quality_threshold_proposal.json` remains `freeze_status=pending`. It proposes 1e-5 rad/s and 1e-4 rad/s² boundary tolerances plus finite engineering caps organized around a 1 rad, 0.3 s quintic reference, numerical margins and safety ceilings; values are explicitly not fitted to observed pass rates. Applying them to the current piecewise-linear word replay would reject candidates, which identifies an input/representation gap rather than a reason to loosen limits.

Approval must decide whether source clips may be continuousized or retimed, whether cores/windows may change, whether finite differences are acceptable instead of continuous derivatives, and how finger coupling, dynamics and hardware limits enter. Any change requires a new policy version and run_id.

## Validation

`audit_p0_4.py` asserted all 899 candidate recomputations, all 35 word checks and three analytic cases, exit 0. For a 1 rad / 1 s quintic it checks peak speed 1.875 rad/s, peak acceleration `10/√3` rad/s², peak jerk 60 rad/s³ and jerk integral 720 rad²/s⁵, including independent 100001-point quadrature. Full pytest was not rerun; this task validates metric algorithms and units.


The v2 proposal uses exact one-sided interval velocity of linear replay (adjacent-sample secant) and zero within-interval acceleration at boundaries. The v1 five-frame quadratic fit remains a legacy diagnostic, not the true continuous source derivative. This difference must be versioned in the contract and measurement policy.

| 指标 / Metric | 提案上限 / Proposed cap | 单位 / Unit |
|---|---:|---|
| `velocity_jump_arm_rad_s` | 1e-05 | rad/s |
| `velocity_jump_finger_rad_s` | 1e-05 | rad/s |
| `acceleration_jump_arm_rad_s2` | 0.0001 | rad/s² |
| `acceleration_jump_finger_rad_s2` | 0.0001 | rad/s² |
| `peak_acceleration_rad_s2` | 120 | rad/s² |
| `peak_jerk_rad_s3` | 3000 | rad/s³ |
| `jerk_integral_rad2_s5` | 1e+06 | rad²/s⁵ |
| `maximum_transition_duration_s` | 6 | s |

Observed development statistics (units defined above):

| 指标 | p50 | p95 | p99 | max |
|---|---:|---:|---:|---:|
| peak arm speed | 15.000000 | 24.999940 | 24.999940 | 24.999940 |
| peak finger speed | 10.000000 | 21.169373 | 25.349300 | 25.349300 |
| peak acceleration | 225.000000 | 374.377234 | 400.741645 | 407.951790 |
| peak jerk | 5853.456528 | 10576.667495 | 11626.783186 | 11734.935362 |
| velocity jump | 8.068215 | 17.886287 | 33.276591 | 33.276591 |
| acceleration jump | 104.735395 | 190.816472 | 317.586360 | 317.586360 |
| jerk integral | 45,779,096.58 | 94,242,015.80 | 115,008,347.67 | 136,104,424.42 |
| transition duration (s) | 0.300000 | 0.400000 | 0.433333 | 0.566667 |
