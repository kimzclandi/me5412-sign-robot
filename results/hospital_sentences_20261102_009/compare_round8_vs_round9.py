"""YOU HURT WHERE, round 8 vs round 9: frame strips around the entry into HURT, and arm speed over time.

Windows render-venv (MuJoCo GPU). Reads each round's render_inputs/YOU__HURT__WHERE (replay.npz, render_plan.json).
Usage: python hurt_compare.py OUT_DIR ROUND_DIR [ROUND_DIR ...]   (ROUND_DIR relative to the repository)
"""
import json
import re
import sys
from pathlib import Path

import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO = Path(r"\\wsl.localhost\Ubuntu\home\kingderman\Documents\ME5412-github-latest")
MODEL = Path(r"C:\Users\23971\Documents\5412\_runtime\render-assets\robot")
CASE = "YOU__HURT__WHERE"
FONT = "C:/Windows/Fonts/msyh.ttc"
COLOURS = {'protected': (78, 215, 143), 'retained': (100, 175, 255), 'cut': (255, 110, 100),
           'transition': (255, 199, 65), 'hold': (180, 180, 180)}
BG = (14, 21, 32)
STEP = 2
LAST_HURT_FRAME = 45
TILE = (200, 188)


def load_round(directory):
    base = REPO / directory / "render_inputs" / CASE
    with np.load(base / "replay.npz", allow_pickle=False) as data:
        motion = {k: data[k] for k in data.files}
    return motion, json.loads((base / "render_plan.json").read_text(encoding="utf-8"))


def short(text):
    text = text.replace(" protected / 用户保护 ", " 保护 ").replace(" retained / 保留 ", " 保留 ")
    text = re.sub(r"ADDED transition \d+ / 新增过渡", "新增过渡", text)
    return text.replace("ADDED return to rest / 新增回到初始姿态", "回到初始姿态")


def entry_window(plan):
    """From YOU's last protected frame to HURT source frame LAST_HURT_FRAME."""
    phases = plan["phases"]["planned"]
    start = max(i for i, (kind, text) in enumerate(phases) if kind == "protected" and text.startswith("#0 YOU"))
    hurt = [(i, int(re.search(r"f(\d+)$", text).group(1))) for i, (_, text) in enumerate(phases)
            if text.startswith("#1 HURT")]
    stop = next(i for i, frame in hurt if frame >= LAST_HURT_FRAME)
    indices = list(range(start, stop + 1, STEP))
    return indices if indices[-1] == stop else indices + [stop]


def strips(rounds, out):
    model = mujoco.MjModel.from_xml_path(str(MODEL / "scene.xml"))
    data = mujoco.MjData(model)
    font, title_font = ImageFont.truetype(FONT, 13), ImageFont.truetype(FONT, 17)
    cameras = []
    for azimuth, lookat, distance in ((180, [0.0, 0, 1.1], 0.85), (90, [0.16, 0, 1.1], 0.95)):
        camera = mujoco.MjvCamera()
        camera.lookat[:] = lookat
        camera.distance, camera.azimuth, camera.elevation = distance, azimuth, -4
        cameras.append(camera)
    rows = []
    with mujoco.Renderer(model, width=400, height=376) as renderer:
        for name, (motion, plan) in rounds:
            addresses = np.array([model.joint(str(n)).qposadr[0] for n in motion["joint_names"]])
            indices = entry_window(plan)
            for view, camera in zip(("正面 front", "侧面 side"), cameras):
                tiles = []
                for index in indices:
                    data.qpos[addresses] = motion["positions"][index]
                    data.qvel[:] = 0
                    mujoco.mj_forward(model, data)
                    renderer.update_scene(data, camera=camera)
                    image = Image.fromarray(renderer.render()).resize(TILE)
                    kind, text = plan["phases"]["planned"][index]
                    canvas = Image.new("RGB", (TILE[0], TILE[1] + 40), BG)
                    canvas.paste(image, (0, 40))
                    draw = ImageDraw.Draw(canvas)
                    draw.text((5, 2), f"{index / 30:.2f}s", font=font, fill="white")
                    draw.text((5, 20), short(text), font=font, fill=COLOURS[kind])
                    draw.rectangle((0, TILE[1] + 34, TILE[0], TILE[1] + 40), fill=COLOURS[kind])
                    tiles.append(canvas)
                rows.append((f"{name} · {view}", tiles))
    width = max(len(t) for _, t in rows) * TILE[0]
    sheet = Image.new("RGB", (width, len(rows) * (TILE[1] + 40 + 30)), BG)
    draw = ImageDraw.Draw(sheet)
    for r, (label, tiles) in enumerate(rows):
        y = r * (TILE[1] + 70)
        draw.text((6, y + 5), label, font=title_font, fill="white")
        for c, tile in enumerate(tiles):
            sheet.paste(tile, (c * TILE[0], y + 30))
    sheet.save(out / "hurt_entry_round8_vs_round9.png")


