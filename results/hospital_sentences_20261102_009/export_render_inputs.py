"""Step 1 of the GPU render (WSL, CPU): export what scripts/render_sequences.py would draw, without drawing it.

render_sequences.py re-verifies each chain and renders with software GL inside WSL (minutes per sentence). Here the
fresh independent recheck already saved by verify_sequences.py is reused (its sequence-file hash must match), and the
replay, the original clips and the per-frame phase labels are written for render_gpu_windows.py, which draws the same
layout with the Windows GPU. Round 3 copy: the planned rest tail is labelled "return to rest". Run from the repository
root:
  .venv/bin/python results/hospital_sentences_20261102_009/export_render_inputs.py
"""
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sign_robot.pair_contract import atomic_json, atomic_motion, file_hash, inside, read_json, read_motion  # noqa: E402
from sign_robot.pair_verification_v2 import _full_replay  # noqa: E402
from sign_robot.sequence_contract import load_sequence_policy, read_sequence  # noqa: E402

RUN = Path(__file__).resolve().parent / "sequences"
OUT = Path(__file__).resolve().parent / "render_inputs"
spec = importlib.util.spec_from_file_location("render_sequences", ROOT / "scripts/render_sequences.py")
render_sequences = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render_sequences)
phase = render_sequences.phase


def main():
    manifest = read_json(RUN / "manifest.json")
    policy, _ = load_sequence_policy(ROOT, manifest["sequence_policy"])
    library = read_json(ROOT / "motions/hospital_v1_motions.json")
    motions = {w["gloss"]: w["motion"] for w in library["glosses"] if w.get("motion")}
    for case in read_json(RUN / "summary.json")["cases"]:
        if not case["selected_attempt"]:
            continue
        sequence_id = case["sequence_id"]
        path = RUN / "sequences" / sequence_id / f"{case['selected_attempt']}.json"
        recheck = read_json(RUN / "independent_recheck" / f"{sequence_id}.json")
        evidence = recheck["evidence"]
        if recheck["sequence_file_sha256"] != file_hash(path) or evidence["numerical_checks_passed"] is not True:
            raise SystemExit(f"Saved independent recheck does not confirm {sequence_id}")
        sequence = read_sequence(path, policy)
        clips = {w["gloss"]: read_motion(inside(ROOT, motions[w["gloss"]])) for w in sequence["word_instances"]}
        motion = _full_replay(sequence, clips)
        words = sequence["word_instances"]
        counts = [len(clips[w["gloss"]]["positions"]) for w in words]
        baseline_q = np.vstack([clips[w["gloss"]]["positions"] for w in words])
        starts = np.cumsum([0, *counts])
        baseline = {"joint_names": motion["joint_names"], "positions": baseline_q,
                    "timestamps_s": np.arange(len(baseline_q)) / 30}
        total = max(len(motion["positions"]), len(baseline_q))

        def label(word):
            return f"#{word['position']} {word['gloss']}"

        def phase_at(index, planned):
            # Same rule as render_sequences.render.phase_at.
            if not planned:
                position = int(np.searchsorted(starts, index, side="right") - 1)
                if position >= len(words):
                    return "hold", "end hold / 结束保持"
                return phase(words[position], index - starts[position], counts[position], label(words[position]))
            if index >= len(motion["positions"]):
                return "hold", "end hold / 结束保持"
            moment = index / 30
            segment = next(s for s in sequence["segments"] if s["start_time_s"] - 1e-10 <= moment <= s["end_time_s"] + 1e-10)
            if segment["kind"] == "polynomial_v2":
                index_ = sequence["segments"].index(segment)
                tail = sequence.get("rest_tail")
                if tail is not None and tail["segment_indices"][0] <= index_ <= tail["segment_indices"][1]:
                    return "transition", "ADDED return to rest / 新增回到初始姿态"
                edge = next(e for e in sequence["edges"] if e["segment_indices"][0] <= index_ <= e["segment_indices"][1])
                return "transition", f"ADDED transition {edge['edge_index']} / 新增过渡"
            word = next(w for w in words if w["instance_id"] == segment["word_instance_id"])
            frame = round(segment["source_frames"][0] + (moment - segment["start_time_s"]) * 30)
            return phase(word, frame, counts[word["position"]], label(word))

        checks = []
        for word in words:
            c0, c1 = word["protected_core_frames"]
            segment = next(s for s in sequence["segments"] if s.get("word_instance_id") == word["instance_id"])
            frames = np.rint((segment["start_time_s"] + (np.arange(c0, c1 + 1) - segment["source_frames"][0]) / 30) * 30).astype(int)
            checks.append({"instance_id": word["instance_id"], "replay_frames": [int(frames[0]), int(frames[-1])],
                           "poses_bitwise_equal": bool(np.array_equal(motion["positions"][frames],
                                                                      clips[word["gloss"]]["positions"][c0:c1 + 1]))})
        folder = OUT / sequence_id
        atomic_motion(folder / "replay.npz", motion)
        atomic_motion(folder / "baseline.npz", baseline)
        atomic_json(folder / "independent_verification.json", evidence)
        atomic_json(folder / "render_plan.json", {
            "schema_version": 1, "sequence_id": sequence_id, "total_frames": total,
            "title": sequence_id.replace("__", " → "), "numerical_checks_passed": True,
            "source_sequence": str(path.relative_to(ROOT)), "source_sequence_sha256": file_hash(path),
            "replay_duration_s": evidence["replay_duration_s"],
            "picks": sorted({round(sequence["segments"][e["segment_indices"][0]]["start_time_s"] * 30)
                             for e in [*sequence["edges"], *([sequence["rest_tail"]] if "rest_tail" in sequence else [])]}),
            "phases": {"original": [phase_at(i, False) for i in range(total)],
                       "planned": [phase_at(i, True) for i in range(total)]},
            "protected_instance_video_checks": checks})
        print(json.dumps({"sequence": sequence_id, "frames": total,
                          "protected_equal": all(c["poses_bitwise_equal"] for c in checks)}), flush=True)


if __name__ == "__main__":
    main()
