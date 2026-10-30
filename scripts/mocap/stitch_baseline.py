"""Baseline sentence playback from the word library (reference for Group 3).

    MUJOCO_GL=egl .venv/bin/python scripts/mocap/stitch_baseline.py YOU BUY BOOK [--render]

Each word is cut to its sign_frames and consecutive words are joined by a fixed
smoothstep blend; the sentence starts and ends at the shared neutral pose. This
is the simplest "direct playback" baseline, not the learned or tuned transition
that Group 3 is responsible for. Output: results/mocap_previews/sentence_<WORDS>.npz
(+ .mp4 with --render), same motion format as the word clips.
"""
from pathlib import Path
import argparse
import json
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sign_robot.motion import load_model, validate_motion

HOSPITAL = ROOT / "motions/hospital_v1_motions.json"
# Lookup order: the hospital map (mocap first, then video), then the full libraries.
LIBRARIES = [ROOT / "motions/studio_galt_v1/index.json", ROOT / "motions/wlasl_video_v1/index.json"]
OUT = ROOT / "results/mocap_previews"


def blend(a, b, seconds, fps):
    n = max(2, int(round(seconds * fps)))
    u = np.linspace(0, 1, n + 1)[1:-1, None]
    u = u * u * (3 - 2 * u)
    return a + u * (b - a)


def stitch(glosses, transition_s=0.5, spans=None):
    """spans, if given a list, receives (gloss, first_frame, last_frame) per word in the output."""
    words = {}
    if HOSPITAL.exists():
        words.update({g["gloss"]: g for g in json.loads(HOSPITAL.read_text())["glosses"] if g["motion_ready"]})
    for path in LIBRARIES:
        if path.exists():
            for w in json.loads(path.read_text())["words"]:
                if w["robot_status"] != "poor":
                    words.setdefault(w["gloss"], w)
    unknown = [g for g in glosses if g not in words]
    if unknown:
        raise SystemExit(f"Not in the library: {unknown}")
    fps = 30
    pieces, names = [], None
    for k, gloss in enumerate(glosses):
        w = words[gloss]
        with np.load(ROOT / w["motion"]) as clip:
            q, names = clip["positions"], clip["joint_names"]
        s0, s1 = w["sign_frames"]
        start = 0 if k == 0 else s0               # first word keeps its rise from neutral
        end = len(q) if k == len(glosses) - 1 else s1 + 1   # last word keeps its return
        segment = q[start:end]
        if pieces:
            pieces.append(blend(pieces[-1][-1], segment[0], transition_s, fps))
        if spans is not None:
            first = sum(len(p) for p in pieces)
            spans.append((gloss, first, first + len(segment) - 1))
        pieces.append(segment)
    q = np.vstack(pieces)
    return {"timestamps_s": np.arange(len(q)) / fps, "joint_names": names, "positions": q}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("glosses", nargs="+")
    parser.add_argument("--transition", type=float, default=0.5, help="blend seconds between words")
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    glosses = [g.upper() for g in args.glosses]
    motion = stitch(glosses, args.transition)
    validate_motion(motion)
    name = "sentence_" + "_".join(glosses)
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / f"{name}.npz", **motion)
    speed = np.abs(np.diff(motion["positions"], axis=0)).max() * 30
    print(f"{name}: {len(motion['timestamps_s'])} frames, {motion['timestamps_s'][-1]:.2f} s, max joint speed {speed:.1f} rad/s")
    if args.render:
        import mujoco
        import imageio.v2 as imageio
        from PIL import Image, ImageDraw
        sys.path.insert(0, str(ROOT / "scripts/mocap"))
        from render_comparison import camera
        from sign_robot.motion import apply_frame
        model = load_model()
        data = mujoco.MjData(model)
        with mujoco.Renderer(model, width=640, height=720) as renderer, \
                imageio.get_writer(OUT / f"{name}.mp4", fps=30, codec="libx264", quality=8, macro_block_size=16, pixelformat="yuv420p") as writer:
            for t, row in zip(motion["timestamps_s"], motion["positions"]):
                apply_frame(model, data, motion["joint_names"], row)
                renderer.update_scene(data, camera=camera(180))
                frame = Image.fromarray(renderer.render())
                ImageDraw.Draw(frame).text((14, 12), f"{' '.join(glosses)} | baseline stitching | {t:4.2f}s", fill=(255, 255, 255))
                writer.append_data(np.asarray(frame))
        print(f"wrote {OUT / (name + '.mp4')}")


if __name__ == "__main__":
    main()
