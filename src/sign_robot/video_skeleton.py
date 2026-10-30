"""Skeletons from MediaPipe pose + hand world landmarks (monocular video).

Exposes the Skeleton interface used by retarget.G1Retargeter (h, t, times,
chest_frame) under the same UE-style bone names as the mocap skeletons. Arms
come from PoseLandmarker world landmarks (metres, hip origin, camera-aligned,
right-handed: x right, y down, z away). Each hand's 21 HandLandmarker world
points are translated onto the pose wrist. Finger flexion is computed from
joint positions, which are true fingertips here (unlike the FBX bone tails).
"""
from __future__ import annotations

import numpy as np
from scipy.signal import savgol_filter

from .retarget import Skeleton, unit

POSE = {"nose": 0, "shoulder_l": 11, "shoulder_r": 12, "elbow_l": 13, "elbow_r": 14, "wrist_l": 15,
        "wrist_r": 16, "pinky_l": 17, "pinky_r": 18, "index_l": 19, "index_r": 20, "hip_l": 23, "hip_r": 24}
# MediaPipe hand: 0 wrist; thumb 1-4 (CMC, MCP, IP, tip); index 5-8; middle 9-12; ring 13-16; pinky 17-20.
FINGER_BASE = {"thumb": 1, "index": 5, "middle": 9, "ring": 13, "pinky": 17}


def fill_gaps(x):
    """Linear interpolation over NaN frames along axis 0 (edges held)."""
    x = x.copy()
    flat = x.reshape(len(x), -1)
    for k in range(flat.shape[1]):
        v = flat[:, k]
        ok = np.isfinite(v)
        if ok.any() and not ok.all():
            v[~ok] = np.interp(np.flatnonzero(~ok), np.flatnonzero(ok), v[ok])
    return x


def smooth(x, window):
    if len(x) < window or window < 5:
        return x
    return savgol_filter(x, window, 2, axis=0)


def drop_outliers(pose, vis, min_vis=0.5, tolerance=0.4):
    """NaN out arm points that MediaPipe was unsure of, or that make a segment length
    deviate from its median by more than `tolerance` (tracking glitches)."""
    original, pose = pose, pose.copy()
    arm = [13, 14, 15, 16]  # elbows, wrists; hips are often out of frame, so they are kept
    if vis is not None:
        pose[:, arm] = np.where(vis[:, arm, None] < min_vis, np.nan, pose[:, arm])
    for a, b in ((11, 13), (13, 15), (12, 14), (14, 16)):  # upper arms, forearms
        length = np.linalg.norm(pose[:, a] - pose[:, b], axis=-1)
        bad = np.abs(length - np.nanmedian(length)) > tolerance * np.nanmedian(length)
        pose[bad, b] = np.nan
    for j in arm:  # never leave a point with no frames at all
        if np.isnan(pose[:, j, 0]).all():
            pose[:, j] = original[:, j]
    return pose


class VideoSkeleton(Skeleton):
    """`pose` [T,33,3], `hands` [T,2,21,3] (index 0 = signer's left, NaN when undetected),
    optional `vis` [T,33] pose visibility used to discard unreliable points."""

    noisy_lengths = True  # retargeter uses median arm length over frames

    def __init__(self, times, pose, hands, vis=None, smooth_s=0.2):
        fps = 1.0 / float(np.median(np.diff(times)))
        window = max(5, int(round(smooth_s * fps)) | 1)
        pose = smooth(fill_gaps(drop_outliers(pose, vis)), window)
        self.hand_detected = np.isfinite(hands[:, :, 0, 0]).mean(axis=0)  # fraction per side
        joints = {}
        for k, s in enumerate("lr"):
            wrist = pose[:, POSE[f"wrist_{s}"]]
            if self.hand_detected[k] > 0:
                local = smooth(fill_gaps(hands[:, k] - hands[:, k, :1]), window)
                pts = wrist[:, None] + local
            else:  # no hand seen: approximate an open hand from the pose hand points
                index, pinky = pose[:, POSE[f"index_{s}"]], pose[:, POSE[f"pinky_{s}"]]
                pts = np.repeat(wrist[:, None], 21, axis=1)
                for f, base in FINGER_BASE.items():
                    tip = index if f in ("thumb", "index") else pinky if f == "pinky" else (index + pinky) / 2
                    for j in range(4):
                        pts[:, base + j] = wrist + (tip - wrist) * (1.0 + 0.6 * j)
            joints[s] = pts
            for f, base in FINGER_BASE.items():
                for i in (1, 2, 3):
                    joints[f"{f}_0{i}_{s}"] = pts[:, base + i - 1]
                joints[f"{f}_tip_{s}"] = pts[:, base + 3]
            joints[f"hand_{s}"] = wrist
            joints[f"lowerarm_{s}"] = pose[:, POSE[f"elbow_{s}"]]
            joints[f"upperarm_{s}"] = pose[:, POSE[f"shoulder_{s}"]]
        mid_sh = (joints["upperarm_l"] + joints["upperarm_r"]) / 2
        joints["pelvis"] = (pose[:, POSE["hip_l"]] + pose[:, POSE["hip_r"]]) / 2
        joints["neck_01"] = mid_sh
        joints["spine_05"] = mid_sh + 0.15 * (joints["pelvis"] - mid_sh)
        joints["head"] = pose[:, POSE["nose"]]
        for s in "lr":
            joints[f"clavicle_{s}"] = mid_sh
        self.joints = joints
        self.names = list(joints)
        self.times = np.asarray(times, float)

    def h(self, name):
        return self.joints[name]

    def t(self, name):
        if name.endswith(("_03_l", "_03_r")):
            return self.joints[name.replace("_03_", "_tip_")]
        raise KeyError(name)

    def crop(self, i0, i1):
        out = object.__new__(VideoSkeleton)
        out.joints = {k: v[i0:i1] for k, v in self.joints.items()}
        out.names, out.hand_detected = self.names, self.hand_detected
        out.times = self.times[i0:i1] - self.times[i0]
        return out

    def flexion(self, finger, s):
        """Sum of bend angles along wrist->MCP->PIP->DIP->tip (thumb: CMC->MCP->IP->tip)."""
        pts = [self.h(f"{finger}_0{i}_{s}") for i in (1, 2, 3)] + [self.t(f"{finger}_03_{s}")]
        dirs = [unit(b - a) for a, b in zip(pts, pts[1:])]
        if finger != "thumb":
            dirs = [unit(self.h(f"middle_01_{s}") - self.h(f"hand_{s}"))] + dirs
        return sum(np.arccos(np.clip((a * b).sum(-1), -1, 1)) for a, b in zip(dirs, dirs[1:]))
