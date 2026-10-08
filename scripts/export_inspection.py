"""Append reproducible, two-view inspection exports without modifying trajectories.

Telemetry is reference trajectory data and kinematic forward calculations, not
physical controller feedback. Different source/config hashes get new run paths.
"""
from datetime import datetime
from hashlib import sha256
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo
import numpy as np
import mujoco

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from sign_robot.motion import ACTION_IDS, apply_frame, load_model, load_motion, require_preview_permission

SCHEMA_VERSION = 1
DECIMALS = 7
MAX_JSON_BYTES = 700_000
CAMERAS = {
    "front": {"label_zh": "正面", "lookat": [0.07, 0, 1.10], "distance": 1.13, "azimuth": 180, "elevation": -4,
              "purpose_zh": "查看双手是否可见、手型与左右横向运动；前后距离会受到透视压缩。"},
    "right_side": {"label_zh": "机器人右侧", "lookat": [0.14, 0, 1.10], "distance": 1.13, "azimuth": 90, "elevation": -4,
                   "purpose_zh": "查看向前与向下位移、手与脸的间距及掌面转动；左右手可能沿视线部分重叠，需配合正面。"},
}
PHASES = {
    "HELLO": [("prepare", "准备抬手", 0, 2), ("expression", "左右挥手", 2, 5.8), ("return", "回到准备姿势", 5.8, 7.8)],
    "THANK_YOU": [("prepare", "准备抬手", 0, 2.5), ("start_hold", "下脸附近起手", 2.5, 3), ("expression", "向前略下表达", 3, 4.8), ("end_hold", "末姿保持", 4.8, 5.4), ("return", "回到准备姿势", 5.4, 8)],
    "PLEASE_WAIT": [("prepare", "准备抬双手", 0, 2), ("expression", "WAIT 词例手指变化", 2, 6.5), ("return", "回到准备姿势", 6.5, 8.5)],
}
KEYFRAMES = {"HELLO": {"start": 2.0, "middle": 3.8, "end": 5.8}, "THANK_YOU": {"start": 2.5, "middle": 3.9, "end": 4.8}, "PLEASE_WAIT": {"start": 2.0, "middle": 4.0, "end": 6.0}}


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def rounded(values):
    values = np.round(np.asarray(values, dtype=float), DECIMALS)
    values[np.abs(values) < 0.5 * 10 ** -DECIMALS] = 0
    return values.tolist()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()


def backward_velocities(timestamps, positions):
    """Reference angular velocity estimate, [T,J]; first sample defined as zero."""
    t, q = np.asarray(timestamps), np.asarray(positions)
    if t.ndim != 1 or q.ndim != 2 or q.shape[0] != len(t) or not np.all(np.diff(t) > 0):
        raise ValueError("Invalid [T], [T,J] arrays or nonincreasing time")
    result = np.zeros_like(q, dtype=float)
    result[1:] = np.diff(q, axis=0) / np.diff(t)[:, None]
    return result


def joint_groups(names, couplings):
    children = {item["child"] for item in couplings}
    groups = {}
    for side, prefix in (("right", "R_"), ("left", "L_")):
        groups[f"{side}_arm"] = [n for n in names if n.startswith(side + "_") and any(part in n for part in ("shoulder", "elbow", "wrist"))]
        groups[f"{side}_hand"] = [n for n in names if n.startswith(prefix) and n not in children]
    return groups


def source_context(root, action, width, height):
    folder = root / "assets/robot"
    # Hash actual vendor bytes as well as the manifest, so local edits cannot hide.
    manifest = json.loads((folder / "upstream_manifest.json").read_text())
    for entry in manifest["files"]:
        if digest(folder / "vendor" / entry["file"]) != entry["sha256"]:
            raise ValueError(f"Vendor integrity failure: {entry['file']}")
    return {"trajectory_sha256": digest(root / f"motions/{action}.npz"),
            "motion_metadata_sha256": digest(root / f"motions/{action}.json"),
            "scene_sha256": digest(folder / "scene.xml"),
            "model_info_sha256": digest(folder / "model_info.json"),
            "upstream_manifest_sha256": digest(folder / "upstream_manifest.json"),
            "exporter_sha256": digest(__file__), "mujoco_version": mujoco.__version__,
            "schema_version": SCHEMA_VERSION, "numeric_decimals": DECIMALS,
            "width": width, "height": height, "fps": 30, "cameras": CAMERAS}


