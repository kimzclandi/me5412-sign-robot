# Motion from public sign-language videos (Group 2)

[中文](video-retargeting.md) · **English** · [Mocap method](mocap-retargeting.en.md) · [Handoff](group2-handoff.en.md)

26 of the 35 hospital-vocabulary words are not in the Studio Galt mocap archive. The planned source, SignAvatars, needs a personal access request that would not arrive in time, so motion is extracted from public ASL dictionary videos instead (2026-10-27).

## Pipeline: inputs and outputs per step

| Step | Script | Input | Output |
|---|---|---|---|
| 1. Download videos | `scripts/video/fetch_wlasl_videos.py` | WLASL v0.3 index (C-UDA, academic use) | `data/video/wlasl/raw/<WORD>/<video_id>.mp4` (**local only, not committed**); `data/video/wlasl/manifest.json` records URL, source and hash |
| 2. Landmarks | `scripts/video/extract_video_landmarks.py` | videos | per-frame 3D coordinates (metres) of 33 body points and 21 points per hand, stored locally in `raw/landmarks/` |
| 3. Robot motion | `scripts/video/retarget_video.py <WORD> --render` | landmarks | one candidate per video in `motions/wlasl_video_v1/candidates/`; the best is copied to `motions/wlasl_video_v1/<WORD>.npz/.json`; comparison videos in `results/video_previews/` |
| 4. Index | `scripts/video/build_video_index.py` | chosen clips | `motions/wlasl_video_v1/index.json`, same fields as the mocap library |
| 5. Overview | `scripts/video/render_video_overview.py` | index | `results/video_previews/overview.png` |

Then run `scripts/mocap/build_hospital_motions.py` to update the hospital map: **for each word the mocap clip is preferred; the video clip is used only when there is no mocap.**

```bash
.venv/bin/python scripts/video/fetch_wlasl_videos.py            # default: 26 missing + 6 comparison words
.venv/bin/python scripts/video/extract_video_landmarks.py
MUJOCO_GL=egl PYTHONPATH=scripts/mocap .venv/bin/python scripts/video/retarget_video.py HURT --render
.venv/bin/python scripts/video/build_video_index.py
.venv/bin/python scripts/mocap/build_hospital_motions.py
```

Requires `pip install mediapipe` and two official models in `models/mediapipe/` (`pose_landmarker_heavy.task`, `hand_landmarker.task`; Google, Apache-2.0; from `storage.googleapis.com/mediapipe-models`).

## Video sources

- Only single-signer, front-facing dictionary videos indexed by WLASL: StartASL, Spread The Sign, ASL Deafined, SignSchool, ASL Bricks. No YouTube; Signing Savvy and Handspeak no longer serve files.
- 2–4 videos per word, 32 words (the 26 missing ones plus YOU, COME, TAKE, HELLO, PLEASE, WHERE for comparison with mocap).
- **Copyright**: videos belong to their sites, are analysed locally only and are not committed; the repository holds only links, hashes and the final robot joint trajectories.

## Method

- **Landmarks**: MediaPipe PoseLandmarker (heavy) gives 3D world coordinates of shoulders, elbows and wrists; HandLandmarker gives 21 points per hand, translated onto the matching wrist. Hands are assigned to sides by the nearest wrist in the image (MediaPipe's own handedness label assumes a mirrored selfie view and is unreliable here).
- **Cleaning**: elbow/wrist frames with visibility below 0.5, or where an upper arm or forearm length deviates more than 40% from its median, are dropped and linearly interpolated, then smoothed with a Savitzky–Golay filter (~0.2 s window). Frames without a detected hand are interpolated too.
- **Fingers**: the videos give real fingertip positions, so finger flexion is the sum of angles along wrist → base → joints → tip.
- **Robot motion**: exactly the same mapping, clearance and neutral start/end as the mocap words. Arm length uses the median over frames (per-frame estimates jitter).
- **Joint filtering and speed limits**: video estimates of thumb rotation and hand orientation flip suddenly (HURT's thumb briefly reached 37.7 rad/s, its left wrist rolled from 1.97 to −1.32 in 4 frames). Joint angles of video words are median-filtered over 5 frames to remove short jumps, then finger joints are rate-limited to 10 rad/s and arm joints to 15 rad/s. The wrist twist that HURT actually contains is kept. Mocap words are unaffected.
- **Choosing a video**: every video of a word is converted; the one with the highest detection rate of the signing hand wins, with lower error as the tie-breaker. All candidates stay in `candidates/`, and the choice is recorded in `selected_from` in the JSON.

## Results

- All 32 words converted; all 35 hospital words now have motion (9 from mocap, 26 from video).
- Video words are graded at most "approximate", never "usable": one camera cannot give reliable depth, and finger detail is coarser than mocap.
- Compared with mocap (YOU, COME, …): direction and position agree, with more jitter; at the start and end the hands rest in front of the waist instead of hanging.
- Error numbers are large (over 10 cm for some words), mostly from the resting hands in front of the waist that the robot hip blocks, plus estimation jitter. Grades rely mainly on the comparison images.
- Spot-checked: THANK-YOU (hand moves forward from the chin), NO, SORRY, YES, WAIT, ME, NIGHT, MEDICINE (circling in the palm in front of the chest), HEADACHE (both hands at forehead height, which on the short-necked robot looks above the head).

## Limitations

- Depth (towards/away from the camera) is a single-camera estimate and the least reliable axis.
- Finger detail and handshapes are coarser than mocap; occluded or out-of-frame hands are interpolated.
- Signers, speed and framing differ between videos, so style is not uniform across words.
- The ASL in the source videos was not verified by this group; robot motions are not reviewed by ASL users.
