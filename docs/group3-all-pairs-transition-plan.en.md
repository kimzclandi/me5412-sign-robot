# Group 3 Task Plan for Transitions Between Every Word Pair

[中文版](group3-all-pairs-transition-plan.md)

- Version: 1.0
- Date: October 31, 2026
- Project: ME5412 hospital communication robot signing research prototype
- Team: two Group 3 members, with implementation and cross-review responsibilities
- Baseline: `group3/r13c`, commit `2875e499d79b7264b3fe0414318b30ca8aab1f4d`
- Purpose: implementation and acceptance plan. New interfaces, files and commands described here are proposed work, not existing capabilities.
- Checkout: `/home/kingderman/Documents/ME5412-github-latest`

## 1 Objective and delivery scope

Group 3 will build a general transition module. Given two registered robot word motions and their permitted entry and departure conditions, it generates a connecting trajectory and an independently verifiable result. Every result must explain whether an acceptable transition was found, why it passed or failed, and how to reproduce it.

This version freezes the 35 hospital words delivered by Group 2. The default scope includes both different words and repeated words: **35 × 35 = 1,225 ordered pairs**, comprising 1,190 different-word pairs and 35 self-pairs. Report both subsets separately. Excluding repetition requires a recorded scope change, not removal from the denominator after evaluation.

`A → B` and `B → A` are separate tasks. Testing `A → A` must preserve both word occurrences and their required boundary; deleting an occurrence or validating only a zero-length connector does not count.

“Every pair” refers to this frozen vocabulary. Unknown words return unsupported, and new vocabulary requires incremental validation. A kinematically connectable pair does not establish a grammatical sign-language sentence.

### 1.1 Completion levels

| Level | Required evidence | Permitted claim |
|---|---|---|
| L1 Coverage and diagnosis | Every pair has a completed run or explicit blocking, timeout or error record | The entire pair space has been scanned |
| L2 Simulation transitions | All 1,225 pairs satisfy frozen geometry, limit, coupling, boundary and smoothness criteria | Every pair passes the specified simulation checks for this library and model |
| L3 Composition and comprehension | Specified multiword checks and qualified human review are complete | Composition and comprehension claims within the reviewed scope |
| L4 Hardware execution | Hardware constraints, control, dynamics and controlled experiments pass | Execution only on the validated device under validated conditions |

The core engineering target is L2, together with multiword engineering acceptance. Language review requires appropriate reviewers. Hardware execution is a separate workstream. L1 coverage and L2 sampled geometry cannot be reported as L3 or L4 completion.

## 2 Baseline and gaps

Current evidence is separate from planned capability. Source locations are listed in Section 17.

| Item | Current evidence | Consequence |
|---|---|---|
| Hospital library | All 35 words have trajectories; metadata labels 5 usable and 30 approximate | motion_ready is availability, not acceptance |
| Planner structure | Direct quintic interpolation, IK routes, neutral hub, retract/approach and limited RRT exist | Extend the existing implementation |
| Batch entry | `--all` covers ten fixed sentences and 19 transitions | Add a distinct all-pairs runner |
| Search exceptions | RRT is enabled for only two pairs; NOW→NURSE has a route preference | Introduce general candidate and budget policies |
| Endpoint exceptions | Several departures and INTERPRETER arrival use fixed frame overrides | Replace unmanaged overrides with versioned window policies |
| NURSE exception | f80 trims 8/79, approximately 10.1266%, pending Thomas confirmation | Keep the decision pending; do not generalize permission |
| Geometry evidence | The handoff reports 19 R13c-f80x PASS transitions; complete run artifacts were absent from the clone | Treat this as a historical report until artifacts are obtained or regenerated and verified |
| Current tests | This environment passed 248 focused tests; full suite: 535 passed, 6 failed | Five failed with missing sentence_transformers; one failed material availability |
| Verification scope | Sampling and collision filters are limited; some guarantees cover only inserted transitions | Add seam and whole-sentence checks and explicit scope metadata |

A fixed random seed alone does not ensure an identical trajectory hash. Wall-clock termination can alter the search process. Validate numerical reproducibility with fixed work budgets in a pinned environment; compare across environments using frozen tolerances.

## 3 Responsibilities and interfaces

