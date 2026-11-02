"""Deterministic approval-clock tests; production continues using UTC wall time."""
import pytest


@pytest.fixture(autouse=True)
def fixed_pair_approval_clock(monkeypatch):
    from pair_v2_fixtures import NOW
    import sign_robot.pair_windows as windows
    monkeypatch.setattr(windows, "_utc_now", lambda: NOW)
