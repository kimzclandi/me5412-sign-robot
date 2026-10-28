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
from sign_robot.transitions import (ENDPOINT_NEAR_M, FPS, MIN_LEG_DURATION_S,
                                    PENETRATION_TOLERANCE_M, MujocoClearance, body_heights,
                                    joint_rate_limits, lookup_words)

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


def verify_saved_sentence(report, model):
    """Recheck saved samples/endpoints; this is a developer check, not a held-out test."""
    path = artifact_path(report["output_npz"])
    motion = read_motion(path)
    q, names = motion["positions"], motion["joint_names"]
    assert len(q) == report["frames"]
    np.testing.assert_allclose(np.diff(motion["timestamps_s"]), 1 / FPS)
    words = lookup_words()
    clearance = MujocoClearance(model, names)
    peaks = {"arm_rad_s": 0.0, "finger_rad_s": 0.0}
    for segment in report["transitions"]:
        clip = q[segment["start_frame"]:segment["end_frame"] + 1]
        chosen = segment["attempts"][segment["selected_attempt"]]
        assert all(n / FPS >= MIN_LEG_DURATION_S for n in chosen["leg_intervals"])
        assert sum(chosen["leg_intervals"]) == len(clip) - 1
        speed = np.abs(np.diff(clip, axis=0)) * FPS
        assert np.all(speed <= joint_rate_limits(names) + 1e-10)
        for limit, key in ((15, "arm_rad_s"), (10, "finger_rad_s")):
            peaks[key] = max(peaks[key], float(speed[:, joint_rate_limits(names) == limit].max(initial=0)))
        for index, gloss, bound in ((0, segment["from_gloss"], 1), (-1, segment["to_gloss"], 0)):
            with np.load(ROOT / words[gloss]["motion"], allow_pickle=False) as source:
                np.testing.assert_array_equal(names, source["joint_names"])
                np.testing.assert_array_equal(clip[index], source["positions"][words[gloss]["sign_frames"][bound]])
        result = clearance(clip)
        endpoints = [clearance(clip[[i]]).min_distance_m for i in (0, -1)]
        floor = min((d for d in endpoints if d is not None), default=None)
        if floor is not None and floor < ENDPOINT_NEAR_M:
            status = "source_collision"
            assert segment["method"] == "source_collision"
            assert not segment["used_via"] and len(segment["attempts"]) == 1
        else:
            status = "PASS" if result.passed else "FAILED"
            assert segment["method"] == ("FAILED" if status == "FAILED" else chosen["kind"])
        hard_floor = floor if floor is not None and floor < -PENETRATION_TOLERANCE_M else None
        assert segment["endpoint_floor_m"] == hard_floor
        relative_ok = (None if hard_floor is None else
                       result.min_distance_m is not None and result.min_distance_m >= hard_floor)
        assert segment["relative_floor_passed"] == relative_ok
        if chosen["kind"] == "hub":
            assert len(chosen["leg_clearance"]) == 2
            offset = 0
            for intervals, saved in zip(chosen["leg_intervals"], chosen["leg_clearance"]):
                leg = clearance(clip[offset:offset + intervals + 1])
                assert leg.passed == saved["passed"]
                assert leg.min_distance_m == saved["min_distance_m"]
                if status == "PASS":
                    assert leg.passed
                offset += intervals
        if chosen["kind"] == "via2":
            assert len(chosen["leg_intervals"]) == 3 and len(chosen["via_directions"]) == 2
        assert status == segment["status"]
        assert result.min_distance_m == segment["clearance"]["min_distance_m"]
        assert segment["min_clearance_mm"] == (None if result.min_distance_m is None else
                                               result.min_distance_m * 1000)
    return {"passed": True, "checks": "saved endpoints, rates, per-leg durations, endpoint gate, whole-path and hub-leg collision classification; source_collision is diagnostic only",
            "transition_peak_rates": peaks}


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
              "planned_method": transition["method"],
              "planned_via_direction": transition["via_direction"],
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
    return {"path": str(destination.relative_to(ROOT) if destination.is_relative_to(ROOT) else destination),
            "fps": FPS, "frames": n_frames,
            "duration_s": n_frames / FPS, "size": [2 * width, 2 * height],
            "layout": "baseline top, planned bottom; front left, right-side right; shorter row holds its end"}


