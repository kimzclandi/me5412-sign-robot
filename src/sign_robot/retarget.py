"""Retarget extracted human mocap skeletons to G1 + Inspire joint trajectories.

Arms: each human wrist is expressed relative to its own shoulder in a per-frame
chest frame, scaled by the robot/human arm-length ratio, and placed relative to
the robot shoulder; a bounded least-squares IK then matches wrist position, hand
orientation and (softly) the elbow direction. Fingers: each human finger's total
flexion is mapped linearly onto the single coupled Inspire finger joint.
This is a kinematic approximation, not a validated ASL rendering.
"""
from __future__ import annotations

import numpy as np
import mujoco
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

ARM_SUFFIXES = ("shoulder_pitch_joint", "shoulder_roll_joint", "shoulder_yaw_joint", "elbow_joint",
                "wrist_roll_joint", "wrist_pitch_joint", "wrist_yaw_joint")
FINGERS = ("index", "middle", "ring", "pinky")
SIDES = {"left": ("l", "L"), "right": ("r", "R")}
# Human total flexion (MCP+PIP+DIP, radians, relative to the bind pose) treated
# as open / fully curled.
FLEX_OPEN, FLEX_FIST = np.radians(15), np.radians(230)
THUMB_FLEX_OPEN, THUMB_FLEX_FIST = np.radians(10), np.radians(110)


def unit(v):
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def hand_frame(wrist, middle_base, index_base, pinky_base):
    """Columns: finger direction, pinky->index direction, their cross product."""
    f = unit(middle_base - wrist)
    a = index_base - pinky_base
    a = unit(a - (a * f).sum(-1, keepdims=True) * f)
    return np.stack([f, a, np.cross(f, a)], axis=-1)


class Skeleton:
    """`rest_rot` [B,3,3] is the bind pose (Studio Galt frame 0: T-pose, straight fingers)."""

    def __init__(self, data, rest_rot):
        self.names = [str(n) for n in data["bone_names"]]
        self.head, self.tail, self.rot = data["head"], data["tail"], data["rot"]
        self.times = data["frame_times_s"]
        self.rest_rot = rest_rot

    def h(self, name):
        return self.head[:, self.names.index(name)]

    def t(self, name):
        return self.tail[:, self.names.index(name)]

    def chest_frame(self):
        """Per-frame rotation whose columns are human forward, left, up."""
        left = unit(self.h("upperarm_l") - self.h("upperarm_r"))
        up = self.h("neck_01") - self.h("pelvis")
        up = unit(up - (up * left).sum(-1, keepdims=True) * left)
        return np.stack([np.cross(left, up), left, up], axis=-1)


def finger_flexion(sk, finger, s):
    """Sum over hand->01->02->03 of each joint's rotation angle away from the bind pose.

    Uses relative bone rotations, so it does not depend on the rig's bone-axis
    convention (bone tails in these FBX files do not point along the finger).
    """
    chain = [f"hand_{s}"] + [f"{finger}_0{i}_{s}" for i in (1, 2, 3)]
    total = 0.0
    for parent, child in zip(chain, chain[1:]):
        a, b = sk.names.index(parent), sk.names.index(child)
        rel = np.einsum("tji,tjk->tik", sk.rot[:, a], sk.rot[:, b])
        rest = sk.rest_rot[a].T @ sk.rest_rot[b]
        total = total + np.linalg.norm(Rotation.from_matrix(np.einsum("ji,tjk->tik", rest, rel)).as_rotvec(), axis=1)
    return total


