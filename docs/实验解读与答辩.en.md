# Experimental interpretation and a 12-minute defense

[中文](实验解读与答辩.md) · **English** · [Documentation index](README.md)

> Historical analysis of the original selection/kinematic prototype. Statements below about no motion training describe that analysis stage. A later separate three-trajectory regression experiment is documented in [learning v1](学习型轨迹模型.en.md); current development follows [the ten-intent guide](ten-intent-learning-guide.en.md).

The project implements limited English selection, kinematic candidate motions, and a reproducible three-method comparison. Semantic methods accept more paraphrases, while the small local LLM introduces wrong executions. Geometry checks do not establish ASL-user comprehension. Complete PLEASE_WAIT, dynamic tracking, and user review remain incomplete.

This rereads 180 saved rows from `results/evaluation/test-20261008T142047221403Z/raw.jsonl`, without model calls/data/threshold/prompt changes. The analysis independently matched 281 numeric/count fields to the original summary; historical file hashes matched before/after. Final charts: `results/analysis/frozen-test-final/`. `frozen-test-v1/` and `frozen-test-v2/` remain layout drafts; the final version adds title spacing and hashes for six images, without numeric changes.

## Project map

Whole English sentence → three-meaning catalog → shared guard/selector → valid ID or nonexecution → review status/trajectory constraints → MuJoCo candidate preview → future human comprehension.

| Layer | Input/output | Evidence at original stage | Limit |
|---|---|---|---|
| Scope | Sentence → HELLO/THANK_YOU/PLEASE_WAIT/rejection | Catalog/whole-meaning limits | Not arbitrary translation; do not execute only part of an added intent. |
| Selection | Text/catalog → Selection | exact, real MiniLM, explicit local LLM research | Valid ID need not be semantically correct. |
| Construction | Authored wrist/coupled-hand targets → `[T,J]` | Keyframes, bounded IK, smoothstep, kinematics | No human 3D extraction or motion training in this historical route. |
| Robot checks | Trajectory/model → limits/coupling/geometry | Fixed-base G1/Inspire; failure iterations | Simplified geometry is not real-robot safety or dynamic tracking. |
| Language/users | Robot expression → meaning paraphrase | THANK_YOU/WAIT videos actually viewed | WAIT lexical example is not full request; no ASL/medical review. |

Learn meaning, contracts, FK/IK, denominators, and frozen experiments first. New labeling, nonmanual features, human tests, and tracking are advanced. This historical stage deferred scale/whole-sentence generation/clinical multilingual deployment, rather than obscuring unconfirmed expressions with complexity.

## Read three charts

English PNG/SVG labels suit slides. For editable charts, use `analysis.json` `chart_data`, never estimates from pixels.

| File | Question |
|---|---|
| `supported_outcomes.png/.svg` | For 30 supported inputs: correct, rejected, wrong ID, error? |
| `out_of_scope_outcomes.png/.svg` | For 30 unsupported inputs: wrong execution? |
| `llm_execution_paths.png/.svg` | Of 60 decisions, guard versus actual model request? |

Supported `S=C+R+W+E_s`: correct ID C, false rejection R, wrong ID W, error E_s. Unsupported `U=J+F+E_u`: correct nonexecution J, wrong execution F, error E_u. Clarify/unsupported count as correct nonexecution outside scope; error does not.

Overall `(C+J)/(S+U)`; supported correct `C/S`; false execution `F/U`; coverage `(C+W+F)/(S+U)`; execution precision `C/(C+W+F)`, null if none. Different denominators answer different questions.

| Recomputed | exact + guard | MiniLM + guard | LLM + guard |
|---|---:|---:|---:|
| Overall correct | 38/60 | 47/60 | 48/60 |
| Supported correct | 8/30 | 17/30 | 20/30 |
| Supported false rejection | 22/30 | 13/30 | 7/30 |
| Supported wrong ID | 0/30 | 0/30 | 1/30 |
| Supported error | 0/30 | 0/30 | 2/30 |
| Unsupported correct rejection | 30/30 | 30/30 | 28/30 |
| Unsupported wrong execution | 0/30 | 0/30 | 2/30 |
| Execution precision | 8/8 | 17/17 | 20/23 |

All 60 are agent-drafted, unreviewed labels. No population accuracy or significance conclusion. LLM improves total by one versus MiniLM but adds false execution; 80% versus 78.3% cannot justify default replacement. Exact/MiniLM 0/30 is not population zero risk.

Of 25 LLM guard decisions: 23 correct unsupported rejections, two supported false rejections. Of 35 received HTTP answers: 20 supported correct, five unsupported correct rejections, five supported rejections, one wrong ID, two wrong executions, two invalid outputs. HTTP contains 28 supported/seven unsupported cases, unlike the guard subset. Comparing 23/25 with 25/35 cannot establish rule superiority; all 48 correct decisions cannot be attributed to LLM.

