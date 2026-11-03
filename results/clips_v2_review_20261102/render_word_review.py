"""Calibration renders of one clips-v2 word against its old clip (Windows render-venv, MuJoCo GPU).

Usage: python render_word_review.py SCRATCH OUT GLOSS C0 C1
SCRATCH holds old_clips/GLOSS.npz and GLOSS_check.json (word_check.py); the new clip comes from the clips-v2 worktree.
[C0, C1] is the word's current protection (v4), drawn as a green band. Writes into OUT: GLOSS_clips_v2.mp4 (30 fps),
GLOSS_clips_v2_slow.mp4 (10 fps), GLOSS_old_vs_clips_v2.mp4 and GLOSS_clips_v2_frames.png (every 3rd frame).
"""
import hashlib
import json
import sys
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

WT = Path(r"\\wsl.localhost\Ubuntu\home\kingderman\Documents\ME5412-group3-clips-v2")
MODEL = Path(r"C:\Users\23971\Documents\5412\_runtime\render-assets\robot")
FONT = "C:/Windows/Fonts/msyh.ttc"
BG, WHITE, GRAY = (14, 21, 32), (235, 235, 235), (150, 160, 175)
ORANGE, GREEN, RED = (255, 160, 60), (78, 215, 143), (240, 80, 70)
VIEW = 480
SOURCE = "group2/clips-v2 (85bc230)"
PARTS = [("R_thumb", "右手拇指"), ("R_index", "右手食指"), ("R_middle", "右手中指"), ("R_ring", "右手无名指"),
         ("R_pinky", "右手小指"), ("L_thumb", "左手拇指"), ("L_index", "左手食指"), ("L_middle", "左手中指"),
         ("L_ring", "左手无名指"), ("L_pinky", "左手小指"), ("left_wrist", "左手腕"), ("right_wrist", "右手腕"),
         ("left_elbow", "左前臂"), ("right_elbow", "右前臂"), ("left_shoulder", "左上臂"),
         ("right_shoulder", "右上臂"), ("left_hip", "左髋"), ("right_hip", "右髋"), ("torso", "躯干"),
         ("fixed_mount", "腰部底座")]


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


def contact_text(row):
    if row["clearance_mm"] < 2.0:
        a, b = (part(x) for x in row["closest"])
        return f"接触 contact：{a} – {b}  {row['clearance_mm']:+.1f} mm", ORANGE
    return f"最小间隙 clearance {row['clearance_mm']:.0f} mm", GRAY


def timeline(draw, x0, x1, y, frames, current, runs, capped, core, font):
    x = lambda f: x0 + f / (frames - 1) * (x1 - x0)
    draw.rectangle((x0, y, x1, y + 12), fill=(45, 55, 70))
    draw.rectangle((x(core[0]), y, x(core[1]), y + 12), fill=(40, 120, 85))
    for run in runs:
        draw.rectangle((x(run["frames"][0]) - 1, y + 3, x(run["frames"][1]) + 1, y + 9), fill=ORANGE)
    for f in capped:
        draw.line((x(f), y - 3, x(f), y), fill=RED, width=2)
    for f in range(0, frames, 10):
        draw.line((x(f), y + 12, x(f), y + 16), fill=GRAY)
        draw.text((x(f) - 6, y + 16), str(f), font=font, fill=GRAY)
    draw.polygon([(x(current) - 6, y - 10), (x(current) + 6, y - 10), (x(current), y - 1)], fill=WHITE)
    draw.line((x(current), y, x(current), y + 12), fill=WHITE, width=2)


