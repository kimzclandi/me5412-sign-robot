"""Hand-authored corrections for video words whose landmarks are wrong.

NURSE (StartASL video 39089): the signer's left hand sits at the bottom edge of the frame, so
MediaPipe places it hanging at the hip and the robot copied that. All four NURSE dictionary
videos show a palm-up left hand with curled fingers in front of the waist, and three of them
(Spread The Sign, ASL Deafined, SignSchool) have the right index and middle fingers resting
horizontally on top of the left wrist. The correction keeps the video's right wrist trajectory
(its tapping motion) and replaces both handshapes and the left arm:
- left hand: palm up, fingers curled, pointing forward and out; wrist under the right fingertips
- right hand: N handshape (index and middle extended), fingers horizontal towards the left
- contact: retargeting scales each arm about its own shoulder, which pulls touching hands
  apart, so the left arm is translated to sit under the right fingertips (see
  G1Retargeter.targets, `contact`), and both hands are lifted 2 cm. The offset was tuned
  by measuring the fingertip over the left wrist in the robot.
"""
import numpy as np

# MediaPipe world frame: x = signer's left, y = down, z = away from the camera.
LEFT, DOWN, FRONT, BACK = (np.array(v, float) for v in ([1, 0, 0], [0, 1, 0], [0, 0, -1], [0, 0, 1]))


def unit(v):
    return v / np.linalg.norm(v)


def hand_points(f, n, side, extended, cupped=False):
    """21 MediaPipe hand points relative to the wrist. f = finger direction, n = direction the palm
    faces; the thumb side is n x f for a left hand and f x n for a right hand."""
    t = unit(np.cross(n, f) if side == "l" else np.cross(f, n))
    bases = {"index": (0.09, 0.025), "middle": (0.09, 0.0), "ring": (0.085, -0.02), "pinky": (0.075, -0.038)}
    lengths = {"index": (0.04, 0.025, 0.02), "middle": (0.045, 0.027, 0.023), "ring": (0.04, 0.025, 0.02), "pinky": (0.03, 0.02, 0.016)}
    pts = np.zeros((21, 3))
    for k, (name, (fb, tb)) in enumerate(bases.items()):
        j0 = 5 + 4 * k
        p = pts[j0] = fb * f + tb * t
        if name in extended:
            steps = [f, f, f]
        elif cupped:  # relaxed, bent towards the palm
            steps = [unit(np.cos(a) * f + np.sin(a) * n) for a in np.radians([30, 70, 105])]
        else:  # curled into the palm
            steps = [unit(0.3 * f + n), unit(-0.6 * f + n), unit(-f + 0.2 * n)]
        for i, (step, length) in enumerate(zip(steps, lengths[name])):
            p = p + length * step
            pts[j0 + 1 + i] = p
    if cupped:
        thumb = [0.02 * f + 0.025 * t, 0.045 * f + 0.04 * t + 0.01 * n, 0.065 * f + 0.045 * t + 0.025 * n, 0.08 * f + 0.04 * t + 0.035 * n]
    elif "thumb" in extended:
        thumb = [0.02 * f + 0.025 * t, 0.045 * f + 0.045 * t, 0.07 * f + 0.06 * t, 0.09 * f + 0.07 * t]
    else:  # across the curled ring finger
        thumb = [0.02 * f + 0.025 * t, 0.04 * f + 0.03 * t + 0.015 * n, 0.055 * f + 0.012 * t + 0.03 * n, 0.065 * f - 0.008 * t + 0.035 * n]
    pts[1:5] = thumb
    return pts


def _elbow(shoulder, wrist, upper, fore):
    """Elbow on both spheres |E-S|=upper, |E-W|=fore: forearm as level as possible, elbow out to the left."""
    d = wrist - shoulder; n = unit(d); c = np.linalg.norm(d)
    x = (upper ** 2 - fore ** 2 + c ** 2) / (2 * c); r = np.sqrt(max(upper ** 2 - x ** 2, 0.0))
    p = unit(np.cross(n, DOWN)); q = np.cross(n, p)
    candidates = [shoulder + x * n + r * (np.cos(a) * p + np.sin(a) * q) for a in np.linspace(0, 2 * np.pi, 720, endpoint=False)]
    return min(candidates, key=lambda e: abs(e[1] - wrist[1]) - 0.5 * e[0])


def correct_nurse(pose, hands, vis):
    pose, hands, vis = pose.copy(), hands.copy(), vis.copy()
    tap = np.nanmedian(pose[:, 16] + (hands[:, 1, 8] - hands[:, 1, 0]), axis=0)  # right index fingertip
    upper = np.nanmedian(np.linalg.norm(pose[:, 14] - pose[:, 12], axis=-1))   # right arm: the left is occluded
    fore = np.nanmedian(np.linalg.norm(pose[:, 16] - pose[:, 14], axis=-1))
    wrist = tap + np.array([0.02, 0.04, 0.0])  # under and slightly outward of the tapping fingertips
    elbow = _elbow(np.nanmedian(pose[:, 11], axis=0), wrist, upper, fore)
    left = hand_points(unit(0.5 * LEFT + 0.87 * FRONT), -DOWN, "l", set(), cupped=True)
    pose[:, 13], pose[:, 15] = elbow, wrist
    pose[:, 17], pose[:, 19] = wrist + left[17], wrist + left[5]
    hands[:, 0] = wrist + left
    right = hand_points(unit(LEFT + 0.2 * FRONT), unit(DOWN + 0.3 * BACK), "r", {"index", "middle"})
    hands[:, 1] = pose[:, 16][:, None] + right
    pose[:, 18], pose[:, 20] = pose[:, 16] + right[17], pose[:, 16] + right[5]
    vis[:, [13, 15, 17, 18, 19, 20]] = 1.0
    return pose, hands, vis


# gloss -> (video it applies to, landmark correction, contact settings for the retargeter, note)
CORRECTIONS = {
    "NURSE": ("39089", correct_nurse,
              {"side": "left", "other": "right", "point": "index_03_r", "offset": [-0.016, 0.06, -0.017], "lift": [0.0, 0.0, 0.02]},
              "Left arm and both handshapes hand-authored from the NURSE dictionary videos (left hand palm up, "
              "fingers curled; right N fingers horizontal on top of the left wrist); right wrist trajectory from the video."),
}
