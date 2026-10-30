"""Turn an extracted mocap skeleton (extract_fbx_skeleton.py) into a G1 motion clip.

    .venv/bin/python scripts/mocap/retarget_to_g1.py --word YOU [--render]

Writes motions/studio_galt_v1/<WORD>.npz (+ .json) in the repository motion
format: timestamps_s [T], joint_names [53], positions [T,53] radians, 30 fps.
The clip starts and ends at the shared neutral pose; metadata core_frames marks
the retargeted sign itself so trajectory stitching can trim the transitions.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sign_robot.motion import load_model, validate_motion
from sign_robot.retarget import G1Retargeter, Skeleton, SIDES

FPS = 30
SKELETON_DIR = ROOT / "data/mocap/studio_galt_v1/skeleton"
OUT_DIR = ROOT / "motions/studio_galt_v1"
TRANSITION_S = 0.8
ACTIVE_SPEED = 0.03  # m/s; slower wrist motion counts as idle


def neutral_pose(retargeter):
    q = np.zeros(retargeter.m.nq)
    for side, prefix in (("left", "L"), ("right", "R")):
        q[retargeter.index[f"{side}_elbow_joint"]] = 0.25
        q[retargeter.index[f"{prefix}_thumb_proximal_yaw_joint"]] = 0.35
        q[retargeter.index[f"{prefix}_thumb_proximal_pitch_joint"]] = 0.08
    return retargeter.couple(q)


def active_range(sk):
    """Skip the leading bind pose, then crop to the frames where a wrist moves."""
    wrists = np.stack([sk.h("hand_l"), sk.h("hand_r")], axis=1)
    dt = np.diff(sk.times)
    speed = (np.linalg.norm(np.diff(wrists, axis=0), axis=-1) / dt[:, None]).max(axis=1)
    start = 0
    while start < len(speed) and speed[start] > 3.0:  # a T-pose jump, not motion
        start += 1
    start += 1
    moving = np.flatnonzero(speed[start:] > ACTIVE_SPEED) + start
    if not len(moving):
        raise RuntimeError("No wrist motion found")
    pad = lambda s: int(round(s / np.median(dt)))
    return max(start, moving[0] - pad(0.2)), min(len(sk.times) - 1, moving[-1] + pad(0.3)) + 1, start


def smoothstep(u):
    return u * u * (3 - 2 * u)


MOCAP_METHOD = ("Human mocap retargeting: shoulder-relative wrist targets scaled by arm length, bounded IK on 7 arm "
                "joints per side (wrist position, hand orientation, soft elbow), finger flexion ratio mapped to coupled Inspire joints")
LIMITATIONS = ["Inspire fingers have no abduction; spread handshapes (e.g. V, 3) cannot be reproduced",
               "Finger and thumb mapping use fixed flexion ranges, not per-signer calibration",
               "Torso, head and face motion are not transferred; robot base is fixed",
               "Shoulder-relative scaling does not preserve exact hand-to-hand or hand-to-body contacts; hand-hand clearance is enforced, so contacts become touching at best",
               "Hanging rest poses deviate a few cm because the human hand rests lower than the robot hip allows",
               "Not reviewed by ASL users"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--word", required=True)
    parser.add_argument("--render", action="store_true", help="also write a robot/skeleton comparison MP4")
    args = parser.parse_args()
    data = np.load(SKELETON_DIR / f"{args.word}.npz")
    source = json.loads((SKELETON_DIR / f"{args.word}.json").read_text())
    full = Skeleton(data, data["rot"][0])
    i0, i1, bind_frames = active_range(full)
    sk = Skeleton({k: data[k][i0:i1] for k in ("head", "tail", "rot")} | {"bone_names": data["bone_names"], "frame_times_s": data["frame_times_s"][i0:i1] - data["frame_times_s"][i0]},
                  rest_rot=data["rot"][0])
    write_clip(args.word, sk, {"dataset": "Studio Galt Sign Language Mocap Archive (CC0-1.0)",
                               "repository_commit": "eb9046596fffcc6e92ee91d021372961f3d4fcaa",
                               "fbx": source["source_fbx"], "fbx_sha256": source["source_sha256"],
                               "source_fps": source["source_fps"], "source_frames_used": [int(i0), int(i1)],
                               "bind_frames_skipped": int(bind_frames)},
               OUT_DIR, MOCAP_METHOD, LIMITATIONS, render=args.render)


def rate_limit(values, max_step):
    """Clamp each frame-to-frame change to +-max_step (removes jitter spikes, adds slight lag)."""
    out = values.copy()
    for t in range(1, len(out)):
        out[t] = out[t - 1] + np.clip(out[t] - out[t - 1], -max_step, max_step)
    return out


def write_clip(word, sk, source, out_dir, method, limitations, render=False, preview_dir=None,
               finger_speed_limit=None, arm_speed_limit=None, median_frames=None):
    """Retarget a cropped skeleton, add neutral transitions and write <out_dir>/<word>.npz/.json.

    The optional filters are for video estimates: `median_frames` median-filters every
    joint (removes few-frame orientation flips), then `finger_speed_limit` and
    `arm_speed_limit` (rad/s) rate-limit the finger drivers and the arm joints."""
    model = load_model()
    info = json.loads((ROOT / "assets/robot/model_info.json").read_text())
    rt = G1Retargeter(model, info["couplings"])
    neutral = neutral_pose(rt)
    q_src, errors, scales = rt.retarget(sk, neutral)

    # Resample the retargeted core to 30 fps, then add eased transitions from/to neutral.
    core_t = np.arange(0, sk.times[-1] + 1e-9, 1 / FPS)
    core = np.stack([np.interp(core_t, sk.times, q_src[:, j]) for j in range(model.nq)], axis=1)
    if median_frames:
        from scipy.signal import medfilt
        core = np.stack([medfilt(core[:, j], median_frames) for j in range(model.nq)], axis=1)
    if finger_speed_limit:
        drivers = [rt.index[n] for n in rt.names if n.endswith(("proximal_joint", "proximal_yaw_joint", "proximal_pitch_joint"))
                   and n[:2] in ("L_", "R_")]
        core[:, drivers] = rate_limit(core[:, drivers], finger_speed_limit / FPS)
    if arm_speed_limit:
        arms = np.concatenate([rt.robot[side]["ids"] for side in SIDES])
        core[:, arms] = rate_limit(core[:, arms], arm_speed_limit / FPS)
    n = int(round(TRANSITION_S * FPS))
    u = smoothstep(np.arange(1, n + 1) / n)[:, None]
    ease_in = neutral + (np.r_[0.0, u[:-1, 0]])[:, None] * (core[0] - neutral)
    ease_out = core[-1] + u * (neutral - core[-1])
    q = np.vstack([ease_in, core, ease_out])
    for row in q:
        rt.couple(row)
    times = np.arange(len(q)) / FPS
    core_frames = [n, n + len(core) - 1]

    lower, upper = model.jnt_range.T
    clipped = float(np.max(np.maximum(lower - q, q - upper)))
    q = np.clip(q, lower, upper)
    speed = np.abs(np.diff(q, axis=0)) * FPS
    motion = {"timestamps_s": times, "joint_names": np.asarray(rt.names), "positions": q}
    validate_motion(motion)
    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_dir / f"{word}.npz", **motion)
    summary = lambda v: {"mean": float(np.mean(v)), "max": float(np.max(v))} if len(v) else None
    # Sign phase: frames where that hand is raised >= 10 cm above its lowest point.
    # Hanging (rest) frames are excluded because the robot hip blocks the human rest pose.
    chest = sk.chest_frame()
    raised = {}
    for side, (s, _) in SIDES.items():
        height = np.einsum("ti,ti->t", chest[:, :, 2], sk.h(f"hand_{s}") - sk.h(f"upperarm_{s}"))
        raised[side] = height > height.min() + 0.10
    sign_error = {side: {"frames": int(raised[side].sum()),
                         "wrist_position_m": summary(np.asarray(errors[side]["wrist_m"])[raised[side]]),
                         "hand_orientation_rad": summary(np.asarray(errors[side]["rot_rad"])[raised[side]])} for side in SIDES}
    meta = {
        "action_id": word, "schema_version": 1, "robot": info["model"],
        "scene_sha256": hashlib.sha256((ROOT / "assets/robot/scene.xml").read_bytes()).hexdigest(),
        "source": source,
        "creation_method": method,
        "execution_mode": "kinematic_qpos_replay", "fps": FPS, "duration_s": float(times[-1]),
        "core_frames": core_frames, "transition_s": TRANSITION_S, "arm_scale": scales,
        "finger_speed_limit_rad_s": finger_speed_limit, "arm_speed_limit_rad_s": arm_speed_limit,
        "median_filter_frames": median_frames,
        "ik_error": {side: {"wrist_position_m": summary(errors[side]["wrist_m"]), "hand_orientation_rad": summary(errors[side]["rot_rad"])} for side in SIDES},
        "ik_error_sign_phase": sign_error,
        "max_joint_limit_clip_rad": max(clipped, 0.0), "max_joint_speed_rad_s": float(speed.max()),
        "asl_reviewed": False, "clinical_use": False,
        "limitations": list(limitations),
    }
    (out_dir / f"{word}.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({k: meta[k] for k in ("action_id", "duration_s", "core_frames", "arm_scale", "ik_error_sign_phase", "max_joint_speed_rad_s", "max_joint_limit_clip_rad")}, indent=1))
    if render:
        from render_comparison import render as render_video
        render_video(word, model, motion, sk, core_frames, **({"out": preview_dir} if preview_dir else {}))
    return meta



if __name__ == "__main__":
    main()
