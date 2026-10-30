# ME5412 — English to ASL Gloss Conversion

[中文](README.md) · **English**

## Overview

This module converts English sentences from the hospital scenario into an ordered sequence of American Sign Language (ASL) glosses from a fixed vocabulary. For example, `Where does it hurt?` becomes `YOU HURT WHERE`.

Group 1 is responsible only for "English text → gloss". This module does not download sign motions, generate robot trajectories, or handle MuJoCo or any other robot simulation.

## In the main repository

- The end-to-end demo `scripts/demo/hospital_demo.py` (see [docs/hospital-demo.en.md](../docs/hospital-demo.en.md)) calls `scripts/translate.py --demo-only` from this folder in a subprocess with `--live`.
- `data/offline/hospital_dialogue_gloss.json` stores the live Gemini output for the 9 scripted dialogue lines (2026-10-31, 9/9 correct), so the demo runs without network or an API key. It is a cache of live results, not an independent test.
- All 35 glosses in `data/vocab/hospital_v1.json` are `motion_ready=true`, confirmed against Group 2's `motions/hospital_v1_motions.json`.

## Layout

```text
data/vocab/hospital_v1.json       35 fixed glosses and English synonyms
data/gloss_eval/gloss_test.csv    20 evaluation sentences
data/offline/                     offline gloss cache for the 9 dialogue lines
src/sign_robot/llm.py             Gemini client over the OpenAI-compatible API
src/sign_robot/gloss.py           text_to_gloss() conversion and strict validation
scripts/translate.py              single-sentence and interactive entry point
scripts/check_gloss.py            resumable, request-capped evaluation script
docs/usage.en.md                  short usage guide for teammates
docs/integration.en.md            calling and status-handling contract for Group 2
results/gloss_check/              test reports
tests/test_offline.py             offline regression tests (no Gemini calls)
```

## Requirements

- Windows 10/11 (also run on Ubuntu with Python 3.12)
- Python 3.12 (project verified with 3.12.7)
- Network access to the Google Gemini API
- A Google AI Studio API key

## Install

In PowerShell:

```powershell
cd D:\me5412_project
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks the activation script, call `.\.venv\Scripts\python.exe` directly without activating.

## API configuration

On first use, copy the template in the module root:

```powershell
Copy-Item .env.example .env
```

Then open `.env` in a text editor on your own machine only and put your own Google AI Studio API key after `GEMINI_API_KEY=`. Never share a real key in chat, source code, the README or Git.

The program reads `.env` from the module root at start-up. `.env` is excluded by `.gitignore`; `.env.example` is safe to commit. Existing system environment variables take precedence and are not overwritten by `.env`. `GEMINI_MODEL` and `GEMINI_BASE_URL` may be omitted; the defaults are `gemini-3.1-flash-lite` and `https://generativelanguage.googleapis.com/v1beta/openai/`.

## Current architecture

The original implementation guide described a local model on a Mac; this delivered version instead calls the online Google Gemini model through the OpenAI-compatible API. It needs network access and a valid Google AI Studio API key, and must not be described as an offline LLM deployment.

## Entering English

Translate one sentence and print the full JSON:

```powershell
python scripts/translate.py "Where does it hurt?"
```

Interactive mode:

```powershell
python scripts/translate.py
```

Type `exit` or `quit` to leave. To allow only glosses whose motions are ready:

```powershell
python scripts/translate.py --demo-only
```

## Output fields

- `status`: `ok`, `unsupported` or `error`.
- `glosses`: ordered gloss list; may be passed to the motion module only when `status=ok`.
- `question`: whether the input is a question.
- `dropped`: English function words or fragments that were not signed.
- `unknown`: important information the vocabulary cannot express.
- `latency_ms`: time taken for this conversion.
- `reason`, `error_category`, `http_status`, `validation_detail`: safe error diagnostics.

`unsupported` means important content is outside the vocabulary; `error` means an API, JSON or validation failure. Both forbid any robot motion.

## Running the 20-sentence test

Dry run by default, never calls Gemini:

```powershell
python scripts/check_gloss.py
```

Capped live test:

```powershell
python scripts/check_gloss.py --live --max-requests 3 --delay 5
```

Selected IDs only:

```powershell
python scripts/check_gloss.py --live --ids s1 s2 p1 --max-requests 9
```

Resume from a live report with the same model, test data and ID selection:

```powershell
python scripts/check_gloss.py --live --ids s1 s2 p1 --resume "results\gloss_check\previous_report.json" --max-requests 9
```

Every request, including retries, counts towards `--max-requests`. Reports are saved in `results/gloss_check/` and never overwrite earlier ones.

Offline regression tests make no Gemini requests:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

## Hand-off to Group 2

Group 2 reads the `glosses` list from the returned dictionary and looks up motions of the same name in order. Only `status=ok` may reach the motion module:

```python
result = text_to_gloss(sentence)
if result["status"] == "ok":
    ordered_motion_names = result["glosses"]
```

In normal mode, `ok` only guarantees that the glosses belong to the 35-gloss vocabulary, not that their motions are ready. Use `demo_only=True` when motions must be available, with `motion_ready` confirmed by Group 2.

The full status handling and calling contract is in [docs/integration.en.md](docs/integration.en.md).

## 35-gloss limit

Executable output is strictly limited to the 35 glosses in `hospital_v1.json`. When important content such as insurance, exact times, X-rays or allergy information cannot be expressed fully, the program returns `unsupported` rather than guessing or outputting partial motions.

## Common errors

- `401`: invalid API key; check `GEMINI_API_KEY`.
- `403`: insufficient project, region or API permission; check the Google AI Studio project.
- `404`: model not visible to the project, or model name / compatible endpoint mismatch.
- `429`: rate or quota limit reached; respect Retry-After and run later.
- `503`: Gemini temporarily unavailable; the test script retries a limited number of times within the cap.
- `timeout`: network or service timeout; resume the test from its report.

The program never switches models automatically and never retries indefinitely.

## Current test results

Final full live report: `results/gloss_check/20261027T011211_866109+0800.json`.

- 20/20 passed
- 26 API requests, 6 of them retries
- 0 final API failures

100% only means that these 20 fixed test sentences all passed in that run; it does not mean every English input is converted correctly. The test was run by Group 1 itself and is not an independent cross-review test.

## Known limitations

- Uses the online Gemini API and needs network access.
- Supports only the 35 predefined glosses.
- The reference word orders and interim project conventions have not been reviewed by ASL professionals.
- Gemini output may vary with service state and model behaviour.
- Correct conversion of every new English sentence is not guaranteed.