### 3.1 Ownership

| Team or role | Responsibility | Handoff evidence |
|---|---|---|
| Group 1 | Text to legal gloss sequence, rejection and clarification, sentence-level language rules | Vocabulary version, sequences, error states and representative inputs |
| Group 2 | Motion sources, robot clips, protected meaning-bearing core, entry/exit windows and motion quality | Motion and metadata hashes, window rationale, defects and permitted modifications |
| Group 3 member A | Endpoint policy, candidate paths, finger policy, search and timing | Implementation, configuration, tests and failure explanations |
| Group 3 member B | Runner, independent verifier, matrices, resumption, playback and integration | Validation reports, regressions, manifests and demos |
| Both members | Difficult-pair diagnosis, cross-review, comparisons and final reporting | Reproducible delivery and recorded sign-off |
| Assigned independent reviewer | Execute review against the frozen revision | Review records independent of that tuning round |

These are proposed responsibilities, not assignments to named people or commitments by other teams. The integration coordinator organizes agreement on shared vocabulary, joint contracts and protected motion content.

### 3.2 Proposed contract

```python
plan_pair(source_gloss, target_gloss, *, library_version, policy, seed)
```

Inputs also bind the model, joint order, motion hashes, permitted windows, boundary positions and derivatives, constraints, candidates and search budget. Offline pair planning depends on the motion contract, so restoring the language model must not block the pair scan.

Outputs include the transition, selected frames, method, status, metrics, verification scope and reproduction metadata. The sentence assembler must consume this result directly. Failed trajectories may be retained for diagnosis but must not automatically enter ordinary playback or execution.

## 4 Library freeze and per-word audit

Create `library_manifest.json` and `word_audit.json` before comparisons. Freeze all 35 glosses, motion paths and hashes, sample times, 53 named coordinates, independent coordinates and coupling, robot geometry, dependency versions and checking policy.

Audit each word for:

1. Array shape, finite values, strictly increasing timestamps, sample rate and joint ordering.
2. Joint limits, coupling error, anomalous speeds and missing frames.
3. Candidate entry and departure clearance and boundary derivatives.
4. Internal collision, critical handshape, palm orientation, relative hand positions and known defects.
5. The protected core and permitted adjustment windows supplied by Group 2.
6. Source/license records and input availability needed for reproduction.

A generic “10% trim allowed” rule is insufficient to define the permitted window. Existing sign_frames are derived from motion geometry and do not establish a linguistically reviewed core. Record engineering and language review separately. Without an approved adjustment window, preserve the original endpoint and record invalid endpoints as blocked.

### 4.1 NURSE decision

Preserve the f80 and strict-cap f81 comparison. f80 uses the approximately 10.13% exception. The handoff reports about 28.43 mm penetration at f81, so switching to f81 does not resolve the defect.

The pending decision applies to this motion version and departure frame. Bind any confirmation to motion hash, frame, ratio, reason, person and date. Updated motion assets do not inherit old frame-number exceptions. Explicitly labelled research comparisons may run before confirmation; final acceptance must not assume approval.

### 4.2 Word classes and motion features

Reuse existing part_of_speech and sentence_role labels for statistics and display, and gradually complete the hospital vocabulary. Missing word classes must not block the geometric scan, and word classes do not determine transition feasibility.

Candidate generation should use hand participation, wrist position and orientation, handshape, crossing configuration, joint-limit margin and boundary motion direction. Compute these features from frozen motions/models and retain the calculation version. Separately record the source and review status of manually added semantic labels.

## 5 Definition of an acceptable transition

### 5.1 Hard constraints and quality objectives

Check hard constraints before ranking quality. A shorter duration or better aggregate score cannot compensate for collision, limit, coupling, protected-core or boundary failures.

