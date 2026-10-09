# Fixed-base robot candidates

[中文](README.md) · **English**

Official source: Unitree `unitree_ros`, commit `5994d4faef0a9cadd3287f8de0199a67eeb2a259`, model `g1_29dof_rev_1_0_with_inspire_hand_DFQ.urdf`.

`vendor/` retains unchanged URDF, 59 referenced meshes, and official README/license: 62 files, 27,189,102 bytes. `upstream_manifest.json` records URLs/SHA256. The first download accessed only fixed-version official public files, without ROS installation, learned-model download, or paid applications.

`scripts/prepare_robot.py` fixes duplicated `meshes/meshes`, exports derived MJCF, and adds fixed mount/scene/palm references. Originals stay unchanged. `scene.xml` actually loaded with MuJoCo 3.15.0: 53 scalar joints, 12 mimic equations, zero actuators. Legs/waist are fixed in trajectories; all 12 finger couplings are explicitly satisfied framewise, never treated as independent drives.

Playback writes `qpos` then calls `mj_forward`. No actuator-based `mj_step` control; no dynamic feasibility, real tracking, or clinical claim. Head/face remain static; fingers cannot independently spread sideways. Expression suitability still requires actual ASL-user review.

From project root:

```sh
.venv/bin/python scripts/fetch_robot.py
.venv/bin/python scripts/prepare_robot.py
.venv/bin/python scripts/build_motions.py
.venv/bin/python scripts/render_motions.py --allow-candidate-preview
.venv/bin/python scripts/check_motion_calibration.py
.venv/bin/python -m pytest tests/test_motion.py -q
.venv/bin/mjpython scripts/play_motion.py --action HELLO --allow-candidate-preview
```

Rendering in a restricted macOS command sandbox may report `invalid CoreGraphics connection`. With authorized local rendering, native MuJoCo Renderer produced PNG/MP4. Interface screen recordings were not substituted for renders.

An agent authored wrist targets/timing; numerical IK solved arms, smooth interpolation formed paths, fingers followed original coupling. These are not extracted human 3D data. `motions/*.json` records sources/construction/scope. PLEASE_WAIT approximates WAIT only, without unverified PLEASE+WAIT concatenation.

The initial THANK_YOU shoulder penetrated torso by up to 4.12 cm. Later checks found excessive start height, collisions after start correction, upward interpolation detours, and excessive head distance. Five development versions remain in `motions/development_failures/`. Final changes used narrower authored shoulder bounds, wrist/elbow torso-distance penalties, and 12 intermediate wrist poses, followed by full checks. These are development fixes, not independent confirmation. Collision scans cover upstream geometry only, without complete safety proof.

`results/previews/THANK_YOU_calibration.json` records source/robot phases, initial/final palm normals, fingertip proxy, and head-distance lower bound. A1 played/inspected video framewise; robot coordinates use FK. Authored-target IK error is not human-3D tracking error. Fingertip proxy remains about 2.6 cm from the head bounding-box lower bound; no mouth contact, smile, or real comprehension validation.

`play_motion.py` actually opened a rotatable native MuJoCo viewer on the original machine with `mjpython`, replayed full HELLO, and exited normally. Add `--loop` for repetition. It is live 3D trajectory playback, not MP4.
