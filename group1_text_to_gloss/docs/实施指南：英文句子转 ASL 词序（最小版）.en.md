# Group 1 implementation guide: English sentences to ASL word order (minimal version)

[中文](实施指南：英文句子转%20ASL%20词序（最小版）.md) · **English**

> Translation of the original plan by @patrick (Oct 26, 2026), kept as a record. The delivered version differs: it calls the online Google Gemini API instead of a local model on a Mac (see [README.en.md](../README.en.md)), and all 35 glosses are now `motion_ready=true`. The "motion source" column below shows the plan at the time; Group 2 finally used Studio Galt mocap for 9 words and public ASL dictionary videos for 26 (SignAvatars needed a personal access request).

Oct 26, 2026 · @patrick

Group 1 builds a conversion module that runs offline: a medical worker types an English sentence, and it outputs a sequence of signs in ASL word order, every one of them in the vocabulary, e.g. `Where does it hurt?` → `YOU HURT WHERE`. The vocabulary and test sentences are already written; follow this guide.

## 1. Your place in the demo

Demo scenario: a deaf patient at a hospital, with no sign language interpreter present. The teacher plays the medical worker and types English; the robot signs it. The whole pipeline runs offline on one Mac:

1. The teacher types `Where does it hurt?` on the web page
2. **Group 1**: a local LLM turns it into `YOU HURT WHERE`; code checks that every word is in the vocabulary
3. The page shows "Robot will sign: YOU · HURT · WHERE" for the teacher to confirm
4. Group 2's library provides a trajectory per word; Group 3 joins the trajectories into a sentence
5. The G1 robot in MuJoCo signs the whole sentence

You are responsible only for step 2: output stops at word names, no motion.

### The 4 deliverables

| # | Deliverable | Location |
| --- | --- | --- |
| 1 | Vocabulary (already written; just check gloss names with Group 2) | `data/vocab/hospital_v1.json` |
| 2 | LLM running offline on the demo Mac, with start-up instructions | `docs/local-llm.md` |
| 3 | Conversion function `text_to_gloss(sentence)` | `src/sign_robot/gloss.py` |
| 4 | 20 test sentences (already written) and a one-click check script | `data/gloss_eval/gloss_test.csv`, `scripts/check_gloss.py` |

The vocabulary and test sentence files were sent with this guide (`hospital_v1.json`, `gloss_test.csv`); put them in the matching places in the repository. Work on your own branch, e.g. `group1/text-to-gloss`, and open a PR when done.

## 2. Vocabulary: 35 words

The LLM may output only these 35 glosses. "English wording" lists phrases the teacher might use that should map to the gloss; put them in the prompt. "Motion source" is Group 2's responsibility and is listed only so you know which words already have motion.

| gloss | Meaning | English wording | Motion source |
| --- | --- | --- | --- |
| HELLO | hello | hello, hi, hey | Studio Galt (to convert) |
| PLEASE | please | please | Studio Galt (to convert) |
| THANK-YOU | thank you | thank you, thanks | SignAvatars |
| SORRY | sorry | sorry, apologize, excuse me | SignAvatars |
| YES | yes | yes, yeah, sure | SignAvatars |
| NO | no | no, nope | SignAvatars |
| YOU | you | you | Studio Galt (converted) |
| YOUR | your | your, yours | SignAvatars |
| ME | I / me | I, me, myself | SignAvatars |
| DEAF | deaf | deaf | SignAvatars |
| DOCTOR | doctor | doctor, physician, Dr | SignAvatars |
| NURSE | nurse | nurse | SignAvatars |
| INTERPRETER | interpreter | interpreter, sign language interpreter, translator | SignAvatars |
| APPOINTMENT | appointment | appointment, booking, reservation | Studio Galt (to convert) |
| MEDICINE | medicine | medicine, medication, pills, tablets, drug | SignAvatars |
| STOMACH | stomach | stomach, belly, tummy | SignAvatars |
| HEADACHE | headache | headache | SignAvatars |
| HAVE | have | have, has, got | SignAvatars |
| NEED | need | need, must, have to, require | SignAvatars |
| WAIT | wait | wait, hold on, one moment | SignAvatars |
| COME | come | come, coming, be here, arrive | Studio Galt (converted) |
| HURT | hurt | hurt, pain, ache, sore, painful | SignAvatars |
| BREATHE-DEEP | breathe deeply | take a deep breath, breathe deeply, breathe in | Studio Galt (to convert) |
| BLOOD-DRAW | draw blood | draw blood, blood test, blood sample | Studio Galt (to convert) |
| TAKE | take (also medicine) | take | Studio Galt (converted) |
| UNDERSTAND | understand | understand, get it | SignAvatars |
| WRITE | write | write, write down, note down | SignAvatars |
| NOT | not (negation) | not, don't, doesn't, didn't | SignAvatars |
| NOW | now | now, right now, immediately | SignAvatars |
| SOON | soon | soon, shortly, in a minute, in a moment | SignAvatars |
| LATER | later | later, after a while | SignAvatars |
| TOMORROW | tomorrow | tomorrow | SignAvatars |
| MORNING | morning | morning, in the morning | SignAvatars |
| NIGHT | night | night, evening, at night, bedtime | SignAvatars |
| WHERE | where | where | SignAvatars |