| Item | Proposed criterion | Freeze point |
|---|---|---|
| Valid trajectory | Finite arrays, increasing timestamps, common joint contract | T00 |
| Endpoint position | Match selected frames; proposed numerical error no greater than 1e-6 rad | T00 confirms precision; preserve source samples |
| Limits and coupling | Check every output coordinate against the model and contract | T00 fixes per-joint tolerances |
| Sampled clearance | Retain the current +2 mm moving-pair research threshold | Record geometry, filters and validation resolution |
| Speed | Current 15 rad/s arms and 10 rad/s fingers are simulation baselines | Hardware limits require separate evidence |
| Velocity and acceleration seams | Measure discontinuities with frozen joint-category tolerances | T03, using development data and noise assessment |
| Acceleration and jerk | Report peaks, quantiles and squared-jerk integral, with numerical quality limits | Freeze in T03 before final evaluation |
| Duration and pauses | Keep the 0.3 s per-leg baseline; add maximum-duration and pause criteria | T03 |
| Core preservation | Compare protected samples; separately record trimming and retiming | Agreement involving Group 2 |
| Self-pairs | Preserve both occurrences and a distinguishable boundary | Review all 35 separately |

Unset thresholds do not imply success. Development runs may report metrics before the policy is complete, but final sign-off requires frozen thresholds. Neither 2 mm nor existing speed settings certify hardware safety.

Soft objectives include reasonable duration, reduced detours, low jerk, fewer unnecessary stops and stable handshape changes. Start with an interpretable ranking. Weighted scoring requires recorded normalization, weights and development rationale, with component metrics retained.

### 5.2 Collision and continuity scope

Playback may remain at 30 fps, but the verifier must sample the actual interpolated curve independently. Recheck the searched path, smoothed path and final timed trajectory.

Record the baseline resolution, test 2× and 4× denser sampling, and adaptively subdivide small-clearance, high-curvature or high-speed intervals. This supports only the stated sampled checks. A continuous collision-free claim needs continuous checking or a conservative proof.

List the same-hand exclusions, static-pair classification and upstream geometry coverage. Audit the rationale before freezing the final collision scope. Do not remove difficult pairs to improve the success rate; reflect unmodelled contacts in the verification scope.

## 6 General planner redesign

### 6.1 Candidate hierarchy

1. Validate inputs and endpoints, including files, windows and endpoint constraints.
2. Try a direct polynomial or spline capable of representing boundary conditions.
3. Generate general IK detours from wrist positions, robot axes and available space.
4. Evaluate coordinated or staggered arms, retract/approach and verified shared intermediate poses. Check both the hub and its connecting paths.
5. Open bounded RRT to remaining pairs with valid endpoints, replacing the two-pair allowlist.
6. Simplify and time-parameterize the path, constrain acceleration, jerk, speed and pauses, then revalidate.
7. Select among candidates passing every hard constraint using the frozen quality rule, retaining summaries and reasons.

Keep R13c as a regression baseline. Move existing exceptions into versioned configuration with rationale before replacing them with general strategies. Avoid losing established results or accumulating undocumented pair-specific branches.

### 6.2 Position velocity and acceleration seams

Zero velocity and acceleration at a transition's own endpoints do not automatically match the adjacent word motion. Estimate boundary derivatives using fixed short tail/head windows and record the estimation method, filtering and units.

Prefer permitted frames with compatible boundary conditions. Easing is allowed only in approved non-core regions. Boundary-conditioned polynomials must be checked for intermediate overshoot. Protected source motion cannot be changed merely to improve smoothness.

Avoid visible stop-and-go behaviour at every RRT node. Compare knot-preserving timing with verified smoothing. Any geometric change requires collision rechecking. The final assembled motion determines seam quality.

### 6.3 Arms and fingers

Current RRT searches 14 arm joints. This lower-dimensional search may remain initially, but every full candidate must include fingers, coupled coordinates and other outputs in validation.

Define explicit finger strategies such as source-shape hold followed by blending, progress-based blending or early target shaping. Changes must stay within allowed windows. Record collision, coupling and unintended gesture effects. A finger-policy failure needs its own cause code; it does not establish that no arm path exists.

### 6.4 Search budget and reproducibility

Acceptance mode uses fixed seeds, node or collision-query budgets, candidate ordering and threading. Wall-clock limits are outer resource protection; hitting them produces TIMEOUT rather than an infeasibility claim.

Use smaller budgets in development and expanded budgets for residual difficult pairs. Retain every attempt_id and report first-attempt and retry success with budget. Keep elapsed-time logs separate from trajectory-content hashes.

## 7 Output files and result states

These proposed names may be revised once before implementation; freeze the output contract first.

