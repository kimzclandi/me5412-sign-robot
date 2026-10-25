# Mocap to G1 retargeting (Group 2)

[中文](mocap-retargeting.md) · **English** · [Documentation index](README.md)

Group 2 converts the Studio Galt ASL motion capture selected by Group 1 (FBX, CC0-1.0, pinned commit `eb9046596fffcc6e92ee91d021372961f3d4fcaa`) into robot trajectories in the repository motion format. All 27 words in Group 1's vocabulary are converted; the grades are below.

## Pipeline: inputs and outputs per step

| Step | Script | Input | Output |
|---|---|---|---|
| 1. Read FBX | `scripts/mocap/extract_fbx_skeleton.py` (headless Blender 4.2 LTS) | `data/mocap/studio_galt_v1/raw/<WORD>/*.fbx` | `data/mocap/studio_galt_v1/skeleton/<WORD>.npz`: per-frame world positions and orientations of chest, shoulder, elbow, wrist and three bones per finger, at source frame rate |
| 2. Retarget | `scripts/mocap/retarget_to_g1.py --word <WORD>` | step 1 output | `motions/studio_galt_v1/<WORD>.npz`: `timestamps_s[T]`, `joint_names[53]`, `positions[T,53]`, radians, 30 fps; the JSON beside it records source, errors and limitations |
| 3. Compare | same with `--render` | step 2 output | `results/mocap_previews/<WORD>.mp4`: human skeleton vs robot, front and right-side views |
| 4. Summary | `scripts/mocap/summarize_library.py` | all clips | `results/mocap_previews/summary.md`: errors, speeds, penetration, palm distance |
| 5. Library index | `scripts/mocap/build_library_index.py` | all clips and Group 1's word list | `motions/studio_galt_v1/index.json`: id, gloss, motion file, `core_frames`, robot grade |

```bash
# one word
~/tools/blender-4.2.3-linux-x64/blender -b --factory-startup --python scripts/mocap/extract_fbx_skeleton.py -- \
  --fbx "data/mocap/studio_galt_v1/raw/YOU/SG ASL You 2025-7-22 No Mesh Full.fbx" --word YOU \
  --out data/mocap/studio_galt_v1/skeleton/YOU.npz
MUJOCO_GL=egl PYTHONPATH=scripts/mocap .venv/bin/python scripts/mocap/retarget_to_g1.py --word YOU --render
# after all words
MUJOCO_GL=egl .venv/bin/python scripts/mocap/summarize_library.py
.venv/bin/python scripts/mocap/build_library_index.py
```

On macOS use `/Applications/Blender.app/Contents/MacOS/Blender` and drop `MUJOCO_GL=egl`. Extracted skeletons are committed, so retargeting alone does not need Blender. Raw FBX files are not committed (`.gitignore`); restore them from Group 1's archive or the pinned upstream commit.

## Interface for Groups 1 and 3

`motions/studio_galt_v1/index.json` is the base of the vocabulary table: ids 1–27 follow the order of Group 1's `recommended_vocabulary.csv`. Each entry has the motion path, duration, `core_frames` and `robot_status`.

- Every clip starts and ends at the same neutral pose, so clips can be played back to back as they are.
- `core_frames` marks the sign itself; when stitching, the 0.8 s transitions can be trimmed and replaced by a transition between the two signs.
- LLM output ids map directly to `id`; words graded `poor` should be replaced or fixed by hand before a demo.

## Mapping method

- **Cropping**: frame 0 of every Studio Galt file is the T-pose bind pose (checked for all 27) and is skipped; the clip is then cropped to where a wrist moves faster than 0.03 m/s, with 0.2 s / 0.3 s padding.
- **Bone names**: ASK uses the 2023 rig (Bicep/Forearm/Index1 …); the extractor has a built-in alias table to the current names.
- **Arms**: a per-frame human chest frame (forward, left, up) is built from the shoulders and the neck–pelvis direction. Wrist and elbow positions relative to the same-side shoulder are scaled by the arm-length ratio (about 0.82) and placed at the robot shoulder. Bounded least-squares IK on the 7 joints per side matches wrist position and hand orientation, and softly the elbow.
- **Collision avoidance**: arms keep 1 cm from the torso and hips; the right hand (solved second) may touch but not enter the already-placed left hand, with all fingers of both hands checked.
- **Continuity**: each arm joint may change by at most 25 rad/s worth of angle per frame, so IK cannot jump to another solution near a joint limit and flip a joint within one frame.
- **Hand orientation**: both human and robot hand frames use wrist→middle-finger base and pinky base→index base, so left/right mirroring stays consistent.
- **Fingers**: per finger, the rotation angles of the hand→1→2→3 joints relative to the bind pose are summed; 15°–230° maps linearly to 0–1.7 rad on the single coupled Inspire joint. Thumb flexion drives pitch (capped at 0.5 so coupled joints stay in range) and thumb crossing over the palm drives yaw. Relative rotations are used because the bone tails in these FBX files do not point along the fingers; positions would add about 90°.
- **Joining**: the core is resampled to 30 fps with 0.8 s smooth transitions from and to the shared neutral pose.

## Results for the 27 words

Grades come from `results/mocap_previews/overview.png`, each word's comparison sheet and video, and the numbers in `summary.md`. They judge whether the robot reproduces the human motion; they are **not an ASL-user review**.

| Grade | Count | Words |
|---|---|---|
| Usable: motion, position and handshape match the human | 14 | ASK, BAG, BIG, BOX, BRING, BUSY, CHILD, COME, COMPUTER, EQUAL, FUTURE, ONE, TAKE, YOU |
| Approximate: recognisable, with a known robot limitation | 11 | Two-hand contact only reaches touching: BALL, BOOK, BUY, CALM, CLEAN, CLOSE, COOK, EVERYONE; hands near the chest look near the face: CUSTOMER; fingers cannot spread: TWO, THREE |
| Poor: fix or replace before a demo | 2 | BABY (crossed-forearm cradle only roughly reproduced), BEFORE (both hands crowd the midline and the right wrist twists unnaturally) |

- Sign-phase wrist error (frames with the hand at least 10 cm above its lowest point): below 2 cm for every usable word, below 3 mm for 12 of them.
- Penetration: at most 14 mm for any word (upstream collision geoms only, excluding mesh overlap between adjacent parts of the same hand).
- In the hanging rest pose at the start and end, wrists deviate 2–3 cm: the human hand hangs lower than the robot hip allows without touching the leg.

## Limitations

- Inspire fingers cannot spread or close together, so V/3 handshapes cannot be reproduced.
- Finger flexion ranges are fixed constants, not calibrated per sign or signer.
- Torso, head and face motion are not transferred; the robot base is fixed. The robot neck is short, so positions near the human face end up nearer the robot head.
- Robot hands are much larger than human hands; two-hand contact signs only reach touching, not full contact.
- Finger closing reaches about 25 rad/s (the real human speed), which a physical Inspire hand may not achieve; Group 3 should rate-limit during stitching.
- Not reviewed by ASL users.
