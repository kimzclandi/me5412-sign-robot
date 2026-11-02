"""Batch video sequencing checks without MuJoCo rendering or MP4 encoding."""

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import imageio.v2 as imageio
import mujoco
import numpy as np
from PIL import ImageDraw


def test_batch_comparison_keeps_order_endpoint_holds_and_singletons(monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "transition_render_evaluator", root / "scripts/evaluate_planned_transitions.py")
    evaluator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluator)

    def motion(values):
        return {"joint_names": np.array(["joint"]),
                "positions": np.array(values, dtype=float)[:, None]}

    motions = {"a_base.npz": motion([0, 1]), "a_plan.npz": motion([10, 11, 12]),
               "b_base.npz": motion([20, 21]), "b_plan.npz": motion([30])}
    reports = [{"glosses": glosses, "baseline": {"path": f"{key}_base.npz"},
                "output_npz": f"{key}_plan.npz", "transitions": [], "word_segments": []}
               for key, glosses in (("a", ["NOW", "NURSE"]), ("b", ["THANK-YOU"]))]
    applied, labels, encoded, encoder_options = [], [], [], {}
    monkeypatch.setattr(evaluator, "read_motion", lambda path: motions[path.name])
    monkeypatch.setattr(evaluator, "apply_frame",
                        lambda model, data, names, pose: applied.append(float(pose[0])))
    monkeypatch.setattr(mujoco, "MjData", lambda model: object())
    monkeypatch.setitem(sys.modules, "render_comparison", SimpleNamespace(camera=lambda angle: angle))

    class Renderer:
        def __init__(self, model, *, width, height):
            self.image = np.zeros((height, width, 3), dtype=np.uint8)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def update_scene(self, data, *, camera):
            pass

        def render(self):
            return self.image

    class Writer:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def append_data(self, frame):
            encoded.append(frame.shape)

    class Draw:
        def rectangle(self, *args, **kwargs):
            pass

        def text(self, xy, text, **kwargs):
            labels.append(text)

    def writer(path, **options):
        encoder_options.update(options)
        return Writer()

    monkeypatch.setattr(mujoco, "Renderer", Renderer)
    monkeypatch.setattr(imageio, "get_writer", writer)
    monkeypatch.setattr(ImageDraw, "Draw", lambda image: Draw())
    result = evaluator.render_comparison_batch(object(), reports, "batch", out_dir=tmp_path)

    # The first baseline and second planned row hold endpoints independently.
    assert applied == [0, 10, 1, 11, 1, 12, 20, 30, 21, 30]
    assert encoded == [(1088, 960, 3)] * 5
    assert encoder_options["ffmpeg_params"] == ["-threads", "1"]
    assert result["sentence_count"] == 2 and result["frames"] == 5
    assert result["sentences"] == [
        {"glosses": ["NOW", "NURSE"], "start_frame": 0, "end_frame": 2, "frames": 3},
        {"glosses": ["THANK-YOU"], "start_frame": 3, "end_frame": 4, "frames": 2},
    ]
    assert any("sentence 1/2" in label for label in labels)
    assert any("sentence 2/2" in label for label in labels)
    assert "NOW NURSE" in labels and "THANK-YOU" in labels

