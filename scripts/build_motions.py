"""Author source-informed, UNREVIEWED kinematic candidates using bounded arm IK.

The input is manually chosen wrist poses and timing, NOT tracked human data.
Outputs: finite arrays [T, 53], timestamps [T], and named scalar joints [53].
"""
from pathlib import Path
import sys
import json
import hashlib
import xml.etree.ElementTree as ET
import numpy as np
import mujoco
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation, Slerp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from sign_robot.motion import load_model

FPS = 30
ARM_SUFFIXES = ("shoulder_pitch_joint", "shoulder_roll_joint", "shoulder_yaw_joint", "elbow_joint", "wrist_roll_joint", "wrist_pitch_joint", "wrist_yaw_joint")


def main():
    model = load_model()
    data = mujoco.MjData(model)
    names = [model.joint(i).name for i in range(model.njnt)]
    index = {n: i for i, n in enumerate(names)}
    info = json.loads((ROOT / "assets/robot/model_info.json").read_text())
    upstream = json.loads((ROOT / "assets/robot/upstream_manifest.json").read_text())
    neutral = np.zeros(model.nq)
    for side, prefix in (("left", "L"), ("right", "R")):
        neutral[index[f"{side}_elbow_joint"]] = 0.25
        neutral[index[f"{prefix}_thumb_proximal_yaw_joint"]] = 0.35
        neutral[index[f"{prefix}_thumb_proximal_pitch_joint"]] = 0.08

    def couple(q):
        for rule in info["couplings"]:
            q[index[rule["child"]]] = rule["offset"] + rule["multiplier"] * q[index[rule["parent"]]]
        return q

    couple(neutral)
    # Columns describe the directions of the hand's original x/y/z axes.
    right_upright = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], dtype=float)
    right_upright_inward = np.array([[0, -1, 0], [0, 0, -1], [1, 0, 0]], dtype=float)
    right_up = Rotation.from_euler("x", 90, degrees=True).as_matrix()
    left_up = Rotation.from_euler("x", -90, degrees=True).as_matrix()
    ik_records = []

    def solve(q, side, position, rotation, label):
        q = q.copy()
        ids = np.array([index[f"{side}_{s}"] for s in ARM_SUFFIXES])
        site = model.site(f"{side}_palm").id
        low, high = model.jnt_range[ids].T.copy()
        # Manual authoring constraint: keep upper arm outside the torso.
        # This is narrower than hardware range and does not claim general IK safety.
        if side == "right":
            high[1] = 0.0
        else:
            low[1] = 0.0
        qref = q[ids].copy()
        torso = model.body("torso_link").id
        torso_geoms = [i for i in range(model.ngeom) if model.geom_bodyid[i] == torso and (model.geom_contype[i] or model.geom_conaffinity[i])]
        arm_bodies = {model.body(f"{side}_{part}_link").id for part in ("shoulder_roll", "shoulder_yaw", "elbow", "wrist_roll", "wrist_pitch", "wrist_yaw")}
        arm_geoms = [i for i in range(model.ngeom) if model.geom_bodyid[i] in arm_bodies and (model.geom_contype[i] or model.geom_conaffinity[i])]
        pairs = [(a, b) for a in arm_geoms for b in torso_geoms]

        def residual(x):
            data.qpos[:] = q
            data.qpos[ids] = x
            mujoco.mj_forward(model, data)
            dp = (data.site_xpos[site] - position) * 5.0
            dr = Rotation.from_matrix(rotation @ data.site_xmat[site].reshape(3, 3).T).as_rotvec()
            clearance = [max(0.0, 0.006 - mujoco.mj_geomDistance(model, data, a, b, 0.03, None)) * 30 for a, b in pairs]
            return np.r_[dp, dr, (x - qref) * 0.003, clearance]

        seed = np.clip(qref, low + 1e-6, high - 1e-6)
        result = least_squares(residual, seed, bounds=(low + 1e-6, high - 1e-6), max_nfev=300, ftol=1e-9, xtol=1e-9, gtol=1e-9)
        if np.linalg.norm(result.fun[:3]) / 5 > 0.02 or np.linalg.norm(result.fun[3:6]) > 0.1:
            alternate = np.array([-0.8, -0.5 if side == "right" else 0.5, 0.2, 0.7, 1.0, -0.6, 0.4])
            candidate = least_squares(residual, np.clip(alternate, low + 1e-6, high - 1e-6), bounds=(low + 1e-6, high - 1e-6), max_nfev=500, ftol=1e-9, xtol=1e-9, gtol=1e-9)
            if np.linalg.norm(candidate.fun) < np.linalg.norm(result.fun):
                result = candidate
        q[ids] = result.x
        err = residual(result.x)
        record = {"label": label, "side": side, "target_position_m": list(position), "position_error_m": float(np.linalg.norm(err[:3]) / 5), "orientation_error_rad": float(np.linalg.norm(err[3:6]))}
        ik_records.append(record)
        if record["position_error_m"] > 0.025 or record["orientation_error_rad"] > 0.15:
            raise RuntimeError(f"Unreachable keyframe: {record}")
        return couple(q)

    def export(action, keyframes, description, source_ids, notes, wait_wiggle=False):
        times = np.arange(round(keyframes[-1][0] * FPS) + 1, dtype=float) / FPS
        q = np.empty((len(times), model.nq))
        k = 0
        for i, time in enumerate(times):
            while k < len(keyframes) - 2 and time > keyframes[k + 1][0]:
                k += 1
            ta, qa = keyframes[k]
            tb, qb = keyframes[k + 1]
            u = np.clip((time - ta) / (tb - ta), 0, 1)
            u = u * u * (3 - 2 * u)
            q[i] = qa * (1 - u) + qb * u
            if wait_wiggle and 2.0 <= time <= 6.5:
                envelope = min(1.0, (time - 2.0) / 0.8, (6.5 - time) / 0.8)
                for hand in ("L", "R"):
                    for finger_i, finger in enumerate(("index", "middle", "ring", "pinky")):
                        q[i, index[f"{hand}_{finger}_proximal_joint"]] += envelope * (0.07 + 0.065 * np.sin(2 * np.pi * (time - 2.0) / 2.4 + finger_i * np.pi / 2))
            couple(q[i])
        speed = np.abs(np.diff(q, axis=0) * FPS)
        lower, upper = model.jnt_range.T
        limits_ok = bool(np.all(q >= lower[None, :] - 1e-8) and np.all(q <= upper[None, :] + 1e-8))
        if not limits_ok:
            raise RuntimeError(f"{action} violates joint limits")
        max_coupling_error = max(float(np.max(np.abs(q[:, index[r['child']]] - r['offset'] - r['multiplier'] * q[:, index[r['parent']]]))) for r in info['couplings'])
        np.savez_compressed(ROOT / f"motions/{action}.npz", timestamps_s=times, joint_names=np.asarray(names), positions=q)
        records = [r for r in ik_records if r['label'].startswith(action)]
        meta = {"action_id": action, "schema_version": 1, "robot": info["model"], "robot_commit": upstream["commit"], "scene_sha256": hashlib.sha256((ROOT / "assets/robot/scene.xml").read_bytes()).hexdigest(),
                "source_ids": source_ids, "creation_method": "Agent-authored manual wrist keyframes, bounded numerical IK, smoothstep interpolation, coupled fingers", "input_data": "Manual engineering targets informed by cited visual/text references; no human motion extraction", "description": description,
                "execution_mode": "kinematic_qpos_replay", "asl_reviewed": False, "language_validation": "unreviewed", "clinical_use": False, "duration_s": float(times[-1]), "fps": FPS,
                "joint_limit_check_passed": limits_ok, "max_mimic_error_rad": max_coupling_error, "max_joint_speed_rad_s": float(speed.max()), "keyframe_ik": records,
                "limitations": notes + ["Facial expression and head motion are absent", "Joint limits and mimic relations checked; no dynamic tracking, torque, or collision-safety claim", "Unreviewed approximation: human ASL comprehensibility has not been tested"],
                "validation_status": {"numeric_structure": "passed", "joint_limits": "passed", "mimic_couplings": "passed", "dynamics": "not_run", "collision_review": "pending", "asl_comprehensibility": "not_reviewed"}}
        (ROOT / f"motions/{action}.json").write_text(json.dumps(meta, indent=2) + "\n")
        print(f"{action}: {q.shape}; {times[-1]:.1f}s; max speed {speed.max():.3f} rad/s; mimic error {max_coupling_error:g}")

    hello = solve(neutral, "right", [0.19, -0.27, 1.13], right_upright, "HELLO_raise")
    hello2 = solve(hello, "right", [0.19, -0.35, 1.13], right_upright, "HELLO_wave_out")
    hello3 = solve(hello2, "right", [0.19, -0.23, 1.13], right_upright, "HELLO_wave_in")
    export("HELLO", [(0, neutral), (2.0, hello), (2.8, hello2), (3.8, hello3), (4.8, hello2), (5.8, hello), (7.8, neutral)], "Raised open right hand with lateral wave; candidate greeting", ["lifeprint_hello"], ["Hand cannot independently abduct fingers; natural human spreading not reproduced"])

    thanks_start_orientation = Rotation.from_euler("x", -30, degrees=True).as_matrix() @ Rotation.from_euler("y", -25, degrees=True).as_matrix() @ right_upright_inward
    # Source-video alignment correction: an explicit lower-face proxy target.
    # This is NOT a measured human landmark or a real lip-contact target.
    tip_start_target = np.array([0.10, -0.02, 1.20])
    palm_start_target = tip_start_target - 0.17 * thanks_start_orientation[:, 0]
    thanks_start = solve(neutral, "right", palm_start_target, thanks_start_orientation, "THANK_YOU_near_face")
    turns = Slerp([0, 1], Rotation.from_matrix(np.stack([thanks_start_orientation, right_up])))
    tip_start = tip_start_target
    tip_end = np.array([0.34, -0.04, 1.08]) + 0.17 * right_up[:, 0]
    thanks_frames = [(0, neutral), (2.5, thanks_start), (3.0, thanks_start)]
    previous = thanks_start
    for phase in np.linspace(0, 1, 13)[1:]:
        orientation = turns(phase).as_matrix()
        tip = (1 - phase) * tip_start + phase * tip_end
        palm = tip - 0.17 * orientation[:, 0]
        previous = solve(previous, "right", palm, orientation, f"THANK_YOU_path_{phase:.3f}")
        thanks_frames.append((3 + 1.8 * phase, previous))
    thanks_end = previous
    thanks_frames.extend([(5.4, thanks_end), (8.0, neutral)])
    export("THANK_YOU", thanks_frames, "Flat right hand moves from a lower-face proxy forward, ending palm-up; candidate thanks", ["lifeprint_thank_you"], ["No actual lip contact; lower-face proxy is an anatomical approximation with a visible gap in front of the head", "Finger spacing differs from the source fingers-together handshape; this hand has no independent finger-adduction joints", "Smile from source is absent", "Twelve intermediate poses approximate a forward and slightly downward fingertip path; orientations come from 2D-reference-informed manual targets"])

    waiting = solve(neutral, "right", [0.31, -0.24, 1.02], right_up, "PLEASE_WAIT_right")
    waiting = solve(waiting, "left", [0.29, 0.23, 1.10], left_up, "PLEASE_WAIT_left")
    export("PLEASE_WAIT", [(0, neutral), (2, waiting), (6.5, waiting), (8.5, neutral)], "WAIT lexical candidate: two palm-up hands and phase-shifted finger flexion; NOT a verified complete PLEASE WAIT expression", ["lifeprint_wait"], ["The action ID is reserved for integration; complete PLEASE WAIT utterance is not verified", "Finger joints are coupled; no independent finger abduction or human-like finger dexterity", "No invented concatenation of PLEASE and WAIT is performed"], wait_wiggle=True)


if __name__ == "__main__":
    main()
