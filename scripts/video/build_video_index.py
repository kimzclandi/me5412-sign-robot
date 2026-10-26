"""Write motions/wlasl_video_v1/index.json for the video-derived clips.

    .venv/bin/python scripts/video/build_video_index.py

Same entry fields as motions/studio_galt_v1/index.json (gloss, motion,
core_frames, sign_frames, robot_status, robot_note). Video-derived clips are
graded "approximate" at best because depth and fingers come from one camera;
POOR lists clips the Group 2 review found noticeably wrong.
"""
from pathlib import Path
import json
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts/mocap"))
from sign_robot.video_skeleton import VideoSkeleton
from retarget_to_g1 import FPS

CLIPS = ROOT / "motions/wlasl_video_v1"
LANDMARKS = ROOT / "data/video/wlasl/raw/landmarks"
RAISED_M = 0.10
DEFAULT_NOTE = "video-derived (single camera): depth and finger shapes less reliable than mocap"
# Group 2 review of results/video_previews/<GLOSS>__<id>_sheet.png and .mp4.
NOTES = {}
POOR = {}


def sign_frames(meta):
    """Output-frame span where either hand is raised, from the stored landmarks."""
    src = meta["source"]
    data = np.load(LANDMARKS / src["gloss"] / f"{src['video_id']}.npz")
    i0, i1 = src["source_frames_used"]
    sk = VideoSkeleton(data["times_s"], data["pose"], data["hands"], data["pose_vis"]).crop(i0, i1)
    up = sk.chest_frame()[:, :, 2]
    raised = np.zeros(len(sk.times), bool)
    for s in ("l", "r"):
        h = np.einsum("ti,ti->t", up, sk.h(f"hand_{s}") - sk.h(f"upperarm_{s}"))
        raised |= h > h.min() + RAISED_M
    idx = np.flatnonzero(raised) if raised.any() else np.arange(len(sk.times))
    c0, c1 = meta["core_frames"]
    to_out = lambda i: int(min(c1, c0 + round(sk.times[i] * FPS)))
    return [to_out(idx[0]), to_out(idx[-1])]


def main():
    entries = []
    for path in sorted(CLIPS.glob("*.json")):
        if path.name == "index.json":
            continue
        meta = json.loads(path.read_text())
        gloss = meta["action_id"]
        status = "poor" if gloss in POOR else "approximate"
        entries.append({
            "gloss": gloss, "motion": str(path.with_suffix(".npz").relative_to(ROOT)),
            "duration_s": round(meta["duration_s"], 3), "core_frames": meta["core_frames"],
            "sign_frames": sign_frames(meta), "robot_status": status,
            "robot_note": POOR.get(gloss) or NOTES.get(gloss, DEFAULT_NOTE),
            "video_id": meta["source"]["video_id"], "video_url": meta["source"]["url"], "asl_reviewed": False,
        })
    index = {"schema_version": 1, "fps": FPS, "neutral_start_end": True,
             "source": "WLASL v0.3 index (C-UDA) -> third-party ASL dictionary videos -> MediaPipe -> G1 retargeting",
             "status_scale": {"usable": "not used for video-derived clips",
                              "approximate": "recognisable motion from a single-camera estimate",
                              "poor": "noticeably wrong; fix or replace before a demo"},
             "words": entries}
    (CLIPS / "index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
    print(f"{len(entries)} video clips: {sum(e['robot_status'] == 'approximate' for e in entries)} approximate, "
          f"{sum(e['robot_status'] == 'poor' for e in entries)} poor")


if __name__ == "__main__":
    main()