| File | Purpose |
|---|---|
| `config/transition_policy.json` | Thresholds, budgets, sampling, finger policies and exceptions |
| `library_manifest.json` | Vocabulary, motions, robot and dependency versions/hashes |
| `word_audit.json` | Endpoints, cores, windows and defects |
| `pairs.jsonl` | Structured attempt records |
| `matrix.csv` | One final status per pair |
| `manifest.json` | Run status, configuration, file inventory and hashes |
| `trajectories/` | Acceptance candidates and diagnostic trajectories |
| `verification/` | Results from independently rereading stored trajectories |
| `review/` | Representative videos, review forms and decisions |

### 7.1 Status contract

Each pair has one mutually exclusive primary status plus multiple reason codes.

| Status | Definition |
|---|---|
| `NOT_RUN` | Not executed |
| `PASS_SIM` | Saved trajectory satisfies every frozen simulation constraint and independent recheck |
| `SOURCE_NEAR` | Relative endpoint floor passed but absolute clearance did not |
| `BLOCKED_ENDPOINT` | Endpoint/window invalid; reasons identify source, target or both |
| `BLOCKED_INPUT` | Library, files, joint contract or frozen metadata invalid |
| `FAILED_SEARCH` | No path found within the stated budget; no impossibility proof |
| `FAILED_QUALITY` | A path exists but fails boundary, finger, smoothness or duration criteria |
| `TIMEOUT` | Resource limit interrupted completion |
| `ERROR` | Program or environment error |

Provide an import mapping for legacy PASS, FAILED and needs_group2_fix, but do not infer PASS_SIM from old status alone. Pending exceptions, unfrozen thresholds and incomplete rechecks exclude a candidate from final acceptance.

### 7.2 Required record fields

```text
run_id, attempt_id, pair_id, source_gloss, target_gloss
library_version, code_commit, environment_id, policy_hash
source_motion_hash, target_motion_hash, model_hash
entry_frame, exit_frame, endpoint_window_version, exception_ids
method, candidate_count, seed, work_budget, wall_time_s
status, reason_codes, diagnostic_details
transition_duration_s, full_clip_duration_s
min_clearance_mm, closest_collision_pair, collision_scope
validation_resolution, dense_recheck_result
joint_limit_error, coupling_error
peak_arm_speed, peak_finger_speed, peak_acceleration, peak_jerk
position_jump, velocity_jump, acceleration_jump, jerk_integral
protected_core_preserved, trim_count, trim_ratio
trajectory_file_hash, canonical_array_hash, verification_hash
language_review_status, hardware_validation_status
```

Canonical array hashing must fix field order, dtype, endianness and timestamp representation. File SHA verifies transfer integrity. Compression-container metadata may alter file hashes without changing numerical arrays.

## 8 All-pairs runner and evidence retention

Add a dedicated `scripts/plan_all_pairs.py` that reuses the core without changing the current fixed-sentence meaning of --all. Proposed commands, **not yet implemented**:

```bash
python scripts/plan_all_pairs.py --library hospital_v1 \
  --include-self --policy config/transition_policy.json \
  --run-id all_pairs_v1 --resume

python scripts/verify_all_pairs.py --run-id all_pairs_v1
python scripts/summarize_all_pairs.py --run-id all_pairs_v1
```

Compute and persist one pair at a time using temporary files and atomic replacement. Resume from validated checkpoints after checking code, policy, model and input hashes. Changes affecting results require a new run_id.

A coarse diagnostic scan may save summaries only, but it is not acceptance evidence. Persist complete trajectories for every candidate to be counted as PASS_SIM, then independently reload them. NPZ files may remain outside Git, but the delivery must include accessible trajectories, manifests and hashes.

Render videos for failure types, boundary cases, representative motion configurations and selected demonstrations. Retain enough failed trajectories for diagnosis without filling storage with identical errors.

### 8.1 Resource budget

First benchmark 30–50 pairs covering simple routes, detours, crossing hands, invalid endpoints and RRT. Measure phase time, memory, output size and failure rates before estimating total cost. This is a development and performance-calibration set.

If every one of 1,225 pairs exhausts the existing 120-second search limit, search alone takes approximately **40.8 serial hours**, before earlier candidates or verification. Use successive rounds: endpoint audit, inexpensive candidates, then bounded search on residual pairs. Fix parallelism only after measuring memory and model isolation.

