# Calling contract for Group 2

[中文](integration.md) · **English**

## Stable entry point

Run Python from the module root, add `src` to the module search path, then import:

```python
from sign_robot import text_to_gloss

result = text_to_gloss(sentence, demo_only=True)
```

It can also be called through `scripts/translate.py`. Do not copy the prompt or reimplement the validation.

In the main repository, the module's package is also named `sign_robot`, so `scripts/demo/hospital_demo.py` runs `scripts/translate.py --demo-only` in a subprocess instead of importing it into the same process.

## Input

- `sentence`: non-empty English string, at most 200 characters.
- `demo_only=True`: allows only glosses with `motion_ready=true` in the current vocabulary. Recommended for robot demos.
- `demo_only=False`: allows all 35 glosses, suited to developing the language module; it does not mean all motions are ready.

## Return statuses

### `status=ok`

Only this status allows consuming `glosses`. The motion module must keep the list order strictly and check that each motion file exists before playing.

### `status=unsupported`

The input contains important meaning the 35-gloss vocabulary cannot express. `glosses` must be empty; no partial motion may be played.

### `status=error`

An API, network, JSON or validation error occurred. No motion may be played, and a previous successful result must not be used as this result.

## Minimal safe call

```python
from sign_robot import text_to_gloss

result = text_to_gloss(user_sentence, demo_only=True)
if result["status"] == "ok":
    ordered_glosses = result["glosses"]
    # Check that each motion exists, then hand over to the transition module.
elif result["status"] == "unsupported":
    show_message("The current vocabulary cannot fully express this sentence")
else:
    show_message("The conversion service is temporarily unavailable")
```

`show_message` and the motion module interface are implemented by the caller.

## Reproducibility

Fixed code, vocabulary, prompt, model ID and configuration keep the interface and validation behaviour consistent, but an online generative model does not guarantee identical glosses on every call. Callers must handle each independent result by its status and must not rely on earlier outputs.

The end-to-end demo's fallback to the offline cache applies only to the 9 cached scripted lines and is labelled `offline_cache_after_live_failure`; it does not reuse arbitrary earlier results.

## Motion vocabulary responsibility

`motion_ready` is the motion readiness confirmed by Group 2. When Group 2 completes or withdraws a motion, both groups should check this field together. Do not assume the robot has a motion just because a gloss belongs to the 35-gloss vocabulary.