def write_tables(reports):
    def seconds(value, signed=False):
        return "—" if value is None else format(value, "+.3f" if signed else ".3f")

    def table(headers, rows):
        return "\n".join(["| " + " | ".join(headers) + " |",
                          "|" + "---|" * len(headers)] +
                         ["| " + " | ".join(map(str, row)) + " |" for row in rows])

    summary, transitions, failed, handoff = [], [], [], []
    for report in reports:
        sentence = " ".join(report["glosses"])
        summary.append([sentence, len(report["word_segments"]), report["transition_count"],
                        report["pass_count"], report["source_collision_count"], report["failed_count"],
                        seconds(report["duration_s"]), seconds(report["baseline"]["duration_s"]),
                        seconds(report["duration_vs_baseline_s"], signed=True)])
        for item in report["source_collision_handoff"]:
            if item not in handoff:
                handoff.append(item)
        for transition in report["transitions"]:
            pair = transition["from_gloss"] + " → " + transition["to_gloss"]
            distance = transition["clearance"]["min_distance_m"]
            transitions.append([sentence, pair, transition["status"],
                                transition["method"],
                                " → ".join(transition["via_directions"]) or "—",
                                f"{transition['duration_s']:.3f}",
                                "null" if distance is None else f"{distance * 1000:.6f}"])
            if transition["status"] == "FAILED":
                worst = transition["worst_collision"]
                failed.append([sentence, pair, " / ".join(worst["bodies"]) if worst else "—",
                               worst["distance_m"] if worst else distance,
                               worst["frame"] if worst else "—", transition["endpoint_floor_m"]])
    handoff_rows = [[item["word"], item["frame"], " / ".join(item["bodies"]),
                     f"{item['clearance_mm']:.6f}", item["distance_m"]]
                    for item in handoff]
    for english in (False, True):
        summary_headers = (["Sentence", "Word segments", "Transitions", "PASS", "source_collision", "FAILED",
                            "Planned s", "Baseline s", "Difference s"] if english else
                           ["句子", "单词段", "过渡数", "PASS", "source_collision", "FAILED", "规划秒数", "基线秒数", "秒数差"])
        transition_headers = (["Sentence", "Transition", "Status", "Method", "Via directions", "Duration s", "Min clearance mm"]
                              if english else ["句子", "过渡", "状态", "方法", "中间点方向", "时长秒", "最小间隙 mm"])
        failure_headers = (["Sentence", "Transition", "Worst body pair", "distance_m", "Transition frame", "Endpoint floor m"]
                           if english else ["句子", "过渡", "最差碰撞体对", "distance_m", "过渡内帧", "端点下限 m"])
        handoff_headers = (["Word", "Source sign_frames index", "Body pair", "Clearance mm", "distance_m"] if english else
                           ["单词", "源 sign_frames 帧索引", "碰撞体对", "间隙 mm", "distance_m"])
        intro = ("# Transition results\n\n[中文](report.md) · **English**\n\n"
                 "Local generated report. Sentence duration is frame count / 30; each transition/leg duration is intervals / 30. "
                 "PASS, source_collision and FAILED are disjoint transition counts. Either endpoint strictly below ENDPOINT_NEAR_M = 0 m "
                 "stops search as source_collision; its emitted direct path is diagnostic only, with full-path penetration still reported. "
                 "Clear endpoints escalate through direct, best via1/via2, then model-qpos0 hub. Singleton sentences have zero checks. "
                 "A null distance means no detected contacts, not a measured positive gap. "
                 "See the [protocol, commands and limitations](../../docs/transition-planner.en.md).\n\n" if english else
                 "# 衔接规划结果\n\n**中文** · [English](report.en.md)\n\n"
                 "本地生成报告。句子时长按帧数 / 30，过渡及各腿时长按时间间隔数 / 30。PASS、source_collision、FAILED 分开计数。"
                 "任一端点严格低于 ENDPOINT_NEAR_M = 0 m 即停止搜索并记为 source_collision；输出的直连仅供诊断，仍报告全路径穿透。"
                 "端点通过后依次尝试直连、最优 via1/via2、模型 qpos0 hub；单词句零次检查。"
                 "null 表示无接触记录，并非测得正间隙。详见[协议、启动命令与限制](../../docs/transition-planner.md)。\n\n")
        content = (intro + table(summary_headers, summary) + "\n\n" +
                   ("## Emitted transitions\n\n" if english else "## 输出过渡\n\n") +
                   table(transition_headers, transitions) + "\n\n" +
                   ("## FAILED worst collisions\n\n" if english else "## FAILED 最差碰撞\n\n") +
                   (table(failure_headers, failed) if failed else ("None." if english else "无。")) + "\n\n" +
                   ("## Group 2 source collision handoff\n\n" if english else "## 交给第二组的源姿态碰撞\n\n") +
                   (table(handoff_headers, handoff_rows) if handoff_rows else ("None." if english else "无。")) + "\n")
        (OUT / ("report.en.md" if english else "report.md")).write_text(content)


