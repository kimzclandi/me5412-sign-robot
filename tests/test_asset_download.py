"""Offline checks that restoration cannot redefine expected model hashes."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path

import pytest


SPEC = importlib.util.spec_from_file_location(
    "fetch_embedding", Path(__file__).resolve().parents[1] / "scripts/fetch_embedding.py")
fetch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fetch)


def entry(payload=b"pinned model data"):
    return {"path": "config.json", "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(), "url": "recorded source"}


def manifest(item=None):
    return {"model_id": fetch.MODEL_ID, "revision": fetch.REVISION,
            "files": [entry() if item is None else item]}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("A test attempted real network access")
    monkeypatch.setattr(fetch.urllib.request, "urlopen", fail)


@pytest.mark.parametrize("field,value", [
    ("model_id", "different/model"), ("revision", "changed"),
    ("files", [{**entry(), "path": "../config.json"}]),
    ("files", [{**entry(), "sha256": "invalid"}]),
    ("files", [entry(), entry()]),
])
def test_invalid_manifest_rejected_before_fetch(tmp_path, monkeypatch, field, value):
    monkeypatch.setattr(fetch, "FILES", ["config.json"])
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({**manifest(), field: value}), encoding="utf-8")
    with pytest.raises(ValueError):
        fetch.load_expected(path)


def test_valid_existing_asset_is_verified_without_download(tmp_path):
    (tmp_path / "config.json").write_bytes(b"pinned model data")
    assert fetch.fetch_file(tmp_path, "config.json", entry(), None) == entry()


@pytest.mark.parametrize("expected", [None, entry()])
def test_existing_drift_or_unrecorded_asset_is_preserved(tmp_path, expected):
    target = tmp_path / "config.json"
    target.write_bytes(b"unrecorded local change")
    with pytest.raises(ValueError, match="preserved unchanged"):
        fetch.fetch_file(tmp_path, "config.json", expected, None)
    assert target.read_bytes() == b"unrecorded local change"


def test_download_hash_failure_never_publishes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(b"drifted response"))
    with pytest.raises(ValueError, match="Downloaded asset differs"):
        fetch.fetch_file(tmp_path, "config.json", entry(), None)
    assert not (tmp_path / "config.json").exists()
    assert not list(tmp_path.glob("*.part"))


def test_verified_download_keeps_recorded_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(b"pinned model data"))
    assert fetch.fetch_file(tmp_path, "config.json", entry(), None) == entry()
    assert (tmp_path / "config.json").read_bytes() == b"pinned model data"
    assert not list(tmp_path.glob("*.part"))


def test_interrupted_download_cleans_temporary_file(tmp_path, monkeypatch):
    def interrupted(*a, **k):
        raise OSError("connection interrupted")
    monkeypatch.setattr(fetch.urllib.request, "urlopen", interrupted)
    with pytest.raises(OSError):
        fetch.fetch_file(tmp_path, "config.json", entry(), None)
    assert not list(tmp_path.iterdir())


def test_restore_does_not_rewrite_expected_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch, "ROOT", tmp_path)
    monkeypatch.setattr(fetch, "FILES", ["config.json"])
    path = tmp_path / "config/embedding_download_manifest.json"
    path.parent.mkdir()
    original = json.dumps(manifest(), ensure_ascii=False, indent=4).encode()
    path.write_bytes(original)
    monkeypatch.setattr(fetch.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(b"pinned model data"))
    fetch.main()
    assert path.read_bytes() == original
    assert (tmp_path / "models/all-MiniLM-L6-v2/config.json").read_bytes() == b"pinned model data"


def test_first_bootstrap_explicitly_records_new_hash_provenance(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(fetch, "ROOT", tmp_path)
    monkeypatch.setattr(fetch, "FILES", ["config.json"])
    monkeypatch.setattr(fetch.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(b"pinned model data"))
    fetch.main()
    saved = json.loads((tmp_path / "config/embedding_download_manifest.json").read_text())
    assert saved["revision"] == fetch.REVISION
    assert "not independently verified" in saved["manifest_provenance"]
    assert "not independent hash verification" in capsys.readouterr().out
