"""Render actual MuJoCo frames and encode local candidate previews.

On macOS the native CoreGraphics connection may require running outside a
restricted command sandbox. Rendering does not claim physical execution.
"""
from pathlib import Path
import sys
import argparse
import json
import numpy as np
import mujoco
from PIL import Image, ImageDraw, ImageFont
import imageio.v2 as imageio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from sign_robot.motion import ACTION_IDS, load_motion, load_model, apply_frame, require_preview_permission


def make_camera():
    camera = mujoco.MjvCamera()
    camera.lookat[:] = [0.06, 0, 1.09]
    camera.distance = 1.25
    camera.azimuth = 180
    camera.elevation = -4
    return camera


def font(size):
    candidates = ["/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def label(frame, action_id, time_s, duration_s):
    image = Image.fromarray(frame)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, image.width, 86), fill=(14, 22, 35))
    draw.text((28, 15), action_id.replace("_", " ") + " | Research candidate", font=font(26), fill=(241, 247, 255))
    draw.text((28, 52), "UNREVIEWED ASL  /  KINEMATIC REPLAY  /  FIXED BASE", font=font(16), fill=(255, 199, 114))
    draw.rectangle((0, image.height - 45, image.width, image.height), fill=(14, 22, 35))
    text = "G1 + Inspire DFQ | 12 mimic couplings retained"
    if action_id == "PLEASE_WAIT":
        text = "WAIT word approximation | Complete PLEASE WAIT utterance unverified"
    draw.text((28, image.height - 32), text, font=font(16), fill=(193, 211, 231))
    draw.text((image.width - 140, 20), f"{time_s:04.1f} / {duration_s:04.1f}s", font=font(17), fill=(193, 211, 231))
    return np.asarray(image)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", nargs="+", default=list(ACTION_IDS), choices=ACTION_IDS)
    parser.add_argument("--allow-candidate-preview", action="store_true")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=960)
    args = parser.parse_args()
    folder = ROOT / "results/previews"
    folder.mkdir(parents=True, exist_ok=True)
    model = load_model()
    data = mujoco.MjData(model)
    camera = make_camera()
    previews = {"HELLO": 3.8, "THANK_YOU": 4.8, "PLEASE_WAIT": 4.0}
    with mujoco.Renderer(model, width=args.width, height=args.height) as renderer:
        for action in args.ids:
            motion = load_motion(action)
            require_preview_permission(motion, args.allow_candidate_preview)
            ts = motion["timestamps_s"]
            preview_index = int(np.argmin(np.abs(ts - previews[action])))
            contacts = {}
            count = 0
            max_depth = 0.0
            with imageio.get_writer(folder / f"{action}.mp4", fps=30, codec="libx264", quality=8, macro_block_size=16, pixelformat="yuv420p") as writer:
                for i, (time, q) in enumerate(zip(ts, motion["positions"])):
                    apply_frame(model, data, motion["joint_names"], q)
                    data.time = float(time)
                    for contact in data.contact:
                        if contact.dist < -0.001:
                            count += 1
                            max_depth = max(max_depth, -float(contact.dist))
                            names = tuple(sorted(model.body(model.geom_bodyid[int(g)]).name for g in contact.geom))
                            contacts[" | ".join(names)] = contacts.get(" | ".join(names), 0) + 1
                    renderer.update_scene(data, camera=camera)
                    frame = label(renderer.render(), action, float(time), float(ts[-1]))
                    writer.append_data(frame)
                    if i == preview_index:
                        Image.fromarray(frame).save(folder / f"{action}.png")
                    if action == "THANK_YOU":
                        for label_name, frame_number in (("start", 75), ("middle", 117), ("end", 144)):
                            if i == frame_number:
                                Image.fromarray(frame).save(folder / f"{action}_{label_name}.png")
            report = {"action_id": action, "frames_rendered": len(ts), "renderer": f"MuJoCo {mujoco.__version__} native Renderer", "mp4": f"results/previews/{action}.mp4", "penetrating_contact_events_below_minus_1mm": count, "maximum_reported_penetration_m": max_depth, "contact_pairs": contacts, "collision_check_scope": "Only collision geoms present in upstream model; not a proof of collision-free motion"}
            (folder / f"{action}_render_report.json").write_text(json.dumps(report, indent=2) + "\n")
            metadata_path = ROOT / f"motions/{action}.json"
            metadata = json.loads(metadata_path.read_text())
            metadata['validation_status']['collision_review'] = "no_penetrations_below_1mm_in_upstream_collision_geoms" if count == 0 else "penetration_detected"
            metadata['validation_status']['rendered_frames'] = len(ts)
            metadata['render_report'] = f"results/previews/{action}_render_report.json"
            metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
            print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
