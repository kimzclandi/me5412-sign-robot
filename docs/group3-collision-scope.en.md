# P0-3 collision coverage and sampling proposal

[中文](group3-collision-scope.md) · [Execution report](../TASK-03.en.md)

Approval: **pending**. This audit and v2 proposal do not modify filtering, assets or formal limits.

| Layer | Current behavior | Exclusion or limitation |
|---|---|---|
| Model | 122 geoms, including 60 with contype=conaffinity=0 | Visual geoms disabled by the delivered model remain unchanged |
| Native eligibility | Current MuJoCo mj_collision; 0 explicit pairs, 0 excludes | Engine mask/body/parent/type rules remain in control; full geom inventory is in JSON |
| Same hand | Names L_/R_ and left_wrist/right_wrist determine side | Excludes every same-side finger/wrist combination, including nonadjacent fingers; needs human scope approval |
| Static classification | Aggregate spans from 35 words / 4,560 frames; IK arm and unknown joints conservatively moving; 136 equal-moving-ancestor body pairs | Not in the moving +2 mm gate; 47 measurable vendor geom pairs reported separately; changing a library-constant joint is rejected |
| Moving geometry | Native-eligible cross-hand, arm, torso and mount pairs | No hospital environment, humans, dynamics, controller error or hardware coverage |
| Detection margin | 2/10/50/250 mm then scene span+1 m until eligible moving contacts appear | finally restores geom/pair margins, masks unchanged; static vendor gaps remeasured with mj_geomDistance |
| Sampling | Actual quintic connector and linear source replay; 1x/2x/4x and 0.04 rad coordinate bound | Sampled geometry only; original word audit is 1x; no continuous guarantee |
| Budget | Planner: 2,048 poses and 30 s for one direct candidate | Current independent verifier has no separate pose/time budget |

A scene-spanning reference-pose query observed 840 retained moving geom pairs, 174 excluded same-hand pairs and 47 separate static pairs. This is a reference-pose observation, not proof of exhaustive native eligibility at every pose.

## Pending v2 sampling proposal

Retain +2 mm, native filters and 0.04 rad coordinate bound. Check at least 1x/2x/4x and time steps no larger than 1/120 s. Use analytic/interval derivative bounds for polynomial subdivision rather than endpoint deltas; include all segment boundaries. Retain complete mapped source intervals and reconstruct/recheck the final saved curve after retiming or shortcuts.

Proposed per-verification caps: 65,536 sampled poses, 327,680 native collision calls, 30 s and subdivision depth 16. Check budgets before allocating arrays. Budget exhaustion, nonfinite data, unsupported representation, changed constant coordinates, missing hashes/approvals or incomplete coverage can never yield PASS_SIM; retain TIMEOUT or explicit incomplete evidence. A completed finite sample audit still declares continuous_collision_certified=false. This is a proposal for the v2 contract; P1-2 will implement it, and human approval is needed before formal use.

## Actual verification

Independently reconstructed and remeasured all 11 known between-frame connector counterexamples. Every one has playback clearance ≥2 mm and dense clearance <2 mm; historical minima match within 1e-6 mm. DOCTOR→NURSE changes from +8.011922 to -25.851034 mm. This covers those connectors only, not a new full matrix or complete-pair acceptance.

Actually ran tests/test_plan_transitions.py and tests/test_transition_endpoint_gate.py: 230 passed, one read-only pytest-cache warning, exit 0. Existing real-sphere geometry cases cover positive/negative distances, same-hand exclusions, mandatory cross-hand/torso detection, static topology, endpoints and restoration of margins/masks. Logs, commands, model inventory and counterexamples are under results/group3_execution_20261031_001/P0-3/.
