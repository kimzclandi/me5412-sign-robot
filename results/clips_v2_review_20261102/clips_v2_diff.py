"""How much did each library clip change between our branch (HEAD) and group2/clips-v2? Saves both NURSE versions."""
import hashlib
import io
import json
import subprocess
from pathlib import Path

import numpy as np

REPO = "/home/kingderman/Documents/ME5412-github-latest"
NEW = "team/group2/clips-v2"
OUT = Path("/mnt/c/Users/23971/AppData/Local/Temp/claude/C--Users-23971-Documents-5412/"
           "76a53951-2677-457f-aee9-a27ba399c535/scratchpad/nurse_v2")
OUT.mkdir(parents=True, exist_ok=True)


def blob(ref, path):
    return subprocess.run(["git", "-C", REPO, "show", f"{ref}:{path}"], check=True, capture_output=True).stdout


def clip(data):
    with np.load(io.BytesIO(data), allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


library = json.loads(blob("HEAD", "motions/hospital_v1_motions.json"))
rows = []
for word in library["glosses"]:
    if not word.get("motion"):
        continue
    old, new = blob("HEAD", word["motion"]), blob(NEW, word["motion"])
    if old == new:
        continue
    a, b = clip(old), clip(new)
    same_shape = a["positions"].shape == b["positions"].shape
    diff = np.abs(a["positions"] - b["positions"]) if same_shape else None
    rows.append((word["gloss"], word["library"].split("/")[-1], a["positions"].shape[0], b["positions"].shape[0],
                 None if diff is None else float(diff.max()), None if diff is None else float(diff.mean()),
                 None if diff is None else int(np.sum(diff.max(axis=1) > 0.05))))
    if word["gloss"] == "NURSE":
        (OUT / "NURSE_old.npz").write_bytes(old)
        (OUT / "NURSE_clips_v2.npz").write_bytes(new)
        print("NURSE keys:", sorted(b), "old sha256", hashlib.sha256(old).hexdigest()[:16],
              "new sha256", hashlib.sha256(new).hexdigest()[:16])
        names = [str(n) for n in b["joint_names"]]
        if diff is not None:
            per_joint = diff.max(axis=0)
            top = np.argsort(-per_joint)[:8]
            print("NURSE largest per-joint changes (rad):", [(names[i], round(float(per_joint[i]), 3)) for i in top])
            frames = diff.max(axis=1)
            print("NURSE frames changed by > 0.05 rad:", int((frames > 0.05).sum()), "of", len(frames),
                  "| first/last:", int(np.argmax(frames > 0.05)), int(len(frames) - 1 - np.argmax(frames[::-1] > 0.05)))
print(f"{len(rows)} clips differ (of {sum(1 for w in library['glosses'] if w.get('motion'))}):")
print("gloss, library, frames old->new, max |dq| rad, mean |dq| rad, frames with >0.05 rad change")
for r in sorted(rows, key=lambda r: -(r[4] or 99)):
    print(" ", r[0], r[1], f"{r[2]}->{r[3]}", None if r[4] is None else round(r[4], 3),
          None if r[5] is None else round(r[5], 4), r[6])
