"""Per-frame source check of a word's old and clips-v2 clip (calibration aid): self-clearance, speed ratio, arm limits.

Usage: word_check.py SCRATCH GLOSS  (old clip at SCRATCH/old_clips/GLOSS.npz; writes SCRATCH/GLOSS_check.json)
Same method as nurse_check.py.
"""
import json
import sys
from pathlib import Path

import numpy as np

W = Path("/home/kingderman/Documents/ME5412-group3-clips-v2")
sys.path.insert(0, str(W / "src"))
from sign_robot.motion import load_model  # noqa: E402
from sign_robot.pair_contract import load_policy, rate_limits, read_motion  # noqa: E402
from sign_robot.transitions import MujocoClearance  # noqa: E402

OUT, GLOSS = Path(sys.argv[1]), sys.argv[2]
policy = load_policy(W / "config/transition_policy_hospital_sentences_fast_v5.json", supported_versions=(1, 2))
constraints = policy["constraints"]
model = load_model(W)
threshold = constraints["min_clearance_m"] * 1000
report = {"gloss": GLOSS, "min_clearance_mm_threshold": threshold, "clips": {}}
for label, path in (("clips_v2", W / f"motions/wlasl_video_v1/{GLOSS}.npz"), ("old", OUT / "old_clips" / f"{GLOSS}.npz")):
    clip = read_motion(path)
    q, names = clip["positions"], np.asarray(clip["joint_names"])
    clearance = MujocoClearance(model, names, library_path=W / "motions/hospital_v1_motions.json")
    caps = rate_limits(names, policy)
    edges = np.abs(np.diff(q, axis=0)) * 30
    speed = np.maximum(np.vstack([edges[:1], edges]), np.vstack([edges, edges[-1:]]))
    bounds = np.asarray([model.joint(str(n)).range for n in names])
    limited = np.asarray([bool(model.joint(str(n)).limited[0]) for n in names])
    arm = np.asarray([any(s in str(n) for s in ("shoulder", "elbow", "wrist")) for n in names])
    frames = []
    for f in range(len(q)):
        result = clearance(q[f:f + 1])
        ratio = speed[f] / caps
        at_limit = limited & arm & ((q[f] <= bounds[:, 0] + 1e-3) | (q[f] >= bounds[:, 1] - 1e-3))
        worst = dict(result.worst_contact or {})
        frames.append({"frame": f, "time_s": round(f / 30, 4),
                       "clearance_mm": round(float(result.min_distance_m) * 1000, 2),
                       "closest": list(worst.get("bodies") or []),
                       "speed_ratio": round(float(ratio.max()), 3), "fastest_joint": str(names[int(ratio.argmax())]),
                       "arm_at_limit": [str(n) for n in names[at_limit]]})
    runs, start = [], None
    for r in frames + [{"frame": len(frames), "clearance_mm": 1e9, "closest": []}]:
        low = r["clearance_mm"] < threshold
        if low and start is None:
            start, pairs = r["frame"], set()
        if low:
            pairs.add(" / ".join(r["closest"]))
        if not low and start is not None:
            runs.append({"frames": [start, r["frame"] - 1],
                         "min_clearance_mm": min(frames[i]["clearance_mm"] for i in range(start, r["frame"])),
                         "bodies": sorted(pairs)})
            start = None
    capped = [r["frame"] for r in frames if r["speed_ratio"] >= 1 - 1e-9]
    report["clips"][label] = {"frames": len(q), "per_frame": frames, "contact_runs": runs, "frames_at_speed_cap": capped}
    print(f"{GLOSS} {label}: {len(q)} frames; speed cap at {capped}")
    for run in runs:
        print(f"   contact f{run['frames'][0]}-{run['frames'][1]}: min {run['min_clearance_mm']} mm, {run['bodies']}")
(OUT / f"{GLOSS}_check.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