Adding a 36th word adds 71 directed pairs including its self-pair. Updating one existing word invalidates at least its 69 incident pairs. A shared model, global collision classification or policy change may require full revalidation.

## 9 Tasks and milestones

Effort estimates are combined productive person-hours for two members, to be updated after the pilot. The total is approximately 64–100 person-hours, excluding Group 2 response time, external review and long machine runs.

| Task | Work | Lead | Dependencies | Hours | Exit evidence |
|---|---|---|---|---:|---|
| T00 | Freeze scope, versions, base criteria and states | Both | None | 2–3 | Complete word/pair list and decision register |
| T01 | Restore environment/materials and reproduce baseline | B | T00 | 3–5 | Actual logs, explained failures, runnable planner |
| T02 | Audit endpoints, cores and windows | A | T00, Group 2 data | 5–8 | All 35 words audited and versioned |
| T03 | Freeze quality metrics and development set | Both | T01, T02 | 4–6 | Executable derivative, jerk, duration and sampling policy |
| T04 | Runner, resumption and matrix | B | T00, T01 | 6–9 | Complete records and safe resume |
| T05 | General candidates, RRT and finger policy | A | T02, T03 | 10–16 | Common planner available to every valid pair |
| T06 | Stored trajectories and independent verifier | B | T03, T04 | 6–9 | Every accepted candidate reloaded and checked |
| T07 | Full scan and failure repair | Both | T04–T06 | 8–12 | Complete matrix, assigned defects and regressions |
| T08 | Triples, longer sequences and repetitions | B, reviewed by A | T07 | 6–10 | Compatible windows, valid seams and whole sequences |
| T09 | Comparisons, playback and human inspection | Both | T07, T08 | 6–10 | Frozen metrics, representative videos and review records |
| T10 | Clean-environment reproduction and freeze | B, reviewed by A | T09 | 4–6 | Instructions, manifests, report and limits |
| T11 | Resource/failure contingency | Both | Throughout | 4–6 | Recorded actual effort and unresolved items |

### 9.1 Milestone exits

- **M0 Baseline frozen:** T00–T03 complete, with explicit external dependencies.
- **M1 Entire scope runnable:** T04 and basic T06 complete; all 1,225 pairs have a primary status with no omissions or duplicates.
- **M2 General planner acceptance:** T05–T07 complete with measured pass rate. If below 100%, continue repair; do not claim universal completion.
- **M3 Composition usable:** T08–T09 complete; demos trace back to matrix and source arrays.
- **M4 Delivery frozen:** T10 complete; an independent reviewer can reproduce the result.

The critical chain is versions/endpoints → quality policy → planner/verifier → full matrix → composition → demonstration/delivery. Runner and planner development can proceed concurrently under a shared contract.

### 9.2 Near-term schedule and deadline

The existing repository guide records **November 3, 2026** as the deadline. Confirm the course notice rather than treating that document as a new authoritative schedule. This plan is dated October 31; full research and external review cannot be promised in three days.

| Date | Priority | If incomplete |
|---|---|---|
| October 31 | T00, T01, initial T02, pilot and decisions | Preserve blockers and scan available inputs |
| November 1 | Runner, initial full matrix and failure distribution; first general planner | Deliver truthful L1 coverage without claiming L2 |
| November 2 | Repair high-impact words, recheck key sequences, prepare comparisons | Freeze demonstrable scope and unresolved items |
| November 3 | Deliver the achieved level with code, reports and reproduction package | If L2 is incomplete, provide continuation ownership and schedule |

Plan approximately 7–10 effective working days for the engineering cycle, plus external motion repair, machine time and review waits. Manage the short-term submission and final universal-coverage objective separately.

## 10 Failure triage and repair

Create defects by root cause rather than duplicating a ticket for every affected pair. A single invalid endpoint can affect many incoming/outgoing edges; prioritize high-impact words.