Each word in `hospital_v1.json` looks like this:

```json
{"gloss": "HURT", "category": "verb", "source": "signavatars", "motion_ready": false, "english": ["hurt", "pain", "ache", "sore", "painful"]}
```

- `motion_ready`: Group 2 sets it to `true` once the word's trajectory is ready. Use all 35 words for development and testing; in the demo allow only words with `motion_ready` `true`, switched by a parameter.
- To add or remove words or rename a gloss, agree with Group 2 first; names must match on both sides.

## 3. Implementation steps

### Step 1: run a local LLM on the demo Mac

- Model: a 7B-class instruction-tuned model, e.g. a 4-bit quantised Qwen2.5-7B-Instruct (about 5 GB).
- Runtime, either: `mlx_lm.server` (fastest on Apple silicon) or llama.cpp's `llama-server`. Both expose an OpenAI-compatible endpoint locally, e.g. `http://127.0.0.1:5413/v1/chat/completions`.
- The repository's `src/sign_robot/llm.py` already contains request code that only connects to the local endpoint; reuse it or use it as a reference.
- Measure on the actual demo Mac: is memory sufficient, how many seconds per sentence. Write installation, download, start commands and measurements into `docs/local-llm.md` so others can follow them.

### Step 2: prompt

The template below; `{VOCAB}` is generated by code from `hospital_v1.json`, one word per line, e.g. `HURT: hurt, pain, ache, sore, painful`. Wording may change, but keep the rules and examples.

```
You are an American Sign Language (ASL) interpreter in a hospital. A hearing medical worker types an English sentence; you convert it into a sequence of ASL glosses for a robot to sign to a Deaf patient.

You may ONLY use these glosses (gloss: English words it covers):
{VOCAB}

Rules:
1. Translate the meaning, not word by word. Use a listed gloss when the English word is a synonym.
2. Drop words ASL does not sign: a, an, the, is, are, am, be, do, does, did, will, would, can, could, to, it, this, that, of, at, in, on, for, and.
3. Put time words (NOW, SOON, LATER, TOMORROW, MORNING, NIGHT) at the start.
4. Put the topic first, then the comment. Example: MEDICINE, MORNING NIGHT TAKE.
5. Put question words (WHERE) at the end.
6. Put NOT after the verb: ME UNDERSTAND NOT.
7. Say pronouns explicitly (YOU, ME, YOUR).
8. If a meaning that matters cannot be expressed with the listed glosses (for example X-ray, insurance, a form, an exact time or number, an allergy), do not guess: return unsupported and list those words in "unknown".

Return ONLY one JSON object, no other text:
{"status": "ok" or "unsupported", "glosses": [...], "question": true or false, "dropped": [...], "unknown": [...]}

Examples:
Input: Where does it hurt?
Output: {"status": "ok", "glosses": ["YOU", "HURT", "WHERE"], "question": true, "dropped": ["does", "it"], "unknown": []}

Input: Take this medicine in the morning and at night.
Output: {"status": "ok", "glosses": ["MEDICINE", "MORNING", "NIGHT", "TAKE"], "question": false, "dropped": ["this", "in", "the", "and", "at"], "unknown": []}

Input: The nurse will draw your blood now.
Output: {"status": "ok", "glosses": ["NOW", "NURSE", "BLOOD-DRAW"], "question": false, "dropped": ["the", "will", "your"], "unknown": []}

Input: Sorry, I don't understand.
Output: {"status": "ok", "glosses": ["SORRY", "ME", "UNDERSTAND", "NOT"], "question": false, "dropped": [], "unknown": []}

Input: Do you need an X-ray?
Output: {"status": "unsupported", "glosses": [], "question": true, "dropped": [], "unknown": ["X-ray"]}
```

Note: the example sentences should not overlap too much with the test sentences in section 4, or the test will be inflated. 3 of the 5 examples above are the same as the dialogue script; replace them with sentences of your own.

### Step 3: the `text_to_gloss` function

```python
def text_to_gloss(sentence: str, demo_only: bool = False) -> dict:
    # 1. Empty input or over 200 characters -> {"status": "unsupported", ...}
    # 2. Load the vocabulary; with demo_only=True keep only motion_ready words
    # 3. Fill the prompt with the vocabulary and query the local model (temperature=0, 15 s timeout)
    # 4. Validate the model output (table below); if any check fails return {"status": "error", "reason": ...}
    # 5. Return the result with "latency_ms" added
```

