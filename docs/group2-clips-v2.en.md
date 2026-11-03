# Group 2 word clips v2: for Group 3 to re-run (2026-11-02)

[中文](group2-clips-v2.md) · **English** · [Group 2 handoff](group2-handoff.en.md) · [Hospital demo](hospital-demo.en.md)

Branch `group2/clips-v2`. Group 3 chose to put both changes below into the final version, so the video word clips are regenerated and Group 3 needs to rebind its protection records and re-run planning on them. **Merged: Group 3 completed round 10 on these clips on 2026-11-03 (`results/hospital_sentences_20261102_010/`), and the demo now uses the round-10 transitions; see the [hospital demo](hospital-demo.en.md).**

## What changed

1. **Collision repair on** (`COLLISION_REPAIR = True` in `scripts/video/retarget_video.py`): filtering and speed limits run after IK and pushed hands into the body or the other hand; penetrating frames are re-solved for both arms from the previous clear frame. Over the 32 video words, max penetration **91.7 → 2.9 mm**, words over 5 mm **29 → 0**; chosen source videos unchanged; mocap words unchanged.
2. **NURSE manual correction** (`scripts/video/manual_corrections.py`): in the StartASL video the signer's left hand is cut off at the bottom of the frame, so MediaPipe placed it hanging at the hip. Checked against the four local NURSE dictionary videos (StartASL, Spread The Sign, ASL Deafined, SignSchool), the left hand is now **palm up, fingers curled, in front of the waist**, and the right hand an **N handshape (index and middle extended) lying horizontally on top of the left wrist**; the right wrist trajectory (the tapping) still comes from the video. A new optional `contact` setting (`G1Retargeter.targets`, NURSE only) cancels the separation caused by scaling each arm about its own shoulder. The right fingertip sits about 2.5 cm right above the left wrist, penetration 0 mm. This is a manual correction, not a recognition result.

## Changed clips (30; NOW and WAIT unchanged)

| Word | Old sha256 (first 12) | New sha256 (first 12) | Old max penetration mm | New max penetration mm |
|---|---|---|---|---|
| COME | `6c4a913fb105` | `ae555e0c1c98` | 11.2 | 0.0 |
| DEAF | `073f5453e484` | `d03abe86acac` | 7.8 | 0.0 |
| DOCTOR | `639f93c6b9c6` | `285cad1a3fc5` | 2.4 | 0.0 |
| HAVE | `0991bf7c0d04` | `ad4110ec387b` | 78.7 | 0.0 |
| HEADACHE | `485f8cdef577` | `8a9263ace636` | 40.1 | 1.1 |
| HELLO | `4bbb39ec1e4e` | `a1335d032605` | 28.1 | 0.0 |
| HURT | `a17641061df3` | `ea696f24ec37` | 23.8 | 0.0 |
| INTERPRETER | `3a159a8bd9af` | `28b47641d859` | 26.8 | 0.0 |
| LATER | `b9722ab602e3` | `3d5c3fd50057` | 38.0 | 0.0 |
| ME | `7470dbf5e39c` | `51dc56733a90` | 7.2 | 0.0 |
| MEDICINE | `b8c5e0b7ade5` | `af1b9b3a1193` | 32.8 | 2.9 |
| MORNING | `88874e76d814` | `19c42f008e08` | 25.8 | 0.0 |
| NEED | `c4ab9fc0ea73` | `a118fe4dc96a` | 29.9 | 0.0 |
| NIGHT | `20dece3ae287` | `f717e35c1179` | 62.6 | 0.0 |
| NO | `4c8af90a878f` | `6e4b2a0e3e2a` | 23.9 | 0.0 |
| NOT | `13b8b2c32a83` | `592363fe1fc1` | 76.6 | 0.0 |
| NURSE | `f75945f059ef` | `e06a52bad350` | 91.7 | 0.0 |
| PLEASE | `6b7b31ab5ff1` | `94708465fc6d` | 39.6 | 0.0 |
| SOON | `0fe325e7186b` | `254411342854` | 19.6 | 0.0 |
| SORRY | `4404913c8cad` | `b3c3893cbab5` | 24.2 | 0.0 |
| STOMACH | `23bb66ab1be2` | `dcabb55275b0` | 66.4 | 0.0 |
| TAKE | `3a99139dfee3` | `88cd19a1cc32` | 7.3 | 0.0 |
| THANK-YOU | `040c0cdea15d` | `09d8295e70a4` | 38.4 | 0.0 |
| TOMORROW | `0228a0538c20` | `9a203ead3dc0` | 59.5 | 0.0 |
| UNDERSTAND | `e50fee8ab934` | `d41eea30720c` | 10.8 | 0.0 |
| WHERE | `d7ec7d39eec7` | `f88bfec4942f` | 59.9 | 1.2 |
| WRITE | `a93d1bc2c5e9` | `c854122677a3` | 38.7 | 0.0 |
| YES | `dd29f2430c76` | `e0ff56fbb911` | 77.2 | 1.5 |
| YOU | `80c5de0eb7ed` | `cc24bbfbdddb` | 51.0 | 1.6 |
| YOUR | `7e0b5dbdad5c` | `92deb7259cc7` | 43.0 | 0.0 |

## What Group 3 needs to do

All 7 multi-word lines contain a changed word and need re-running: s1 (HAVE), s2 (NEED, INTERPRETER), s3 (DOCTOR, SOON), s4 (HURT), s6 (NURSE), s7 (MEDICINE, MORNING, NIGHT), s8 (UNDERSTAND).

1. Rebind the protection records on this branch: the current records are bound by hash to the old clips (`bcdefc4`) and report `STALE_USER_PROTECTION_MOTION`; on this branch 28 Group 3 tests fail for that reason, as expected.
2. Re-run round-8 planning, producing `render_inputs/<sentence>/replay.npz` in the same format as before.
3. Once returned, Group 2 compares against the baseline with `scripts/demo/compare_stitching.py`, merges only if it is not worse than now, and regenerates the demo videos.

## Other changes on this branch

- `scripts/demo/hospital_demo.py`: if an old Group 3 plan does not match the new clips, it falls back to the baseline with a message instead of failing.
- `results/video_previews/`: comparison videos for all 32 video words and the overview re-rendered on the new clips.
- Tests: all Group 2 tests pass (video words must carry a collision-repair record with at most 5 mm left; NURSE must come from 39089 with a manual-correction record).

## Limitations

- NURSE's left arm and both handshapes are hand-authored from the dictionary videos, not recognised; not reviewed by ASL users.
- The right fingers do not fully rest on the left wrist (about 2.5 cm gap), because collision avoidance uses convex hulls that are bulkier than the real hands.
