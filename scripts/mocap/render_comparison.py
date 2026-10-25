"""2x2 MP4: source human skeleton (front, side) | G1 render (front, side).

Output: results/mocap_previews/<WORD>.mp4 plus a contact sheet PNG. Rendering is
kinematic replay only; the skeleton panels are drawn from the extracted mocap in
the signer's chest frame (finger tips are drawn to the 03 bone head).
"""
from pathlib import Path
import sys

import numpy as np
import mujoco
import imageio.v2 as imageio
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sign_robot.motion import apply_frame

OUT = ROOT / "results/mocap_previews"
W, H = 480, 540
SCALE = 520  # pixels per metre in the skeleton panels
FINGERS = ("thumb", "index", "middle", "ring", "pinky")
BONES = ([("pelvis", "spine_05"), ("spine_05", "neck_01"), ("neck_01", "head")]
         + [(a + s, b + s) for s in ("_l", "_r") for a, b in (("clavicle", "upperarm"), ("upperarm", "lowerarm"), ("lowerarm", "hand"))]
         + [(f"hand{s}", f"{f}_01{s}") for s in ("_l", "_r") for f in FINGERS]
         + [(f"{f}_0{i}{s}", f"{f}_0{i + 1}{s}") for s in ("_l", "_r") for f in FINGERS for i in (1, 2)])


def skeleton_panel(sk, t, view, title):
    image = Image.new("RGB", (W, H), (245, 247, 250))
    draw = ImageDraw.Draw(image)
    chest = sk.chest_frame()[t]
    origin = (sk.h("upperarm_l")[t] + sk.h("upperarm_r")[t]) / 2

    def px(name):
        p = chest.T @ (sk.h(name)[t] - origin)  # forward, left, up
        # front: viewer faces the signer (signer's left on screen right);
        # side: viewer on the signer's right, signer faces screen right (as the robot camera).
        horizontal = p[1] if view == "front" else p[0]
        return (W / 2 + horizontal * SCALE, H * 0.3 - p[2] * SCALE)
    for a, b in BONES:
        colour = (200, 60, 60) if a.endswith("_r") else (40, 90, 200) if a.endswith("_l") else (90, 90, 90)
        draw.line([px(a), px(b)], fill=colour, width=3)
    draw.text((12, 10), title, fill=(20, 30, 45))
    return image


def camera(azimuth):
    cam = mujoco.MjvCamera()
    cam.lookat[:] = [0.1, 0, 1.0]
    cam.distance = 1.5
    cam.azimuth = azimuth
    cam.elevation = -4
    return cam


def render(word, model, motion, sk, core_frames):
    OUT.mkdir(parents=True, exist_ok=True)
    data = mujoco.MjData(model)
    front, side = camera(180), camera(90)  # side camera on the robot's right
    q, ts = motion["positions"], motion["timestamps_s"]
    c0, c1 = core_frames
    frames = []
    with mujoco.Renderer(model, width=W, height=H) as renderer, \
            imageio.get_writer(OUT / f"{word}.mp4", fps=30, codec="libx264", quality=8, macro_block_size=16, pixelformat="yuv420p") as writer:
        for i, (time_s, row) in enumerate(zip(ts, q)):
            apply_frame(model, data, motion["joint_names"], row)
            views = []
            for cam in (front, side):
                renderer.update_scene(data, camera=cam)
                views.append(Image.fromarray(renderer.render()))
            phase = "core" if c0 <= i <= c1 else "transition"
            for v, name in zip(views, ("front", "right side")):
                ImageDraw.Draw(v).text((12, 10), f"G1 {name} | {phase} | {time_s:4.2f}s", fill=(255, 255, 255))
            src = int(np.clip(np.searchsorted(sk.times, time_s - ts[c0]), 0, len(sk.times) - 1))
            panel = Image.new("RGB", (2 * W, 2 * H))
            panel.paste(skeleton_panel(sk, src, "front", f"{word} mocap front (red = right hand)"), (0, 0))
            panel.paste(views[0], (W, 0))
            panel.paste(skeleton_panel(sk, src, "side", f"{word} mocap right side"), (0, H))
            panel.paste(views[1], (W, H))
            writer.append_data(np.asarray(panel))
            frames.append(panel)
    picks = np.linspace(c0, c1, 4).astype(int)
    sheet = Image.new("RGB", (4 * W, H))
    for k, i in enumerate(picks):
        sheet.paste(frames[i].resize((W, H)), (k * W, 0))
    sheet.save(OUT / f"{word}_sheet.png")
    print(f"wrote {OUT / (word + '.mp4')} and contact sheet")
