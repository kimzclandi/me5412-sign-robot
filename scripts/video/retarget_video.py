"""Retarget MediaPipe landmarks from WLASL dictionary videos to G1 clips.

    MUJOCO_GL=egl PYTHONPATH=scripts/mocap .venv/bin/python scripts/video/retarget_video.py GLOSS ... [--render]

Every downloaded video of a gloss becomes a candidate clip in
motions/wlasl_video_v1/candidates/<GLOSS>__<video_id>.npz (+ .json), using the
same retargeting, clearance and neutral transitions as the mocap clips. The
candidate with the lowest sign-phase IK error among those whose signing hand is
detected in at least half the frames is copied to motions/wlasl_video_v1/<GLOSS>.npz/.json.
Words listed in manual_corrections.CORRECTIONS (NURSE) use their corrected video instead.
Video-derived depth and finger detail are less reliable than mocap.
"""
from pathlib import Path
import argparse
import json
import shutil
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts/mocap"))
from sign_robot.video_skeleton import VideoSkeleton
from retarget_to_g1 import LIMITATIONS, active_range, write_clip
from manual_corrections import CORRECTIONS

MANIFEST = ROOT / "data/video/wlasl/manifest.json"
LANDMARKS = ROOT / "data/video/wlasl/raw/landmarks"
OUT = ROOT / "motions/wlasl_video_v1"
PREVIEWS = ROOT / "results/video_previews"
FINGER_SPEED_LIMIT = 10.0  # rad/s; video thumb/finger estimates jitter far faster than real signing
ARM_SPEED_LIMIT = 15.0  # rad/s; stops wrist-roll flips from noisy hand orientation
MIN_COVERAGE = 0.5  # fraction of clip frames with the signing hand detected
MEDIAN_FRAMES = 5  # at 30 fps: removes orientation glitches shorter than ~0.1 s
# On from clips v2 (2026-11-02): 29 of 32 words dropped from up to 92 mm penetration to 3 mm.
# Group 3's round-8 plans were bound by hash to the unrepaired clips (bcdefc4) and must rebind.
COLLISION_REPAIR = True
METHOD = ("Monocular video retargeting: MediaPipe PoseLandmarker/HandLandmarker world landmarks (Savitzky-Golay "
          "smoothed, gaps interpolated) -> same G1 retargeting as the mocap clips (scaled shoulder-relative wrist "
          "targets, bounded 7-DoF IK per arm with clearance, finger flexion from joint positions)")
VIDEO_LIMITATIONS = ["Depth (towards/away from the camera) is estimated from a single view and is the least reliable axis",
                     "Hands undetected in some frames are interpolated; finger flexion is noisier than mocap",
                     "Source videos are third-party dictionary clips indexed by WLASL (C-UDA); they are not redistributed"]

def skeleton(gloss, video_id):
    """Full-length skeleton, with the manual correction applied when one exists for this video."""
    data = np.load(LANDMARKS / gloss / f"{video_id}.npz")
    pose, hands, vis = data["pose"], data["hands"], data["pose_vis"]
    fix = CORRECTIONS.get(gloss)
    if fix and fix[0] == video_id:
        pose, hands, vis = fix[1](pose, hands, vis)
    return data, VideoSkeleton(data["times_s"], pose, hands, vis), fix if fix and fix[0] == video_id else None


