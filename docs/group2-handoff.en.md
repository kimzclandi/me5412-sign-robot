# Group 2 handoff: demonstrations → robot joint trajectories

[中文](group2-handoff.md) · **English** · [Method details](mocap-retargeting.en.md)

Status (2026-10-26): all 27 words in Group 1's vocabulary are converted to G1 joint trajectories. Code, data, videos and tests are in PR [#5](https://github.com/kimzclandi/me5412-sign-robot/pull/5) (branch `group2/fbx-retarget-you`), not yet merged into `master`.

## 1. Where this sits in the pipeline

```
Teacher's sentence → [Group 1] LLM → ids [1, 6, 14]
                   → [Group 2, this delivery] id → one robot joint trajectory per word (prepared offline)
                   → [Group 3] stitch the clips into a sentence → MuJoCo playback
```

Group 2's output is **data prepared offline** and independent of the operating system: `.npz` files produced on Linux work unchanged on a Mac.

## 2. For Group 3

| File | Content |
|---|---|
| `motions/studio_galt_v1/index.json` | **Entry point.** 27 words, each with `id` (1–27), `gloss`, motion path, duration, `core_frames`, `sign_frames`, `robot_status` and a note |
| `motions/studio_galt_v1/<WORD>.npz` | `timestamps_s[T]`, `joint_names[53]`, `positions[T,53]`, radians, 30 fps — the existing repository motion format, playable with `sign_robot.motion.apply_frame` |
| `motions/studio_galt_v1/<WORD>.json` | Source FBX and hash, IK error, peak joint speed, limitations |
| `scripts/mocap/stitch_baseline.py` | **Simplest sentence baseline**: each word cut to `sign_frames`, fixed 0.5 s smooth blend between words. Usable as Group 3's required "direct playback" comparison |
| `results/mocap_previews/sentence_YOU_BUY_BOOK.mp4` | Example sentence from the baseline |

### Frame ranges per word

```
0 ────── core_frames[0] ── sign_frames[0] ════ sign ════ sign_frames[1] ── core_frames[1] ────── T-1
  neutral→                  hand rises from rest          hand returns to rest          →neutral
  0.8 s transition                                                                      0.8 s transition
```

- Every clip starts and ends at **the same neutral pose**, so clips can be played back to back without jumps, but the robot lowers its hands between words.
- To stitch a sentence, blend from one word's `sign_frames[1]` to the next word's `sign_frames[0]`; `stitch_baseline.py` does exactly this.
- `sign_frames`: the span where either hand is at least 10 cm above its lowest position in that word.

### Stitching example

```bash
MUJOCO_GL=egl .venv/bin/python scripts/mocap/stitch_baseline.py YOU BUY BOOK --render   # drop MUJOCO_GL=egl on macOS
```

Writes `results/mocap_previews/sentence_YOU_BUY_BOOK.npz` (same motion format) and `.mp4`. Words outside the library, e.g. `MEDICINE`, are rejected.

### Notes for Group 3

- **Finger speed**: finger closing reaches about 25 rad/s (real human speed), which a physical Inspire hand may not achieve. Rate-limit if aiming at real hardware.
- **Known baseline issue**: YOU's `sign_frames` ends while the hand is already dropping, so the right arm dips briefly between YOU and BUY. This is where Group 3's transition method can improve on, and be compared with, the baseline.
- **Interfaces unchanged**: `ACTION_IDS`, `data/catalog.json` and the three original motions are untouched; the new library lives in `motions/studio_galt_v1/`. Whether to extend `ACTION_IDS` for the demo is a joint decision of all three groups.

## 3. For Group 1

- `id` in `index.json` is the number the LLM should output (same order as Group 1's `recommended_vocabulary.csv`).
- Grades (whether the robot reproduces the human motion — **not an ASL review**):
  - Usable (14): ASK, BAG, BIG, BOX, BRING, BUSY, CHILD, COME, COMPUTER, EQUAL, FUTURE, ONE, TAKE, YOU
  - Approximate (13): BABY, BALL, BEFORE, BOOK, BUY, CALM, CLEAN, CLOSE, COOK, CUSTOMER, EVERYONE, THREE, TWO
  - Poor (0)
- For preset demo sentences prefer usable words, e.g. `YOU COME`, `CHILD TAKE BOX`, `EVERYONE EQUAL`.
- To add words: send Group 2 the FBX from the same source (Studio Galt); following [Method details](mocap-retargeting.en.md) takes a few minutes per word.

## 4. For Group 2 teammates (what was done and how to check it)

1. **Overview image**: `results/mocap_previews/overview.png` — 27 words, human skeleton left, robot right in each pair.
2. **Videos**: `results/mocap_previews/<WORD>.mp4` — top row front, bottom row right side; human left, robot right.
3. **Numbers**: `results/mocap_previews/summary.md` — per-word error, speed, penetration, palm distance.
4. **Method**: [mocap-retargeting.en.md](mocap-retargeting.en.md) — inputs/outputs per step, mapping, limitations.
5. **Code**: `src/sign_robot/retarget.py` (mapping), `scripts/mocap/` (extract, retarget, render, summarise, index, stitching baseline).
6. **Tests**: `tests/test_retarget.py` — format, limits, couplings, start/end pose and error checks for all 27 words.

Reproduce locally (no Blender needed; extracted skeletons are committed):

```bash
git fetch origin && git switch group2/fbx-retarget-you
.venv/bin/python -m pytest -q tests/test_retarget.py
MUJOCO_GL=egl PYTHONPATH=scripts/mocap .venv/bin/python scripts/mocap/retarget_to_g1.py --word YOU --render
```

### Key numbers

- 27/27 words converted; 14 usable, 13 approximate, 0 poor.
- Sign-phase wrist error: below 2 cm for every usable word.
- Penetration: at most 16 mm for any word (upstream collision geoms only).
- 252 repository tests pass; the only failure, `test_project_overview`, also fails on `master` (doc edits without updated website allow-list hashes) and is unrelated to Group 2.

## 5. Not done — work teammates can pick up

- **ASL review**: grades are an engineering judgement; nobody fluent in ASL has checked them.
- **Finger calibration**: flexion range is a fixed constant (15°–230°), not tuned per word.
- **macOS check**: the pipeline has only run on Linux; if the final demo runs on a Mac, run the tests and a render there.
- **Existing `master` test failure**: update the six document hashes in the website allow-list, and add this document and the method document to the `docs/README.md` index.
- **Raw FBX**: not committed; restore from Group 1's archive or the pinned Studio Galt commit when needed.
