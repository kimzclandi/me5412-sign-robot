"""Compare sentence trajectories from a transition method against the baseline stitching.

    MUJOCO_GL=egl .venv/bin/python scripts/demo/compare_stitching.py CANDIDATE_DIR --label group3_v1

CANDIDATE_DIR holds one trajectory per scripted line, named like the baseline
(s1.npz ... s9.npz) in the repository motion format: timestamps_s[T],
joint_names[53], positions[T,53] in radians at 30 fps. The baseline is
results/demo/<id>.npz from scripts/demo/hospital_demo.py. Lines missing on
either side are skipped and listed.

Per line and method: format checks (53 named joints, 30 fps, joint limits,
mimic couplings, neutral start/end), duration, peak and 95th-percentile arm and
finger speed, RMS arm jerk (smoothness), the fraction of the signing span in
which both hands sink back to rest (the baseline's dip between words), and the
deepest collision-geometry penetration between different bodies.
Writes results/stitch_compare/<label>/summary.json, summary.md and
<id>.png (hand height and arm speed over time, baseline vs candidate).
"""
from pathlib import Path
import argparse
import json
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sign_robot.motion import apply_frame, load_model, validate_motion

BASELINE = ROOT / "results/demo"
OUT = ROOT / "results/stitch_compare"
FPS = 30
RAISED_M = 0.10  # same threshold as sign_frames: hand at least 10 cm above its lowest point
NEUTRAL = {"left_elbow_joint": 0.25, "right_elbow_joint": 0.25, "L_thumb_proximal_yaw_joint": 0.35,
           "R_thumb_proximal_yaw_joint": 0.35, "L_thumb_proximal_pitch_joint": 0.08, "R_thumb_proximal_pitch_joint": 0.08}


def same_hand(bodies):
    """Overlap between finger links and their own wrist is mesh adjacency, not a collision."""
    sides = {b[0] if b[:2] in ("L_", "R_") else ("L" if b.startswith("left_wrist") else "R" if b.startswith("right_wrist") else None) for b in bodies}
    return len(sides) == 1 and None not in sides


class Robot:
    def __init__(self):
        import mujoco
        self.mujoco = mujoco
        self.m = load_model()
        self.d = mujoco.MjData(self.m)
        self.names = [self.m.joint(i).name for i in range(self.m.njnt)]
        self.couplings = json.loads((ROOT / "assets/robot/model_info.json").read_text())["couplings"]
        self.wrists = [self.m.body(f"{s}_wrist_yaw_link").id for s in ("left", "right")]
        neutral = dict.fromkeys(self.names, 0.0) | NEUTRAL
        for c in self.couplings:
            neutral[c["child"]] = c["multiplier"] * neutral[c["parent"]] + c["offset"]
        self.neutral = neutral

    def check(self, motion):
        names = [str(n) for n in motion["joint_names"]]
        q, t = motion["positions"], motion["timestamps_s"]
        col = {n: i for i, n in enumerate(names)}
        limited = [(col[n], *self.m.jnt_range[self.m.joint(n).id]) for n in names if self.m.jnt_limited[self.m.joint(n).id]]
        over = max((max(lo - q[:, i].min(), q[:, i].max() - hi, 0.0) for i, lo, hi in limited), default=0.0)
        coupling = max(float(np.abs(q[:, col[c["child"]]] - (c["multiplier"] * q[:, col[c["parent"]]] + c["offset"])).max())
                       for c in self.couplings)
        neutral = np.array([self.neutral[n] for n in names])
        return {"joints": len(names), "same_joint_set": sorted(names) == sorted(self.names),
                "fps": round(float(1 / np.median(np.diff(t))), 2),
                "joint_limit_excess_rad": round(float(over), 4), "coupling_error_rad": round(coupling, 4),
                "start_from_neutral_rad": round(float(np.abs(q[0] - neutral).max()), 4),
                "end_at_neutral_rad": round(float(np.abs(q[-1] - neutral).max()), 4)}

    def kinematics(self, motion):
        """Per frame: higher wrist height (m) and deepest penetration between different bodies (m)."""
        names = motion["joint_names"]
        heights, depths = [], []
        for row in motion["positions"]:
            apply_frame(self.m, self.d, names, row)
            heights.append(float(self.d.xpos[self.wrists, 2].max()))
            depth = 0.0
            for contact in self.d.contact[:self.d.ncon]:
                bodies = sorted(self.m.body(self.m.geom_bodyid[int(g)]).name for g in contact.geom)
                if contact.dist < -0.001 and not same_hand(bodies):
                    depth = max(depth, -float(contact.dist))
            depths.append(depth)
        return np.array(heights), np.array(depths)


