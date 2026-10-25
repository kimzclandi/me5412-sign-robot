# Mocap to G1 retargeting (Group 2)

[中文](mocap-retargeting.md) · **English** · [Documentation index](README.md)

Group 2 converts the Studio Galt ASL motion capture selected by Group 1 (FBX, CC0-1.0, pinned commit `eb9046596fffcc6e92ee91d021372961f3d4fcaa`) into robot trajectories in the repository motion format. YOU is working end to end; the other 26 words have not been processed yet.

## Pipeline: inputs and outputs per step

| Step | Script | Input | Output |
|---|---|---|---|
| 1. Read FBX | `scripts/mocap/extract_fbx_skeleton.py` (headless Blender 4.2 LTS) | `data/mocap/studio_galt_v1/raw/<WORD>/*.fbx` | `data/mocap/studio_galt_v1/skeleton/<WORD>.npz`: per-frame world positions and orientations of chest, shoulder, elbow, wrist and three bones per finger, at source frame rate |
| 2. Retarget | `scripts/mocap/retarget_to_g1.py --word <WORD>` | step 1 output | `motions/studio_galt_v1/<WORD>.npz`: `timestamps_s[T]`, `joint_names[53]`, `positions[T,53]`, radians, 30 fps; the JSON beside it records source, errors and limitations |
| 3. Compare | same with `--render` | step 2 output | `results/mocap_previews/<WORD>.mp4`: human skeleton vs robot, front and right-side views |

```bash
~/tools/blender-4.2.3-linux-x64/blender -b --factory-startup --python scripts/mocap/extract_fbx_skeleton.py -- \
  --fbx "data/mocap/studio_galt_v1/raw/YOU/SG ASL You 2025-7-22 No Mesh Full.fbx" --word YOU \
  --out data/mocap/studio_galt_v1/skeleton/YOU.npz
MUJOCO_GL=egl PYTHONPATH=scripts/mocap .venv/bin/python scripts/mocap/retarget_to_g1.py --word YOU --render
```

On macOS use `/Applications/Blender.app/Contents/MacOS/Blender` and drop `MUJOCO_GL=egl`. Raw FBX files are not committed (`.gitignore`); restore them from Group 1's archive or the pinned upstream commit.

## Mapping method

- **Cropping**: frame 0 of each Studio Galt file is the T-pose bind pose and is skipped; the clip is then cropped to where a wrist moves faster than 0.03 m/s, with 0.2 s / 0.3 s padding. The YOU file is 10 s long; the active part is about 3.2 s.
- **Arms**: a per-frame human chest frame (forward, left, up) is built from the shoulders and the neck–pelvis direction. Wrist and elbow positions relative to the same-side shoulder are scaled by the arm-length ratio (about 0.82) and placed at the robot shoulder. Bounded least-squares IK on the 7 joints per side matches wrist position and hand orientation, and softly the elbow, while keeping torso clearance and continuity with the previous frame.
- **Hand orientation**: both human and robot hand frames use wrist→middle-finger base and pinky base→index base, so left/right mirroring stays consistent.
- **Fingers**: per finger, the rotation angles of the hand→1→2→3 joints relative to the bind pose are summed; 15°–230° maps linearly to 0–1.7 rad on the single coupled Inspire joint. Thumb flexion drives pitch (capped at 0.5 so coupled joints stay in range) and thumb crossing over the palm drives yaw.
- **Joining**: the core is resampled to 30 fps with 0.8 s smooth transitions from and to the shared neutral pose; `core_frames` in the JSON marks the sign itself so Group 3 can trim transitions when stitching.

## YOU results

- Wrist position error 0.5 mm mean, 2.9 mm max; hand orientation error at most 0.004 rad; no joint-limit violations.
- In the comparison video the index finger points forward with the other three fingers closed, matching the human skeleton.
- Known differences: the human elbow bends more than the robot's straighter arm. Finger closing reaches 13.7 rad/s, the real human speed, which a physical Inspire hand may not achieve; Group 3 should rate-limit during stitching.

## Limitations

- Inspire fingers cannot spread or close together, so V/3 handshapes cannot be reproduced (TWO and THREE will be distorted).
- Finger flexion ranges are fixed constants, not calibrated per sign or signer.
- Torso, head and face motion are not transferred; the robot base is fixed.
- Per-shoulder scaling does not preserve hand-to-hand or hand-to-body contacts (BUY, CLEAN, COOK, BOOK need extra handling).
- Not reviewed by ASL users.
- ASK uses an older rig naming and needs an alias table first.
