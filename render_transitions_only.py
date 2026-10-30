"""Render saved R13 transitions only; never run verification or planning.

Run / 运行 (PowerShell):
  & 'C:\\Users\\23971\\Documents\\5412\\me5412-sign-robot\\.venv\\Scripts\\python.exe' -B .\\render_transitions_only.py

The default output is C:\\Users\\23971\\grokbot_exports\\r13_transitions.
Use --compile-only to rebuild index.txt and the title-card compilation from
existing clips. Source reports, motions, and repository files are read only.
默认逐段渲染并生成索引及带标题卡的合集；--compile-only 仅重建索引和合集。
只读取既有报告与动作，不校验碰撞、不重新规划、不修改既有项目文件。
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

# Keep imported project helpers from creating __pycache__ files in the worktree.
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts/mocap"))

import evaluate_planned_transitions as e
from render_comparison import camera
from stitch_baseline import blend, stitch
import imageio.v2 as imageio
import imageio_ffmpeg
import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

DEFAULT_REPORT = ROOT / "results/planned_transitions/round13b/report.json"
DEFAULT_OUTPUT = Path(r"C:\Users\23971\grokbot_exports\r13_transitions")
WIDTH, HEIGHT = 480, 544  # Same panel dimensions as render_comparison_batch.
PAD_FRAMES = int(round(0.5 * e.FPS))
TRANSITION_SECONDS = 0.5


@dataclass
class Window:
    motion: dict
    start: int
    end: int
    transition_start: int
    transition_end: int

    @property
    def frames(self):
        return self.end - self.start + 1

    def phase(self, local_frame):
        if local_frame >= self.frames:
            return "end hold"
        index = self.start + local_frame
        if index < self.transition_start:
            return "outgoing word"
        if index > self.transition_end:
            return "incoming word"
        return "transition"


@dataclass
class Clip:
    sentence: int
    order: int
    transition: dict
    baseline: Window
    planned: Window

    @property
    def pair(self):
        return f"{self.transition['from_gloss']}\u2192{self.transition['to_gloss']}"

    @property
    def filename(self):
        return (f"s{self.sentence:02d}_t{self.order}_"
                f"{self.transition['from_gloss']}-{self.transition['to_gloss']}.mp4")

    @property
    def frames(self):
        return max(self.baseline.frames, self.planned.frames)


def clearance_mm(transition):
    """Preserve the report's display cap and units; do not recompute metrics."""
    if transition.get("min_clearance_mm_display") is not None:
        return str(transition["min_clearance_mm_display"])
    if transition.get("min_clearance_m") is not None:
        return e.format_clearance_mm(transition["min_clearance_m"])
    return e.format_clearance_mm(transition["min_clearance_mm"] / 1000)


def baseline_with_segments(glosses, words, sources):
    """Use the real stitch output and reconstruct its library-slice offsets."""
    motion = stitch(glosses, transition_s=TRANSITION_SECONDS)
    segments, cursor, previous_end = [], 0, None
    for k, gloss in enumerate(glosses):
        word = words[gloss]
        if gloss not in sources:
            sources[gloss] = e.read_motion(e.artifact_path(word["motion"]))
        source = sources[gloss]
        if not np.array_equal(source["joint_names"], motion["joint_names"]):
            raise ValueError(f"{gloss}: inconsistent baseline joint names")
        q = source["positions"]
        first = 0 if k == 0 else int(word["sign_frames"][0])
        last = len(q) - 1 if k == len(glosses) - 1 else int(word["sign_frames"][1])
        if k:
            # blend() contains interior frames only; endpoints belong to words.
            cursor += len(blend(previous_end, q[first], TRANSITION_SECONDS, e.FPS))
        segments.append({"gloss": gloss, "start_frame": cursor,
                         "end_frame": cursor + last - first})
        cursor += last - first + 1
        previous_end = q[last]
    if cursor != len(motion["positions"]):
        raise ValueError("Reconstructed baseline offsets do not match stitch()")
    return motion, segments


