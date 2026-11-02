"""End-to-end hospital demo: English sentence -> ASL gloss (Group 1) -> G1 motion (Group 2) -> playback.

    MUJOCO_GL=egl .venv/bin/python scripts/demo/hospital_demo.py --line s4 --render   # one scripted line
    MUJOCO_GL=egl .venv/bin/python scripts/demo/hospital_demo.py --all --render       # all 9 scripted lines
    MUJOCO_GL=egl .venv/bin/python scripts/demo/hospital_demo.py --acts               # plus one video per demo act
    .venv/bin/python scripts/demo/hospital_demo.py "Where does it hurt?" --view       # interactive viewer (macOS: .venv/bin/mjpython)
    .venv/bin/python scripts/demo/hospital_demo.py "Where is the pain?" --live        # call Group 1's Gemini module

Glosses come from Group 1's offline cache of the 9 scripted lines by default, so
the demo needs no network or API key. --live runs group1_text_to_gloss in a
subprocess (its package also is named sign_robot) with demo_only, so every gloss
it accepts has a motion; if the API fails, a cached line is used and labelled as
such, otherwise nothing is played. Words are joined by Group 3's planned
transitions (round 8, results/hospital_sentences_20261102_008) when the sentence
was planned, with the first word's own rise from neutral in front; otherwise, and
with --transitions baseline, by scripts/mocap/stitch_baseline.py.
Output: results/demo/<name>.npz, .json and (with --render) .mp4 with captions;
baseline outputs go to results/demo/baseline/ (the reference of compare_stitching.py).
"""
from pathlib import Path
import argparse
import json
import re
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts/mocap"))
from sign_robot.motion import apply_frame, load_model, validate_motion
from stitch_baseline import HOSPITAL, stitch

GROUP1 = ROOT / "group1_text_to_gloss"
CACHE = GROUP1 / "data/offline/hospital_dialogue_gloss.json"
OUT = ROOT / "results/demo"
PLANNED = ROOT / "results/hospital_sentences_20261102_008/render_inputs"  # Group 3, round 8
FPS = 30
LABELS = {"group3": "Group 3 planned transitions", "baseline": "baseline stitching"}
# The four acts of the demo slides (13-16): one patient's visit from registration to discharge.
ACTS = {"act1_registration": ["s1", "s2"], "act2_consultation": ["s3", "s4", "s5"],
        "act3_treatment": ["s6", "s7"], "act4_discharge": ["s8", "s9"]}


def normalize(sentence):
    return re.sub(r"[^a-z0-9]+", " ", sentence.lower()).strip()


def cached_lines():
    return json.loads(CACHE.read_text())["lines"]


def from_cache(key):
    for line in cached_lines():
        if key.lower() == line["id"] or normalize(key) == normalize(line["sentence"]):
            return {"id": line["id"], "sentence": line["sentence"], "glosses": line["glosses"],
                    "question": line["question"], "gloss_source": "offline_cache"}
    return None


def live(sentence):
    """Group 1's text_to_gloss(sentence, demo_only=True) as a subprocess; returns its JSON result."""
    proc = subprocess.run([sys.executable, str(GROUP1 / "scripts/translate.py"), sentence, "--demo-only"],
                          cwd=GROUP1, capture_output=True, text=True, timeout=120)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        tail = (proc.stderr.strip().splitlines() or ["no output"])[-1]
        return {"status": "error", "reason": tail}


def resolve(key, use_live):
    if not use_live:
        line = from_cache(key)
        if line is None:
            raise SystemExit(f"Not in the offline cache: {key!r}. Cached lines: "
                             + ", ".join(l["id"] for l in cached_lines()) + ". Use --live to call Group 1's model.")
        return line
    result = live(key)
    if result.get("status") == "ok":
        return {"id": None, "sentence": key, "glosses": result["glosses"], "question": result.get("question"),
                "gloss_source": "live_gemini", "latency_ms": result.get("latency_ms")}
    if result.get("status") == "unsupported":
        raise SystemExit(f"Group 1 rejected the sentence (unsupported; unknown={result.get('unknown')}); nothing is played.")
    line = from_cache(key)
    if line is None:
        raise SystemExit(f"Group 1 model unavailable ({result.get('reason')}) and the sentence is not cached; nothing is played.")
    print(f"Group 1 model unavailable ({result.get('reason')}); using the offline cache for {line['id']}.")
    line["gloss_source"] = "offline_cache_after_live_failure"
    return line