Overall LLM selector median ~18.77 ms; HTTP subset ~20.06 ms, both including overhead. Service was prestarted; readiness was outside 60. Neither is cold start nor end-to-end visible motion latency.

## Failures explain mechanisms

Expected labels below belong to the frozen draft, without ASL/linguistic human review. `analysis.json` deterministically selects the lowest case ID within method/failure/path and includes both unsupported false executions. Diagnostic examples are not a population sample.

| Case | Input/phenomenon | Failure | Diagnosis and inference limits |
|---|---|---|---|
| test-003 | `Hello to you!` | exact rejects | Limited aliases, not inability to produce HELLO. |
| test-006 | `Good to see you!` | MiniLM rejects | Similarity/catalog did not accept; human review must still assess complete equivalence. |
| test-016 | `Much appreciated!` | LLM selects HELLO | Allowlisting limits labels, not semantic correctness. |
| test-017 | `I really appreciate what you did.` | Guard rejection, no model | `what` triggers metalinguistic rule; not LLM inference failure. |
| test-021 | `Wait a moment.` | `THERE_ARE_NO_SUCH_INFORMATION, PLEASE_WAIT` → error | Strict parser does not extract plausible ID from malformed output; preserves evidence. |
| test-025 | `Give me a moment, please.` | Model CLARIFY | Actual model call; distinguish from guard rejection. |
| test-038 | `She wants to thank you.` | Executes THANK_YOU | Protocol expects speaker thanking listener; third-party role lost. |
| test-040 | `They thanked me yesterday.` | Executes THANK_YOU | Past event treated as present expression; keywords miss whole meaning. |

C1 should human-review labels/pragmatics, retain disputes, and create a new version. B1/B2 use new development material/protocol followed by new final tests. Adding these examples to the old prompt and retesting cannot yield independent confirmation.

## Five useful reasoning models

| Model | Meaning/reason | Use/limit | Engineering application |
|---|---|---|---|
| Typed compilation pipeline | Text → limited ID → known motion; contracts reduce ambiguity | Small inspectable catalogs; valid IDs can still be wrong and missing meanings must not be forced | Draw layer inputs/outputs and detectable failures. |
| Layered acceptance | Format, semantics, geometry, dynamics, comprehension differ | Multimodule systems; one metric cannot substitute for all layers | Specify what “passed” tested and omitted. |
| Rejection has a cost | Coverage trades against wrong execution; all-reject can score deceptively well | Allowlisted retrieval/thresholds; no universal optimum without error costs | Report rejection, execution errors, coverage, accuracy. |
| Actual-path attribution | A button may run rules/model/errors; quality/timing belong to actual path | Hybrid systems; guarded subsets are not random model samples | Preserve request/response; distinguish model/rule/permission. |
| Constrained mapping | Human targets map through morphology/bounds/coupling/time | Different bodies; low IK residual validates authored-target fit, not language | Ask target origin/observability before keyframes/retargeting. |

Connect them by complete meaning → constrained representation → layered checks → path-based failure explanation.

## Three conditional debates

### Replace MiniLM because LLM scores higher?

For replacement: supported correct 20/30 versus 17/30. Against immediate replacement: 2/30 unsupported false executions versus observed zero, plus wrong ID/invalid outputs. These imply different error costs. Higher coverage may help if missed expression is costly and human confirmation is available; costly wrong expressions favor stricter gates/clarification. Real costs/labels are unvalidated. Preserve `not_accepted_for_default` and test a new development protocol; one-point advantage does not reverse gate failure.

### Do WAIT and PLEASE lexical examples establish a complete request?

Lexical decomposition helps analyze hands/orientation/location/path. Complete expression requires context/order/pauses/face/nonmanual information. Current evidence supports WAIT only. English concatenation assumes cross-language word order/politeness equivalence without evidence. Keep compatible ID with explicit candidate/unverified label. ASL also does not represent SgSL automatically. Next: complete-request source and uncaptioned meaning paraphrases.

### Are authored keyframes inferior to video retargeting?

Keyframes make constraints/failures explicit and produce an interpretable early prototype. Video retargeting may preserve details/timing but depends on visibility, pose estimation, scale/frames, morphology. Monocular viewing cannot precisely recover occlusion/depth/contact. Actual historical route: observed demonstration → authored targets → bounded IK/interpolation, without human-3D reconstruction, Mink/dex-retargeting comparison, or motion learning. THANK_YOU calibrated near-lip/palm/forward-down features but retains face gap/adduction/face limits. Establish a keyframe baseline, then compare licensed suitable 3D data under the same task/robot/protocol. Do not assume superiority.

