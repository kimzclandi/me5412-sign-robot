# group2/clips-v2 clip review and protection bundle v4 (2026-11-02)

[中文](README.md) · **English**

Development evidence only, not verified ASL. **No trajectories were solved here** (the user asked not to solve for now);
this directory only compares clips, renders them and writes the protection bundle.

## Background

Group 2 (2026-11-02): the new word clips exist only on `group2/clips-v2` (`85bc230`), so Group 3 should continue on a new
branch made from it; NURSE's pose changed a lot, so the earlier NURSE exit settings and protection window need adjusting.
This branch, `group3/clips-v2`, was created from `85bc230` in its own working directory,
`/home/kingderman/Documents/ME5412-group3-clips-v2` (the original checkout is untouched). The meshes in
`assets/robot/vendor/` are not tracked and were copied from the original checkout (62 files, byte-identical); the tracked
`assets/robot` files are the same as on the old branch.

## What clips-v2 changed

Against the clips that rounds 8 and 9 used (`e8e025d`), 24 of the 35 clips changed, all with unchanged frame counts; the 9
mocap words, WAIT and NOW are unchanged.

- **NURSE**: essentially a new motion. 123 of 127 frames change by more than 0.05 rad in some joint; the left wrist roll by
  up to 3.9 rad.
- **The other 23 video-derived words**: collision repair touching a few frames. Largest joint change (rad) / frames changing
  by more than 0.05 rad: THANK-YOU 1.48/21, WRITE 0.84/34, YES 0.83/32, MORNING 0.75/36, NOT 0.69/23, STOMACH 0.62/20,
  HAVE 0.38/26, TOMORROW 0.37/11, HEADACHE 0.34/11, LATER 0.29/12, YOUR 0.26/5, MEDICINE 0.24/11, NO 0.21/7, DOCTOR 0.21/3,
  NEED 0.18/8, NIGHT 0.17/36, HURT 0.15/18, SOON 0.14/5, SORRY 0.12/25, INTERPRETER 0.11/6, ME 0.06/3, UNDERSTAND 0.06/1,
  DEAF 0.06/1 (`clips_v2_diff.py`).

## The new NURSE (`nurse_check.json`)

Self-clearance per frame with the planner's `MujocoClearance` (sampled, not a continuous-collision proof); speeds are the
30 Hz neighbouring-frame differences the source audit uses.

| | Old NURSE | New NURSE (clips-v2) |
|---|---|---|
| Deepest penetration | −91.7 mm (f112, left wrist into the torso) | −0.3 mm (f33, right thumb against the left wrist) |
| Frames at the speed cap | 15 (f29–39, f80–84, including the old flip) | 0 |
| Frames below 2 mm clearance | 23 | 25: f25–33, 40–43, 50–51, 54–55, 76, 78, 80–85 |