def metrics(robot, motion):
    validate_motion(motion)
    names = [str(n) for n in motion["joint_names"]]
    q, t = motion["positions"], motion["timestamps_s"]
    dt = float(np.median(np.diff(t)))
    arm = [i for i, n in enumerate(names) if any(k in n for k in ("shoulder", "elbow", "wrist"))]
    finger = [i for i, n in enumerate(names) if n[:2] in ("L_", "R_")]
    velocity = np.diff(q, axis=0) / dt
    jerk = np.diff(q[:, arm], n=3, axis=0) / dt ** 3
    height, depth = robot.kinematics(motion)
    raised = np.flatnonzero(height > height.min() + RAISED_M)
    span = height[raised[0]:raised[-1] + 1] if len(raised) else height[:0]
    dips = int(np.sum(np.diff((span > height.min() + RAISED_M).astype(int)) == -1)) if len(span) else 0
    return {"duration_s": round(float(t[-1] - t[0]), 2), **robot.check(motion),
            "arm_speed_max": round(float(np.abs(velocity[:, arm]).max()), 2),
            "arm_speed_p95": round(float(np.percentile(np.abs(velocity[:, arm]).max(axis=1), 95)), 2),
            "finger_speed_max": round(float(np.abs(velocity[:, finger]).max()), 2),
            "arm_jerk_rms": round(float(np.sqrt(np.mean(jerk ** 2))), 1),
            "rest_fraction_in_signing": round(float(np.mean(span <= height.min() + RAISED_M)), 3) if len(span) else None,
            "dips_to_rest": dips,
            "penetration_max_mm": round(1000 * float(depth.max()), 1)}, (t - t[0], height, np.abs(velocity[:, arm]).max(axis=1))


def plot(curves, title, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(8, 4.5), sharex=True)
    for label, (t, height, speed) in curves.items():
        top.plot(t, height, label=label)
        bottom.plot(t[1:], speed, label=label)
    top.set_ylabel("higher wrist height (m)")
    bottom.set_ylabel("peak arm joint speed (rad/s)")
    bottom.set_xlabel("time (s)")
    top.set_title(title)
    top.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


ROWS = [("duration_s", "duration (s)"), ("arm_speed_max", "peak arm speed (rad/s)"),
        ("arm_speed_p95", "p95 arm speed (rad/s)"), ("finger_speed_max", "peak finger speed (rad/s)"),
        ("arm_jerk_rms", "RMS arm jerk (rad/s³)"), ("rest_fraction_in_signing", "time at rest while signing"),
        ("dips_to_rest", "dips to rest"), ("penetration_max_mm", "max penetration (mm)"),
        ("joint_limit_excess_rad", "joint-limit excess (rad)"), ("coupling_error_rad", "coupling error (rad)"),
        ("start_from_neutral_rad", "start vs neutral (rad)"), ("end_at_neutral_rad", "end vs neutral (rad)")]


def compare(candidate_dir, label, baseline_dir=BASELINE, out_root=OUT, plots=True):
    candidate_dir, baseline_dir = Path(candidate_dir), Path(baseline_dir)
    ids = sorted({p.stem for p in candidate_dir.glob("*.npz")} & {p.stem for p in baseline_dir.glob("*.npz")})
    skipped = sorted({p.stem for p in candidate_dir.glob("*.npz")} ^ {p.stem for p in baseline_dir.glob("*.npz")})
    if not ids:
        raise SystemExit(f"No common trajectories between {candidate_dir} and {baseline_dir}")
    out = Path(out_root) / label
    out.mkdir(parents=True, exist_ok=True)
    robot = Robot()
    lines = {}
    for key in ids:
        result, curves = {}, {}
        for method, folder in (("baseline", baseline_dir), (label, candidate_dir)):
            with np.load(folder / f"{key}.npz") as f:
                motion = {k: f[k] for k in ("timestamps_s", "joint_names", "positions")}
            result[method], curves[method] = metrics(robot, motion)
        lines[key] = result
        if plots:
            plot(curves, f"{key}: baseline vs {label}", out / f"{key}.png")
    summary = {"label": label, "candidate_dir": str(candidate_dir), "baseline_dir": str(baseline_dir),
               "lines": lines, "skipped": skipped,
               "note": "Kinematic checks on collision geometry; not an ASL comprehension test."}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    md = [f"# Baseline vs {label}", "", f"Lines: {', '.join(ids)}" + (f"; skipped: {', '.join(skipped)}" if skipped else ""), "",
          f"| metric | baseline (mean) | {label} (mean) |", "|---|---|---|"]
    for key, name in ROWS:
        values = {m: [lines[i][m][key] for i in ids if lines[i][m][key] is not None] for m in ("baseline", label)}
        md.append(f"| {name} | " + " | ".join(f"{np.mean(v):.3g}" if v else "—" for v in values.values()) + " |")
    md += ["", "Per line:", "", "| line | method | duration (s) | peak arm speed | RMS jerk | rest while signing | dips | penetration (mm) |",
           "|---|---|---|---|---|---|---|---|"]
    for i in ids:
        for m, r in lines[i].items():
            md.append(f"| {i} | {m} | {r['duration_s']} | {r['arm_speed_max']} | {r['arm_jerk_rms']} | "
                      f"{r['rest_fraction_in_signing']} | {r['dips_to_rest']} | {r['penetration_max_mm']} |")
    md += ["", summary["note"]]
    (out / "summary.md").write_text("\n".join(md) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("candidate_dir", help="folder with s1.npz ... s9.npz from the transition method")
    parser.add_argument("--label", required=True, help="name of the method, used for the output folder")
    parser.add_argument("--baseline", default=str(BASELINE))
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args()
    summary = compare(args.candidate_dir, args.label, args.baseline, plots=not args.no_plots)
    print((OUT / args.label / "summary.md").read_text())
    if summary["skipped"]:
        print("skipped (only on one side):", ", ".join(summary["skipped"]))


if __name__ == "__main__":
    main()
