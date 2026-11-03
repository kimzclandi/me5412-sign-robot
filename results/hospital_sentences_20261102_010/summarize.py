"""Per-pair and per-sentence table for round 10, read from the saved run records (writes nothing but summary.json).

Run from the repository root: .venv/bin/python results/hospital_sentences_20261102_010/summarize.py
"""
import glob
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from sign_robot.pair_contract import connector_interior_stops


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    pairs = []
    for recheck in sorted(D.glob("selected_recheck_*/summary.json")):
        run = recheck.parent.name.split("_")[-1]
        run_dir = D / f"pair_runs/hospital_sentences_20261102_010_{run}"
        for row in load(recheck)["rows"]:
            pid, chosen = row["pair_id"], row["selected_candidate_id"]
            attempts = sorted((run_dir / "attempts" / pid).glob("*.json"))
            reviews = [load(f)["evidence"] for f in sorted((run_dir / "verification" / pid).glob("*.json"))]
            trajectory = load(run_dir / "candidates" / pid / f"{chosen}.json")["trajectory"]
            diagnostic = load(run_dir / "attempts" / pid / f"{chosen}.json")["diagnostic"]
            segments = trajectory["segments"]
            duration = segments[-2]["end_time_s"] - segments[1]["start_time_s"]
            source, target = trajectory["word_instances"]
            frames = round(duration * 30)
            gap = (source["source_frames"][1] - source["protected_core_frames"][1]) + frames + (
                target["protected_core_frames"][0] - target["source_frames"][0])
            m = row["metrics"]
            pairs.append({
                "pair": pid.replace("__", "→"), "run": run, "attempts": len(attempts),
                "numerical_pass": sum(bool(r.get("numerical_checks_passed")) for r in reviews), "selected": chosen,
                "method": diagnostic["method"], "curve": diagnostic["timing"].get("smooth_timing", {}).get("kept", {}).get("curve"),
                "cut": f"{diagnostic['exit_frame']}→{diagnostic['entry_frame']}", "connector_frames": frames,
                "stops": connector_interior_stops(segments[1:-1]), "between_cores": gap,
                "peak_jerk": m["peak_jerk_rad_s3"], "peak_acceleration": m["peak_acceleration_rad_s2"],
                "jerk_integral": m["analytic_connector_jerk_integral_rad2_s5"], "min_clearance_mm": row["min_clearance_mm"],
                "recheck_agrees": row["agrees_with_saved_review"]})
    sentences = []
    for report in sorted(D.glob("videos_*/*/report.json")):
        r = load(report)
        with np.load(report.parent / "replay.npz") as z:
            n = len(z["timestamps_s"])
        sentences.append({"sentence": r["sequence_id"].replace("__", " "), "frames": n,
                          "seconds": round(r["replay_duration_s"], 2),
                          "protected_unchanged": sum(c["poses_bitwise_equal"] for c in r["protected_instance_video_checks"]),
                          "protected_total": len(r["protected_instance_video_checks"])})
    out = {"pairs": pairs, "sentences": sentences,
           "sequence_status": load(D / "sequences/summary.json")["status_counts"]}
    (D / "summary.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for p in pairs:
        print(" | ".join(str(p[k]) for k in ("pair", "run", "attempts", "numerical_pass", "selected", "method", "curve", "cut",
                                              "connector_frames", "stops", "between_cores")),
              f"| jerk {p['peak_jerk']:.0f} acc {p['peak_acceleration']:.0f} J {p['jerk_integral']:.3g} clr {p['min_clearance_mm']:.1f}")
    for s in sentences:
        print(s)
    print(out["sequence_status"])


if __name__ == "__main__":
    main()
