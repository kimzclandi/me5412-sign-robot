import numpy as np
import pytest
from sign_robot import learned_motion as lm


def test_phase_endpoints_and_invalid_input():
    basis = lm.phase_features(np.array([0.0, .5, 1.0]), np.linspace(0, 1, 40), 1.5/39)
    assert basis.shape == (3, 40)
    assert np.all(basis[[0, 2]] == 0)
    assert np.any(basis[1] > 0)
    with pytest.raises(ValueError): lm.phase_features(np.array([1.01]), np.linspace(0, 1, 40), 1.5/39)


def test_unsupported_text_never_loads_checkpoint(monkeypatch):
    monkeypatch.setattr(lm, "load_checkpoint", lambda *_: pytest.fail("Unsupported text must not load the model"))
    result = lm.generate("Please take two pills")
    assert result["status"] == "unsupported" and result["positions"] is None


def test_model_inference_does_not_load_demonstration_files(monkeypatch):
    if not (lm.EXPERIMENT / "model.npz").exists(): pytest.skip("Single registered fit has not run yet")
    original = np.load
    accessed = []
    def checked(path, *args, **kwargs):
        accessed.append(str(path))
        assert "/motions/" not in str(path)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(np, "load", checked)
    lm.load_checkpoint.cache_clear()
    result = lm.generate("Hello")
    assert result["positions"].shape == (235, 53)
    assert any(path.endswith("model.npz") for path in accessed)
    assert result["default_enabled"] is False


def test_slow_generation_changes_sampling_without_replay():
    if not (lm.EXPERIMENT / "model.npz").exists(): pytest.skip("Single registered fit has not run yet")
    ordinary, slow = lm.generate("Hello"), lm.generate("Hello", duration_s=7.8*1.2)
    assert len(slow["timestamps_s"]) > len(ordinary["timestamps_s"])
    assert slow["timestamps_s"][-1] == pytest.approx(ordinary["timestamps_s"][-1]*1.2)
    assert lm.generate("Hello", duration_s=1)["positions"] is None
