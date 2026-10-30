# Talking points: slides 6–11 (Groups 1 and 2)

[中文](presentation-notes.md) · **English** · [Hospital demo](hospital-demo.en.md)

For the "Text to Gloss (slides 6–7)" and "Gloss to Motion (slides 8–11)" parts of the Google Slides draft. Each slide lists points to put on the slide, a script and where the numbers come from. All numbers come from files in the repository (2026-10-31); presenters may reword freely but should not change numbers or drop the limitations. Replace the stitching comparison on slide 11 once Group 3's results are in.

## Slide 6 · Word order: English vs ASL

**Points**
- ASL is not word-for-word English: articles, copulas and auxiliaries are dropped (a, the, is, do, will…)
- Time words first: `NOW NURSE BLOOD-DRAW`
- Topic, then comment: `MEDICINE MORNING NIGHT TAKE`
- Question words last: `YOU HURT WHERE`
- Negation after the verb: `ME UNDERSTAND NOT`

**Script**: "Where does it hurt?" becomes YOU HURT WHERE in ASL. So the first step is not a dictionary lookup but reordering the sentence into ASL word order. We wrote these rules into the prompt.

**Caveat**: the reference word orders follow these rules and have not been reviewed by anyone who knows ASL.

## Slide 7 · LLM plus vocabulary validation, and test results

**Points**
- Online Gemini (`gemini-3.1-flash-lite`) handles understanding and ordering; code does the checking: output must be valid JSON, every gloss must be in the 35-gloss vocabulary, at most 10 words
- Important information outside the vocabulary (X-ray, insurance, allergy, exact time) returns `unsupported`, and the robot **does not move**
- 20-sentence test: original lines 9/9, paraphrases 6/6, out-of-vocabulary 5/5 correctly rejected, no wrong execution
- The demo reads offline results for the 9 lines by default; live calls are an extra

**Script**: an LLM may invent words, so we don't trust it directly; we check every field. We would rather refuse than sign an incomplete message.

**Sources**: `group1_text_to_gloss/results/gloss_check/20261027T011211_866109+0800.json` (20/20, 26 requests, 6 of them retries); the ~6.6 s average is Group 1's reported value. Re-run of the 9 original lines on 2026-10-31: 9/9, most in 1–2 s, one retried request took about 46 s.

**Caveat**: this is Group 1's self-test, not an independent cross-review test; the online model needs network and an API key.

## Slide 8 · Where the motion library comes from

**Points**
- All 35 glosses have robot motion
- 9 from the Studio Galt sign-language mocap archive (CC0, pinned upstream commit): YOU, COME, TAKE, HELLO, PLEASE, APPOINTMENT, BREATHE-DEEP, BLOOD-DRAW, WHERE
- 26 from public ASL dictionary videos indexed by WLASL, with 3D body and hand landmarks from MediaPipe
- The planned SignAvatars data needed a personal access request that would not arrive in time; videos are analysed locally only and not committed

**Script**: mocap is the ideal data but does not cover the whole hospital vocabulary, so the remaining 26 words are extracted from single-signer, front-facing dictionary videos.

## Slide 9 · Retargeting: from human to the G1 robot

**Points**
- Chest-centred frame; wrist and elbow targets scaled by arm length
- Inverse kinematics on 7 joints per arm within joint limits, also matching palm orientation
- Finger flexion mapped to the Inspire hand (6 actuated joints per hand, with coupled joints); the thumb is limited by its joint range
- Keeps hands out of the body, legs and the other hand; limits per-frame joint change to avoid sudden wrist flips
- Output: 30 fps, 53 joint coordinates (26 active), same neutral pose at start and end

**Script**: human and robot bodies and joints differ, so angles cannot be copied; we first align hand position and orientation, then solve within the robot's own joint limits.

**Numbers**: mocap library of 33 words: 16 "usable", 17 "approximate"; every "usable" word has sign-phase wrist error below 2 cm; penetration at most 19 mm (upstream collision geometry only).

## Slide 10 · Problems with video data and the fixes

**Points**
- Problem 1, jitter: video estimates of thumb and wrist orientation flip suddenly (HURT's thumb briefly at 37.7 rad/s) → 5-frame median filter, fingers limited to 10 rad/s, arms to 15 rad/s
- Problem 2, unequal arm lengths: an arm angled towards the camera looks shorter, by up to 1.9x, which magnifies one side's motion → both arms share one scale
- Problem 3, wrong video choice: choosing by detection rate once picked a MEDICINE video with 22 cm error → now the lowest-error video among those with ≥ 50% detection
- Result: MEDICINE error 192 mm → 6 mm; median error of the 26 video words 6 mm, 15 of them within 1 cm
- All 26 video words are graded "approximate", never "usable"

**Script**: this slide tells the "find the problem, locate the cause, fix, verify" story. Group 3 noticed MEDICINE looked odd; we traced it to arm scaling and video choice, and the fix improved every video word.

**Caveat**: 6 words still have 4–11 cm error (MORNING, NIGHT, HEADACHE, WRITE, YES, ME), mainly where hands are near the head or the arms cross, so the robot's joint limits and collision avoidance hold it back. Depth from a single camera is the least reliable axis.

**Source**: `motions/hospital_v1_motions.json` and `ik_error_sign_phase` in each word's `.json`.

## Slide 11 · Sentence stitching baseline (to be compared with Group 3)

**Points**
- Each word cut to the span where the hand is raised (`sign_frames`), fixed 0.5 s smooth blend between words
- One command goes from English sentence → gloss → motion → video: `scripts/demo/hospital_demo.py`
- The 9 dialogue lines take 3.8–16 s each, about 91 s back to back (`results/demo/hospital_dialogue.mp4`)
- Known issue: the arms dip briefly between words, which is exactly what Group 3's transition method should improve and be compared against

## Limitations for every slide

- Robot motions are **candidate signs**, not reviewed by ASL users; never call them "verified ASL"
- Kinematic replay (fixed base, no dynamics); it does not show that a real robot can move at the same speed
- The human dictionary videos on the right belong to their sites; credit the source (StartASL, Spread The Sign, etc.) and do not share the original videos publicly