def run(gloss, video, render):
    data, full, fix = skeleton(gloss, video["video_id"])
    i0, i1, _ = active_range(full)
    sk = full.crop(i0, i1)
    if fix:
        sk.contact = fix[2]
    detected = np.isfinite(data["hands"][i0:i1, :, 0, 0])
    source = {"dataset": "WLASL v0.3 index (C-UDA) -> third-party ASL dictionary video", "gloss": gloss,
              "video_id": video["video_id"], "url": video["url"], "host": video["source"],
              "video_sha256": video["sha256"], "source_fps": float(data["fps"]),
              "source_frames_used": [int(i0), int(i1)],
              "hand_detection_rate_in_clip": {"left": float(detected[:, 0].mean()), "right": float(detected[:, 1].mean())}}
    if fix:
        source["manual_correction"] = {"note": fix[3], "contact": fix[2]}
    name = f"{gloss}__{video['video_id']}"
    meta = write_clip(name, sk, source, OUT / "candidates", METHOD, LIMITATIONS + VIDEO_LIMITATIONS,
                      render=render, preview_dir=PREVIEWS, finger_speed_limit=FINGER_SPEED_LIMIT,
                      arm_speed_limit=ARM_SPEED_LIMIT, median_frames=MEDIAN_FRAMES, collision_repair=COLLISION_REPAIR)
    # Coverage of the dominant (more raised) hand drives the choice of video.
    sign = meta["ik_error_sign_phase"]
    active = [s for s in ("left", "right") if sign[s]["frames"]]
    coverage = max((source["hand_detection_rate_in_clip"][s] for s in active), default=0.0)
    error = max((sign[s]["wrist_position_m"]["max"] for s in active), default=1.0)
    return name, coverage, error

def render_chosen(gloss, manifest):
    """Re-render the comparison video of the chosen clip without re-running IK."""
    from sign_robot.motion import load_model
    from render_comparison import render as render_video
    meta = json.loads((OUT / f"{gloss}.json").read_text())
    video = next(v for v in manifest[gloss] if v["video_id"] == meta["source"]["video_id"])
    i0, i1 = meta["source"]["source_frames_used"]
    sk = skeleton(gloss, video["video_id"])[1].crop(i0, i1)
    with np.load(OUT / f"{gloss}.npz") as clip:
        motion = {k: clip[k] for k in ("timestamps_s", "joint_names", "positions")}
    render_video(f"{gloss}__{video['video_id']}", load_model(), motion, sk, meta["core_frames"], out=PREVIEWS)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("glosses", nargs="+")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--render-only", action="store_true", help="only re-render the chosen clips' comparison videos")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())["videos"]
    if args.render_only:
        for gloss in [g.upper() for g in args.glosses]:
            render_chosen(gloss, manifest)
        return
    for gloss in [g.upper() for g in args.glosses]:
        results = []
        for video in manifest[gloss]:
            if not (LANDMARKS / gloss / f"{video['video_id']}.npz").exists():
                continue
            try:
                results.append(run(gloss, video, False))
            except RuntimeError as exc:
                print(f"{gloss} {video['video_id']}: skipped ({exc})")
        if not results:
            print(f"{gloss}: no usable video")
            continue
        # Lowest sign-phase error among videos whose signing hand is seen often enough;
        # coverage alone once picked a MEDICINE video with 22 cm error over one with 3 cm.
        covered = [r for r in results if r[1] >= MIN_COVERAGE] or [max(results, key=lambda r: r[1])]
        if gloss in CORRECTIONS:  # the corrected video, whose contact makes its raw IK error incomparable
            covered = [r for r in results if r[0] == f"{gloss}__{CORRECTIONS[gloss][0]}"]
        best = min(covered, key=lambda r: r[2])
        if args.render:  # render only the chosen candidate
            run(gloss, next(v for v in manifest[gloss] if f"{gloss}__{v['video_id']}" == best[0]), True)
        for ext in (".npz", ".json"):
            shutil.copy(OUT / "candidates" / f"{best[0]}{ext}", OUT / f"{gloss}{ext}")
        meta = json.loads((OUT / f"{gloss}.json").read_text())
        meta["action_id"] = gloss
        meta["selected_from"] = [{"candidate": n, "dominant_hand_coverage": round(c, 3), "sign_wrist_err_max_m": round(e, 4)} for n, c, e in results]
        (OUT / f"{gloss}.json").write_text(json.dumps(meta, indent=2) + "\n")
        print(f"{gloss:12s} chose {best[0]} (coverage {best[1]:.2f}, wrist err {best[2] * 1000:.1f} mm) from {len(results)}")

if __name__ == "__main__":
    main()
