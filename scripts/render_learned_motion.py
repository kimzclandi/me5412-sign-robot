"""Render the saved learned NPZ outputs; never substitute demonstration videos.

No training, trajectory correction, or changes to the frozen report occur here.
The output folder is immutable after publication and its hashes are checked on reuse.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile

import imageio.v2 as imageio
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from sign_robot.motion import ACTION_IDS, apply_frame, load_model, require_preview_permission, validate_motion
from export_inspection import CAMERAS, KEYFRAMES, backward_velocities, digest

WIDTH, HEIGHT, FPS = 960, 720, 30


def source_hashes(folder):
    files = [folder / name for name in ("model.npz", "model.json", "protocol.json", "report.json")]
    files += [folder / f"{action}.{ext}" for action in ACTION_IDS for ext in ("npz", "json")]
    files += [ROOT / "assets/robot" / name for name in ("scene.xml", "model_info.json", "upstream_manifest.json")]
    files += [Path(__file__), ROOT / "scripts/export_inspection.py", ROOT / "src/sign_robot/motion.py"]
    vendor = json.loads((ROOT / "assets/robot/upstream_manifest.json").read_text())
    for entry in vendor["files"]:
        path = ROOT / "assets/robot/vendor" / entry["file"]
        if digest(path) != entry["sha256"]:
            raise ValueError(f"Vendor integrity failure: {path}")
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in files}


def load_saved_motion(folder, action):
    # Intentionally read the new model output, not motion.load_motion().
    with np.load(folder / f"{action}.npz", allow_pickle=False) as source:
        motion = {k: source[k].copy() for k in ("timestamps_s", "joint_names", "positions")}
    motion["metadata"] = json.loads((folder / f"{action}.json").read_text())
    validate_motion(motion)
    if motion["metadata"]["action_id"] != action:
        raise ValueError("Output metadata action mismatch")
    if not np.allclose(np.diff(motion["timestamps_s"]), 1 / FPS, atol=1e-10, rtol=0):
        raise ValueError("This renderer requires the saved 30 FPS output; no implicit resampling")
    return motion


def inspect_motion(model, motion, action):
    q, names = motion["positions"], motion["joint_names"].tolist()
    limits = model.jnt_range[[model.joint(n).id for n in names]]
    couplings = json.loads((ROOT / "assets/robot/model_info.json").read_text())["couplings"]
    index = {n: i for i, n in enumerate(names)}
    mimic = max(float(np.abs(q[:, index[c["child"]]] - c["offset"] - c["multiplier"] * q[:, index[c["parent"]]]).max()) for c in couplings)
    depth = []
    data = mujoco.MjData(model)
    for frame in q:
        apply_frame(model, data, names, frame)
        depth.append(max([0.] + [-float(c.dist) for c in data.contact]))
    with np.load(ROOT / f"motions/{action}.npz", allow_pickle=False) as demo:
        if not np.array_equal(demo["joint_names"], motion["joint_names"]):
            raise ValueError("Cannot compare mismatched joint names")
        delta = q - demo["positions"]
    return {"frame_count": len(q), "joint_count": len(names),
            "joint_limit_violation_rad": float(max(0., np.max(limits[:, 0] - q), np.max(q - limits[:, 1]))),
            "max_mimic_error_rad": mimic,
            "max_reference_speed_rad_s": float(np.abs(backward_velocities(motion["timestamps_s"], q)).max()),
            "frames_with_penetration_over_1mm": int(np.count_nonzero(np.asarray(depth) > .001)),
            "maximum_reported_penetration_m": max(depth),
            "max_abs_difference_from_demonstration_rad": float(np.abs(delta).max()),
            "positions_identical_to_demonstration": bool(np.array_equal(delta, np.zeros_like(delta))),
            "collision_scope": "Upstream collision geoms at saved sample frames only",
            "asl_reviewed": False, "dynamics_run": False}


def render(model, motion, folder, action):
    font_path = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
    font = ImageFont.truetype(str(font_path), 21) if font_path.exists() else ImageFont.load_default(size=21)
    small = ImageFont.truetype(str(font_path), 13) if font_path.exists() else ImageFont.load_default(size=13)
    data = mujoco.MjData(model)
    t = motion["timestamps_s"]
    keyframes = {key: int(np.argmin(abs(t - time_s))) for key, time_s in KEYFRAMES[action].items()}
    views = {}
    with mujoco.Renderer(model, width=WIDTH, height=HEIGHT) as renderer:
        for view, settings in CAMERAS.items():
            camera = mujoco.MjvCamera()
            camera.lookat[:] = settings["lookat"]
            camera.distance, camera.azimuth, camera.elevation = settings["distance"], settings["azimuth"], settings["elevation"]
            mp4 = folder / f"{action}_{view}.mp4"
            with imageio.get_writer(mp4, fps=FPS, codec="libx264", quality=8, macro_block_size=16, pixelformat="yuv420p") as writer:
                for i, (time_s, frame) in enumerate(zip(t, motion["positions"])):
                    apply_frame(model, data, motion["joint_names"], frame)
                    renderer.update_scene(data, camera=camera)
                    image = Image.fromarray(renderer.render())
                    draw = ImageDraw.Draw(image)
                    draw.rectangle((0, 0, WIDTH, 60), fill=(14, 22, 35))
                    draw.text((20, 9), f"LEARNED OUTPUT | {action.replace('_', ' ')} | {view.replace('_', ' ').upper()} | {time_s:.2f}s", font=font, fill=(240, 246, 255))
                    draw.text((20, 37), "SAVED MODEL-GENERATED NPZ / UNREVIEWED ASL / KINEMATIC REPLAY", font=small, fill=(255, 199, 114))
                    draw.rectangle((0, HEIGHT - 30, WIDTH, HEIGHT), fill=(14, 22, 35))
                    footer = "Same-demonstration regression; not unseen-action generalization or physical control"
                    if action == "PLEASE_WAIT":
                        footer = "WAIT lexical candidate; complete PLEASE WAIT expression remains unverified"
                    draw.text((20, HEIGHT - 23), footer, font=small, fill=(200, 216, 233))
                    writer.append_data(np.asarray(image))
                    for key, frame_index in keyframes.items():
                        if i == frame_index:
                            image.save(folder / f"{action}_{view}_{key}.png")
                            if key == "middle":
                                image.save(folder / f"{action}_{view}.png")
            reader = imageio.get_reader(mp4)
            metadata = reader.get_meta_data()
            count = 0
            for decoded in reader:
                if decoded.shape != (HEIGHT, WIDTH, 3):
                    raise ValueError("Decoded frame size mismatch")
                count += 1
            reader.close()
            if count != len(t) or metadata["fps"] != FPS:
                raise ValueError("Decoded frame count/FPS does not match the learned NPZ")
            views[view] = {"view": view, "mp4": mp4.name, "png": f"{action}_{view}.png",
                           "frame_count": count, "fps": FPS, "width": WIDTH, "height": HEIGHT,
                           "keyframes": {key: {"png": f"{action}_{view}_{key}.png", "frame_index": idx, "timestamp_s": float(t[idx])} for key, idx in keyframes.items()}}
    return views


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-candidate-preview", action="store_true")
    args = parser.parse_args()
    source = ROOT / "results/motion_learning/v1"
    motions = {action: load_saved_motion(source, action) for action in ACTION_IDS}
    for motion in motions.values():
        require_preview_permission(motion, args.allow_candidate_preview)
    hashes = source_hashes(source)
    output = source / "previews"
    if output.exists():
        saved = json.loads((output / "preview_manifest.json").read_text())
        if hashes != saved["source_sha256"]:
            raise ValueError("Existing preview source hashes differ; refusing to overwrite")
        for name, expected in saved["output_sha256"].items():
            if digest(output / name) != expected:
                raise ValueError(f"Existing preview modified: {name}")
        print("Existing learned previews verified; no files overwritten.")
        return
    pending = Path(tempfile.mkdtemp(prefix=".previews-pending-", dir=source))
    model = load_model(ROOT)
    manifest = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
                "source_sha256": hashes, "mujoco_version": mujoco.__version__, "cameras": CAMERAS,
                "execution_mode": "saved_learned_npz_kinematic_replay", "asl_reviewed": False,
                "validation_scope": "Independent replay/geometry checks of generated arrays; no independent ASL/generalization evaluation",
                "actions": {}}
    for action, motion in motions.items():
        inspection = inspect_motion(model, motion, action)
        views = render(model, motion, pending, action)
        manifest["actions"][action] = {"trajectory": (source / f"{action}.npz").relative_to(ROOT).as_posix(),
                                        "trajectory_sha256": digest(source / f"{action}.npz"),
                                        "independent_inspection": inspection, "views": views}
        print(json.dumps({"action_id": action, **inspection}), flush=True)
    if source_hashes(source) != hashes:
        raise ValueError("Frozen sources changed while rendering; partial output retained without publication")
    manifest["output_sha256"] = {p.name: digest(p) for p in sorted(pending.iterdir())}
    (pending / "preview_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    pending.rename(output)
    print(output / "preview_manifest.json", flush=True)


if __name__ == "__main__":
    main()