class G1Retargeter:
    def __init__(self, model, couplings):
        self.m, self.d = model, mujoco.MjData(model)
        self.names = [model.joint(i).name for i in range(model.njnt)]
        self.index = {n: i for i, n in enumerate(self.names)}
        self.couplings = couplings
        mujoco.mj_forward(self.m, self.d)
        self.robot = {}
        for side, (_, p) in SIDES.items():
            body = lambda n: self.d.xpos[self.m.body(n).id].copy()
            shoulder, elbow, wrist = body(f"{side}_shoulder_pitch_link"), body(f"{side}_elbow_link"), body(f"{side}_wrist_yaw_link")
            frame0 = hand_frame(wrist, body(f"{p}_middle_proximal"), body(f"{p}_index_proximal"), body(f"{p}_pinky_proximal"))
            site = self.m.site(f"{side}_palm").id
            self.robot[side] = {
                "shoulder": shoulder, "arm_length": np.linalg.norm(elbow - shoulder) + np.linalg.norm(wrist - elbow),
                # Constant offset from the palm site frame to the anatomical hand frame.
                "site_to_hand": self.d.site_xmat[site].reshape(3, 3).T @ frame0,
                "ids": np.array([self.index[f"{side}_{s}"] for s in ARM_SUFFIXES]),
            }

    def couple(self, q):
        for rule in self.couplings:
            q[self.index[rule["child"]]] = rule["offset"] + rule["multiplier"] * q[self.index[rule["parent"]]]
        return q

    def targets(self, sk):
        """Robot-frame wrist, elbow and palm-site rotation targets per side, per frame."""
        chest = sk.chest_frame()
        out = {}
        for side, (s, _) in SIDES.items():
            r = self.robot[side]
            shoulder = sk.h(f"upperarm_{s}")
            human_len = np.linalg.norm(sk.h(f"lowerarm_{s}")[0] - shoulder[0]) + np.linalg.norm(sk.h(f"hand_{s}")[0] - sk.h(f"lowerarm_{s}")[0])
            scale = r["arm_length"] / human_len
            to_robot = lambda p: r["shoulder"] + scale * np.einsum("tji,tj->ti", chest, p - shoulder)
            human_hand = hand_frame(sk.h(f"hand_{s}"), sk.h(f"middle_01_{s}"), sk.h(f"index_01_{s}"), sk.h(f"pinky_01_{s}"))
            hand_in_chest = np.einsum("tji,tjk->tik", chest, human_hand)
            out[side] = {"wrist": to_robot(sk.h(f"hand_{s}")), "elbow": to_robot(sk.h(f"lowerarm_{s}")),
                         "site_rot": hand_in_chest @ r["site_to_hand"].T, "scale": scale}
        return out

    def hand_joints(self, sk):
        q = {}
        for side, (s, p) in SIDES.items():
            for finger in FINGERS:
                ratio = np.clip((finger_flexion(sk, finger, s) - FLEX_OPEN) / (FLEX_FIST - FLEX_OPEN), 0, 1)
                q[f"{p}_{finger}_proximal_joint"] = ratio * 1.7
            thumb = np.clip((finger_flexion(sk, "thumb", s) - THUMB_FLEX_OPEN) / (THUMB_FLEX_FIST - THUMB_FLEX_OPEN), 0, 1)
            # Opposition: how far the thumb tip crosses towards the pinky side of the palm.
            frame = hand_frame(sk.h(f"hand_{s}"), sk.h(f"middle_01_{s}"), sk.h(f"index_01_{s}"), sk.h(f"pinky_01_{s}"))
            tip = np.einsum("tji,tj->ti", frame, sk.h(f"thumb_03_{s}") - sk.h(f"index_01_{s}"))
            width = np.linalg.norm(sk.h(f"index_01_{s}") - sk.h(f"pinky_01_{s}"), axis=-1)
            q[f"{p}_thumb_proximal_yaw_joint"] = np.clip(-tip[:, 1] / width, 0, 1) * 1.3
            # 0.5, not the 0.6 joint limit: mimic multipliers 1.6/2.4 would push the
            # intermediate (0.8) and distal (1.2) thumb joints past their ranges.
            q[f"{p}_thumb_proximal_pitch_joint"] = thumb * 0.5
        return q

    def solve_arm(self, q, side, wrist, elbow, site_rot, previous, clearance_pairs):
        r = self.robot[side]
        ids = r["ids"]
        low, high = self.m.jnt_range[ids].T
        wrist_body = self.m.body(f"{side}_wrist_yaw_link").id
        elbow_body = self.m.body(f"{side}_elbow_link").id
        site = self.m.site(f"{side}_palm").id

        def residual(x):
            self.d.qpos[:] = q
            self.d.qpos[ids] = x
            mujoco.mj_forward(self.m, self.d)
            dp = (self.d.xpos[wrist_body] - wrist) * 10.0
            de = (self.d.xpos[elbow_body] - elbow) * 2.0
            dr = Rotation.from_matrix(site_rot @ self.d.site_xmat[site].reshape(3, 3).T).as_rotvec()
            clear = [max(0.0, 0.01 - mujoco.mj_geomDistance(self.m, self.d, a, b, 0.05, None)) * 50 for a, b in clearance_pairs]
            return np.r_[dp, de, dr, (x - previous) * 0.1, clear]

        seed = np.clip(previous, low + 1e-6, high - 1e-6)
        result = least_squares(residual, seed, bounds=(low + 1e-6, high - 1e-6), max_nfev=200, xtol=1e-8, ftol=1e-8)
        err = residual(result.x)
        return result.x, float(np.linalg.norm(err[:3]) / 10), float(np.linalg.norm(err[6:9]))

    def clearance_pairs(self, side):
        collides = lambda g: self.m.geom_contype[g] or self.m.geom_conaffinity[g]
        torso = {self.m.body(n).id for n in ("torso_link", "pelvis") if mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_BODY, n) >= 0}
        arm = {self.m.body(f"{side}_{part}_link").id for part in ("elbow", "wrist_roll", "wrist_pitch", "wrist_yaw")}
        tg = [g for g in range(self.m.ngeom) if self.m.geom_bodyid[g] in torso and collides(g)]
        ag = [g for g in range(self.m.ngeom) if self.m.geom_bodyid[g] in arm and collides(g)]
        return [(a, b) for a in ag for b in tg]

    def retarget(self, sk, neutral):
        tg = self.targets(sk)
        fingers = self.hand_joints(sk)
        pairs = {side: self.clearance_pairs(side) for side in SIDES}
        q_all = np.zeros((len(sk.times), self.m.nq))
        errors = {side: {"wrist_m": [], "rot_rad": []} for side in SIDES}
        previous = {side: neutral[self.robot[side]["ids"]].copy() for side in SIDES}
        for t in range(len(sk.times)):
            q = neutral.copy()
            for name, values in fingers.items():
                q[self.index[name]] = values[t]
            for side in SIDES:
                x, ep, er = self.solve_arm(q, side, tg[side]["wrist"][t], tg[side]["elbow"][t], tg[side]["site_rot"][t], previous[side], pairs[side])
                q[self.robot[side]["ids"]] = x
                previous[side] = x
                errors[side]["wrist_m"].append(ep)
                errors[side]["rot_rad"].append(er)
            q_all[t] = self.couple(q)
        return q_all, errors, {side: tg[side]["scale"] for side in SIDES}
