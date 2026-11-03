"""Old vs clips-v2 poses at the frames where a protected word changed (Windows render-venv, MuJoCo GPU).

Usage: python render_boundary_compare.py SCRATCH OUT
SCRATCH holds old_clips/<GLOSS>.npz, boundary_check.json and boundary_detail.json; new clips come from the worktree.
Writes words_in_sentences_old_vs_new.png and other_words_old_vs_new.png.
"""
import json
import sys
from pathlib import Path

import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

WT = Path(r"\\wsl.localhost\Ubuntu\home\kingderman\Documents\ME5412-group3-clips-v2")
MODEL = Path(r"C:\Users\23971\Documents\5412\_runtime\render-assets\robot")
FONT = "C:/Windows/Fonts/msyh.ttc"
BG, WHITE, GRAY, ORANGE = (14, 21, 32), (235, 235, 235), (150, 160, 175), (255, 160, 60)
VIEW = 360
WHERE = {"start": "保护起始帧", "end": "保护结束帧", "core max": "保护区间内变化最大的帧"}


def load(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}


def main():
    scratch, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    checks = {r["gloss"]: r for r in json.loads((scratch / "boundary_check.json").read_text(encoding="utf-8"))}
    detail = json.loads((scratch / "boundary_detail.json").read_text(encoding="utf-8"))
    model = mujoco.MjModel.from_xml_path(str(MODEL / "scene.xml"))
    data = mujoco.MjData(model)
    cameras = []
    for azimuth, lookat, distance in ((180, [0.0, 0, 1.0], 1.3), (90, [0.12, 0, 1.0], 1.15)):
        camera = mujoco.MjvCamera()
        camera.lookat[:] = lookat
        camera.distance, camera.azimuth, camera.elevation = distance, azimuth, -4
        cameras.append(camera)
    f14, f18 = ImageFont.truetype(FONT, 14), ImageFont.truetype(FONT, 18)
    renderer = mujoco.Renderer(model, width=VIEW, height=VIEW)

    def views(clip, frame):
        addresses = np.array([model.joint(str(n)).qposadr[0] for n in clip["joint_names"]])
        data.qpos[addresses] = clip["positions"][frame]
        data.qvel[:] = 0
        mujoco.mj_forward(model, data)
        images = []
        for camera in cameras:
            renderer.update_scene(data, camera=camera)
            images.append(Image.fromarray(renderer.render()))
        return images

    for name, keep in (("words_in_sentences_old_vs_new.png", True), ("other_words_old_vs_new.png", False)):
        rows = [d for d in detail if d["in_sentences"] == keep]
        sheet = Image.new("RGB", (4 * VIEW, 44 + len(rows) * (VIEW + 58)), BG)
        draw = ImageDraw.Draw(sheet)
        title = "句子用到的词" if keep else "其他词"
        draw.text((10, 10), f"{title}：旧版（第八/九轮所用）vs 新版（clips-v2）· 每行依次为 旧-正面、新-正面、旧-侧面、新-侧面",
                  font=f18, fill=WHITE)
        for r, d in enumerate(rows):
            y = 44 + r * (VIEW + 58)
            check = checks[d["gloss"]]
            old = load(scratch / "old_clips" / f"{d['gloss']}.npz")
            new = load(WT / "motions/wlasl_video_v1" / f"{d['gloss']}.npz")
            side = next((s for s in ("start", "end") if check[s]["frame"] == d["frame"]), None)
            clearance = (f"；自身间隙 旧 {check[side]['clearance_old_mm']:+.1f} mm → 新 {check[side]['clearance_new_mm']:+.1f} mm"
                         if side else "")
            draw.text((10, y + 6), f"{d['gloss']} f{d['frame']}（{WHERE[d['where']]}，保护 f{d['core'][0]}–{d['core'][1]}）",
                      font=f18, fill=ORANGE if d["where"] != "core max" else WHITE)
            draw.text((10, y + 32), f"手指最多移动 {d['max_finger_disp_mm']:.0f} mm，手/手臂最多 {d['max_non_finger_disp_mm']:.0f} mm"
                      + clearance, font=f14, fill=GRAY)
            old_views, new_views = views(old, d["frame"]), views(new, d["frame"])
            for c, (image, label) in enumerate(((old_views[0], "旧 old"), (new_views[0], "新 new"),
                                                 (old_views[1], "旧 old"), (new_views[1], "新 new"))):
                sheet.paste(image, (c * VIEW, y + 58))
                ImageDraw.Draw(sheet).text((c * VIEW + 8, y + 62), label, font=f14, fill=WHITE)
        sheet.save(out / name)
        print(name, len(rows), "rows")


if __name__ == "__main__":
    main()
