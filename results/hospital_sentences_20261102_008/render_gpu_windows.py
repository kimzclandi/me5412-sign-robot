"""Step 2 of the GPU render (native Windows Python, GPU OpenGL): draw what export_render_inputs.py exported.

Same layout, cameras, colours, labels and encoder settings as scripts/render_sequences.py (original clips top, sequence
bottom; front left, side right; 320x384 views; libx264 at 30 fps). Imports nothing from sign_robot. MuJoCo cannot open
\\\\wsl.localhost paths, so the model is a copy of assets/robot that must match the repository copy file by file.
Usage (Windows):
  python render_gpu_windows.py --repo //wsl.localhost/Ubuntu/home/kingderman/Documents/ME5412-github-latest
      --model-copy C:/.../render-assets/robot --output C:/.../render-out --case SEQUENCE_ID
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

import imageio.v2 as imageio
import mujoco
import numpy as np
from OpenGL import GL
from PIL import Image, ImageDraw, ImageFont

INPUTS = "results/hospital_sentences_20261102_008/render_inputs"
COLOURS = {'protected': (78, 215, 143), 'retained': (100, 175, 255), 'cut': (255, 110, 100),
           'transition': (255, 199, 65), 'hold': (180, 180, 180)}
FONT = "C:/Windows/Fonts/msyh.ttc"


def tree_hash(folder):
    digest = hashlib.sha256()
    for path in sorted(p for p in Path(folder).rglob("*") if p.is_file()):
        digest.update(path.relative_to(folder).as_posix().encode() + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def load(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--model-copy", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--case", required=True)
    args = parser.parse_args()
    started = time.monotonic()
    repo, copy = Path(args.repo), Path(args.model_copy)
    model_hash = tree_hash(copy)
    if model_hash != tree_hash(repo / "assets/robot"):
        raise SystemExit("Model copy differs from the repository assets/robot")
    source = repo / INPUTS / args.case
    plan = json.loads((source / "render_plan.json").read_text(encoding="utf-8"))
    motion, baseline = load(source / "replay.npz"), load(source / "baseline.npz")
    folder = Path(args.output) / args.case
    folder.mkdir(parents=True)
    model = mujoco.MjModel.from_xml_path(str(copy / "scene.xml"))
    data = mujoco.MjData(model)
    joints = [model.joint(str(name)) for name in motion["joint_names"]]
    if any(int(j.type[0]) not in (int(mujoco.mjtJoint.mjJNT_HINGE), int(mujoco.mjtJoint.mjJNT_SLIDE)) for j in joints):
        raise SystemExit("Only scalar joints are supported by the trajectory contract")
    addresses = np.array([j.qposadr[0] for j in joints])
    cameras = []
    for azimuth in (180, 90):
        camera = mujoco.MjvCamera()
        camera.lookat[:] = [.06, 0, 1.02]
        camera.distance, camera.azimuth, camera.elevation = 1.6, azimuth, -4
        cameras.append(camera)
    font = ImageFont.truetype(FONT, 14)
    width, height = 320, 384
    status = 'NUMERICAL PASS / 数值通过 · FORMAL OFF / 正式关闭'
    picks, stills = set(plan["picks"]), []
    with mujoco.Renderer(model, width=width, height=height) as renderer:
        gl_renderer = GL.glGetString(GL.GL_RENDERER).decode()

        def views(q):
            data.qpos[addresses] = q
            data.qvel[:] = 0
            mujoco.mj_forward(model, data)
            images = []
            for camera in cameras:
                renderer.update_scene(data, camera=camera)
                images.append(Image.fromarray(renderer.render()))
            return images

        with imageio.get_writer(folder / 'comparison.mp4', fps=30, codec='libx264', quality=8, macro_block_size=16,
                                pixelformat='yuv420p', ffmpeg_params=['-threads', '1']) as writer:
            for index in range(plan["total_frames"]):
                panel = Image.new('RGB', (width * 2, height * 2 + 112), (14, 21, 32))
                draw = ImageDraw.Draw(panel)
                draw.text((8, 5), f'{plan["title"]}  {index / 30:.2f}s', font=font, fill='white')
                draw.text((8, 29), status, font=font, fill=(130, 235, 170))
                draw.text((8, 54), 'SEQUENCE / 多词序列 · ALGORITHM windows / 算法窗口 · KINEMATIC / 运动学回放', font=font, fill='white')
                draw.text((8, 79), 'Green 保护 | Blue 保留 | Red 裁剪 | Yellow 新增 | Gray 保持', font=font, fill='white')
                for row, (planned, m) in enumerate(((False, baseline), (True, motion))):
                    q = m['positions'][min(index, len(m['positions']) - 1)]
                    kind, text = plan["phases"]["planned" if planned else "original"][index]
                    for column, image in enumerate(views(q)):
                        d = ImageDraw.Draw(image)
                        d.rectangle((0, 0, width, 60), fill=(14, 21, 32))
                        d.text((6, 3), ('AUTO / 自动' if planned else 'ORIGINAL / 原始') + ' · ' + ('front 正面' if column == 0 else 'side 侧面'), font=font, fill='white')
                        d.text((6, 29), text, font=font, fill=COLOURS[kind])
                        d.rectangle((0, height - 6, width, height), fill=COLOURS[kind])
                        panel.paste(image, (column * width, 112 + row * height))
                writer.append_data(np.asarray(panel))
                if index in picks:
                    stills.append(panel.copy())
    sheet = Image.new('RGB', (640 * len(stills), 880))
    for i, still in enumerate(stills):
        sheet.paste(still, (640 * i, 0))
    sheet.save(folder / 'contact_sheet.png')
    report = {"sequence_id": args.case, "source_sequence": plan["source_sequence"],
              "source_sequence_sha256": plan["source_sequence_sha256"], "numerical_checks_passed": True,
              "verification": "saved independent recheck reused (export_render_inputs.py checks its sequence hash)",
              "formal_acceptance_enabled": False, "playback_eligible": False, "fps": 30,
              "video_frames": plan["total_frames"], "video_duration_s": plan["total_frames"] / 30,
              "replay_duration_s": plan["replay_duration_s"],
              "layout": "original full clips top, sequence bottom; front left, side right; shorter row holds end",
              "protected_instance_video_checks": plan["protected_instance_video_checks"],
              "renderer": {"gl_renderer": gl_renderer, "mujoco": mujoco.__version__, "model_tree_sha256": model_hash,
                           "label_font": FONT, "render_wall_time_s": round(time.monotonic() - started, 2)},
              "files": {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in folder.iterdir() if f.is_file()}}
    (folder / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"sequence": args.case, "frames": plan["total_frames"], "gl": gl_renderer,
                      "seconds": report["renderer"]["render_wall_time_s"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
