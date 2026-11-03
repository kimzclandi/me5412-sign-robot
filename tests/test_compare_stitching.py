import importlib.util
import shutil

import numpy as np
from sign_robot.motion import ROOT

spec = importlib.util.spec_from_file_location("compare_stitching", ROOT / "scripts/demo/compare_stitching.py")
cmp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cmp)


def _copy(ids, folder):
    folder.mkdir()
    for key in ids:
        shutil.copy(ROOT / f"results/demo/{key}.npz", folder / f"{key}.npz")


def test_identical_candidate_matches_baseline_and_passes_format_checks(tmp_path):
    _copy(["s5", "s9"], tmp_path / "base")
    _copy(["s9"], tmp_path / "cand")
    summary = cmp.compare(tmp_path / "cand", "same", tmp_path / "base", tmp_path / "out", plots=False)
    assert list(summary["lines"]) == ["s9"] and summary["skipped"] == ["s5"]
    base, cand = summary["lines"]["s9"]["baseline"], summary["lines"]["s9"]["same"]
    assert base == cand
    assert base["joints"] == 53 and base["same_joint_set"] and base["fps"] == 30.0
    assert base["joint_limit_excess_rad"] == 0 and base["coupling_error_rad"] < 1e-6
    assert base["start_from_neutral_rad"] < 1e-6 and base["end_at_neutral_rad"] < 1e-6
    assert (tmp_path / "out/same/summary.md").exists()


def test_smoother_candidate_has_lower_jerk_and_speed(tmp_path):
    _copy(["s4"], tmp_path / "base")
    (tmp_path / "cand").mkdir()
    with np.load(ROOT / "results/demo/s4.npz") as f:
        motion = {k: f[k] for k in f.files}
    kernel = np.ones(9) / 9
    motion["positions"] = np.stack([np.convolve(np.pad(c, 4, mode="edge"), kernel, mode="valid") for c in motion["positions"].T], axis=1)
    np.savez(tmp_path / "cand/s4.npz", **motion)
    lines = cmp.compare(tmp_path / "cand", "smooth", tmp_path / "base", tmp_path / "out", plots=False)["lines"]["s4"]
    assert lines["smooth"]["arm_jerk_rms"] < lines["baseline"]["arm_jerk_rms"]
    assert lines["smooth"]["arm_speed_max"] < lines["baseline"]["arm_speed_max"]