def build_telemetry(root, action, context, model=None):
    motion = load_motion(action, root)
    model = model or load_model(root)
    t, q = motion["timestamps_s"], motion["positions"]
    names = [str(n) for n in motion["joint_names"]]
    ids = [model.joint(n).id for n in names]
    limits = model.jnt_range[ids]
    info = json.loads((root / "assets/robot/model_info.json").read_text())
    coupling = info["couplings"]
    index = {name: i for i, name in enumerate(names)}
    velocity = backward_velocities(t, q)
    urdf = ET.parse(root / "assets/robot/vendor/g1_29dof_rev_1_0_with_inspire_hand_DFQ.urdf")
    vlimits = {j.get("name"): float(j.find("limit").get("velocity")) for j in urdf.findall("joint") if j.find("limit") is not None}
    vlimits = np.asarray([vlimits[n] for n in names])
    mimic_error = np.max(np.stack([np.abs(q[:, index[r['child']]] - r['offset'] - r['multiplier'] * q[:, index[r['parent']]]) for r in coupling]), axis=0)
    collision_depth = []
    palms = {"right": [], "left": []}
    normals = {"right": [], "left": []}
    data = mujoco.MjData(model)
    for frame in q:
        apply_frame(model, data, names, frame)
        collision_depth.append(max([0.0] + [-float(c.dist) for c in data.contact]))
        for side, sign in (("right", 1), ("left", -1)):
            site = data.site(f"{side}_palm")
            palms[side].append(site.xpos.copy())
            normals[side].append(sign * site.xmat.reshape(3, 3)[:, 1])
    result = {
        "schema_version": 1, "action_id": action, "trajectory_sha256": context["trajectory_sha256"],
        "timestamps_s": rounded(t), "joint_names": names, "positions_rad": rounded(q), "velocities_rad_s": rounded(velocity),
        "joint_limits_rad": rounded(limits), "joint_velocity_limits_rad_s": rounded(vlimits),
        "joint_groups": joint_groups(names, coupling), "mimic_couplings": coupling,
        "phase_intervals": [{"name": n, "label_zh": label, "start_s": a, "end_s": b} for n, label, a, b in PHASES[action]],
        "phase_boundary_rule": "Intervals are [start_s,end_s); final interval includes its end.",
        "robot": {"name": info["model"], "nq": model.nq, "actuator_count": model.nu, "fixed_base": True, "upstream_commit": motion["metadata"]["robot_commit"]},
        "units": {"timestamps_s": "s", "positions_rad": "rad", "velocities_rad_s": "rad/s", "joint_limits_rad": "rad", "joint_velocity_limits_rad_s": "rad/s", "palm_positions_m": "m", "penetration_depth_m": "m", "mimic_error_max_rad": "rad", "palm_normals": "unit vector"},
        "velocity_definition": "Backward finite difference of reference positions: v[0]=0, v[i]=(q[i]-q[i-1])/(t[i]-t[i-1]); not measured physical velocity.",
        "numeric_precision": {"decimal_places": DECIMALS, "source": "Original float64 NPZ retained unchanged; JSON rounds for display", "max_rounding_error": 0.5 * 10 ** -DECIMALS},
        "execution_mode": "kinematic_qpos_replay", "asl_reviewed": False,
        "telemetry_kind": "reference_trajectory_and_forward_kinematics_not_sensor_or_controller_feedback",
        "palm_positions_m": {s: rounded(v) for s, v in palms.items()}, "palm_normals": {s: rounded(v) for s, v in normals.items()},
        "palm_normal_definition": "Right wrist local +Y; left wrist local -Y. World +X forward, +Y robot left, +Z up.",
        "penetration_depth_m": rounded(collision_depth), "mimic_error_max_rad": rounded(mimic_error),
        "validation": {"frame_count": len(t), "joint_count": len(names), "fps": 30, "joint_limits_passed": bool(np.all(q >= limits[:, 0]-1e-8) and np.all(q <= limits[:, 1]+1e-8)),
                       "reference_velocity_limits_passed": bool(np.all(np.abs(velocity) <= vlimits + 1e-8)),
                       "max_reference_speed_rad_s": float(np.abs(velocity).max()), "max_mimic_error_rad": float(mimic_error.max()),
                       "frames_with_penetration_over_1mm": int(np.count_nonzero(np.asarray(collision_depth) > .001)),
                       "maximum_reported_penetration_m": max(collision_depth),
                       "collision_scope": "Only upstream collision geoms; no general collision-safety claim", "dynamics": "not_run", "ASL_comprehensibility": "not_reviewed"},
        "inspection_views": CAMERAS, "provenance": context,
        "limitations": motion["metadata"]["limitations"]
    }
    if len(json_bytes(result)) >= MAX_JSON_BYTES:
        raise ValueError("Inspection telemetry exceeds 700 KB limit")
    return result


def check_existing(run_dir, context):
    """Refuse reuse if either provenance or completed output bytes differ."""
    record = json.loads((run_dir / "run.json").read_text())
    if record["context"] != context:
        raise ValueError("Refusing to overwrite a run with different source/config hashes")
    for relative, expected in record["output_sha256"].items():
        if digest(run_dir / relative) != expected:
            raise ValueError(f"Existing inspection output changed: {relative}")
    return record