def name_for(line):
    return line["id"] or "sentence_" + "_".join(line["glosses"])


def planned(glosses, spans):
    """Group 3's planned sentence with the first word's rise from neutral in front, or None if not planned.

    Planned sentences start at the first word's protected core; that frame is taken from the
    word clip itself, so the clip's own frames up to it join without a jump."""
    folder = PLANNED / "__".join(glosses)
    if not (folder / "replay.npz").exists():
        return None
    with np.load(folder / "replay.npz") as f:
        motion = {k: f[k] for k in ("timestamps_s", "joint_names", "positions")}
    first = next(g for g in json.loads(HOSPITAL.read_text())["glosses"] if g["gloss"] == glosses[0])
    with np.load(ROOT / first["motion"]) as clip:
        assert [str(n) for n in clip["joint_names"]] == [str(n) for n in motion["joint_names"]]
        rise = clip["positions"]
    q = motion["positions"]
    k = int(np.abs(rise - q[0]).max(axis=1).argmin())
    if np.abs(rise[k] - q[0]).max() > 1e-6:
        raise ValueError(f"{folder.name}: first frame is not a frame of the {glosses[0]} clip")
    q = np.vstack([rise[:k], q])
    plan = json.loads((folder / "render_plan.json").read_text())
    starts = [0] + [c["replay_frames"][0] + k for c in plan["protected_instance_video_checks"][1:]] + [len(q)]
    spans += [(g, a, b - 1) for g, a, b in zip(glosses, starts, starts[1:])]
    return {"timestamps_s": np.arange(len(q)) / FPS, "joint_names": motion["joint_names"], "positions": q}


def build(line, transition_s, transitions="group3"):
    spans = []
    motion = planned(line["glosses"], spans) if transitions == "group3" else None
    method = "group3" if motion is not None else "baseline"
    if motion is None:
        motion = stitch(line["glosses"], transition_s, spans)
    validate_motion(motion)
    library = {g["gloss"]: g.get("library") for g in json.loads(HOSPITAL.read_text())["glosses"]}
    out = OUT if transitions == "group3" else OUT / "baseline"
    out.mkdir(parents=True, exist_ok=True)
    name = name_for(line)
    np.savez_compressed(out / f"{name}.npz", **motion)
    stitching = {"group3": "Group 3 round 8 planned transitions (results/hospital_sentences_20261102_008), first word's rise prepended",
                 "baseline": "baseline: sign_frames cut + fixed smoothstep blend (scripts/mocap/stitch_baseline.py)"}[method]
    meta = dict(line, stitching=stitching, stitching_label=LABELS[method],
                transition_s=transition_s, frames=len(motion["timestamps_s"]),
                duration_s=round(float(motion["timestamps_s"][-1]), 3),
                words=[{"gloss": g, "frames": [a, b], "library": library.get(g)} for g, a, b in spans],
                note="Candidate robot signing, not reviewed by ASL users; video-derived words are approximate.")
    (out / f"{name}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    return motion, meta


def current_word(meta, frame):
    for k, word in enumerate(meta["words"]):
        if frame <= word["frames"][1]:
            return k
    return len(meta["words"]) - 1


def render(motion, meta, out):
    import mujoco
    import imageio.v2 as imageio
    from PIL import Image, ImageDraw, ImageFont
    from render_comparison import camera
    model = load_model()
    data = mujoco.MjData(model)
    big, small = ImageFont.load_default(26), ImageFont.load_default(18)
    with mujoco.Renderer(model, width=960, height=720) as renderer, \
            imageio.get_writer(out, fps=FPS, codec="libx264", quality=8, macro_block_size=16, pixelformat="yuv420p") as writer:
        for frame, row in enumerate(motion["positions"]):
            apply_frame(model, data, motion["joint_names"], row)
            renderer.update_scene(data, camera=camera(180))
            image = Image.fromarray(renderer.render())
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, 0, 960, 52), fill=(20, 20, 20))
            draw.text((16, 12), meta["sentence"], font=big, fill=(255, 255, 255))
            draw.rectangle((0, 660, 960, 720), fill=(20, 20, 20))
            x, active = 16, current_word(meta, frame)
            for k, word in enumerate(meta["words"]):
                draw.text((x, 676), word["gloss"], font=big, fill=(255, 210, 60) if k == active else (150, 150, 150))
                x += draw.textlength(word["gloss"], font=big) + 22
            draw.text((16, 60), f"gloss: {meta['gloss_source']} | {meta['stitching_label']} | not ASL-reviewed",
                      font=small, fill=(230, 230, 230))
            writer.append_data(np.asarray(image))


