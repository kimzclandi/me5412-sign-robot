"""Tabulate every retargeted clip in motions/studio_galt_v1 for review.

    MUJOCO_GL=egl .venv/bin/python scripts/mocap/summarize_library.py

Per word: duration, IK error, peak arm/finger speed, deepest penetration among the
upstream collision geoms, and the closest palm-to-palm distance (contact signs).
Writes results/mocap_previews/summary.json and summary.md.
"""
from pathlib import Path
import csv
import json
import sys

import numpy as np
import mujoco

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sign_robot.motion import apply_frame, load_model

CLIPS = ROOT / "motions/studio_galt_v1"
OUT = ROOT / "results/mocap_previews"


def same_hand(bodies):
    """Overlap between finger links and their own wrist is mesh adjacency, not a collision."""
    sides = {b[0] if b[:2] in ("L_", "R_") else ("L" if b.startswith("left_wrist") else "R" if b.startswith("right_wrist") else None) for b in bodies}
    return len(sides) == 1 and None not in sides


def main():
    model = load_model()
    data = mujoco.MjData(model)
    vocab = {r["word"]: r for r in csv.DictReader(open(ROOT / "data/mocap/studio_galt_v1/recommended_vocabulary.csv", encoding="utf-8-sig"))}
    palms = [model.site(f"{s}_palm").id for s in ("left", "right")]
    rows = []
    for path in sorted(CLIPS.glob("*.npz")):
        meta = json.loads(path.with_suffix(".json").read_text())
        with np.load(path) as clip:
            names, q = clip["joint_names"], clip["positions"]
        arm = [i for i, n in enumerate(names) if "shoulder" in n or "elbow" in n or "wrist" in n]
        finger = [i for i, n in enumerate(names) if str(n)[:2] in ("L_", "R_")]
        speed = np.abs(np.diff(q, axis=0)) * meta["fps"]
        depth, pairs, gap = 0.0, {}, np.inf
        c0, c1 = meta["core_frames"]
        for row in q[c0:c1 + 1]:
            apply_frame(model, data, names, row)
            gap = min(gap, float(np.linalg.norm(data.site_xpos[palms[0]] - data.site_xpos[palms[1]])))
            for contact in data.contact[:data.ncon]:
                bodies = sorted(model.body(model.geom_bodyid[int(g)]).name for g in contact.geom)
                if contact.dist < -0.001 and not same_hand(bodies):
                    key = " | ".join(bodies)
                    pairs[key] = max(pairs.get(key, 0.0), -float(contact.dist))
                    depth = max(depth, -float(contact.dist))
        word = meta["action_id"]
        # IK error during the sign phase (hand raised); rest-pose frames are excluded.
        sign = {k: v for k, v in meta["ik_error_sign_phase"].items() if v["frames"]}
        rows.append({
            "word": word, "part_of_speech": vocab.get(word, {}).get("part_of_speech"),
            "core_s": round((c1 - c0) / meta["fps"], 2),
            "wrist_err_max_mm": round(1000 * max(e["wrist_position_m"]["max"] for e in sign.values()), 1) if sign else None,
            "rot_err_max_rad": round(max(e["hand_orientation_rad"]["max"] for e in sign.values()), 3) if sign else None,
            "arm_speed_max": round(float(speed[:, arm].max()), 2), "finger_speed_max": round(float(speed[:, finger].max()), 2),
            "penetration_max_mm": round(1000 * depth, 1), "penetrating_pairs": pairs,
            "palm_gap_min_m": round(gap, 3),
        })
    (OUT / "summary.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
    head = ["word", "part_of_speech", "core_s", "wrist_err_max_mm", "rot_err_max_rad", "arm_speed_max", "finger_speed_max", "penetration_max_mm", "palm_gap_min_m"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(str(r[h]) for h in head) + " |" for r in rows]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