def arm_speed(motion):
    names = [str(n) for n in motion["joint_names"]]
    arm = [i for i, n in enumerate(names) if any(k in n for k in ("shoulder", "elbow", "wrist"))]
    v = np.gradient(motion["positions"], 1 / 30, axis=0, edge_order=2)
    return np.linalg.norm(v[:, arm], axis=1)


def speed_chart(rounds, out):
    font, title_font = ImageFont.truetype(FONT, 14), ImageFont.truetype(FONT, 17)
    panel_w, panel_h, left, top = 1100, 210, 60, 34
    longest = max(len(m["positions"]) for _, (m, _) in rounds) / 30
    y_max = 30.0
    image = Image.new("RGB", (left + panel_w + 30, len(rounds) * (panel_h + top + 40) + 30), "white")
    draw = ImageDraw.Draw(image)
    band = {"protected": (214, 242, 226), "retained": (214, 230, 250), "transition": (255, 236, 186),
            "cut": (255, 220, 216), "hold": (236, 236, 236)}
    for r, (name, (motion, plan)) in enumerate(rounds):
        y0 = 10 + r * (panel_h + top + 40) + top
        speed = arm_speed(motion)
        n = len(speed)
        x = lambda t: left + t / longest * panel_w
        y = lambda s: y0 + panel_h - min(s, y_max) / y_max * panel_h
        phases = plan["phases"]["planned"][:n]
        start = 0
        for i in range(1, n + 1):
            if i == n or phases[i][0] != phases[start][0]:
                draw.rectangle((x(start / 30), y0, x(i / 30), y0 + panel_h), fill=band[phases[start][0]])
                start = i
        for s in range(0, int(y_max) + 1, 10):
            draw.line((left, y(s), left + panel_w, y(s)), fill=(200, 200, 200), width=1)
            draw.text((left - 26, y(s) - 9), f"{s}", font=font, fill=(90, 90, 90))
        for t in range(0, int(longest) + 1):
            draw.text((x(t) - 4, y0 + panel_h + 4), f"{t}s", font=font, fill=(90, 90, 90))
        points = [(x(i / 30), y(s)) for i, s in enumerate(speed)]
        draw.line(points, fill=(40, 40, 40), width=2)
        draw.text((left, y0 - top + 6), f"{name}: {n} 帧 ({n / 30:.1f} s) · 手臂速度 arm speed (rad/s)",
                  font=title_font, fill=(20, 20, 20))
    legend = "底色：绿 = 用户保护，黄 = 新增衔接，蓝 = 保留的源动作 · green protected, yellow added connector, blue retained source"
    draw.text((left, image.height - 24), legend, font=font, fill=(60, 60, 60))
    image.save(out / "arm_speed_round8_vs_round9.png")


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    labels = {"hospital_sentences_20261102_008": "第八轮 round 8（HURT 保护 f27–57）",
              "hospital_sentences_20261102_009": "第九轮 round 9（HURT 保护 f37–57）"}
    rounds = [(labels.get(Path(d).name, d), load_round(d)) for d in sys.argv[2:]]
    strips(rounds, out)
    speed_chart(rounds, out)
    for name, (motion, plan) in rounds:
        indices = entry_window(plan)
        print(json.dumps({"round": name, "frames": len(motion["positions"]),
                          "entry_window": [indices[0], indices[-1]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