- **Input/endpoints:** Group 2 repairs motion, core or windows. Group 3 supplies frame numbers, closest collision pairs, curves and reproduction.
- **Search insufficiency:** Group 3 examines candidates, budget, search space and path quality. Failure within budget only describes the current method.
- **Finger/coupling defects:** Isolate handshape timing, non-arm policies and coupling reconstruction.
- **Boundary/duration defects:** Adjust approved windows, boundary conditions and timing; slowing playback alone does not establish appropriate rhythm.
- **Model/filter defects:** Audit geometry and collision assumptions, version any changes and rerun affected scope.
- **Environment errors:** Record ERROR and rerun after repair; do not count them as algorithm success or failure.

Each repair retains a minimal reproduction, change rationale, expected affected scope, regression result and remaining limits. Preserve original evidence and write new candidates to new directories.

## 11 Multiword composition

Pair tests use the permitted internal departure of A and entry of B. Validate sentence-start rise from neutral and sentence-end return separately, avoiding confusion with the special first/last treatment of two-word demos.

For `A → B → C`, jointly choose B's entry and departure. Entry must not exceed departure, and the protected core must survive. Context-dependent endpoints require compatible joint selection; concatenating two independently passing but incompatible pair outputs is insufficient.

The suite must include:

1. Regression of the current ten fixed sentences.
2. Middle-word window compatibility enumeration. Fixed word-level windows need one check per word. Pair-dependent windows require triple metadata combinations: 35³ = 42,875 inexpensive window/core checks before full geometry.
3. At least 100 frozen three-word sequences covering every word in the middle, hazardous endpoints and crossing hands. This is an engineering target finalized in T03.
4. At least 20 five-word sequences plus repetition cases with varied rhythm and handshape.
5. Full-frame and dense checks for every final demo, including word interiors, inserted paths and seams.

Sampled composition tests support only their tested scope, not arbitrary-length sentences. Report pre-existing word-interior defects separately from transition success.

## 12 Comparative experiments and human review

Compare under the same vocabulary, endpoint policy, model, timing and collision rules:

- B0: fixed-duration direct interpolation.
- B1: existing R13c hierarchical planner.
- B2: the general planner in this plan.
- Optional ablations: disable RRT, derivative matching or finger strategies to identify their effects.

Hold endpoints fixed in the main algorithm comparison. Evaluate changed window policies separately and report trim amounts. A failing baseline remains a failure; do not relax criteria.

Report coverage, absolute simulation pass rate, first-attempt/retry success, failure causes, duration and computational cost, clearance, speed, seam derivative jumps, jerk, detours and core preservation. Use all 1,225 pairs as the denominator, with 1,190 distinct-word and 35 self-pairs separately. Eligible-endpoint subset metrics may supplement, not replace, full-scope results.

Scanning the full matrix during repair makes it development acceptance evidence. Claims about unseen-pair generalization require a held-out set frozen before tuning. Resampling, timing variants and repeated seeds of the same pair cannot cross training and independent-test boundaries.

Human inspection covers every failure type and boundary case, followed by stratified random passing examples. At least two engineering reviewers independently record hesitation, detours, handshape discontinuity and word recognizability concerns. Language claims require appropriately qualified reviewers, predefined recognition/continuity tasks and presentation order, and the actual participant count. Without that review, language comprehension remains unvalidated.

## 13 Optional learned component

Current-vocabulary all-pairs coverage can begin with geometric planning and bounded search. Deep learning is not a prerequisite for the scan or verifier.

If the course requires a learned component, separately freeze a research question, such as predicting durations or intermediate poses to reduce search cost. Verified planner outputs may supply targets, but retain source/validation versions and do not call them human transition demonstrations.

Start with candidate ranking or initialization, keep the same final verifier, and retain a general-planner fallback. Integrate learning only after same-budget comparisons show useful success, quality or speed improvements. Split complete pairs or sources across train/development/independent test. Unseen-word claims additionally require holding out words and every incident pair.

If the course still requires ten-class ID-conditioned motion generation, register that as an additional deliverable. Completing this transition module does not automatically meet that requirement.

## 14 Risks and responses