def prepare_clips(report):
    words, sources, clips = e.lookup_words(), {}, []
    for si, sentence in enumerate(report["sentences"], 1):
        if not sentence["transitions"]:
            continue
        glosses = sentence["glosses"]
        if len(sentence["transitions"]) != len(glosses) - 1:
            raise ValueError(f"Sentence {si}: transition count does not match words")
        planned = e.read_motion(e.artifact_path(sentence["output_npz"]))
        baseline, baseline_segments = baseline_with_segments(glosses, words, sources)
        if len(baseline["positions"]) != sentence["baseline"]["frames"]:
            raise ValueError(f"Sentence {si}: baseline length changed")
        if len(planned["positions"]) != sentence["frames"]:
            raise ValueError(f"Sentence {si}: saved planned length changed")
        planned_segments = sentence["word_segments"]
        if len(planned_segments) != len(glosses):
            raise ValueError(f"Sentence {si}: word segment count does not match words")
        # Saved word_segments already encode the report's planned-side trims.
        # Check their integer coordinates with that report's explicit policy;
        # never re-trim a saved trajectory or use today's default overrides.
        for k, segment in enumerate(planned_segments):
            word = words[glosses[k]]
            source_start = (0 if k == 0 else e.target_start_frame(
                word, overrides=sentence.get("target_start_frame_overrides", {})))
            source_end = (len(sources[glosses[k]]["positions"]) - 1
                          if k == len(glosses) - 1 else e.source_end_frame(
                              word, overrides=sentence.get("source_end_frame_overrides", {})))
            if (segment["gloss"] != glosses[k] or
                    (segment["source_start_frame"], segment["source_end_frame"]) !=
                    (source_start, source_end)):
                raise ValueError(f"Sentence {si}: saved word bounds disagree with its trim policy")
        for k, transition in enumerate(sentence["transitions"]):
            if (transition["from_gloss"], transition["to_gloss"]) != tuple(glosses[k:k + 2]):
                raise ValueError(f"Sentence {si}: transition order does not match words")
            p0, p1 = int(transition["start_frame"]), int(transition["end_frame"])
            if (p0, p1) != (planned_segments[k]["end_frame"],
                            planned_segments[k + 1]["start_frame"]):
                raise ValueError(f"Sentence {si}: saved transition/word endpoints disagree")
            b0, b1 = baseline_segments[k]["end_frame"], baseline_segments[k + 1]["start_frame"]
            # Share the outgoing padding length so transition starts line up.
            lead = min(PAD_FRAMES, p0 - planned_segments[k]["start_frame"],
                       b0 - baseline_segments[k]["start_frame"])
            pw = Window(planned, p0 - lead,
                        min(p1 + PAD_FRAMES, planned_segments[k + 1]["end_frame"]), p0, p1)
            bw = Window(baseline, b0 - lead,
                        min(b1 + PAD_FRAMES, baseline_segments[k + 1]["end_frame"]), b0, b1)
            if not (0 <= pw.start <= p0 < p1 <= pw.end < len(planned["positions"]) and
                    0 <= bw.start <= b0 < b1 <= bw.end < len(baseline["positions"])):
                raise ValueError(f"Sentence {si}: invalid transition window")
            clips.append(Clip(si, k + 1, transition, bw, pw))
    if not clips:
        raise ValueError("Report has no transitions to render")
    return clips


def font(size, bold=False):
    fonts = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    for name in (("segoeuib.ttf", "arialbd.ttf") if bold else ("segoeui.ttf", "arial.ttf")):
        try:
            return ImageFont.truetype(str(fonts / name), size)
        except OSError:
            pass
    return ImageFont.truetype("DejaVuSans.ttf", size)


def video_writer(path):
    return imageio.get_writer(
        str(path), fps=e.FPS, codec="libx264", quality=8, macro_block_size=16,
        pixelformat="yuv420p", ffmpeg_log_level="error",
        ffmpeg_params=["-threads", "1", "-movflags", "+faststart"])


