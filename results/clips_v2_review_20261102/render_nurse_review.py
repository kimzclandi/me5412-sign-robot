"""NURSE review renders for the user's protection calibration (Windows render-venv, MuJoCo GPU).

Usage: python render_nurse_review.py SCRATCH OUT
SCRATCH holds NURSE_old.npz and nurse_check.json (nurse_check.py); the new clip is read from the group3/clips-v2 worktree.
Writes into OUT: NURSE_clips_v2.mp4 (30 fps), NURSE_clips_v2_slow.mp4 (10 fps), NURSE_old_vs_clips_v2.mp4,
NURSE_clips_v2_frames.png (every 4th frame) and NURSE_clips_v2_timeline.png.
"""
import hashlib
import json
import sys
import time
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

WT = Path(r"\\wsl.localhost\Ubuntu\home\kingderman\Documents\ME5412-group3-clips-v2")
MODEL = Path(r"C:\Users\23971\Documents\5412\_runtime\render-assets\robot")
FONT = "C:/Windows/Fonts/msyh.ttc"
BG, WHITE, GRAY = (14, 21, 32), (235, 235, 235), (150, 160, 175)
ORANGE, GREEN = (255, 160, 60), (78, 215, 143)
VIEW = 480
OLD_CORE = (38, 75)
SOURCE = "group2/clips-v2 (85bc230)"
PARTS = [("R_thumb", "右手拇指"), ("R_index", "右手食指"), ("R_middle", "右手中指"), ("R_ring", "右手无名指"),
         ("R_pinky", "右手小指"), ("L_thumb", "左手拇指"), ("L_index", "左手食指"), ("L_middle", "左手中指"),
         ("L_ring", "左手无名指"), ("L_pinky", "左手小指"), ("left_wrist", "左手腕"), ("right_wrist", "右手腕"),
         ("left_elbow", "左前臂"), ("right_elbow", "右前臂"), ("left_shoulder", "左上臂"),
         ("right_shoulder", "右上臂"), ("left_hip", "左髋"), ("right_hip", "右髋"), ("torso", "躯干")]


def part(body):
    return next((zh for key, zh in PARTS if str(body).startswith(key)), str(body))


