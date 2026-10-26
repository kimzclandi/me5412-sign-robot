"""Run MediaPipe pose + hand landmarkers over downloaded WLASL videos.

    .venv/bin/python scripts/video/extract_video_landmarks.py [GLOSS ...]

For each video in data/video/wlasl/manifest.json writes
data/video/wlasl/raw/landmarks/<GLOSS>/<video_id>.npz (local, gitignored) with
times_s [T], pose [T,33,3] world metres, pose_vis [T,33], hands [T,2,21,3]
world metres (0 = signer's left, NaN if undetected) and the per-side detection rate.
Detected hands are assigned to a side by the nearest pose wrist in the image,
not by MediaPipe's handedness label (which assumes a mirrored selfie view).
Models: models/mediapipe/{pose_landmarker_heavy,hand_landmarker}.task (Google, Apache-2.0).
"""
from pathlib import Path
import argparse
import json
import sys

import numpy as np
import imageio.v2 as imageio
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data/video/wlasl/manifest.json"
RAW = ROOT / "data/video/wlasl/raw"
MODELS = ROOT / "models/mediapipe"


def landmarkers():
    mode = vision.RunningMode.VIDEO
    pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(MODELS / "pose_landmarker_heavy.task")), running_mode=mode, num_poses=1))
    hands = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(MODELS / "hand_landmarker.task")), running_mode=mode, num_hands=2,
        min_hand_detection_confidence=0.3, min_hand_presence_confidence=0.3, min_tracking_confidence=0.3))
    return pose, hands


def extract(path, frame_start=1, frame_end=-1):
    reader = imageio.get_reader(path, "ffmpeg")
    fps = float(reader.get_meta_data().get("fps") or 30.0)
    pose_lm, hand_lm = landmarkers()
    times, poses, vis, hands = [], [], [], []
    with pose_lm, hand_lm:
        for i, frame in enumerate(reader):
            if i + 1 < frame_start or (frame_end > 0 and i + 1 > frame_end):
                continue
            h, w = frame.shape[:2]
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(frame[:, :, :3]))
            stamp = int(round(i * 1000 / fps))
            p = pose_lm.detect_for_video(image, stamp)
            k = hand_lm.detect_for_video(image, stamp)
            pose = np.full((33, 3), np.nan)
            v = np.zeros(33)
            two = np.full((2, 21, 3), np.nan)
            if p.pose_world_landmarks:
                pose = np.array([[l.x, l.y, l.z] for l in p.pose_world_landmarks[0]])
                v = np.array([l.visibility for l in p.pose_world_landmarks[0]])
                img = np.array([[l.x * w, l.y * h] for l in p.pose_landmarks[0]])
                wrists = img[[15, 16]]  # signer's left, right
                cands = []
                for world, image_lm in zip(k.hand_world_landmarks, k.hand_landmarks):
                    xy = np.array([image_lm[0].x * w, image_lm[0].y * h])
                    d = np.linalg.norm(wrists - xy, axis=1)
                    cands.append((d, np.array([[l.x, l.y, l.z] for l in world])))
                taken = set()
                for d, world in sorted(cands, key=lambda c: c[0].min()):
                    for side in np.argsort(d):
                        if side not in taken and d[side] < 0.25 * max(w, h):
                            two[side] = world
                            taken.add(side)
                            break
            times.append(stamp / 1000.0)
            poses.append(pose)
            vis.append(v)
            hands.append(two)
    hands = np.array(hands)
    return {"times_s": np.array(times) - times[0], "pose": np.array(poses), "pose_vis": np.array(vis), "hands": hands,
            "hand_detection_rate": np.isfinite(hands[:, :, 0, 0]).mean(axis=0), "fps": fps}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("glosses", nargs="*")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())["videos"]
    for gloss in [g.upper() for g in args.glosses] or list(manifest):
        for video in manifest[gloss]:
            out = RAW / "landmarks" / gloss / f"{video['video_id']}.npz"
            if out.exists():
                continue
            src = RAW / gloss / f"{video['video_id']}.mp4"
            try:
                result = extract(src, video["frame_start"], video["frame_end"])
            except Exception as exc:  # unreadable or empty video: skip, keep going
                print(f"{gloss} {video['video_id']}: FAILED {type(exc).__name__}: {exc}", file=sys.stderr)
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(out, **result)
            pose_rate = np.isfinite(result["pose"][:, 0, 0]).mean()
            print(f"{gloss:12s} {video['video_id']:>6s} {video['source']:32s} frames {len(result['times_s']):4d} "
                  f"pose {pose_rate:.2f} hands L {result['hand_detection_rate'][0]:.2f} R {result['hand_detection_rate'][1]:.2f}")


if __name__ == "__main__":
    main()
