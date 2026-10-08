import json
import pytest
from sign_robot import inspection

RUN_ID = "1111111111111111"


@pytest.fixture
def artifacts(tmp_path):
    folder = tmp_path / f"results/inspection/HELLO/{RUN_ID}"
    folder.mkdir(parents=True)
    prefix = f"results/inspection/HELLO/{RUN_ID}/"
    payload = {"action_id": "HELLO", "trajectory_sha256": "fixture-sha"}
    (folder / "telemetry.json").write_text(json.dumps(payload))
    for ext in ("mp4", "png"):
        (folder / ("front." + ext)).write_bytes(b"0123456789")
    entry = {"action_id": "HELLO", "run_id": RUN_ID, "trajectory_sha256": "fixture-sha", "telemetry": prefix+"telemetry.json",
             "views": {"front": {"mp4": prefix+"front.mp4", "png": prefix+"front.png"}}}
    manifest = {"schema_version": 1, "actions": {"HELLO": entry}, "runs": [entry]}
    (folder.parent.parent / "manifest.json").write_text(json.dumps(manifest))
    return tmp_path, entry


def test_inspection_inventory_and_identity(artifacts):
    root, _ = artifacts
    item = inspection.inventory(root)["actions"]["HELLO"]
    assert item["views"]["front"]["video_url"] == f"/inspection-media/HELLO/{RUN_ID}/front.mp4"
    assert item["telemetry_url"] == f"/api/inspection/HELLO/{RUN_ID}"
    data = inspection.telemetry("HELLO", root, run_id=RUN_ID)
    assert data["trajectory_sha256"] == "fixture-sha" and data["run_id"] == RUN_ID
    assert inspection.media("HELLO", "front", "mp4", root, run_id=RUN_ID).read_bytes() == b"0123456789"


def test_missing_inspection_is_explicit(tmp_path):
    assert inspection.inventory(tmp_path)["actions"] == {}
    with pytest.raises(FileNotFoundError):
        inspection.telemetry("HELLO", tmp_path, run_id=RUN_ID)


@pytest.mark.parametrize("relative", ["data/private.json", "results/inspection/../../data/private.json"])
def test_private_path_cannot_be_served(tmp_path, relative):
    (tmp_path / "data").mkdir()
    (tmp_path / "data/private.json").write_text("{}")
    with pytest.raises(ValueError):
        inspection.artifact_path(relative, tmp_path, suffix=".json")


def test_symlink_cannot_escape(tmp_path):
    folder = tmp_path / "results/inspection"
    folder.mkdir(parents=True)
    target = tmp_path / "private.json"
    target.write_text("{}")
    (folder / "leak.json").symlink_to(target)
    with pytest.raises(ValueError):
        inspection.artifact_path("results/inspection/leak.json", tmp_path, suffix=".json")


def test_mismatched_trajectory_fails_closed(artifacts):
    root, entry = artifacts
    (root / entry["telemetry"]).write_text(json.dumps({"action_id":"HELLO", "trajectory_sha256":"different"}))
    with pytest.raises(ValueError, match="identity"):
        inspection.telemetry("HELLO", root, run_id=RUN_ID)


def test_unknown_action_and_view_fail_closed(artifacts):
    root, _ = artifacts
    with pytest.raises(ValueError):
        inspection.telemetry("../HELLO", root, run_id=RUN_ID)
    with pytest.raises(ValueError):
        inspection.media("HELLO", "../../data", "json", root, run_id=RUN_ID)


@pytest.mark.parametrize("run_id", ["../1111111111111111", "invalid", "F" * 16, "2" * 16])
def test_invalid_or_unregistered_run_is_not_resolved_to_latest(artifacts, run_id):
    root, _ = artifacts
    with pytest.raises((ValueError, FileNotFoundError)):
        inspection.telemetry("HELLO", root, run_id=run_id)


def test_fixed_run_survives_latest_pointer_change(artifacts):
    root, old = artifacts
    before = inspection.inventory(root)["actions"]["HELLO"]
    new_id = "2222222222222222"
    new = json.loads(json.dumps(old).replace(RUN_ID, new_id).replace("fixture-sha", "new-sha"))
    folder = root / "results/inspection/HELLO" / new_id
    folder.mkdir()
    (folder / "telemetry.json").write_text(json.dumps({"action_id": "HELLO", "trajectory_sha256": "new-sha"}))
    for ext in ("mp4", "png"):
        (folder / f"front.{ext}").write_bytes(b"new content")
    (root / "results/inspection/manifest.json").write_text(json.dumps({
        "schema_version": 1, "actions": {"HELLO": new}, "runs": [old, new]}))
    assert inspection.inventory(root)["actions"]["HELLO"]["run_id"] == new_id
    assert inspection.telemetry("HELLO", root, run_id=before["run_id"])["trajectory_sha256"] == "fixture-sha"
    assert inspection.media("HELLO", "front", "mp4", root, run_id=before["run_id"]).read_bytes() == b"0123456789"


def test_manifest_cannot_point_one_run_at_another_runs_media(artifacts):
    root, entry = artifacts
    new_id = "2222222222222222"
    folder = root / "results/inspection/HELLO" / new_id
    folder.mkdir()
    (folder / "front.mp4").write_bytes(b"different run")
    entry["views"]["front"]["mp4"] = f"results/inspection/HELLO/{new_id}/front.mp4"
    (root / "results/inspection/manifest.json").write_text(json.dumps({
        "schema_version": 1, "actions": {"HELLO": entry}, "runs": [entry]}))
    with pytest.raises(ValueError, match="another action or run"):
        inspection.media("HELLO", "front", "mp4", root, run_id=RUN_ID)
