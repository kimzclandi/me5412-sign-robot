from sign_robot.pipeline import resolve_execution
from sign_robot.contracts import validate_selection
import pytest


CATALOG = [{"action_id": "HELLO", "asl_review_status": "unreviewed"}]
SELECT = {"status": "execute", "action_id": "HELLO"}


def test_review_gate_requires_explicit_preview(tmp_path):
    (tmp_path / "HELLO.mp4").write_bytes(b"fixture")
    assert resolve_execution(SELECT, catalog=CATALOG, preview_dir=tmp_path)["state"] == "review_required"
    assert resolve_execution(SELECT, catalog=CATALOG, preview_dir=tmp_path, allow_candidate_preview=True)["state"] == "ready"
    assert resolve_execution(SELECT, catalog=CATALOG, preview_dir=tmp_path, allow_candidate_preview="true")["state"] == "review_required"


def test_missing_motion_never_returns_a_playable_url(tmp_path):
    result = resolve_execution(SELECT, catalog=CATALOG, preview_dir=tmp_path, allow_candidate_preview=True)
    assert result["state"] == "unavailable" and result["preview_url"] is None


def test_rejection_cannot_carry_action_id():
    with pytest.raises(ValueError):
        validate_selection({"status": "unsupported", "action_id": "HELLO"}, CATALOG)


def test_unknown_action_is_not_played(tmp_path):
    with pytest.raises(ValueError):
        resolve_execution({"status": "execute", "action_id": "../../secret"}, catalog=CATALOG,
                          preview_dir=tmp_path, allow_candidate_preview=True)