def render_frame_pair(model, data, renderer, cameras, clip, local_frame, fonts):
    """Small adaptation of the existing batch render loop with custom labels."""
    panel = Image.new("RGB", (2 * WIDTH, 2 * HEIGHT))
    transition = clip.transition
    rates = transition["peak_rates"]
    for row, (label, window) in enumerate((("BASELINE", clip.baseline), ("PLANNED", clip.planned))):
        frame_index = window.start + min(local_frame, window.frames - 1)
        e.apply_frame(model, data, window.motion["joint_names"],
                      window.motion["positions"][frame_index])
        for col, cam in enumerate(cameras):
            renderer.update_scene(data, camera=cam)
            frame = Image.fromarray(renderer.render())
            draw = ImageDraw.Draw(frame)
            draw.rectangle((0, 0, WIDTH, 136), fill=(18, 24, 32))
            view = "front" if col == 0 else "right side"
            lines = [
                f"{label} | {view} | s{clip.sentence:02d} t{clip.order} | {local_frame / e.FPS:.2f}s",
                clip.pair,
                f"Planner method: {transition['method']} | {transition.get('status', '')}",
                f"Planner min clearance: {clearance_mm(transition)} mm",
                f"Planner peak arm: {rates['arm_rad_s']:.3f} rad/s",
                f"Planner peak finger: {rates['finger_rad_s']:.3f} rad/s",
                ("fixed 0.5s smoothstep" if row == 0 else "saved planned path") +
                f" | {window.phase(local_frame)}",
            ]
            for line_index, text in enumerate(lines):
                draw.text((12, 5 + 18 * line_index), text,
                          font=fonts[1 if line_index == 1 else 0], fill="white")
            draw.rectangle((0, HEIGHT - 25, WIDTH, HEIGHT), fill=(18, 24, 32))
            draw.text((12, HEIGHT - 23), "Kinematic candidate preview; ASL unreviewed",
                      font=fonts[0], fill=(230, 208, 160))
            panel.paste(frame, (col * WIDTH, row * HEIGHT))
    return np.asarray(panel)


def render_clips(clips, out):
    model = e.load_model(e.ROOT)
    data = mujoco.MjData(model)
    cameras = (camera(180), camera(90))
    fonts = (font(14), font(16, bold=True))
    with mujoco.Renderer(model, width=WIDTH, height=HEIGHT) as renderer:
        # This reports the active GPU/context instead of assuming a GL backend.
        from OpenGL import GL
        print("OpenGL renderer:", GL.glGetString(GL.GL_RENDERER), flush=True)
        print("OpenGL vendor:", GL.glGetString(GL.GL_VENDOR), flush=True)
        for number, clip in enumerate(clips, 1):
            print(f"[{number}/{len(clips)}] {clip.filename}: {clip.frames} frames; "
                  f"baseline={clip.baseline.frames}, planned={clip.planned.frames}; "
                  f"method={clip.transition['method']}", flush=True)
            with video_writer(out / clip.filename) as writer:
                for i in range(clip.frames):
                    writer.append_data(render_frame_pair(model, data, renderer, cameras, clip, i, fonts))
                    if (i + 1) % e.FPS == 0 or i == clip.frames - 1:
                        print(f"  {i + 1}/{clip.frames} frames", flush=True)


def write_index(clips, out, report_path):
    lines = [f"# Source report: {report_path}",
             "# 30 fps; baseline top, planned bottom; front left, right side right.",
             "# Metrics describe the saved PLANNED transition, including on baseline panels.",
             "# Both transitions start together; shorter row holds its last frame; no time warping.",
             "# Source windows are sentence-local, zero-based, inclusive; baseline is reconstructed stitch().",
             "# Kinematic candidate previews; ASL unreviewed. No clearance/rate recomputation.",
             "filename\tsentence_index\tfrom_to\tframes\tduration_s\tmethod\tmin_clearance_mm"
             "\tpeak_arm_rad_s\tpeak_finger_rad_s\tbaseline_frames\tplanned_frames"
             "\tbaseline_source_window\tplanned_source_window"]
    for clip in clips:
        t = clip.transition
        values = (clip.filename, clip.sentence, clip.pair, clip.frames,
                  f"{clip.frames / e.FPS:.6f}", t["method"], clearance_mm(t),
                  t["peak_rates"]["arm_rad_s"], t["peak_rates"]["finger_rad_s"],
                  clip.baseline.frames, clip.planned.frames,
                  f"{clip.baseline.start}:{clip.baseline.end}",
                  f"{clip.planned.start}:{clip.planned.end}")
        lines.append("\t".join(map(str, values)))
    path = out / "index.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def title_card(clip, number, count):
    image = Image.new("RGB", (2 * WIDTH, 2 * HEIGHT), (18, 24, 32))
    draw = ImageDraw.Draw(image)
    t = clip.transition
    lines = [
        (f"R13 TRANSITION {number:02d} / {count}", 26, (140, 185, 225)),
        (clip.pair, 42, "white"),
        (f"Sentence {clip.sentence:02d}  |  Transition {clip.order}", 26, "white"),
        (f"Planner method: {t['method']}", 30, "white"),
        (f"Minimum clearance: {clearance_mm(t)} mm", 28, "white"),
        (f"Peak arm: {t['peak_rates']['arm_rad_s']:.3f} rad/s", 28, "white"),
        (f"Peak finger: {t['peak_rates']['finger_rad_s']:.3f} rad/s", 28, "white"),
        (f"Saved planner status: {t.get('status', '')}", 24, (230, 208, 160)),
        ("BASELINE top  |  PLANNED bottom", 24, (180, 200, 220)),
        ("Front left  |  Right side right", 24, (180, 200, 220)),
        ("Kinematic candidate preview; ASL unreviewed", 22, (230, 208, 160)),
    ]
    y = 130
    for text, size, colour in lines:
        face = font(size, bold=size == 42)
        while draw.textbbox((0, 0), text, font=face)[2] > image.width - 80:
            size -= 1
            face = font(size, bold=False)
        draw.text((40, y), text, font=face, fill=colour)
        y += size + 25
    return np.asarray(image)