def tree_hash(folder):
    digest = hashlib.sha256()
    for path in sorted(p for p in Path(folder).rglob("*") if p.is_file()):
        digest.update(path.relative_to(folder).as_posix().encode() + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def load(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}


class Views:
    def __init__(self, names):
        self.model = mujoco.MjModel.from_xml_path(str(MODEL / "scene.xml"))
        self.data = mujoco.MjData(self.model)
        self.addresses = np.array([self.model.joint(str(n)).qposadr[0] for n in names])
        self.cameras = []
        for azimuth, lookat, distance in ((180, [0.0, 0, 1.0], 1.3), (90, [0.12, 0, 1.0], 1.15)):
            camera = mujoco.MjvCamera()
            camera.lookat[:] = lookat
            camera.distance, camera.azimuth, camera.elevation = distance, azimuth, -4
            self.cameras.append(camera)
        self.renderer = mujoco.Renderer(self.model, width=VIEW, height=VIEW)

    def __call__(self, q):
        self.data.qpos[self.addresses] = q
        self.data.qvel[:] = 0
        mujoco.mj_forward(self.model, self.data)
        images = []
        for camera in self.cameras:
            self.renderer.update_scene(self.data, camera=camera)
            images.append(Image.fromarray(self.renderer.render()))
        return images


def contact_text(row):
    if row["clearance_mm"] < 2.0:
        a, b = (part(x) for x in row["closest"])
        return f"接触 contact：{a} – {b}  {row['clearance_mm']:+.1f} mm", ORANGE
    return f"最小间隙 clearance {row['clearance_mm']:.0f} mm", GRAY


def timeline(draw, x0, x1, y, frames, current, runs, core=None, font=None):
    width = x1 - x0
    x = lambda f: x0 + f / (frames - 1) * width
    draw.rectangle((x0, y, x1, y + 12), fill=(45, 55, 70))
    if core:
        draw.rectangle((x(core[0]), y, x(core[1]), y + 12), fill=(40, 120, 85))
    for run in runs:
        a, b = run["frames"]
        draw.rectangle((x(a) - 1, y + 3, x(b) + 1, y + 9), fill=ORANGE)
    for f in range(0, frames, 10):
        draw.line((x(f), y + 12, x(f), y + 16), fill=GRAY)
        draw.text((x(f) - 6, y + 16), str(f), font=font, fill=GRAY)
    draw.polygon([(x(current) - 6, y - 8), (x(current) + 6, y - 8), (x(current), y + 1)], fill=WHITE)
    draw.line((x(current), y, x(current), y + 12), fill=WHITE, width=2)


def chart(out, rows_new, rows_old, runs_new, n):
    """Clearance and speed over the clip, new solid, old thin grey for reference."""
    f14 = ImageFont.truetype(FONT, 14)
    width, panel_h, left = 1200, 200, 70
    image = Image.new("RGB", (width, 2 * panel_h + 150), "white")
    draw = ImageDraw.Draw(image)
    x = lambda f: left + f / (n - 1) * (width - left - 30)
    deepest_old = min(r["clearance_mm"] for r in rows_old)
    for p, (title, key, low, high, line, unit) in enumerate((
            ("最小自身间隙 self-clearance", "clearance_mm", -5.0, 15.0, 2.0, "mm"),
            ("最快关节 / 速度上限 speed ratio", "speed_ratio", 0.0, 1.1, 1.0, ""))):
        y0 = 40 + p * (panel_h + 50)
        y = lambda v: y0 + panel_h - (min(max(v, low), high) - low) / (high - low) * panel_h
        for run in runs_new:
            draw.rectangle((x(run["frames"][0]) - 2, y0, x(run["frames"][1]) + 2, y0 + panel_h), fill=(255, 232, 205))
        draw.line((left, y(line), width - 30, y(line)), fill=(200, 80, 60), width=1)
        draw.text((width - 120, y(line) - 18), f"门槛 {line:g} {unit}".strip(), font=f14, fill=(200, 80, 60))
        for value in np.linspace(low, high, 5):
            draw.text((8, y(value) - 8), f"{value:g}", font=f14, fill=(90, 90, 90))
        draw.line([(x(i), y(r[key])) for i, r in enumerate(rows_old)], fill=(170, 170, 170), width=1)
        draw.line([(x(i), y(r[key])) for i, r in enumerate(rows_new)], fill=(31, 95, 191), width=2)
        note = f"（旧版最低 {deepest_old:.1f} mm，超出坐标范围）" if key == "clearance_mm" else ""
        draw.text((left, y0 - 26), f"{title}{'（' + unit + '）' if unit else ''}：蓝 = 新版，灰 = 旧版；橙色底 = 新版接触帧{note}",
                  font=f14, fill=(30, 30, 30))
        for f in range(0, n, 10):
            draw.text((x(f) - 6, y0 + panel_h + 4), str(f), font=f14, fill=(90, 90, 90))
    image.save(out / "NURSE_clips_v2_timeline.png")


def main():
    scratch, out = Path(sys.argv[1]), Path(sys.argv[2])
    chart_only = sys.argv[3:] == ["chart"]
    out.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    if tree_hash(MODEL) != tree_hash(WT / "assets/robot"):
        raise SystemExit("Model copy differs from the worktree's assets/robot")
    new, old = load(WT / "motions/wlasl_video_v1/NURSE.npz"), load(scratch / "NURSE_old.npz")
    check = json.loads((scratch / "nurse_check.json").read_text(encoding="utf-8"))
    rows_new, rows_old = check["clips"]["clips_v2"]["per_frame"], check["clips"]["old"]["per_frame"]
    runs_new, runs_old = check["clips"]["clips_v2"]["contact_runs"], check["clips"]["old"]["contact_runs"]
    n = len(new["positions"])
    if chart_only:
        chart(out, rows_new, rows_old, runs_new, n)
        return
    views = Views(new["joint_names"])
    f12, f14, f18, f30 = (ImageFont.truetype(FONT, s) for s in (12, 14, 18, 30))
    new_views = [views(q) for q in new["positions"]]
    old_views = [views(q) for q in old["positions"]]

    def header(draw, f, width):
        draw.text((14, 6), f"NURSE 新版本 · {SOURCE}", font=f18, fill=WHITE)
        draw.text((14, 32), f"f{f} / {n - 1}    {f / 30:.2f} s", font=f30, fill=WHITE)

    def single(f):
        panel = Image.new("RGB", (2 * VIEW, 144 + VIEW), BG)
        draw = ImageDraw.Draw(panel)
        header(draw, f, 2 * VIEW)
        text, colour = contact_text(rows_new[f])
        draw.text((14, 76), text, font=f18, fill=colour)
        timeline(draw, 20, 2 * VIEW - 20, 112, n, f, runs_new, font=f12)
        for c, image in enumerate(new_views[f]):
            panel.paste(image, (c * VIEW, 144))
            ImageDraw.Draw(panel).text((c * VIEW + 8, 150), "正面 front" if c == 0 else "侧面 side", font=f14, fill=GRAY)
        return panel

    def compare(f):
        panel = Image.new("RGB", (2 * VIEW, 96 + 2 * (40 + VIEW)), BG)
        draw = ImageDraw.Draw(panel)
        draw.text((14, 6), "NURSE：旧版（第八轮所用）vs 新版（clips-v2），按帧号对齐", font=f18, fill=WHITE)
        draw.text((14, 34), f"f{f} / {n - 1}    {f / 30:.2f} s", font=f30, fill=WHITE)
        for r, (label, rows, imgs, core) in enumerate((("旧版 old", rows_old, old_views, OLD_CORE),
                                                       ("新版 clips-v2", rows_new, new_views, None))):
            y = 96 + r * (40 + VIEW)
            text, colour = contact_text(rows[f])
            if core:
                inside = core[0] <= f <= core[1]
                tag = f"旧保护 f{core[0]}–{core[1]}" + ("（在保护内）" if inside else "")
                draw.text((10, y + 8), f"{label} · {tag}", font=f18, fill=GREEN if inside else GRAY)
            else:
                draw.text((10, y + 8), f"{label} · 保护区间待标定", font=f18, fill=WHITE)
            draw.text((VIEW + 10, y + 10), text, font=f14, fill=colour)
            for c, image in enumerate(imgs[f]):
                panel.paste(image, (c * VIEW, y + 40))
        return panel

    frames_single = [single(f) for f in range(n)]
    for name, fps in (("NURSE_clips_v2.mp4", 30), ("NURSE_clips_v2_slow.mp4", 10)):
        with imageio.get_writer(out / name, fps=fps, codec="libx264", quality=8, macro_block_size=16,
                                pixelformat="yuv420p", ffmpeg_params=["-threads", "1"]) as writer:
            for panel in frames_single:
                writer.append_data(np.asarray(panel))
    with imageio.get_writer(out / "NURSE_old_vs_clips_v2.mp4", fps=30, codec="libx264", quality=8, macro_block_size=16,
                            pixelformat="yuv420p", ffmpeg_params=["-threads", "1"]) as writer:
        for f in range(n):
            writer.append_data(np.asarray(compare(f)))

    # every 4th frame (plus the last), front and side per tile
    picks = list(range(0, n, 4)) + ([n - 1] if (n - 1) % 4 else [])
    tile_w, tile_h, cols = 2 * 240, 240 + 34, 4
    sheet = Image.new("RGB", (cols * tile_w, 50 + -(-len(picks) // cols) * tile_h), BG)
    draw = ImageDraw.Draw(sheet)
    draw.text((10, 12), f"NURSE 新版本 · {SOURCE} · 每 4 帧一格（左正面、右侧面）；橙色 = 右手拇指碰到左手腕（< 2 mm）",
              font=f18, fill=WHITE)
    for i, f in enumerate(picks):
        x, y = (i % cols) * tile_w, 50 + (i // cols) * tile_h
        for c, image in enumerate(new_views[f]):
            sheet.paste(image.resize((240, 240)), (x + c * 240, y + 34))
        low = rows_new[f]["clearance_mm"] < 2.0
        draw.text((x + 8, y + 6), f"f{f}  {f / 30:.2f} s" + ("   接触" if low else ""), font=f18,
                  fill=ORANGE if low else WHITE)
        draw.rectangle((x, y + 34, x + tile_w - 1, y + tile_h - 1), outline=(40, 50, 65))
    sheet.save(out / "NURSE_clips_v2_frames.png")
    chart(out, rows_new, rows_old, runs_new, n)
    print(json.dumps({"frames": n, "outputs": sorted(p.name for p in out.iterdir()),
                      "seconds": round(time.monotonic() - started, 1)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