def view(motion):
    import time
    import mujoco
    import mujoco.viewer
    model = load_model()
    data = mujoco.MjData(model)
    with mujoco.viewer.launch_passive(model, data) as viewer:
        viewer.cam.lookat[:] = [0.06, 0, 1.09]
        viewer.cam.distance, viewer.cam.azimuth, viewer.cam.elevation = 1.25, 180, -4
        start = time.monotonic()
        while viewer.is_running():
            frame = int((time.monotonic() - start) * FPS)
            if frame >= len(motion["positions"]):
                break
            with viewer.lock():
                apply_frame(model, data, motion["joint_names"], motion["positions"][frame])
            viewer.sync()
            time.sleep(1 / 60)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("sentence", nargs="?", help="English sentence (cached line, or any sentence with --live)")
    which.add_argument("--line", help="scripted line id, e.g. s4")
    which.add_argument("--all", action="store_true", help="all scripted lines in the offline cache")
    which.add_argument("--acts", action="store_true", help="all lines plus one video per demo act (implies --render)")
    parser.add_argument("--live", action="store_true", help="call Group 1's Gemini module (needs network and group1_text_to_gloss/.env)")
    parser.add_argument("--transitions", choices=["group3", "baseline"], default="group3",
                        help="Group 3's planned transitions where available (default), or the baseline stitching")
    parser.add_argument("--transition", type=float, default=0.5, help="baseline blend seconds between words")
    parser.add_argument("--render", action="store_true", help="write a captioned .mp4")
    parser.add_argument("--view", action="store_true", help="play in the interactive MuJoCo viewer")
    args = parser.parse_args()
    args.render = args.render or args.acts
    batch = args.all or args.acts
    keys = [l["id"] for l in cached_lines()] if batch else [args.line or args.sentence]
    out = OUT if args.transitions == "group3" else OUT / "baseline"
    for key in keys:
        line = resolve(key, args.live and not batch)
        motion, meta = build(line, args.transition, args.transitions)
        name = name_for(line)
        print(f"{name}: {meta['sentence']!r} -> {' '.join(line['glosses'])} [{line['gloss_source']}; {meta['stitching_label']}], "
              f"{meta['frames']} frames, {meta['duration_s']:.1f} s -> {out / name}.npz")
        if args.render:
            render(motion, meta, out / f"{name}.mp4")
            print(f"  wrote {out / name}.mp4")
        if args.view:
            view(motion)
    if batch and args.render:
        concat([out / f"{key}.mp4" for key in keys], out / "hospital_dialogue.mp4")
        print(f"wrote {out / 'hospital_dialogue.mp4'}")
    if args.acts:
        for act, ids in ACTS.items():
            concat([out / f"{key}.mp4" for key in ids], out / f"{act}.mp4")
            print(f"wrote {out / act}.mp4 ({', '.join(ids)})")


def concat(paths, out, gap_s=1.0):
    """All scripted lines back to back, with a short hold on each line's last frame."""
    import imageio.v2 as imageio
    with imageio.get_writer(out, fps=FPS, codec="libx264", quality=8, macro_block_size=16, pixelformat="yuv420p") as writer:
        for path in paths:
            with imageio.get_reader(path) as reader:
                for frame in reader:
                    writer.append_data(frame)
            for _ in range(int(gap_s * FPS)):
                writer.append_data(frame)


if __name__ == "__main__":
    main()
