"""Recheck saved plans, measure YOU→BUY sag, optionally render a 2x2 comparison.

    .venv/bin/python scripts/plan_transitions.py --all
    MUJOCO_GL=egl .venv/bin/python scripts/evaluate_planned_transitions.py --render-comparison

The video is baseline on the top row and planned on the bottom, front/right-side
views in each row. Both play at the original 30 fps, without time warping; the
shorter sentence holds its last frame. Failed segments are explicitly labelled.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import platform

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from sign_robot.motion import apply_frame, load_model, validate_motion
from sign_robot.transitions import FPS, body_heights, joint_rate_limits, lookup_words

OUT = ROOT / "results/planned_transitions"
PREVIEWS = ROOT / "results/mocap_previews"


def read_motion(path):
    with np.load(path, allow_pickle=False) as data:
        motion = {k: data[k].copy() for k in ("timestamps_s", "joint_names", "positions")}
    validate_motion(motion)
    return motion


def artifact_path(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def load_report(path):
    return json.loads(path.read_text())


def verify_saved_sentence(report):
    """Independent saved-artifact check, including both transition endpoints."""
    path = artifact_path(report["output_npz"])
    motion = read_motion(path)
    q, names = motion["positions"], motion["joint_names"]
    assert len(q) == report["frames"]
    np.testing.assert_allclose(np.diff(motion["timestamps_s"]), 1 / FPS)
    words = lookup_words()
    peaks = {"arm_rad_s": 0.0, "finger_rad_s": 0.0}
    for segment in report["transitions"]:
        clip = q[segment["start_frame"]:segment["end_frame"] + 1]
        speed = np.abs(np.diff(clip, axis=0)) * FPS
        assert np.all(speed <= joint_rate_limits(names) + 1e-10)
        for limit, key in ((15, "arm_rad_s"), (10, "finger_rad_s")):
            peaks[key] = max(peaks[key], float(speed[:, joint_rate_limits(names) == limit].max(initial=0)))
        for index, gloss, bound in ((0, segment["from_gloss"], 1), (-1, segment["to_gloss"], 0)):
            with np.load(ROOT / words[gloss]["motion"], allow_pickle=False) as source:
                np.testing.assert_array_equal(names, source["joint_names"])
                np.testing.assert_array_equal(clip[index], source["positions"][words[gloss]["sign_frames"][bound]])
    return {"passed": True, "transition_peak_rates": peaks}


def measure_sag(model, sentence):
    """Separate undershoot below endpoints from descent inherited inside YOU."""
    baseline = read_motion(PREVIEWS / "sentence_YOU_BUY_BOOK.npz")
    planned = read_motion(artifact_path(sentence["output_npz"]))
    names = planned["joint_names"]
    np.testing.assert_array_equal(names, baseline["joint_names"])
    transition = sentence["transitions"][0]
    words = lookup_words()
    start = words["YOU"]["sign_frames"][1]
    # Baseline uses 0.5 s = 15 intervals; confirm against actual stored endpoint.
    baseline_end = start + 15
    source = read_motion(ROOT / words["BUY"]["motion"])
    boundary_difference = float(np.max(np.abs(baseline["positions"][baseline_end] -
                                      source["positions"][words["BUY"]["sign_frames"][0]])))
    # The archived baseline has ~1e-8 rad numerical differences from today's
    # word NPZ. Use the archive as-is; planned endpoints remain bit-exact above.
    np.testing.assert_allclose(baseline["positions"][baseline_end],
                               source["positions"][words["BUY"]["sign_frames"][0]], rtol=0, atol=1e-7)
    bodies = ("right_wrist_yaw_link", "right_elbow_link")
    result = {"glosses": ["YOU", "BUY"], "fps": FPS,
              "metric": "undershoot = max(0, min(start_z, end_z) - min(z)); includes boundary samples",
              "units": "metres", "baseline_interval": [start, baseline_end],
              "planned_interval": [transition["start_frame"], transition["end_frame"]],
              "planned_transition_status": transition["status"],
              "planned_used_via": transition["used_via"],
              "archived_baseline_buy_boundary_difference_rad": boundary_difference}
    for key, motion, a, b in (
            ("baseline", baseline, start, baseline_end),
            ("planned", planned, transition["start_frame"], transition["end_frame"])):
        heights = body_heights(model, names, motion["positions"][a:b + 1], bodies)
        result[key] = {"frames_including_endpoints": b - a + 1, "duration_s": (b - a) / FPS}
        for j, body in enumerate(bodies):
            z = heights[:, j]
            result[key][body] = {"start_z_m": float(z[0]), "end_z_m": float(z[-1]),
                                 "minimum_z_m": float(z.min()),
                                 "undershoot_below_lower_endpoint_m": float(max(0, min(z[0], z[-1]) - z.min())),
                                 "drop_from_start_m": float(max(0, z[0] - z.min())),
                                 "heights_m": z.tolist()}
    with np.load(ROOT / words["YOU"]["motion"], allow_pickle=False) as source:
        s0, s1 = words["YOU"]["sign_frames"]
        z = body_heights(model, names, source["positions"][s0:s1 + 1], bodies)
    result["inherited_source_descent"] = {
        "source_frames": [s0, s1],
        "note": "Same in baseline and planned: exact boundary and word-slice preservation prevents removing this descent.",
        **{body: {"peak_z_m": float(z[:, j].max()), "end_z_m": float(z[-1, j]),
                  "peak_to_end_drop_m": float(z[:, j].max() - z[-1, j])}
           for j, body in enumerate(bodies)}}
    # The task's sag fix must not be claimed if the emitted artifact regresses.
    assert result["planned"][bodies[0]]["undershoot_below_lower_endpoint_m"] < 1e-7
    return result


def _phase(report, index):
    for segment in report["transitions"]:
        if segment["start_frame"] <= index <= segment["end_frame"]:
            return f"{segment['from_gloss']} -> {segment['to_gloss']} [{segment['status']}]"
    for segment in report["word_segments"]:
        if segment["start_frame"] <= index <= segment["end_frame"]:
            return segment["gloss"]
    return "end hold"


def render_comparison(model, planned_report, destination):
    import imageio.v2 as imageio
    import mujoco
    from PIL import Image, ImageDraw
    sys.path.insert(0, str(ROOT / "scripts/mocap"))
    from render_comparison import camera

    baseline = read_motion(PREVIEWS / "sentence_YOU_HURT_WHERE.npz")
    planned = read_motion(artifact_path(planned_report["output_npz"]))
    data = mujoco.MjData(model)
    width, height = 480, 544  # Dimensions divisible by the encoder macroblock.
    cams = (camera(180), camera(90))
    destination.parent.mkdir(parents=True, exist_ok=True)
    n_frames = max(len(baseline["positions"]), len(planned["positions"]))
    with mujoco.Renderer(model, width=width, height=height) as renderer, imageio.get_writer(
            destination, fps=FPS, codec="libx264", quality=8, macro_block_size=16,
            pixelformat="yuv420p", ffmpeg_params=["-threads", "1"]) as writer:
        for i in range(n_frames):
            panel = Image.new("RGB", (2 * width, 2 * height))
            for row, (label, motion) in enumerate((("BASELINE", baseline), ("PLANNED", planned))):
                frame_index = min(i, len(motion["positions"]) - 1)
                apply_frame(model, data, motion["joint_names"], motion["positions"][frame_index])
                for col, cam in enumerate(cams):
                    renderer.update_scene(data, camera=cam)
                    frame = Image.fromarray(renderer.render())
                    draw = ImageDraw.Draw(frame)
                    draw.rectangle((0, 0, width, 60), fill=(18, 24, 32))
                    phase = _phase(planned_report, frame_index) if row else "fixed 0.5s smoothstep"
                    if i >= len(motion["positions"]):
                        phase = "end hold (no time warping)"
                    draw.text((12, 8), f"{label} | YOU HURT WHERE | {i / FPS:.2f}s", fill="white")
                    draw.text((12, 27), f"{'front' if col == 0 else 'right side'} | {phase}", fill="white")
                    draw.text((12, 44), "Kinematic candidate preview; ASL unreviewed", fill=(230, 208, 160))
                    panel.paste(frame, (col * width, row * height))
            writer.append_data(np.asarray(panel))
            if i % 30 == 0 or i == n_frames - 1:
                print(f"comparison render {i + 1}/{n_frames} frames", flush=True)
            if i == 100:
                panel.save(OUT / "you_hurt_where_comparison_frame.png")
    return {"path": str(destination.relative_to(ROOT)), "fps": FPS, "frames": n_frames,
            "duration_s": n_frames / FPS, "size": [2 * width, 2 * height],
            "layout": "baseline top, planned bottom; front left, right-side right; shorter row holds its end"}


def write_tables(reports):
    head = "| Sentence | Transitions | Pass | Failed | Planned s | Baseline s | Difference s |"
    lines = [head, "|---|---:|---:|---:|---:|---:|---:|"]
    for report in reports:
        lines.append(f"| {' '.join(report['glosses'])} | {report['transition_count']} | "
                     f"{report['pass_count']} | {report['failed_count']} | {report['duration_s']:.3f} | "
                     f"{report['baseline']['duration_s']:.3f} | {report['duration_vs_baseline_s']:+.3f} |")
    table = "\n".join(lines)
    failed = [t for report in reports for t in report["transitions"] if t["status"] == "FAILED"]
    detail = "\n\n".join(f"- **{t['from_gloss']} → {t['to_gloss']}: FAILED** — " + "; ".join(t["reasons"])
                           for t in failed)
    chinese_detail = (detail.replace(": FAILED", ": 失败").replace("penetration", "穿透")
                      .replace("sample", "采样帧").replace("start_endpoint", "起点")
                      .replace("end_endpoint", "终点").replace("interior", "内部"))
    chinese_table = table.replace(head, "| 句子 | 过渡数 | 通过 | 失败 | 规划秒数 | 基线秒数 | 秒数差 |")
    (OUT / "report.en.md").write_text(
        "# Transition results\n\n[中文](report.md) · **English**\n\n"
        "Duration is frame count / 30, including the final displayed frame. "
        "Pass/fail counts cover inserted transitions only; singleton sentences have zero checks. "
        "See the [protocol, commands and limitations](../../docs/transition-planner.en.md).\n\n" +
        table + "\n\nFailure details (raw collision body names):\n\n" + detail + "\n")
    (OUT / "report.md").write_text(
        "# 衔接规划结果\n\n**中文** · [English](report.en.md)\n\n"
        "时长按帧数 / 30 计算，包含最后一帧显示时间。通过/失败只统计插入的过渡；"
        "单词句没有过渡检查。详见[协议、启动命令与限制](../../docs/transition-planner.md)。\n\n" +
        chinese_table + "\n\n失败详情（碰撞体名称保留原始标识；采样帧按过渡内位置编号）：\n\n" + chinese_detail + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=OUT / "report.json")
    parser.add_argument("--render-comparison", action="store_true")
    parser.add_argument("--copy-to", type=Path, default=Path("/workspace/you_hurt_where_baseline_vs_planned.mp4"))
    args = parser.parse_args(argv)
    report = load_report(args.report)
    for sentence in report["sentences"]:
        sentence["artifact_verification"] = verify_saved_sentence(sentence)
    model = load_model(ROOT)
    sag_sentence = next(s for s in report["sentences"] if s["glosses"] == ["YOU", "BUY", "BOOK"])
    sag = measure_sag(model, sag_sentence)
    (OUT / "you_buy_sag.json").write_text(json.dumps(sag, indent=2) + "\n")
    if args.render_comparison:
        sentence = next(s for s in report["sentences"] if s["glosses"] == ["YOU", "HURT", "WHERE"])
        video = render_comparison(model, sentence, OUT / "you_hurt_where_baseline_vs_planned.mp4")
        shutil.copy2(artifact_path(video["path"]), args.copy_to)
        video["copy"] = str(args.copy_to)
        report["comparison_video"] = video
    report["you_buy_sag"] = str((OUT / "you_buy_sag.json").relative_to(ROOT))
    inputs = {segment["motion"] for sentence in report["sentences"] for segment in sentence["word_segments"]}
    inputs.update(sentence["baseline"]["path"] for sentence in report["sentences"])
    inputs.update(("assets/robot/scene.xml", "motions/hospital_v1_motions.json",
                   "assets/robot/upstream_manifest.json", "assets/robot/model_info.json",
                   "motions/studio_galt_v1/index.json", "motions/wlasl_video_v1/index.json"))
    report["input_sha256"] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                              for name in sorted(inputs)}
    import mujoco
    report["runtime_versions"] = {"python": platform.python_version(), "numpy": np.__version__,
                                  "mujoco": mujoco.__version__}
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    write_tables(report["sentences"])
    print(f"saved {OUT / 'you_buy_sag.json'} and report tables; all saved endpoints/rates verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