Validation rules (never trust the model alone):

| Check | On failure |
| --- | --- |
| Output parses as JSON with all fields | `error`, reason `invalid_json` |
| `status` is only `ok` or `unsupported` | `error` |
| With `ok`, `glosses` is non-empty and every word is in the current vocabulary | `error`, reason `unknown_gloss` |
| With `ok`, at most 10 words | `error` |
| With `unsupported`, `glosses` is empty | `error` |
| Model unreachable or timed out | `error`, reason `llm_unavailable` |

No automatic retries, and no forcing words out of the model's free text. With `error` and `unsupported` the interface plays no motion.

## 4. Test sentences, check script and acceptance

### 20 test sentences (`gloss_test.csv`)

In the reference answers, `|` separates several word orders that all count as correct.

| id | Type | English | Reference | Question |
| --- | --- | --- | --- | --- |
| s1 | Script line | Hello, do you have an appointment? | HELLO YOU APPOINTMENT HAVE | yes |
| s2 | Script line | Do you need an interpreter? | YOU NEED INTERPRETER | yes |
| s3 | Script line | Please wait, the doctor will come soon. | PLEASE WAIT DOCTOR COME SOON | no |
| s4 | Script line | Where does it hurt? | YOU HURT WHERE | yes |
| s5 | Script line | Take a deep breath. | BREATHE-DEEP | no |
| s6 | Script line | The nurse will draw your blood now. | NOW NURSE BLOOD-DRAW | no |
| s7 | Script line | Take this medicine in the morning and at night. | MEDICINE MORNING NIGHT TAKE | no |
| s8 | Script line | Do you understand? | YOU UNDERSTAND | yes |
| s9 | Script line | Thank you. | THANK-YOU | no |
| p1 | Paraphrase | Where is the pain? | YOU HURT WHERE \| HURT WHERE | yes |
| p2 | Paraphrase | Hi, have you booked an appointment? | HELLO YOU APPOINTMENT HAVE | yes |
| p3 | Paraphrase | The doctor will be here shortly, please wait. | DOCTOR COME SOON PLEASE WAIT \| PLEASE WAIT DOCTOR COME SOON | no |
| p4 | Paraphrase | Is an interpreter needed? | YOU NEED INTERPRETER \| INTERPRETER NEED | yes |
| p5 | Paraphrase | Take your pills every morning and every night. | MEDICINE MORNING NIGHT TAKE \| MORNING NIGHT MEDICINE TAKE | no |
| p6 | Paraphrase | Sorry, I don't understand. Can you write it down? | SORRY ME UNDERSTAND NOT PLEASE WRITE \| SORRY ME UNDERSTAND NOT YOU WRITE | yes |
| o1 | Out of vocabulary | Do you need an X-ray? | reject | yes |
| o2 | Out of vocabulary | Please show me your insurance card. | reject | no |
| o3 | Out of vocabulary | Your appointment is at 3:30 pm. | reject | no |
| o4 | Out of vocabulary | Are you allergic to penicillin? | reject | yes |
| o5 | Out of vocabulary | Please fill in this form. | reject | no |

These reference answers follow the rules in section 3 and have not been reviewed by anyone who knows ASL. If someone in the team knows ASL or can find someone who does, have them check first; reasonable word orders may be added.

### Check script `scripts/check_gloss.py`

- Read `gloss_test.csv` line by line and call `text_to_gloss`.
- Scoring:
  - Sentences to reject: correct if `status` is `unsupported`.
  - Other sentences: correct if `status` is `ok` and `glosses` joined by spaces exactly matches one of the references.
  - `question` is recorded separately and does not affect scoring.
- Print per line: id, correct or not, model output, reference, latency. At the end print how many of each of the three types were correct and the slowest latency.
- Save results to `results/gloss_check/<time>.json` without overwriting earlier results.

### Acceptance criteria

- [ ] Script lines 9/9 correct
- [ ] Out-of-vocabulary sentences 5/5 rejected
- [ ] Paraphrases (6): report honestly how many were correct and explain each failure
- [ ] Never output a word outside the vocabulary (guaranteed by the validation code)
- [ ] Return `error` without crashing when the local model is disconnected
- [ ] Measure per-sentence latency on the demo Mac and record it in `docs/local-llm.md`
- [ ] Open a PR with the above code and files from the `group1/text-to-gloss` branch

If paraphrases do not match, adjust the rules and examples in the prompt first; do not copy test sentences into the examples verbatim. Once this version is done, Group 3 can connect the interface and motion module. If time allows, add the rule-baseline comparison and an independent test set from the full task description (link in the Chinese original).
