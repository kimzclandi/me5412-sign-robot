"""Old vs clips-v2 poses at each word's current protection start/end frame (and inside the core).

Old clips come from our branch (group3/trajectory-planning HEAD), new ones from the group3/clips-v2 worktree. Protection
intervals are the latest bundle (v3: HURT [37,57], MORNING [26,37], NURSE [38,75], the rest from the user's sheet).
Pose difference = largest joint-angle change and largest displacement of any robot body origin (forward kinematics).
Self-clearance at the boundary frames uses the planner's MujocoClearance on the new branch.
"""
import io
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

MAIN = Path("/home/kingderman/Documents/ME5412-github-latest")
W = Path("/home/kingderman/Documents/ME5412-group3-clips-v2")
sys.path.insert(0, str(W / "src"))
import mujoco  # noqa: E402
from sign_robot.motion import load_model  # noqa: E402
from sign_robot.transitions import MujocoClearance  # noqa: E402

OUT = Path(sys.argv[1])
SENTENCE_WORDS = {w for s in ("HELLO YOU APPOINTMENT HAVE", "YOU NEED INTERPRETER", "PLEASE WAIT DOCTOR COME SOON",
                              "YOU HURT WHERE", "NOW NURSE BLOOD-DRAW", "MEDICINE MORNING NIGHT TAKE", "YOU UNDERSTAND",
                              "BREATHE-DEEP", "THANK-YOU") for w in s.split()}


def old_clip(path):
    data = subprocess.run(["git", "-C", str(MAIN), "show", f"HEAD:{path}"], check=True, capture_output=True).stdout
    with np.load(io.BytesIO(data), allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def new_clip(path):
    with np.load(W / path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


model = load_model(W)
data = mujoco.MjData(model)
library = json.loads((W / "motions/hospital_v1_motions.json").read_text())
bundle = {r["gloss"]: r for r in json.loads((MAIN / "config/user_protected_hospital35_v3.json").read_text())["records"]}
clearance = None


def body_positions(names, q):
    addresses = np.array([model.joint(str(n)).qposadr[0] for n in names])
    out = []
    for pose in np.atleast_2d(q):
        data.qpos[addresses] = pose
        mujoco.mj_kinematics(model, data)
        out.append(data.xpos[1:].copy())
    return np.array(out)


body_names = [model.body(i).name for i in range(1, model.nbody)]
rows = []
for word in library["glosses"]:
    gloss, path = word["gloss"], word.get("motion")
    if not path or gloss == "NURSE":
        continue
    a, b = old_clip(path), new_clip(path)
    if np.array_equal(a["positions"], b["positions"]):
        continue
    names = a["joint_names"]
    if clearance is None:
        clearance = MujocoClearance(model, np.asarray(names), library_path=W / "motions/hospital_v1_motions.json")
    c0, c1 = bundle[gloss]["protected_core_frames"]
    pa, pb = body_positions(names, a["positions"]), body_positions(names, b["positions"])
    disp = np.linalg.norm(pa - pb, axis=2) * 1000          # frames x bodies, mm
    dq = np.abs(a["positions"] - b["positions"])            # frames x joints, rad
    row = {"gloss": gloss, "in_sentences": gloss in SENTENCE_WORDS, "core": [c0, c1], "frames": len(dq)}
    for label, f in (("start", c0), ("end", c1)):
        j, k = int(dq[f].argmax()), int(disp[f].argmax())
        row[label] = {"frame": f, "max_dq_rad": round(float(dq[f].max()), 4), "joint": str(names[j]),
                      "max_disp_mm": round(float(disp[f].max()), 1), "body": body_names[k],
                      "clearance_old_mm": round(float(clearance(a["positions"][f:f + 1]).min_distance_m) * 1000, 1),
                      "clearance_new_mm": round(float(clearance(b["positions"][f:f + 1]).min_distance_m) * 1000, 1)}
    core = disp[c0:c1 + 1].max(axis=1)
    moved = np.flatnonzero(disp.max(axis=1) > 10.0)
    row["core_max_disp_mm"] = round(float(core.max()), 1)
    row["core_max_disp_frame"] = int(c0 + core.argmax())
    row["core_frames_over_10mm"] = int((core > 10.0).sum())
    row["frames_over_10mm"] = [int(moved.min()), int(moved.max())] if len(moved) else None
    row["frames_over_10mm_count"] = int(len(moved))
    rows.append(row)

rows.sort(key=lambda r: (not r["in_sentences"], -max(r["start"]["max_disp_mm"], r["end"]["max_disp_mm"])))
(OUT / "boundary_check.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
print("gloss | sentence | core | start: dq rad / disp mm (body) / clearance old->new | end: same | "
      "core max disp mm @frame, core frames >10mm | all frames >10mm")
for r in rows:
    s, e = r["start"], r["end"]
    print(f"{r['gloss']:12s} {'Y' if r['in_sentences'] else '-'} {r['core']} | "
          f"f{s['frame']}: {s['max_dq_rad']:.3f} / {s['max_disp_mm']:.1f} ({s['body']}) / {s['clearance_old_mm']}->{s['clearance_new_mm']} | "
          f"f{e['frame']}: {e['max_dq_rad']:.3f} / {e['max_disp_mm']:.1f} ({e['body']}) / {e['clearance_old_mm']}->{e['clearance_new_mm']} | "
          f"{r['core_max_disp_mm']} @f{r['core_max_disp_frame']}, {r['core_frames_over_10mm']} | "
          f"{r['frames_over_10mm']} n={r['frames_over_10mm_count']}")