def main():
    scratch, out, gloss = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    core = (int(sys.argv[4]), int(sys.argv[5]))
    out.mkdir(parents=True, exist_ok=True)
    if tree_hash(MODEL) != tree_hash(WT / "assets/robot"):
        raise SystemExit("Model copy differs from the worktree's assets/robot")
    new, old = load(WT / f"motions/wlasl_video_v1/{gloss}.npz"), load(scratch / "old_clips" / f"{gloss}.npz")
    check = json.loads((scratch / f"{gloss}_check.json").read_text(encoding="utf-8"))
    rows = {k: check["clips"][k]["per_frame"] for k in ("clips_v2", "old")}
    runs = {k: check["clips"][k]["contact_runs"] for k in ("clips_v2", "old")}
    capped = {k: check["clips"][k]["frames_at_speed_cap"] for k in ("clips_v2", "old")}
    n = len(new["positions"])
    model = mujoco.MjModel.from_xml_path(str(MODEL / "scene.xml"))
    data = mujoco.MjData(model)
    addresses = np.array([model.joint(str(name)).qposadr[0] for name in new["joint_names"]])
    cameras = []
    for azimuth, lookat, distance in ((180, [0.0, 0, 1.0], 1.3), (90, [0.12, 0, 1.0], 1.15)):
        camera = mujoco.MjvCamera()
        camera.lookat[:] = lookat
        camera.distance, camera.azimuth, camera.elevation = distance, azimuth, -4
        cameras.append(camera)
    renderer = mujoco.Renderer(model, width=VIEW, height=VIEW)

    def views(q):
        data.qpos[addresses] = q
        data.qvel[:] = 0
        mujoco.mj_forward(model, data)
        images = []
        for camera in cameras:
            renderer.update_scene(data, camera=camera)
            images.append(Image.fromarray(renderer.render()))
        return images

    f12, f14, f18, f30 = (ImageFont.truetype(FONT, s) for s in (12, 14, 18, 30))
    new_views, old_views = [views(q) for q in new["positions"]], [views(q) for q in old["positions"]]
    core_text = f"当前保护 f{core[0]}–{core[1]}（待重新标定）"
    legend = "进度条：绿 = 当前保护，橙 = 接触（< 2 mm），红线 = 达到速度上限"

    def single(f):
        panel = Image.new("RGB", (2 * VIEW, 160 + VIEW), BG)
        draw = ImageDraw.Draw(panel)
        draw.text((14, 6), f"{gloss} 新版本 · {SOURCE}", font=f18, fill=WHITE)
        inside = core[0] <= f <= core[1]
        draw.text((2 * VIEW - 14 - draw.textlength(core_text, font=f14), 10), core_text, font=f14,
                  fill=GREEN if inside else GRAY)
        draw.text((14, 32), f"f{f} / {n - 1}    {f / 30:.2f} s", font=f30, fill=WHITE)
        text, colour = contact_text(rows["clips_v2"][f])
        if f in capped["clips_v2"]:
            text, colour = text + "   ·   速度达到上限", RED if colour == GRAY else colour
        draw.text((14, 76), text, font=f18, fill=colour)
        timeline(draw, 20, 2 * VIEW - 20, 110, n, f, runs["clips_v2"], capped["clips_v2"], core, f12)
        draw.text((20, 143), legend, font=f12, fill=GRAY)
        for c, image in enumerate(new_views[f]):
            panel.paste(image, (c * VIEW, 160))
            ImageDraw.Draw(panel).text((c * VIEW + 8, 166), "正面 front" if c == 0 else "侧面 side", font=f14, fill=GRAY)
        return panel

    def compare(f):
        panel = Image.new("RGB", (2 * VIEW, 96 + 2 * (40 + VIEW)), BG)
        draw = ImageDraw.Draw(panel)
        draw.text((14, 6), f"{gloss}：旧版（第八/九轮所用）vs 新版（clips-v2），按帧号对齐", font=f18, fill=WHITE)
        draw.text((14, 34), f"f{f} / {n - 1}    {f / 30:.2f} s", font=f30, fill=WHITE)
        inside = core[0] <= f <= core[1]
        for r, (label, key, imgs) in enumerate((("旧版 old", "old", old_views), ("新版 clips-v2", "clips_v2", new_views))):
            y = 96 + r * (40 + VIEW)
            text, colour = contact_text(rows[key][f])
            draw.text((10, y + 8), f"{label} · 保护 f{core[0]}–{core[1]}" + ("（在保护内）" if inside else ""),
                      font=f18, fill=GREEN if inside else GRAY)
            draw.text((VIEW + 10, y + 10), text, font=f14, fill=colour)
            for c, image in enumerate(imgs[f]):
                panel.paste(image, (c * VIEW, y + 40))
        return panel

    frames = [single(f) for f in range(n)]
    for name, fps in ((f"{gloss}_clips_v2.mp4", 30), (f"{gloss}_clips_v2_slow.mp4", 10)):
        with imageio.get_writer(out / name, fps=fps, codec="libx264", quality=8, macro_block_size=16,
                                pixelformat="yuv420p", ffmpeg_params=["-threads", "1"]) as writer:
            for panel in frames:
                writer.append_data(np.asarray(panel))
    with imageio.get_writer(out / f"{gloss}_old_vs_clips_v2.mp4", fps=30, codec="libx264", quality=8,
                            macro_block_size=16, pixelformat="yuv420p", ffmpeg_params=["-threads", "1"]) as writer:
        for f in range(n):
            writer.append_data(np.asarray(compare(f)))

    picks = list(range(0, n, 3)) + ([n - 1] if (n - 1) % 3 else [])
    tile_w, tile_h, cols = 2 * 240, 240 + 34, 4
    sheet = Image.new("RGB", (cols * tile_w, 50 + -(-len(picks) // cols) * tile_h), BG)
    draw = ImageDraw.Draw(sheet)
    draw.text((10, 12), f"{gloss} 新版本 · {SOURCE} · 每 3 帧一格（左正面、右侧面）；绿 = 当前保护 f{core[0]}–{core[1]}，"
                        "橙 = 接触，红 = 速度上限", font=f18, fill=WHITE)
    for i, f in enumerate(picks):
        x, y = (i % cols) * tile_w, 50 + (i // cols) * tile_h
        for c, image in enumerate(new_views[f]):
            sheet.paste(image.resize((240, 240)), (x + c * 240, y + 34))
        low = rows["clips_v2"][f]["clearance_mm"] < 2.0
        tags = ("  接触" if low else "") + ("  速度上限" if f in capped["clips_v2"] else "")
        colour = ORANGE if low else RED if f in capped["clips_v2"] else WHITE
        draw.text((x + 8, y + 6), f"f{f}  {f / 30:.2f} s{tags}", font=f18, fill=colour)
        border = GREEN if core[0] <= f <= core[1] else (40, 50, 65)
        draw.rectangle((x, y + 34, x + tile_w - 1, y + tile_h - 1), outline=border, width=3 if border == GREEN else 1)
    sheet.save(out / f"{gloss}_clips_v2_frames.png")
    print(json.dumps({"gloss": gloss, "frames": n, "outputs": sorted(p.name for p in out.iterdir() if p.name.startswith(gloss))},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
