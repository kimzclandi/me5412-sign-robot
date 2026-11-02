"""Kinematic stills of each source-defective protected core at its worst frame (evidence for source review).

Usage: render_worst_frames.py PREFLIGHT_DIR
Writes PREFLIGHT_DIR/worst_frames/<WORD>.png and contact_sheet.png; never overwrites.
"""
import json
import os
from pathlib import Path
import sys

ROOT = Path("/home/kingderman/Documents/ME5412-github-latest")
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MUJOCO_GL", "egl")

import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from sign_robot.motion import apply_frame, load_model
from sign_robot.pair_contract import read_json, read_motion


def main(preflight_dir):
    directory = ROOT / preflight_dir
    result = read_json(directory / "preflight.json")
    output = directory / "worst_frames"
    output.mkdir()
    model = load_model(ROOT)
    data = mujoco.MjData(model)
    cameras = []
    for azimuth in (180, 90):
        camera = mujoco.MjvCamera()
        camera.lookat[:] = [.06, 0, 1.02]
        camera.distance, camera.azimuth, camera.elevation = 1.6, azimuth, -4
        cameras.append(camera)
    font = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 13)
    tiles, index = [], []
    with mujoco.Renderer(model, width=240, height=288) as renderer:
        for gloss, row in sorted(result["words"].items()):
            defects = row["core"]["defects"]
            if not defects:
                continue
            clip = read_motion(ROOT / row["motion"])
            geometry = next((d for d in defects if d["metric"] == "sampled_core_clearance_mm"), None)
            defect = geometry or defects[0]
            frame = int(round(defect["source_frame"]))
            apply_frame(model, data, clip["joint_names"], clip["positions"][frame])
            views = []
            for camera in cameras:
                renderer.update_scene(data, camera=camera)
                views.append(Image.fromarray(renderer.render()))
            tile = Image.new("RGB", (480, 340), (14, 21, 32))
            tile.paste(views[0], (0, 52))
            tile.paste(views[1], (240, 52))
            draw = ImageDraw.Draw(tile)
            worst = row["core"]["geometry"]["worst_contact"] or {}
            kinds = "+".join(sorted({d["metric"].replace("sampled_core_clearance_mm", "clearance").replace("speed_ratio", "speed") for d in defects}))
            draw.text((6, 3), f"{gloss}  f{frame}  core {row['core']['protected_core_frames']}  [{kinds}]", font=font, fill="white")
            if geometry:
                draw.text((6, 26), f"{geometry['value']:.2f} mm  {' / '.join(worst.get('bodies', []))}", font=font, fill=(255, 140, 125))
            else:
                draw.text((6, 26), f"speed ratio {defect['value']:.3f}  {defect.get('joint')}", font=font, fill=(255, 199, 65))
            tile.save(output / f"{gloss}.png")
            tiles.append(tile)
            index.append({"gloss": gloss, "frame": frame, "metric": defect["metric"], "value": defect["value"],
                          "bodies": worst.get("bodies") if geometry else None, "joint": defect.get("joint")})
    columns = 4
    rows = (len(tiles) + columns - 1) // columns
    sheet = Image.new("RGB", (480 * columns, 340 * rows), (0, 0, 0))
    for i, tile in enumerate(tiles):
        sheet.paste(tile, ((i % columns) * 480, (i // columns) * 340))
    sheet.save(output / "contact_sheet.png")
    (output / "index.json").write_text(json.dumps({"kinematic_stills_only": True, "frames": index}, indent=1) + "\n")
    print(json.dumps({"words": len(tiles), "output": str(output.relative_to(ROOT))}))


if __name__ == "__main__":
    main(sys.argv[1])
