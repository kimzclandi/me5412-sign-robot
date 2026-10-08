"""The web adapter exposes generated coordinates and FK from the same frames."""
import json

import mujoco
import numpy as np
import pytest

from sign_robot import learning_api as api
from sign_robot import learned_motion
from sign_robot.motion import load_model, apply_frame


@pytest.mark.parametrize("payload", [
    {}, {"text": None}, {"text": 123}, {"text": "x" * 1001},
    {"text": "Hello", "duration_scale": True},
    {"text": "Hello", "duration_scale": "1.2"},
    {"text": "Hello", "duration_scale": 0},
    {"text": "Hello", "duration_scale": 1.1},
    {"text": "Hello", "duration_scale": float("nan")},
])
def test_invalid_generation_parameters_never_load_model(payload, monkeypatch):
    monkeypatch.setattr(api, "status", lambda *_: pytest.fail("Invalid request must not load model"))
    with pytest.raises(ValueError):
        api.generate_request(payload)


@pytest.mark.parametrize("text", ["Where is the pharmacy?", "I do not want to wait.", "Hello and thank you", ""])
def test_unsupported_request_has_no_coordinates_or_pose(text, monkeypatch):
    monkeypatch.setattr(api, "status", lambda *_: pytest.fail("Unsupported input must not load model"))
    result = api.generate_request({"text": text})
    assert result["accepted"] is False and result["positions_rad"] is None
    assert "kinematics" not in result and result["asl_reviewed"] is False


def test_changed_checkpoint_blocks_inference_without_touching_original(tmp_path, monkeypatch):
    # Reuse metadata only; a deliberately bad temporary weight file must fail
    # against the real experiment's recorded hash before model inference.
    for relative in ("results/motion_learning/v1/report.json", "results/motion_learning/v1/model.json",
                     "data/corpus_index/how2sign_realigned_v1/download_manifest.json"):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((api.ROOT / relative).read_bytes())
    (tmp_path / "results/motion_learning/v1/model.npz").write_bytes(b"changed temporary checkpoint")
    assert api.status(tmp_path)["checkpoint_hash_verified"] is False
    monkeypatch.setattr(learned_motion, "generate", lambda *a, **k: pytest.fail("Hash mismatch must block inference"))
    with pytest.raises(ValueError, match="checkpoint hash"):
        api.generate_request({"text": "Hello"}, tmp_path)


def test_rejected_engineering_candidate_has_no_playable_kinematics(monkeypatch):
    monkeypatch.setattr(api, "status", lambda *_: {"checkpoint_hash_verified": True,
        "durations_s": {"HELLO": 7.8}, "model_sha256": "fixture"})
    monkeypatch.setattr(learned_motion, "generate", lambda *a, **k: {
        "status": "rejected_candidate", "accepted": False,
        "positions": np.zeros((2, 1)), "timestamps_s": np.array([0., 1.]),
        "joint_names": np.array(["fixture"]), "rejection_reasons": ["fixture_gate_failed"]})
    monkeypatch.setattr(api, "kinematic_preview", lambda *_: pytest.fail("Rejected coordinates cannot become playable pose"))
    result = api.generate_request({"text": "Hello"})
    assert result["accepted"] is False and "kinematics" not in result
    assert result["positions_rad"] == [[0.], [0.]]  # Diagnostic values remain explicit.


@pytest.mark.parametrize("text,action,scale,duration", [
    ("Hello", "HELLO", 1.0, 7.8),
    ("Thank you", "THANK_YOU", 1.2, 9.6),
    ("Please wait", "PLEASE_WAIT", 1.0, 8.5),
])
def test_real_adapter_pose_matches_generated_joint_frames(text, action, scale, duration):
    result = api.generate_request({"text": text, "duration_scale": scale})
    assert result["accepted"] is True and result["action_id"] == action
    assert result["asl_reviewed"] is False and result["default_enabled"] is False
    assert result["conditioning_text"] == text and result["duration_s"] == pytest.approx(duration)
    times = np.asarray(result["timestamps_s"])
    positions = np.asarray(result["positions_rad"])
    assert positions.shape == (len(times), 53) and np.isfinite(positions).all()
    assert np.all(np.diff(times) > 0) and times[0] == 0 and times[-1] == pytest.approx(duration)
    kin = result["kinematics"]
    points = np.asarray(kin["positions_m"])
    assert points.shape == (len(times), len(kin["body_names"]), 3) and np.isfinite(points).all()
    model = load_model()
    state = mujoco.MjData(model)
    ids = [model.body(name).id for name in kin["body_names"]]
    assert all(int(model.body_parentid[ids[b]]) == ids[a] for a, b in kin["edges"])
    # Independently recompute beginning, expression and final pose from the
    # returned positions; no demonstration-file/no-replay test is duplicated.
    for frame in (0, len(times) // 2, len(times) - 1):
        apply_frame(model, state, result["joint_names"], positions[frame])
        np.testing.assert_allclose(points[frame], state.xpos[ids], atol=5.1e-8, rtol=0)
    assert json.loads(json.dumps(result, allow_nan=False))["action_id"] == action
