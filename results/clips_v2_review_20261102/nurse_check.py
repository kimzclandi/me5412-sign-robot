"""Per-frame source check of the old and clips-v2 NURSE (calibration aid): self-clearance, speed ratio, joint limits.

Uses the group3/clips-v2 worktree's code, robot model and motion library. Clearance is the planner's MujocoClearance on
each original frame (sampled, not a continuous proof). Speeds are the 30 Hz edge differences the source audit uses; a
frame takes the larger of its two edges. Writes nurse_check.json next to the saved clips.
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

OUT = Path(sys.argv[1])
policy = load_policy(W / "config/transition_policy_hospital_sentences_fast_v5.json", supported_versions=(1, 2))
constraints = policy["constraints"]
model = load_model(W)
NEAR_LIMIT_RAD = 1e-3
report = {"min_clearance_mm_threshold": constraints["min_clearance_m"] * 1000,
          "speed_caps_rad_s": {"arm": constraints["arm_speed_rad_s"], "finger": constraints["finger_speed_rad_s"]},
          "clips": {}}
for label, path in (("clips_v2", W / "motions/wlasl_video_v1/NURSE.npz"), ("old", OUT / "NURSE_old.npz")):
    clip = read_motion(path)
    q, names = clip["positions"], np.asarray(clip["joint_names"])
    clearance = MujocoClearance(model, names, library_path=W / "motions/hospital_v1_motions.json")
    caps = rate_limits(names, policy)
    edges = np.abs(np.diff(q, axis=0)) * 30
    speed = np.maximum(np.vstack([edges[:1], edges]), np.vstack([edges, edges[-1:]]))
    bounds = np.asarray([model.joint(str(n)).range for n in names])
    limited = np.asarray([bool(model.joint(str(n)).limited[0]) for n in names])
    frames = []
    for f in range(len(q)):
        result = clearance(q[f:f + 1])
        ratio = speed[f] / caps
        at_limit = limited & ((q[f] <= bounds[:, 0] + NEAR_LIMIT_RAD) | (q[f] >= bounds[:, 1] - NEAR_LIMIT_RAD))
        worst = dict(result.worst_contact or {})
        arm = np.asarray([any(s in str(n) for s in ("shoulder", "elbow", "wrist")) for n in names])
        frames.append({"frame": f, "time_s": round(f / 30, 4),
                       "clearance_mm": round(float(result.min_distance_m) * 1000, 2),
                       "closest": list(worst.get("bodies") or []),
                       "speed_ratio": round(float(ratio.max()), 3), "fastest_joint": str(names[int(ratio.argmax())]),
                       "arm_at_limit": [str(n) for n in names[at_limit & arm]]})
    bad_clear = [r["frame"] for r in frames if r["clearance_mm"] < report["min_clearance_mm_threshold"]]
    capped = [r["frame"] for r in frames if r["speed_ratio"] >= 1 - 1e-9]
    worst = min(frames, key=lambda r: r["clearance_mm"])
    report["clips"][label] = {"path": str(path), "frames": len(q), "per_frame": frames,
                              "frames_below_clearance": bad_clear, "frames_at_speed_cap": capped,
                              "worst_clearance": worst}
    print(f"{label}: {len(q)} frames; clearance < 2 mm at {len(bad_clear)} frames {bad_clear[:40]}")
    print(f"   worst clearance {worst['clearance_mm']} mm at f{worst['frame']} between {worst['closest']}")
    print(f"   speed cap reached at {len(capped)} frames {capped[:40]}")
    limit_frames = [r["frame"] for r in frames if r["arm_at_limit"]]
    joints = sorted({j for r in frames for j in r["arm_at_limit"]})
    print(f"   an arm joint at a limit in {len(limit_frames)} frames {limit_frames[:40]} {joints}")
    runs, start = [], None
    for r in frames + [{"frame": len(frames), "clearance_mm": 1e9, "closest": []}]:
        low = r["clearance_mm"] < report["min_clearance_mm_threshold"]
        if low and start is None:
            start, pairs = r["frame"], set()
        if low:
            pairs.add(" / ".join(r["closest"]))
        if not low and start is not None:
            depth = min(frames[i]["clearance_mm"] for i in range(start, r["frame"]))
            runs.append((start, r["frame"] - 1, depth, sorted(pairs)))
            start = None
    for a, b, depth, pairs in runs:
        print(f"   contact f{a}-{b}: min {depth} mm, {pairs}")
    report["clips"][label]["contact_runs"] = [{"frames": [a, b], "min_clearance_mm": d, "bodies": p}
                                               for a, b, d, p in runs]
(OUT / "nurse_check.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