Every contact in the new clip is the right thumb touching the left wrist, i.e. the sign's own wrist taps; the left wrist
mostly rests on a joint limit over f30–74. Charts: `NURSE_clips_v2_frames.png` (every 4th frame, front and side) and
`NURSE_clips_v2_timeline.png` (clearance and speed, old clip in grey). The videos are not committed; they are on this
machine in `C:\Users\23971\Documents\5412\_runtime\render-out\nurse_clips_v2_162019\` (normal speed, 3× slow, old vs new).

## User decisions (chat, 2026-11-02)

- **New NURSE protected f23–f79** (0.77–2.63 s). The user first gave f23–f80; frame 80 is the first frame of the last wrist
  tap (right thumb already on the left wrist, 0.35 mm), a connector cannot leave from a frame in contact, and the user chose
  to drop that tap and end at f79 (4.24 mm). f23 has 5.9 mm clearance and barely moves.
- **Every other word keeps its v3 interval**, based on the boundary review below (the user did not ask for any change).
- No new trajectory solving for now.

## Boundary review (`boundary_check.json`, `boundary_detail.json`)

Old vs new clip at each v3 interval's start and end frame: the largest joint-angle change and the largest displacement of
any robot body origin under forward kinematics.

- 17 of the 23 collision-repaired words have identical start and end poses (0 mm).
- 6 words differ at a boundary, each because collision repair moved a finger or hand out of the body:

| Word | Interval | Frame that differs | Largest finger move | Largest hand/arm move | Self-clearance (old → new) |
|---|---|---|---|---|---|
| HAVE (sentence word) | f24–54 | end f54 | 21 mm | 6 mm (wrist ≈5°) | −15.8 → −0.2 mm |
| INTERPRETER (sentence word) | f30–60 | start f30 | 10 mm | 2.5 mm | −12.9 → −0.1 mm |
| TOMORROW | f24–66 | start f24 | 66 mm | 27 mm | −30.9 → +8.9 mm |
| YES | f18–69 | start f18 | 64 mm | 22 mm | −32.3 → +9.2 mm |
| WRITE | f27–69 | start f27 / end f69 | 2 / 9 mm | 2.5 / 9 mm | −3.4 → 0.0 / −9.6 → −0.1 mm |
| SORRY | f21–168 | end f168 | 7 mm | 4 mm | −7.3 → 0.0 mm |

- Changes inside the sentence words' intervals (boundaries identical): THANK-YOU 5 frames over 10 mm, at most 52 mm (f28,
  the left arm slightly farther from the body); NIGHT 6 frames, at most 33 mm (f42); HAVE 14 frames, at most 32 mm (f43);
  UNDERSTAND, MEDICINE and DOCTOR one frame each (28.5, 24, 19 mm); INTERPRETER 2 frames (at most 12.5 mm). NEED, HURT, SOON and MORNING
  are unchanged inside their intervals (their changes are all outside).
- Other words inside their intervals: YOUR 79 mm at f36, ME 13 mm, LATER 20 mm; NO, DEAF, STOMACH, HEADACHE and NOT unchanged.
- Images: `words_in_sentences_old_vs_new.png` (sentence words) and `other_words_old_vs_new.png` (other words); each row is
  old front, new front, old side, new side.

## Protection bundle v4 (`config/user_protected_hospital35_v4.json`)

- Written by `make_protection_v4.py` from v3: NURSE becomes [23, 79]; the 24 changed clips' hashes are re-bound
  (`rebinding.json`); every other interval is identical to v3. It loads with the planner's own loader against this branch's
  motion library (35/35 records).
- v3 (round 9: HURT from frame 37) was carried over from `group3/trajectory-planning` byte for byte; v1 and v2 stay.

## Protection bundle v5 (`config/user_protected_hospital35_v5.json`)

After watching the clips-v2 renders of HAVE and INTERPRETER (chat, 2026-11-02), the user **moved INTERPRETER to f19–f40**
(0.64–1.33 s, was f30–f60) and **kept HAVE at f24–f54**. `make_protection_v5.py` writes v5 from v4, replacing only the
INTERPRETER record, and validates it with the planner's loader (35/35). The renders use `word_check.py` (per-frame checks,
`HAVE_check.json`, `INTERPRETER_check.json`) and `render_word_review.py`; the frame sheets are `HAVE_clips_v2_frames.png`
and `INTERPRETER_clips_v2_frames.png`; the videos are only on this machine in
`C:\Users\23971\Documents\5412\_runtime\render-out\have_interpreter_clips_v2\`.

- INTERPRETER's new start f19 lies in the hand-contact span f17–24, so the connector must enter at f16 or earlier; f25–27
  and f32–35 reach the speed cap (source motion).
- HAVE's end f54 lies in the contact span f41–56, f59 has contact and f61–65 reach the speed cap; a connector leaving HAVE
  must start from a clean frame after f57.

## Not done yet

- **No trajectory solving** (the user's instruction). All seven sentences need re-planning on the new clips; NURSE's staged
  exit was designed for the old pose (left hand down at the lap) and needs a new design before solving.
- Round 9 (YOU HURT WHERE) results and the round-9 parts of the project record are still only on
  `group3/trajectory-planning`; this branch's TASK-28, STATE and HANDOFF are the versions published to the team repository
  this morning.
- The analysis and render scripts here (`nurse_check.py`, `boundary_check.py`, `boundary_detail.py`, `clips_v2_diff.py`,
  `render_nurse_review.py`, `render_boundary_compare.py`) ran from a temporary directory with this machine's paths written
  in; they are kept as a record of the method. The old clips were read from `group3/trajectory-planning`.

## Reproduction

```bash
cd /home/kingderman/Documents/ME5412-group3-clips-v2
/home/kingderman/Documents/ME5412-github-latest/.venv/bin/python results/clips_v2_review_20261102/make_protection_v4.py   # writes only files that do not exist yet
```