def compile_clips(clips, out, ffmpeg):
    destination = out / "r13_all_transitions.mp4"
    # Cards and the concat list are temporary and stay outside the repository.
    with tempfile.TemporaryDirectory(prefix="_title_cards_", dir=out) as tmp:
        temp = Path(tmp)
        parts = []
        for number, clip in enumerate(clips, 1):
            print(f"Title card {number}/{len(clips)}: {clip.pair}", flush=True)
            card = temp / f"title_{number:02d}.mp4"
            frame = title_card(clip, number, len(clips))
            with video_writer(card) as writer:
                for _ in range(int(e.FPS)):
                    writer.append_data(frame)
            parts.extend((card, out / clip.filename))
        manifest = temp / "concat.txt"
        manifest.write_text("".join(
            "file '" + path.resolve().as_posix().replace("'", "'\\''") + "'\n"
            for path in parts), encoding="utf-8")
        print(f"Concatenating {len(clips)} clips with 1-second title cards...", flush=True)
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                        "-f", "concat", "-safe", "0", "-i", str(manifest),
                        "-map", "0:v:0", "-an", "-c:v", "copy", "-movflags", "+faststart",
                        str(destination)], check=True)
    return destination


def verify_clips(clips, out):
    expected = {clip.filename for clip in clips}
    actual = {p.name for p in out.glob("s[0-9][0-9]_t*_*.mp4")}
    if actual != expected:
        raise RuntimeError(f"Clip list mismatch: missing={expected - actual}, extra={actual - expected}")
    if any((out / name).stat().st_size == 0 for name in expected):
        raise RuntimeError("One or more rendered clips are empty")
    first = clips[0]
    with imageio.get_reader(str(out / first.filename)) as reader:
        frame = reader.get_data(0)
        count = reader.count_frames()
    if frame.shape[:2] != (2 * HEIGHT, 2 * WIDTH) or count != first.frames:
        raise RuntimeError(f"First clip has unexpected size or frame count: {frame.shape}, {count}")
    print(f"Verified {len(clips)} non-empty clips; first clip decodes with {count} frames.", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--compile-only", action="store_true",
                        help="Reuse existing transition clips; rebuild index and title-card compilation")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    report = e.load_report(args.report.resolve())
    clips = prepare_clips(report)
    print(f"Loaded {len(report['sentences'])} sentences / {len(clips)} transitions; ffmpeg={ffmpeg}", flush=True)
    if not args.compile_only:
        render_clips(clips, out)
    verify_clips(clips, out)
    index = write_index(clips, out, args.report.resolve())
    compilation = compile_clips(clips, out, ffmpeg)
    if not compilation.is_file() or not compilation.stat().st_size:
        raise RuntimeError("Compilation was not written")
    print(f"DONE: {len(clips)} clips + compilation in {time.monotonic() - started:.1f}s", flush=True)
    for path in [*(out / clip.filename for clip in clips), index, compilation]:
        print(f"{path}\t{path.stat().st_size:,} bytes", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
