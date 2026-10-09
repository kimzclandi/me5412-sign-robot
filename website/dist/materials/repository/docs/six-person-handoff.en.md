# Six-person handoff cards

[中文](six-person-handoff.md) · **English** · [Documentation index](README.md)

> **Historical cards.** These preserve initial/v1 learning responsibilities/evidence. Since 2026-10-09, the current direction is ten intents/learned motions, two people each for language, motion, integration/presentation. Read [latest guide](ten-intent-learning-guide.en.md), [GitHub workflow](github-collaboration.en.md), and [dependencies](code-dependencies.en.md) first.

## Additional work after learning v1

One text-conditioned RBF ridge fit and 35,263 How2Sign text records are completed. Effective motion demonstrations remain three authored trajectories. Initial cards below retain module context.

| Owner | Next work | Files/acceptance |
|---|---|---|
| A1 | Usable human demonstrations; full meaning, hands, nonmanual features | Corpus/source records; index existence is not acquired video/pose. |
| A2 | Map sourced human motion to robot; hands/contact/coupling | New trajectories/frame checks; preserve motions/v1. |
| B1 | English/motion pairs; negation, roles, compounds, missing labels | New manifests; no tuning on seen final failures. |
| B2 | Next text-conditioned model with new independent demonstrations | Freeze v2 before training; v1 read-only. |
| C1 | Independent motions/videos/users; comprehension | Alternate frames are fit only; video comparison is not human understanding. |
| C2 | Generation API, skeleton/rendering, reproduction/presentation | learning API/web/v4; rejected inputs clear old output. |

Read [learning](学习型轨迹模型.en.md)/[corpus](语料规模与模型升级.en.md). This is trained regression, not general deep ASL generation. Preserve initial LLM negatives. Teammates choose report results after checking; engineering acceptance is not language review.

Existing artifacts: three candidates, exact/real semantic matching, optional local LLM API, web demo, raw evaluation. Engineering output does not complete ASL/course research. Copy task prompts to each person's agent, but avoid six agents editing shared files.

Everyone reads AGENTS.md, contracts/interfaces.json, data/catalog.json and records actual state. Preserve development failures/evaluation/frozen tests; no validated-candidate claims, paid applications, or contacting reviewers for teammates. Independently check source-media permissions. C2 coordinates shared interfaces.

## A1: motion sources and ASL review

Inputs: source manifest, source/video review docs, catalog, three motion JSONs.

```text
Check the four Lifeprint sources and their support. Find a fully viewable contextual ASL PLEASE_WAIT request; do not treat PLEASE/WAIT concatenation as verified. For each candidate, check handshape, palm orientation, location, path, pauses/repetition, and nonmanual features; record URL, times, viewing method, license. Save only permitted material. Prepare an uncaptioned review form asking ASL users to paraphrase meaning and recording deviations. Prepare questions/invitation draft only; do not send messages. Never change asl_review_status without actual review. Provide Chinese/English documentation.
```

Acceptance: at least one full-expression verification, confirmed/unconfirmed fields per motion, blank forms separate from results, reviewer identity/authorization confirmed by the user. If no suitable example exists, retain WAIT-only boundaries without invented evidence.

## A2: robot and key handshapes

Inputs: model/upstream manifests, build/render scripts, motion module, trajectories/previews, A1 records.

```text
Check actual independent joints/coupling of fixed-base arms/hands. Focus on THANK_YOU near-lip/lower-face fingertips and upward final palm, and WAIT differentiated finger flexion. State source/geometry deviations before minimal corrections; preserve failed trajectories/reasons. Do not improve appearance by penetration or dropping constraints. Separately report kinematic playback, limits, collision, actual dynamic tracking; unrun dynamics cannot pass. Record meaning gaps from unavailable face features. Regenerate framewise previews/geometry after changes. Provide both languages.
```

Acceptance: three repeatable trajectories, front/side keyframes/reports; names/columns align; source facts separate from authored approximations; unavailable capability remains a limitation. PNG/MP4 does not establish comprehension.

## B1: exact and semantic selection

Inputs: language module, embedding config/download manifest, development examples, language tests. **Do not read frozen questions/failures for tuning.**

