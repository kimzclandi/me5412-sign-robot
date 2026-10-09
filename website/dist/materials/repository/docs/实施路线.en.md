# From the current prototype to the ME5412 course delivery

[中文](实施路线.md) · **English** · [Documentation index](README.md)

> **Updated direction.** This retains the earlier three-motion/text-method comparison plan. The latest main line is ten fixed intents and conditional motion learning, with deadline 2026-11-03. Use the [latest guide](ten-intent-learning-guide.en.md) and [GitHub collaboration](github-collaboration.en.md) for current work.

Suggested early scope: text selection and robot signing candidates in limited medical-service scenarios. Compare exact matching, embeddings, and local LLM under one catalog/rejection policy: correct selection, false rejection, wrong execution, and morphology limits. Do not describe arbitrary-English-to-complete-ASL translation.

The course brief allows concept/design/simulation, without requiring hardware. Delivery is slides, deadline 2026-11-03, 10–15 minutes plus five minutes Q&A. This plan follows the confirmed six-person group. Suggested future dates do not imply completion.

## Implementation route

```text
English / phrase selection
 → shared rejection → exact / MiniLM / local LLM
 → valid candidate ID or explicit rejection
 → separate candidate-preview gate
 → checked trajectory → MuJoCo playback/video

Public video → handshape/palm/location/path observation
 → authored key poses → bounded IK → interpolation → framewise checks
```

Language emits discrete IDs, never joint angles. Separate modules distinguish input misunderstanding from motion mismatch, making improvements interpretable. Historical six-person tasks and agent prompts: [handoff cards](six-person-handoff.en.md).

## Understand existing robot construction

Input: authored palm positions/orientations/times. Output: `positions[T,53]`, rows for time and columns for named joints. The 53 coordinates include passive joints and are not 53 independent drives. The base is fixed with 12 finger mimic relations.

`scripts/build_motions.py` uses bounded least squares per arm, reducing palm position/orientation error and change from previous posture, with penalties for insufficient arm/torso geometry distances. Weights are engineering choices; convergence does not prove correctness/collision freedom. Check the complete trajectory separately.

Keyframe interpolation: `s(u)=3u²−2u³`, `q(u)=(1−s)q₀+s q₁`. u is segment-normalized time, q₀/q₁ adjacent joint vectors. Endpoint velocity is zero; acceleration continuity is not guaranteed. THANK_YOU adds intermediate palm targets to avoid upward fingertip detours from endpoint-only joint interpolation. Evaluate preparation/retraction separately from the signing core.

Essential concepts: coordinates, forward/inverse kinematics, limits/coupling, selection rejection, and evaluation denominators. Dynamic tracking/monocular retargeting are advanced. This historical plan deferred large-scale training, arbitrary translation, cloud inference, and hardware procurement.

## Historical milestone plan

| Suggested dates, 2026 | Owners | Acceptable output |
|---|---|---|
| Oct 9–12 | A1/A2 | Check demonstrations; address complete WAIT-request source gap; document missing fingers/face; front/side frames. |
| Oct 13–18 | B1/B2/C1 | Human-check new development labels; freeze protocol before tuning; retain failures and create independent tests. |
| Oct 19–25 | C1/C2 | Second-machine reproduction, comparisons/failure categories; uncaptioned ASL-user paraphrase if available, otherwise qualitative video comparison only. |
| Oct 26–30 | All; C2 compiles | Slides, raw-record index, demo/offline backup; each teammate explains one success/failure. |
| Oct 31–Nov 2 | All | Rehearsal/defense checks, freeze files, confirm submission method against course notice. |

With limited time, retain complete HELLO/THANK_YOU demos and mark WAIT's expression gap. Do not splice unverified signing to increase counts. Without real-user review, retain “video-referenced simulation candidates” in titles/conclusions.

## Presentation structure

Suggested 10–12 slides: scenario/question, finite scope, interfaces, morphology, video observations, IK/trajectories, three selection methods, frozen evaluation, failures, demo, limits/next steps. Separate correct-ID rate from signing comprehensibility. Zero wrong execution in a small dataset is not zero risk; shared-rule contributions cannot be credited to LLM.

Each teammate should explain inputs/outputs, robot versus language constraints, evidence of actual operation, failing counterexamples, and an experiment that distinguishes competing explanations. Unclear points need a minimal reproduction, not memorized agent conclusions.
