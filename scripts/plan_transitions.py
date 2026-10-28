"""Plan rate-limited, collision-checked transitions between hospital word clips.

Examples::

    .venv/bin/python scripts/plan_transitions.py YOU BUY BOOK
    MUJOCO_GL=egl .venv/bin/python scripts/plan_transitions.py YOU HURT WHERE --render
    MUJOCO_GL=egl .venv/bin/python scripts/plan_transitions.py --all

The first word deliberately keeps its frame-0 rise from neutral and the final
word keeps its return to neutral, matching ``stitch_baseline.py``. Only the
inter-word portions are replaced by minimum-jerk blends. Output uses the same
``timestamps_s``, ``joint_names``, ``positions`` NPZ contract as the baseline,
with a distinct ``planned_sentence_`` filename prefix.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import json
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from sign_robot.motion import load_model
from sign_robot.transitions import plan_sentence

OUT = ROOT / "results/mocap_previews"
REPORT_OUT = ROOT / "results/planned_transitions"
SENTENCES = (
    ("HELLO", "YOU", "APPOINTMENT", "HAVE"),
    ("MEDICINE", "MORNING", "NIGHT", "TAKE"),
    ("NOW", "NURSE", "BLOOD-DRAW"),
    ("PLEASE", "WAIT", "DOCTOR", "COME", "SOON"),
    ("YOU", "BUY", "BOOK"),
    ("YOU", "HURT", "WHERE"),
    ("YOU", "NEED", "INTERPRETER"),
    ("YOU", "UNDERSTAND"),
    ("BREATHE-DEEP",),
    ("THANK-YOU",),
)


def _baseline_duration(glosses):
    path = OUT / ("sentence_" + "_".join(glosses) + ".npz")
    if not path.exists():
        return None, None
    with np.load(path, allow_pickle=False) as data:
        frames = len(data["timestamps_s"])
    return frames, frames / 30


def _enrich_report(report, glosses, output):
    output = output.resolve()
    frames, seconds = _baseline_duration(glosses)
    report = dict(report)
    report["output_npz"] = str(output.relative_to(ROOT) if output.is_relative_to(ROOT) else output)
    report["baseline"] = {"path": str((OUT / ("sentence_" + "_".join(glosses) + ".npz")).relative_to(ROOT)),
                          "frames": frames, "duration_s": seconds}
    report["duration_vs_baseline_s"] = (None if seconds is None else report["duration_s"] - seconds)
    return report


def render_motion(path, glosses, out_path):
    """Render one planned sentence with the same camera style as baseline."""
    import imageio.v2 as imageio
    import mujoco
    from PIL import Image, ImageDraw
    sys.path.insert(0, str(ROOT / "scripts/mocap"))
    from render_comparison import camera
    from sign_robot.motion import apply_frame

    with np.load(path, allow_pickle=False) as data:
        motion = {key: data[key] for key in ("timestamps_s", "joint_names", "positions")}
    model = load_model(ROOT)
    mjdata = mujoco.MjData(model)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with mujoco.Renderer(model, width=640, height=720) as renderer, imageio.get_writer(
            out_path, fps=30, codec="libx264", quality=8, macro_block_size=16,
            pixelformat="yuv420p", ffmpeg_params=["-threads", "1"]) as writer:
        for index, (t, row) in enumerate(zip(motion["timestamps_s"], motion["positions"])):
            apply_frame(model, mjdata, motion["joint_names"], row)
            renderer.update_scene(mjdata, camera=camera(180))
            frame = Image.fromarray(renderer.render())
            ImageDraw.Draw(frame).text((14, 12),
                f"{' '.join(glosses)} | planned minimum jerk | {t:4.2f}s",
                fill=(255, 255, 255))
            writer.append_data(np.asarray(frame))
            if index % 30 == 0 or index == len(motion["positions"]) - 1:
                print(f"planned render {index + 1}/{len(motion['positions'])} frames", flush=True)
    return out_path


def plan_one(glosses, *, model=None, render=False, out_dir=OUT):
    glosses = tuple(g.upper() for g in glosses)
    motion, report = plan_sentence(glosses, model=model)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = "planned_sentence_" + "_".join(glosses)
    npz_path = out_dir / f"{stem}.npz"
    np.savez_compressed(npz_path, **motion)
    report = _enrich_report(report, glosses, npz_path)
    if render:
        report["output_mp4"] = str(render_motion(npz_path, glosses, out_dir / f"{stem}.mp4"))
    print(f"{stem}: {report['frames']} frames, {report['duration_s']:.3f}s; "
          f"transitions {report['transition_count']} pass {report['pass_count']} "
          f"source_collision {report['source_collision_count']} failed {report['failed_count']}")
    for transition in report["transitions"]:
        directions = " -> ".join(transition["via_directions"])
        print("  SEGMENT", transition["from_gloss"], "->", transition["to_gloss"],
              transition["method"], directions, transition["status"],
              "minimum contact distance", transition["min_clearance_mm"], "mm;",
              transition["duration_s"], "s")
        for warning in transition["warnings"]:
            print("  WARNING", transition["from_gloss"], "->", transition["to_gloss"], warning)
        if transition["status"] == "FAILED":
            reasons = transition["reasons"]
            reason = "; ".join(reasons[:3])
            if len(reasons) > 3:
                reason += f"; +{len(reasons) - 3} more (see JSON report)"
            print("  FAILED", transition["from_gloss"], "->", transition["to_gloss"],
                  reason)
            print("    worst collision:", transition["worst_collision"])
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=(
        "Plan 30 fps hospital gloss transitions with minimum-jerk interpolation. "
        "The first word keeps its frame-0 rise and the last word keeps its return "
        "to neutral, matching stitch_baseline."))
    parser.add_argument("glosses", nargs="*", help="uppercase or lowercase hospital glosses")
    parser.add_argument("--all", action="store_true", help="run nine scripted sentences plus THANK-YOU (ten total)")
    parser.add_argument("--render", action="store_true", help="also write planned MP4 previews")
    parser.add_argument("--out-dir", type=Path, default=OUT)
    parser.add_argument("--report", type=Path, default=REPORT_OUT / "report.json")
    args = parser.parse_args(argv)
    if args.all and args.glosses:
        parser.error("--all cannot be combined with positional glosses")
    batches = SENTENCES if args.all else (tuple(args.glosses),)
    if not batches[0]:
        parser.error("provide glosses or use --all")
    # One model object is enough for a run; collision data are per sentence in
    # plan_sentence, avoiding a second heavy model-loading process.
    model = load_model(ROOT)
    try:
        reports = [plan_one(batch, model=model, render=args.render, out_dir=args.out_dir) for batch in batches]
    except ValueError as exc:
        parser.error(str(exc))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    handoff = []
    for sentence in reports:
        for item in sentence["source_collision_handoff"]:
            if item not in handoff:
                handoff.append(item)
    payload = {"planner_protocol": "round3_endpoint_near_via1_via2_hub",
               "sentences": reports,
               "totals": {key: sum(s[key] for s in reports) for key in
                          ("transition_count", "pass_count", "source_collision_count", "failed_count")},
               "source_collision_handoff": handoff}
    args.report.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