```text
Use only public development data and separately supplied human-reviewed new variants to analyze alias/MiniLM false rejection. Separate guard rejection from embedding thresholds; inspect negation, roles, qualifiers, mixed meanings. First record a new protocol: sources, candidate thresholds, criteria, freeze time; then propose changes. Preserve current code/config/initial results. Do not add final-set sentences as aliases to improve old scores. Supply version differences/new independent-test requirements to C1. Maintain paired documentation.
```

Acceptance: categorized development errors, protocol/candidate config, reproducible old version, development basis per threshold; no independent-confirmation claim on reused final data.

## B2: local LLM

Inputs: llm module/default/research/provenance configs, startup script, V1/V2 feasibility records, development data/tests. Use actual model/port configuration; exclude private paths.

```text
Verify existing free local service starts in a fresh process and returns legal status/action_id. Keep loopback-only, no redirects/proxies, allowlisted outputs. Record version, quantization, arguments, cold startup, timeout. Test development understanding, invalid JSON, and whole mixed intents; guard success is not LLM inference. No paid API, duplicate downloads, or final-set prompt tuning. Freeze new prompt/protocol before optimization, then C1 uses new tests; preserve old errors. Supply bilingual instructions.
```

Acceptance: reproducible start/stop, positive/rejection/invalid/timeout evidence, config/source versions. High rejection/instability must be reported; no exact fallback posing as LLM success.

Historical B2: all three V1 outputs invalid. One V2 format repair gave only 2/3 correct; Please wait was falsely rejected. Further tuning stopped; default stayed off. Explain failure/new protocol rather than use final questions to optimize.

C1 later tested unchanged V2 explicitly: 48/60 overall, 2/30 unsupported false executions, 1/30 supported wrong ID, 2/60 invalid replies. Actual model called for 35, guard handled 25. This does not reverse gate failure/default-off or credit all successes to LLM. Do not tune V2 from these final questions.

## C1: independent evaluation

Inputs: evaluate script/tests, source manifest, development/final data, results. C1 may read final questions; B1/B2 may not tune against them.

```text
Check denominators/raw first results. The 60 final labels are agent-drafted/unreviewed, not formal human data. Organize independent teammate checks of complete meaning, especially greetings, gratitude roles, wait/pause pragmatics. Record disputes without overwriting labels. Save revised v2 labels/reasons and freeze SHA256 after confirming review. If selection changes, use new final questions/protocol. Report supported correct, false rejection, unsupported execution, coverage, errors, cold/warm latency, all failure text. Without ASL users, report text/geometry only. Document in both languages.
```

Acceptance: old data/results unchanged; new human-label records/frozen hashes/config/raw data together; disputes retained; error not successful rejection; all-reject not high quality.

Preserve initial `test-20261008T135255840626Z`, blocked-loopback `test-20261008T141909955017Z`, and actual three-method `test-20261008T142047221403Z`. The latter two source/config/provenance hashes match. Keep permission failure; permission repair is not tuning. Reproduce using the latter summary's bound versions and [source record](source-review.en.md) execution conditions.

## C2: integration, reproduction, presentation

Inputs: launcher, packaging/lock, server/pipeline/web/README, other five deliveries.

```text
Reproduce on another teammate's fresh environment: OS/Python, installation, resource hashes, startup/failures. Verify unreviewed labels, default blocking, explicit candidate preview, unsupported inputs, unknown IDs, unavailable backend, stale prior motion. Prepare offline backup and 10–15 minute slides; distinguish sources, selection, simulation, ASL, clinical value. Coordinate shared-interface versions with the five others. Do not hide failures or claim hospital deployment. Maintain bilingual explanations and UI.
```

Acceptance: second-machine logs, full demonstration recording, UI failure list, backup/delivery index; offline LLM availability stated; every slide metric traceable to raw evidence.

## Handoff rhythm

A1 sources determine A2 scope; A2 acceptance feeds C2. B1/B2 freeze versions for C1; C1 retains raw results before conclusions. C2 compiles evidence/gaps; each person explains methods/evidence/failures. Agent-generated code does not establish teammate mastery or research completion.
