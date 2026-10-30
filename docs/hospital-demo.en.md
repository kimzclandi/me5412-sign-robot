# Hospital end-to-end demo

[中文](hospital-demo.md) · **English** · [Group 2 handoff](group2-handoff.en.md)

One command runs the whole pipeline: a nurse's or doctor's English sentence → [Group 1] ASL gloss → [Group 2] G1 joint trajectory per word → stitched sentence → MuJoCo playback or a captioned video. By default it reads Group 1's offline results for the 9 scripted dialogue lines, so **the live demo needs no network and no API key**.

```
English sentence → gloss (offline cache, or --live calls Group 1's Gemini) → look up motions/hospital_v1_motions.json
                 → baseline stitching (scripts/mocap/stitch_baseline.py; Group 3's transition replaces this step) → playback / video
```

## 1. Setup after download (once)

Only Python 3.12 is needed; the minimal demo requirements leave out torch and MiniLM and install in a few minutes:

```bash
git clone https://github.com/kimzclandi/me5412-sign-robot && cd me5412-sign-robot
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-demo.txt
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python scripts/fetch_robot.py      # official Unitree G1 + Inspire hand model (~27 MB, pinned commit, hash-checked)
.venv/bin/python scripts/prepare_robot.py
.venv/bin/python -m pytest -q tests/test_hospital_demo.py tests/test_retarget.py
```

On Windows replace `.venv/bin/python` with `.venv\Scripts\python`. Setup for the full prototype (web page, MiniLM, learned model) is in the repository [README](../README.en.md).

## 2. Demo commands

| Purpose | Command |
|---|---|
| Play one line in the interactive 3D viewer (drag to rotate) | `.venv/bin/python scripts/demo/hospital_demo.py --line s4 --view` (macOS: `.venv/bin/mjpython`) |
| Select by sentence | `.venv/bin/python scripts/demo/hospital_demo.py "Where does it hurt?" --view` |
| Write a captioned video | `MUJOCO_GL=egl .venv/bin/python scripts/demo/hospital_demo.py --line s4 --render` (drop `MUJOCO_GL=egl` on macOS/Windows) |
| All 9 lines plus one full-dialogue video | `MUJOCO_GL=egl .venv/bin/python scripts/demo/hospital_demo.py --all --render` |
| Additionally, one video per act for slides 13–16 | `MUJOCO_GL=egl .venv/bin/python scripts/demo/hospital_demo.py --acts` |
| Any sentence typed live (calls Group 1's online model) | `.venv/bin/python scripts/demo/hospital_demo.py "Where is the pain?" --live --view` |

The 9 scripted lines (s1–s9) are in `group1_text_to_gloss/data/offline/hospital_dialogue_gloss.json`, e.g. s4 `Where does it hurt?` → `YOU HURT WHERE`. The video shows the English sentence at the top and highlights glosses word by word at the bottom, labelled with the gloss source, the stitching method and "not ASL-reviewed".

## 3. Live mode and failures

`--live` runs `group1_text_to_gloss/scripts/translate.py --demo-only` in a subprocess, which allows only glosses that have motion. It needs network and `GEMINI_API_KEY` in `group1_text_to_gloss/.env` (copy `.env.example` and fill in your own key; **never commit it or post it in the group chat**).

| Case | Behaviour |
|---|---|
| Model returns glosses | Plays normally, source `live_gemini` |
| Sentence outside the vocabulary (e.g. `Please show me your insurance card.`) | Shows the rejection, **plays nothing** |
| Network/API failure, sentence among the 9 cached lines | Uses the offline result, source `offline_cache_after_live_failure` |
| Network/API failure, sentence not cached | Error, plays nothing |
| No `--live` and sentence not cached | Error listing the available s1–s9 |

Measured 2026-10-31: all 9 lines correct online, most in 1–2 s, one request retried and took about 46 s. For the presentation, use the offline cache by default and `--live` only as an extra.

## 4. Outputs

- `results/demo/<name>.npz`: sentence trajectory in the repository motion format (`timestamps_s`, `joint_names`, `positions`, radians, 30 fps).
- `results/demo/<name>.json`: sentence, glosses, source, frame range and source library (mocap or video) of each word.
- `results/demo/<name>.mp4` and `results/demo/hospital_dialogue.mp4` (all 9 lines, about 91 s): committed, ready for the slides or as a backup if the network or laptop fails.
- The 4 act videos for slides 13–16 (robot only, with the English sentence and word-by-word gloss captions): `act1_registration.mp4` (lines 1–2, about 23 s), `act2_consultation.mp4` (lines 3–5, about 33 s), `act3_treatment.mp4` (lines 6–7, about 22 s), `act4_discharge.mp4` (lines 8–9, about 13 s). The human dictionary videos the slide notes mention for the right side belong to their sites and are not committed; if needed, combine them locally and credit the source.

## 5. Hand-off to Group 3

Stitching is currently the simplest baseline: each word cut to `sign_frames`, a fixed 0.5 s smooth blend between words, so the arms dip briefly between words. When Group 3's transition method is ready, replace the `stitch(...)` call in `hospital_demo.py`; the rest of the pipeline stays the same, and the baseline remains the "direct playback" comparison.

## 6. Limitations

- Robot motions are candidate signs, not reviewed by ASL users; the 26 video-derived words are graded "approximate".
- The offline cache covers only the 9 scripted lines; other sentences need `--live`. The cache stores live results and is not an independent test.
- Kinematic replay (fixed base, no dynamics); it does not show that a real robot can move at the same speed.
- Run end to end from a fresh download only on Linux (Ubuntu, Python 3.12); macOS and Windows are untested.
