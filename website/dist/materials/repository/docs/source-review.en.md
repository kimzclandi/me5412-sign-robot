# Sources and exploratory evaluation record

[中文](source-review.md) · **English** · [Documentation index](README.md)

Checked 2026-10-08 (Asia/Singapore). This is an agent's source/engineering record, with no ASL-user or clinical validation. Machine-readable detail: `data/source_manifest.json`.

## Three current candidates

| ID | Checked source | Construction evidence | Unsupported claims |
|---|---|---|---|
| HELLO | [ASLU hello](https://www.lifeprint.com/asl101/pages-signs/h/hello.htm) | Text permits a natural sideways greeting wave. | No numeric handshape/orientation/duration; robot understanding unreviewed. |
| THANK_YOU | [ASLU thank you](https://www.lifeprint.com/asl101/pages-signs/t/thankyou.htm) | Flat hand from near lips forward/slightly down; final image/path inspected, palm upward. | Robot smile absent; avoid confusing GOOD. |
| PLEASE_WAIT | [WAIT](https://www.lifeprint.com/asl101/pages-signs/w/wait.htm), [PLEASE](https://www.lifeprint.com/asl101/pages-signs/p/please.htm) | WAIT text/sequential photos: raised/offset hands, upward/oblique palms, finger movement. | No complete polite request demonstration; two dictionary entries do not validate a sentence. |

Initial checks used THANK_YOU/WAIT images/animation captures/sequences. Later, user-requested official videos were actually played and inspected framewise; see [video calibration](video-calibration.en.md). Manifest records viewing/times. HELLO/PLEASE still rely on teaching text. Numeric angles, arm adaptation, timing, and interpolation are authored approximations.

PLEASE discusses request expression/pragmatics and frequent sentence-final placement. `PLEASE_WAIT` is retained for interface compatibility. If only WAIT is implemented, UI/metadata must say “WAIT candidate; complete polite request unverified.” English-order dictionary concatenation is not validated ASL.

## Use and localization

[Lifeprint permissions](https://www.lifeprint.com/asl101/pages-layout/permission.htm) permit links/self-study; current permission does not cover public copying/embedding of images, videos, or course materials. We retain links, short authored observations, and project trajectories only. No author contact, personal-information application, or endorsement. Recheck actual material/terms for future publication; accessible is not redistributable.

[SADeaf's SgSL description](https://sadeaf.org.sg/sgsl-course/) identifies the local Deaf community's language. ASL here is a course engineering choice and does not establish suitability for all Singapore Deaf users.

## Evaluation protocol v1

- Development: 18; final: 60 (30 supported, 30 out-of-library/negated/role-shifted/mixed/medical/ambiguous). Agent-drafted/initially labeled, not human-reviewed; not the previously suggested 120-example human dataset.
- Whole-sentence meaning must match one catalog candidate. Additional time/place/conditions/intent cannot be partially executed.
- Developers use development data, not final questions for tuning. Final SHA256 froze before the first experiment; scripts enforce it and preserve failures.
- Final SHA256: `83a4f5310f28f45a5cc2aeecf6660742c2bf93b0b0f99660ad08d6d02f2f4231`.
- Development SHA256: `e33fc62e3280cbbf6b61578e99c5ca9a08c492139e683cec0178f2e500bfdf04`.
- Only English → candidate ID/rejection is evaluated. Correct ID does not validate motion execution, ASL, or medical communication.
- Main accuracy counts out-of-library clarify/unsupported as correct nonexecution; error is wrong. Strict status agreement is also saved.
- Supported correct rate: execute with correct ID / supported cases.
- Supported false rejection: clarify/unsupported / supported cases. Runtime errors remain separate.
- Out-of-library wrong execution: execute / out-of-library cases.
- Coverage: all execute / all cases. Execution precision: correct executed IDs / all execute; null if none, never 100%.
- Save raw decisions, failures, and summary together. Do not modify questions/lower gates to pass or call a post-error rerun independent.
- Latency is evaluator wall time including guards/method. One non-guard catalog-alias readiness/warmup per method is separate from stable distributions. Report median/P95/max, not first-visible robot-motion delay.
- Missing backend skips the entire method; guard-handled cases are not LLM performance. LLM default was unconfigured; test only when actual service is explicitly enabled.

```sh
.venv/bin/python scripts/evaluate.py --split dev
.venv/bin/python scripts/evaluate.py --split test
```

Every run uses a new directory and refuses overwrite. Record unavailable-model reasons in summary. Human label review and ASL-user uncaptioned paraphrases remain future work.

## First frozen results, 2026-10-08

`results/evaluation/test-20261008T135255840626Z/`: summary, 120 actual records in `raw.jsonl`, 35 failures. Language source SHA256: `f0a9a40be70ce1bdd0d55672f24b8fcdfc7cf4e8d24ecc2ffc54ca7333568e0f`. Test/source hashes matched before/after; no final-set tuning/question rewriting.

| Metric | exact + shared guard | MiniLM + shared guard |
|---|---:|---:|
| Overall behavior | 38/60 (63.3%) | 47/60 (78.3%) |
| Supported correct | 8/30 (26.7%) | 17/30 (56.7%) |
| Supported false rejection | 22/30 (73.3%) | 13/30 (43.3%) |
| Out-of-library wrong execution | 0/30 | 0/30 |
| Coverage | 8/60 (13.3%) | 17/60 (28.3%) |
| Execution precision | 8/8 | 17/17 |
| Runtime errors | 0/60 | 0/60 |
| Median/P95 call | 0.0076/0.0142 ms | 3.2399/3.7593 ms |
| Separate readiness/load | 0.3303 ms | 2430.7508 ms |

LLM was `not_run`, without score. Embedding correctly selected nine additional supported examples but rejected 13. Zero wrong execution/observed precision does not establish population zero risk: common rules, simple negatives, and unreviewed labels constrain conclusions. Motion/ASL comprehension were outside scope.

## Negative local LLM development feasibility

B2 reused an existing free small local service for three fixed development positives without final-set access/tuning:

- V1: actual HTTP succeeded, but all answers were only `execute`, without JSON/ID. Strict parsing yielded `llm_invalid_response`; requests/replies preserved in `config/llm_local_feasibility_v1.json`.
- V2: one authorized format repair changed outputs to five complete labels, strictly matched and wrapped as Selection. `Hello → HELLO`, `Thank you → THANK_YOU`, `Please wait → CLARIFY`: 3/3 valid format, 2/3 correct. Failed the prerequired all-three gate. See `config/llm_local_feasibility_v2_label.json`.
- No further development prompt changes; V2 rejection was not counted correct. Default `config/llm.json` remained unconfigured. Both trials are development evidence, not final generalization.

The unchanged V2 was subsequently explicitly authorized as a negative research comparison. This did not change gate failure, questions, thresholds, prompt, or model. Default stays off; `SIGN_ROBOT_LLM_CONFIG=config/llm_experimental.json` explicitly selects research configuration.

## Actual additional LLM comparison, 2026-10-08

Actual run: `results/evaluation/test-20261008T142047221403Z/`. Preserve initial results and `test-20261008T141909955017Z/`: sandbox blocked loopback, the service received no request, readiness showed `request_attempted=true`, `response_received=false`, and entire LLM was `not_run`. This is not model-quality failure. Only local access permission was fixed; recorded reason specifies retaining not_run and unchanged model/protocol. Both additional directories have identical source/config/provenance hashes before/after.

This is an added-method comparison on the same small frozen set, not new human confirmation. Final SHA remained; B1/B2 did not tune against questions. Research config SHA256: `029a9a8cac30db39bee31c3c3dee2c8de8fd12c298875afa04317760189393b9`. Every actual HTTP prompt prefix SHA256: `763a7102f8acc89dab9ed133d2303ec9feda94cf24b11379df198d4eac53f379`, matching development V2. Actual model files, architecture, existing conversion source: `config/llm_local_provenance.json`. Original tuning history was not independently established; this is neither new training nor a pristine official baseline.

| Metric | exact + guard | MiniLM + guard | Local roughly 0.5B LLM + guard |
|---|---:|---:|---:|
| Overall | 38/60 (63.3%) | 47/60 (78.3%) | 48/60 (80.0%) |
| Supported correct | 8/30 | 17/30 | 20/30 |
| Supported false rejection | 22/30 | 13/30 | 7/30 |
| Supported wrong ID | 0/30 | 0/30 | 1/30 |
| Out-of-library wrong execution | 0/30 | 0/30 | 2/30 |
| Coverage | 8/60 | 17/60 | 23/60 |
| Execution precision | 8/8 | 17/17 | 20/23 (87.0%) |
| Error, including invalid labels | 0/60 | 0/60 | 2/60 |
| Selector median/P95 | 0.0080/0.0160 ms | 3.0392/3.2139 ms | 18.7660/24.4787 ms |
| Separate readiness | 0.3842 ms | 2063.5158 ms | 38.5327 ms |

For LLM's 60 decisions, shared guards ended 25; 35 received actual HTTP replies. One extra readiness request is excluded. The HTTP subset correctly selected/rejected 25/35; selector median/P95 20.0599/36.5609 ms. It is a post-guard conditional subset, not random population or pure-model timing without overhead. Service was already started; LLM readiness is not cold startup. MiniLM readiness includes loading in the evaluation process.

LLM's slightly higher total includes two out-of-library gratitude executions, one wrong supported ID, and two invalid labels. Strict parsing preserves errors without exact fallback. Evidence does not support default enablement or greater reliability than embedding. `counterexamples.jsonl` retains all 47 failures; `raw.jsonl` all 180 decisions with Selection/path/raw text/HTTP metadata.

The evaluator additionally records pre/post actual-config hashes, model provenance, V1/V2 gate evidence, and attribution to guard, received HTTP, attempted-without-response, or pre-HTTP failure. Tests check unavailable-backend scoring, denominators, and raw retention. They do not replace human labels, ASL review, or real-robot acceptance.