| Risk | Signal | Response |
|---|---|---|
| Source defects affect many pairs | Failures cluster on one word's incident edges | A consolidates defects, Group 2 repairs, B reruns affected scope |
| Trimming changes meaning | Core removed or window unconfirmed | Withhold final acceptance and retain comparison/decision record |
| Sampling misses collision | Status changes with denser sampling | Refine validation and recheck affected matrix |
| Search cost grows | Many budgets exhausted | Staged search, caching, fixed work and explicit timeout |
| Fingers introduce collision | Arm path passes but full trajectory fails | Repair timing/search policy and classify separately |
| Passing motions look unnatural | Stops, long pauses or large detours | Derivative/duration criteria and human comparisons |
| Pairwise success fails in sentences | Middle-word entry/exit conflict | Joint window choice, triple checks and whole-sequence validation |
| Versions mix | Same gloss points to different hashes | Invalidate cache and reject stale acceptance |
| External review/repair delayed | Required evidence unavailable | Deliver actual achieved level with ownership and next dates |

## 15 Deliverables and definition of done

### 15.1 Delivery package

Code includes the general planner, versioned policy, all-pairs runner, independent verifier, resumption, regressions, summaries and playback tools. Chinese and English instructions provide real commands, dependencies, resource restoration and troubleshooting.

Results include frozen manifests, per-word audit, every primary status, all accepted trajectories, verification, failure diagnostics, composition results, representative videos, review records and checksums. Large assets stay in the agreed result store; Git retains manifests and retrieval instructions. Verify recipient access. A machine-local absolute path or inventory alone is not a backup.

### 15.2 L2 final checklist

- [ ] Vocabulary, model, policy, dependencies, randomness and budgets are frozen.
- [ ] Every one of 1,225 pairs has exactly one final primary status.
- [ ] **All 1,225 pairs are PASS_SIM**; all other status counts are zero.
- [ ] Every accepted trajectory is saved and independently reloaded.
- [ ] Exceptions and windows have versioned confirmation records.
- [ ] Thresholds were frozen before acceptance and not relaxed after poor results.
- [ ] Position, velocity, acceleration and jerk boundary checks pass.
- [ ] Repetition, triple compatibility and the frozen composition suite pass.
- [ ] Clean-environment reproduction is complete and tolerated differences are archived.
- [ ] The report states geometry/sampling scope and separate language/hardware status.

An incomplete matrix can be delivered as a stage result, but universal pair completion remains unfinished. Failure within budget is not an infeasibility proof.

## 16 First execution cycle and decisions

1. Freeze the 35-word/1,225-pair list and current code/resources.
2. Run focused baseline tests; restore semantic dependencies/material records alongside the offline work.
3. Audit endpoints, internal defects and windows, prioritizing high-impact words.
4. Freeze development samples, quality metrics and deterministic search budgets.
5. Implement the runner and independent records; produce the first full baseline matrix.
6. Prioritize algorithm work from measured failures, then recheck the matrix and composition suite.

| Decision | Planning default | Latest point |
|---|---|---|
| Include repetitions | Include and separately report 35 pairs | T00 |
| Group 2 cores/windows | Preserve original endpoints until confirmed; record blockers | T02 |
| NURSE f80 exception | Research comparison allowed, final acceptance pending | T02 |
| Acceleration, jerk, seam tolerances, duration | Assess development data/noise, then freeze | T03 |
| Required learned component | Register separately from transition engineering | T00 |
| November 3 deadline | Confirm course notice; report actual completion level | T00 |
| Language/hardware review resources | Keep unvalidated until evidence exists | Before corresponding review |

## 17 Evidence and inspection points

These are project evidence locations, not external performance guarantees.

- [Latest Group 3 handoff](HANDOFF_group3.md): R13c-f80x, exception and historical results.
- [Planner guide](transition-planner.en.md): candidate hierarchy, gates and limitations.
- [Group 2 handoff](group2-handoff.en.md): hospital words, sources, quality and interfaces.
- [Hospital motion index](../motions/hospital_v1_motions.json): vocabulary and paths.
- [Planner core](../src/sign_robot/transitions.py): endpoint, RRT, finger and collision policies.
- [Current batch entry](../scripts/plan_transitions.py): fixed ten-sentence workflow.
- [Current verifier](../scripts/evaluate_planned_transitions.py): stored-trajectory checks.
- [Team implementation guide](ten-intent-learning-guide.en.md): previous learning objectives, roles and recorded deadline.

This document defines future work and acceptance. It does not execute an all-pairs scan, approve the NURSE exception or modify algorithms or motion assets.