## Twelve minutes, six people, two each

| Time | Slide | Owner | Single question/evidence |
|---|---:|---|---|
| 0:00–1:00 | 1 | A1 | Problem/three expressions, whole sentence/rejection. |
| 1:00–2:00 | 2 | A1 | Sources, WAIT gap, ASL/SgSL, review. |
| 2:00–3:00 | 3 | A2 | Morphology, independent/coupled joints, fixed base, contract. |
| 3:00–4:00 | 4 | A2 | THANK_YOU correction, authored targets, palm/face gap. |
| 4:00–5:00 | 5 | B1 | exact/MiniLM, mechanism/thresholds. |
| 5:00–6:00 | 6 | B1 | Guards and false rejection; whole-sentence example. |
| 6:00–7:00 | 7 | B2 | Local model, strict labels, 2/3 gate failure. |
| 7:00–8:00 | 8 | B2 | Valid wrong IDs, false executions, invalid replies. |
| 8:00–9:00 | 9 | C1 | Draft 60 labels, hashes, shared guard, denominators. |
| 9:00–10:00 | 10 | C1 | Three charts and path-specific conclusions. |
| 10:00–11:00 | 11 | C2 | Candidate preview/rejection and video backup. |
| 11:00–12:00 | 12 | C2 | Done/not done/next; why not a signing translation product. |

Reserve about five minutes Q&A. Everyone should explain another module's interface/failure.

Thirty-second answer: We built three-expression English selection and robot kinematics. Rules, embeddings, or a research local LLM return candidate IDs; whole inputs outside scope do not execute. On the same 60 unreviewed draft cases, methods got 38/47/48 correct; LLM covered more variants but made false executions. Motion was authored/calibrated against public examples. Geometry and human comprehension are separate. Next priorities are complete expressions and human evaluation.

## Status and minimum checks

Done at this analysis stage: source/viewing records, three candidates/previews, real MiniLM/local LLM calls, development/sandbox failures, frozen tests/raw output, independent recount/charts, default unreviewed-motion protection.

Not done at that stage: human-3D extraction/training, full PLEASE_WAIT confirmation, human comprehension, clinical validation, dynamic tracking, confirmation of teammates' mastery. Second-machine completion requires C2 logs. Later regression learning is separately documented.

Before presenting: file/report hashes agree; candidates remain unreviewed; observations differ from authored coordinates; denominators/draft labels appear on charts; failures are accessible; backend/service state is explicit; first-frame latency is not model latency. Historical LLM scores do not establish live availability when UI is disabled.

## Active recall, without supplied answers

1. If all 60 are rejected, what are overall accuracy, supported correct, coverage, precision under the 30/30 split? Why is one score misleading?
2. What do wrong ID, clarify, and error mean on supported cases? Why are the latter two not all successful safe rejection?
3. How do 35 HTTP and 25 guard inputs differ? What confounds direct accuracy comparison?
4. If a new scenario adds 300 unsupported cases, what does old 0/30 establish, and what needs retesting?
5. Which meaning rules label `Thank you for waiting.`? Why do thanks/wait keywords not prove two executable intents? How record disagreement?
6. What does WAIT omit from `Please wait five minutes.`? Preconditions for rejection, clarification, or catalog extension?
7. With different arm length/stronger coupling, what data can be reused and what must be recalculated?
8. Low IK error but face gap/unadducted fingers: what passed, what did not, and next acceptance?
9. Why are official lexical viewing, a complete-sentence demonstration, and robot-user paraphrase different evidence? What localization layer applies in Singapore?
10. After seeing eight failures, how design development/testing without treating seen final data as independent?

Minimal practice: without model calls, each person chooses a different raw case and hand-computes denominator/path/outcome/conclusion, then checks `analysis.json`. Diagnose meaning, contract, denominator, or attribution confusion.

## Reproduce read-only analysis

`scripts/analyze_evaluation.py` uses stored text/expected IDs/status/HTTP metadata, without importing selectors. Input: 60 rows per three methods. Output: counts and three charts. Existing directories cannot be overwritten.

Original plotting used separate `/private/tmp/me5412-analysis-venv`, Matplotlib 3.10.7, leaving inference/lock unchanged. Install final `plotting-requirements.txt` in a separate environment, then choose a nonexistent directory:

```sh
python scripts/analyze_evaluation.py --output-dir results/analysis/my-readonly-reproduction
```

Layout fixes only reread records. `analysis.json` retains input/chart SHA256, recomputed counts, summary agreement, paths, and eight raw failures. Numeric inconsistency raises errors rather than silently adopting summary values.
