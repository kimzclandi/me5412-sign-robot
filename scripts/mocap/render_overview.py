"""One image with every word: human skeleton | G1 robot at the most expressive frame.

    MUJOCO_GL=egl PYTHONPATH=scripts/mocap .venv/bin/python scripts/mocap/render_overview.py

"Most expressive" = the source frame where either hand is highest. Writes
results/mocap_previews/overview.png.
"""
from pathlib import Path
import json
import sys

import numpy as np
import mujoco
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sign_robot.motion import apply_frame, load_model
from sign_robot.retarget import Skeleton
from retarget_to_g1 import SKELETON_DIR, active_range
import render_comparison as rc

TW, TH, COLS = 240, 270, 6


def main():
    model = load_model()
    data = mujoco.MjData(model)
    index = json.loads((ROOT / "motions/studio_galt_v1/index.json").read_text())["words"]
    rows = -(-len(index) // COLS)
    grid = Image.new("RGB", (COLS * 2 * TW, rows * TH), (30, 30, 30))
    with mujoco.Renderer(model, width=rc.W, height=rc.H) as renderer:
        for k, entry in enumerate(index):
            word = entry["gloss"]
            raw = np.load(SKELETON_DIR / f"{word}.npz")
            i0, i1, _ = active_range(Skeleton(raw, raw["rot"][0]))
            sk = Skeleton({key: raw[key][i0:i1] for key in ("head", "tail", "rot")}
                          | {"bone_names": raw["bone_names"], "frame_times_s": raw["frame_times_s"][i0:i1] - raw["frame_times_s"][i0]},
                          raw["rot"][0])
            c0, c1 = entry["core_frames"]
            with np.load(ROOT / entry["motion"]) as clip:
                names, q = clip["joint_names"], clip["positions"]
            t = int(np.argmax(np.maximum(sk.h("hand_l")[:, 2], sk.h("hand_r")[:, 2])))
            apply_frame(model, data, names, q[min(c0 + int(round(sk.times[t] * 30)), c1)])
            renderer.update_scene(data, camera=rc.camera(180))
            robot = Image.fromarray(renderer.render()).resize((TW, TH))
            ImageDraw.Draw(robot).text((6, 6), f"{entry['id']} {word} ({entry['robot_status']})", fill=(255, 255, 0))
            x, y = (k % COLS) * 2 * TW, (k // COLS) * TH
            grid.paste(rc.skeleton_panel(sk, t, "front", word).resize((TW, TH)), (x, y))
            grid.paste(robot, (x + TW, y))
    grid.save(ROOT / "results/mocap_previews/overview.png")
    print(f"wrote overview.png {grid.size}")


if __name__ == "__main__":
    main()