def write_fixed_mount_finding(model):
    """Report source/runtime evidence; never change geometry or collision masks."""
    body = model.body("fixed_mount")
    geoms = [g for g in range(model.ngeom) if model.geom_bodyid[g] == body.id]
    rows = []
    for geom in geoms:
        mesh = model.mesh(int(model.geom_dataid[geom])).name
        rows.append(f"| {geom} | {mesh} | {int(model.geom_contype[geom])} | "
                    f"{int(model.geom_conaffinity[geom])} | {int(model.geom_group[geom])} |")
    table = ("| geom ID | mesh | contype | conaffinity | group |\n"
             "|---|---|---|---|---|\n" + "\n".join(rows))
    info = json.loads((ROOT / "assets/robot/model_info.json").read_text())
    adaptation = next(item for item in info["adaptations"] if "Fixed mount" in item)
    position = ", ".join(f"{value:g}" for value in body.pos)
    finding = f"""# fixed_mount evidence / fixed_mount 证据

## 中文

`assets/robot/scene.xml:65` 定义包装体 `fixed_mount`，局部位置为 ({position}) m。
`scripts/prepare_robot.py:27–31` 创建 `pos=\"0 0 0.79\"` 的包装体，并把导入的 worldbody
子元素重新挂到它下面，使模型成为抬高的固定基座模拟。`assets/robot/model_info.json`
记录 `fixed_base=true` 和 `{adaptation}`；运行模式为 `{info['execution_mode']}`。

模型直接挂在该体上的 mesh / 碰撞掩码如下（MuJoCo 运行时读取；XML 第 66–68 行）：

{table}

`pelvis` 与一份 `pelvis_contour_link` 是视觉几何（0/0）；另一份
`pelvis_contour_link` 省略 XML 掩码属性，运行时为 1/1，参与碰撞。
证据支持它是虚拟挂载 / 固定基座包装，并非单独增加的真实机器人夹具；体名下的活动碰撞网格
仍是骨盆轮廓几何。`MujocoClearance` 必须保留它，不能按 `fixed_mount` 体名过滤。
这里仅调查定义和几何含义，没有更改模型、掩码或 2 mm 阈值，也没有验证真实硬件。

## English

`assets/robot/scene.xml:65` defines the `fixed_mount` wrapper body at ({position}) m.
`scripts/prepare_robot.py:27–31` creates `pos=\"0 0 0.79\"` and re-parents the imported
worldbody children beneath it for raised fixed-base simulation. `assets/robot/model_info.json`
records `fixed_base=true`, `{adaptation}`, and `{info['execution_mode']}`.

The table above reads the three directly attached mesh geoms and their masks from MuJoCo
(XML lines 66–68). `pelvis` and one `pelvis_contour_link` geom are visual-only (0/0).
The other `pelvis_contour_link` omits XML mask attributes and has active runtime masks 1/1.
This is a virtual mounting / fixed-base wrapper, rather than an additional real-robot fixture.
Its active collision mesh is still pelvis-contour geometry and must remain in
`MujocoClearance`; filtering the body name would discard that geometry. This investigation
changes no model, mask, or 2 mm threshold and makes no hardware-validation claim.

Regenerate / 重新生成：`.venv/bin/python scripts/evaluate_planned_transitions.py`
after / 之前先运行 `.venv/bin/python scripts/plan_transitions.py --all`.
"""
    path = OUT / "fixed_mount_finding.md"
    path.write_text(finding)
    return str(path.relative_to(ROOT))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=OUT / "report.json")
    parser.add_argument("--render-comparison", action="store_true")
    parser.add_argument("--copy-to", type=Path, default=Path("/workspace/you_hurt_where_baseline_vs_planned_v2.mp4"))
    args = parser.parse_args(argv)
    report = load_report(args.report)
    model = load_model(ROOT)
    for sentence in report["sentences"]:
        sentence["artifact_verification"] = verify_saved_sentence(sentence, model)
    report["fixed_mount_finding"] = write_fixed_mount_finding(model)
    sag_sentence = next(s for s in report["sentences"] if s["glosses"] == ["YOU", "BUY", "BOOK"])
    sag = measure_sag(model, sag_sentence)
    (OUT / "you_buy_sag.json").write_text(json.dumps(sag, indent=2) + "\n")
    if args.render_comparison:
        sentence = next(s for s in report["sentences"] if s["glosses"] == ["YOU", "HURT", "WHERE"])
        video = render_comparison(model, sentence, OUT / "you_hurt_where_baseline_vs_planned_v2.mp4")
        shutil.copy2(artifact_path(video["path"]), args.copy_to)
        video["copy"] = str(args.copy_to)
        report["comparison_video"] = video
    report["you_buy_sag"] = str((OUT / "you_buy_sag.json").relative_to(ROOT))
    inputs = {segment["motion"] for sentence in report["sentences"] for segment in sentence["word_segments"]}
    inputs.update(sentence["baseline"]["path"] for sentence in report["sentences"])
    inputs.update(("assets/robot/scene.xml", "motions/hospital_v1_motions.json",
                   "assets/robot/upstream_manifest.json", "assets/robot/model_info.json",
                   "motions/studio_galt_v1/index.json", "motions/wlasl_video_v1/index.json",
                   "scripts/prepare_robot.py", "src/sign_robot/transitions.py"))
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
