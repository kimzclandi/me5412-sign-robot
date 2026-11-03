"""Detail for the words whose protection boundary or core changed: fingers only, or the hand/arm too? Plus NURSE f23/f80."""
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

OUT = Path(sys.argv[1])
rows = json.loads((OUT / "boundary_check.json").read_text())
model = load_model(W)
data = mujoco.MjData(model)
bodies = [model.body(i).name for i in range(1, model.nbody)]
finger = np.array([b.startswith(("L_", "R_")) for b in bodies])
library = {w["gloss"]: w for w in json.loads((W / "motions/hospital_v1_motions.json").read_text())["glosses"]}


def clips(path):
    old = subprocess.run(["git", "-C", str(MAIN), "show", f"HEAD:{path}"], check=True, capture_output=True).stdout
    out = []
    for raw in (old, (W / path).read_bytes()):
        with np.load(io.BytesIO(raw), allow_pickle=False) as z:
            out.append({k: z[k] for k in z.files})
    return out


def xpos(names, q):
    addresses = np.array([model.joint(str(n)).qposadr[0] for n in names])
    data.qpos[addresses] = q
    mujoco.mj_kinematics(model, data)
    return data.xpos[1:].copy()


picks = []
for r in rows:
    frames = []
    for side in ("start", "end"):
        if r[side]["max_disp_mm"] > 0.5:
            frames.append((side, r[side]["frame"]))
    if r["in_sentences"] and r["core_max_disp_mm"] > 0.5:
        frames.append(("core max", r["core_max_disp_frame"]))
    if frames:
        picks.append((r["gloss"], r["in_sentences"], r["core"], frames))

detail = []
for gloss, in_sentences, core, frames in picks:
    a, b = clips(library[gloss]["motion"])
    names = [str(n) for n in a["joint_names"]]
    for label, f in frames:
        d = np.linalg.norm(xpos(names, a["positions"][f]) - xpos(names, b["positions"][f]), axis=1) * 1000
        dq = np.abs(a["positions"][f] - b["positions"][f])
        changed = [(names[i], round(float(dq[i]), 3)) for i in np.argsort(-dq) if dq[i] > 0.005][:6]
        arm_changed = [c for c in changed if not c[0].startswith(("L_", "R_"))]
        item = {"gloss": gloss, "in_sentences": in_sentences, "core": core, "where": label, "frame": f,
                "max_finger_disp_mm": round(float(d[finger].max()), 1),
                "max_non_finger_disp_mm": round(float(d[~finger].max()), 1),
                "changed_joints": changed, "arm_joints_changed": arm_changed}
        detail.append(item)
        print(f"{gloss:11s} {'Y' if in_sentences else '-'} core {core} {label:8s} f{f:<3d} finger {item['max_finger_disp_mm']:5.1f} mm, "
              f"hand/arm {item['max_non_finger_disp_mm']:5.1f} mm; joints {changed}")
(OUT / "boundary_detail.json").write_text(json.dumps(detail, ensure_ascii=False, indent=1))

nurse = json.loads((OUT / "nurse_check.json").read_text())["clips"]["clips_v2"]["per_frame"]
print("NURSE clips-v2 around the user's new protection [23, 80]:")
for f in list(range(20, 27)) + list(range(76, 90)):
    r = nurse[f]
    print(f"  f{f}: clearance {r['clearance_mm']:6.2f} mm {r['closest'] if r['clearance_mm'] < 2 else ''} "
          f"speed ratio {r['speed_ratio']:.2f} ({r['fastest_joint']}) arm at limit {r['arm_at_limit']}")