def render_views(model, motion, folder, width, height):
    import imageio.v2 as imageio
    from PIL import Image, ImageDraw, ImageFont
    action = motion["metadata"]["action_id"]
    data = mujoco.MjData(model)
    font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
    font = ImageFont.truetype(font_path, 21) if Path(font_path).exists() else ImageFont.load_default(size=21)
    small = ImageFont.truetype(font_path, 13) if Path(font_path).exists() else ImageFont.load_default(size=13)
    with mujoco.Renderer(model, width=width, height=height) as renderer:
        for view, settings in CAMERAS.items():
            camera = mujoco.MjvCamera()
            camera.lookat[:] = settings["lookat"]
            camera.distance, camera.azimuth, camera.elevation = settings["distance"], settings["azimuth"], settings["elevation"]
            times = motion["timestamps_s"]
            keyframes = {name: int(np.argmin(abs(times-t))) for name, t in KEYFRAMES[action].items()}
            with imageio.get_writer(folder / f"{view}.mp4", fps=30, codec="libx264", quality=8, macro_block_size=16, pixelformat="yuv420p") as writer:
                for i, (time_s, frame) in enumerate(zip(times, motion["positions"])):
                    apply_frame(model, data, motion["joint_names"], frame)
                    renderer.update_scene(data, camera=camera)
                    image = Image.fromarray(renderer.render())
                    draw = ImageDraw.Draw(image)
                    draw.rectangle((0, 0, width, 60), fill=(14, 22, 35))
                    draw.text((20, 9), f"{action.replace('_', ' ')} | {view.replace('_', ' ').upper()} | {time_s:.2f}s", font=font, fill=(240, 246, 255))
                    draw.text((20, 37), "UNREVIEWED ASL / FIXED-BASE KINEMATIC INSPECTION / NOT DYNAMICS", font=small, fill=(255, 199, 114))
                    draw.rectangle((0, height-30, width, height), fill=(14, 22, 35))
                    footer = "Actual MuJoCo render | 12 mimic relations preserved | 30 FPS"
                    if action == "PLEASE_WAIT":
                        footer = "WAIT word approximation; complete PLEASE WAIT utterance remains unverified"
                    draw.text((20, height-23), footer, font=small, fill=(200, 216, 233))
                    writer.append_data(np.asarray(image))
                    for name, index in keyframes.items():
                        if i == index:
                            image.save(folder / f"{view}_{name}.png")
                            if name == "middle":
                                image.save(folder / f"{view}.png")


def export_action(root, action, width=960, height=720, allow_candidate_preview=False):
    motion = load_motion(action, root)
    require_preview_permission(motion, allow_candidate_preview)
    context = source_context(root, action, width, height)
    run_id = sha256(json_bytes(context)).hexdigest()[:16]
    parent = root / "results/inspection" / action
    parent.mkdir(parents=True, exist_ok=True)
    final = parent / run_id
    if final.exists():
        return check_existing(final, context)
    pending = Path(tempfile.mkdtemp(prefix=f".pending-{run_id}-", dir=parent))
    model = load_model(root)
    telemetry = build_telemetry(root, action, context, model)
    (pending / "telemetry.json").write_bytes(json_bytes(telemetry))
    render_views(model, motion, pending, width, height)
    # Detect source mutations during a long render before publishing the run.
    if source_context(root, action, width, height) != context:
        raise ValueError("Source/config changed during export; partial output retained, manifest unchanged")
    relative = final.relative_to(root).as_posix()
    entry = {"action_id": action, "run_id": run_id, "trajectory_sha256": context["trajectory_sha256"],
             "telemetry": f"{relative}/telemetry.json", "views": {view: {"mp4": f"{relative}/{view}.mp4", "png": f"{relative}/{view}.png", "keyframes": {key: f"{relative}/{view}_{key}.png" for key in ("start", "middle", "end")}} for view in CAMERAS}}
    record = {"schema_version": 1, "context": context, "entry": entry,
              "created_at": datetime.now(ZoneInfo("Asia/Singapore")).isoformat(),
              "workspace_head_at_export": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
              "output_sha256": {p.name: digest(p) for p in sorted(pending.iterdir())}}
    (pending / "run.json").write_bytes(json_bytes(record))
    pending.rename(final)
    return record


def update_manifest(path, records):
    manifest = json.loads(path.read_text()) if path.exists() else {"schema_version": 1, "actions": {}, "runs": []}
    if manifest["schema_version"] != 1:
        raise ValueError("Unsupported existing inspection manifest")
    known = {(r["action_id"], r["run_id"]) for r in manifest["runs"]}
    for record in records:
        entry = record["entry"]
        if (entry["action_id"], entry["run_id"]) not in known:
            manifest["runs"].append(entry)
            known.add((entry["action_id"], entry["run_id"]))
        manifest["actions"][entry["action_id"]] = entry
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(json_bytes(manifest))
    temporary.replace(path)
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", nargs="+", choices=ACTION_IDS, default=list(ACTION_IDS))
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--allow-candidate-preview", action="store_true")
    args = parser.parse_args()
    if args.width % 16 or args.height % 16:
        parser.error("Video dimensions must be divisible by 16")
    records = []
    for action in args.ids:
        record = export_action(ROOT, action, args.width, args.height, args.allow_candidate_preview)
        records.append(record)
        print(json.dumps(record["entry"], ensure_ascii=False), flush=True)
    update_manifest(ROOT / "results/inspection/manifest.json", records)


if __name__ == "__main__":
    main()
