"""Overview image of the video-derived clips: MediaPipe skeleton | G1 robot.

    MUJOCO_GL=egl PYTHONPATH=scripts/mocap .venv/bin/python scripts/video/render_video_overview.py

Uses the frame where either hand is highest. Writes results/video_previews/overview.png.
"""
from pathlib import Path
import json
import sys

import numpy as np
import mujoco
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts/mocap"))
from sign_robot.motion import apply_frame, load_model
from sign_robot.video_skeleton import VideoSkeleton
import render_comparison as rc

LANDMARKS = ROOT / "data/video/wlasl/raw/landmarks"
TW, TH, COLS = 240, 270, 6


def main():
    model = load_model()
    data = mujoco.MjData(model)
    index = json.loads((ROOT / "motions/wlasl_video_v1/index.json").read_text())["words"]
    rows = -(-len(index) // COLS)
    grid = Image.new("RGB", (COLS * 2 * TW, rows * TH), (30, 30, 30))
    with mujoco.Renderer(model, width=rc.W, height=rc.H) as renderer:
        for k, entry in enumerate(index):
            meta = json.loads((ROOT / entry["motion"]).with_suffix(".json").read_text())
            src = meta["source"]
            raw = np.load(LANDMARKS / src["gloss"] / f"{src['video_id']}.npz")
            sk = VideoSkeleton(raw["times_s"], raw["pose"], raw["hands"], raw["pose_vis"]).crop(*src["source_frames_used"])
            c0, c1 = entry["core_frames"]
            with np.load(ROOT / entry["motion"]) as clip:
                names, q = clip["joint_names"], clip["positions"]
            up = sk.chest_frame()[:, :, 2]
            height = np.maximum(*(np.einsum("ti,ti->t", up, sk.h(f"hand_{s}") - sk.h(f"upperarm_{s}")) for s in "lr"))
            t = int(np.argmax(height))
            apply_frame(model, data, names, q[min(c0 + int(round(sk.times[t] * 30)), c1)])
            renderer.update_scene(data, camera=rc.camera(180))
            robot = Image.fromarray(renderer.render()).resize((TW, TH))
            ImageDraw.Draw(robot).text((6, 6), f"{entry['gloss']} ({entry['robot_status']})", fill=(255, 255, 0))
            x, y = (k % COLS) * 2 * TW, (k // COLS) * TH
            grid.paste(rc.skeleton_panel(sk, t, "front", entry["gloss"]).resize((TW, TH)), (x, y))
            grid.paste(robot, (x + TW, y))
    grid.save(ROOT / "results/video_previews/overview.png")
    print(f"wrote overview.png {grid.size}")


if __name__ == "__main__":
    main()
