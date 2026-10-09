"""Frozen metric identities and the new, explicit download boundary."""
import hashlib
import http.client
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

from sign_robot import project_overview as project
from sign_robot import server


def test_real_overview_preserves_data_units_and_snapshot_scope():
    result = project.overview()
    assert result["metrics"] == {"supported_actions": 3, "independent_demonstrations": 3,
                                 "metadata_rows": 35263, "motion_targets": 0, "historical_tests": 206}
    assert result["evidence_snapshot"]["not_live"] is True
    assert result["evidence_snapshot"]["created_utc"] == "2026-10-08T15:27:42.652545+00:00"
    assert result["model"]["train_frames"] == 367 and result["model"]["validation_frames"] == 365
    assert sum(item["metadata_rows"] for item in result["corpus"]["splits"]) == 35263
    assert result["model"]["asl_reviewed"] is False
    assert all(not item["asl_reviewed"] for item in result["generated_previews"])
    assert all(item["available"] for item in result["materials"])
    # No source-side paths, raw corpus records or model arrays in the public contract.
    assert all("path" not in item for item in result["materials"])
    assert "positions_rad" not in json.dumps(result)
    assert "sentence_index.jsonl" not in json.dumps(result)


def test_evaluation_retains_separate_denominators_and_failures():
    result = project.overview()["evaluation"]
    assert result["case_count"] == 60 and result["raw_rows"] == 180
    assert result["supported_cases"] == result["out_of_scope_cases"] == 30
    assert result["labels_status"] == "agent_draft_unreviewed"
    for method in result["methods"]:
        assert sum(method["supported"].values()) == method["n_supported"] == 30
        assert sum(method["out_of_scope"].values()) == method["n_unsupported"] == 30
        assert method["accuracy"]["denominator"] == 60
    llm = next(item for item in result["methods"] if item["id"] == "llm")
    assert llm["accuracy"]["numerator"] == 48
    assert llm["supported"] == {"correct_selection": 20, "wrong_rejection": 7, "wrong_action_id": 1, "error": 2}
    assert llm["out_of_scope"]["false_execution"] == 2
    assert result["llm_http_cases"] == 35 and result["shared_guard_cases"] == 25
    assert result["llm_default_enabled"] is False


def test_published_previews_match_independent_render_manifest():
    manifest = json.loads((project.ROOT / "results/motion_learning/v1/previews/preview_manifest.json").read_text())
    files = [item for key, item in project.FILES.items() if key.startswith("learned-")]
    assert len(files) == 12
    for item in files:
        assert item["sha256"] == manifest["output_sha256"][Path(item["path"]).name]


@pytest.fixture
def fixed_file(tmp_path, monkeypatch):
    body = b"0123456789"
    relative = "deliverables/fixture/\u6c47\u62a5.pdf"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_bytes(body)
    spec = {"path": relative, "sha256": hashlib.sha256(body).hexdigest(), "title": "Fixture",
            "category": "report", "mime": "application/pdf", "description": "fixture only", "disposition": "inline"}
    monkeypatch.setattr(project, "FILES", {"fixture": spec})
    return tmp_path, path, spec


@pytest.mark.parametrize("key", ["../fixture", "%2e%2e%2fsecret", "fixture/../../secret", "model.npz", "sentence_index.jsonl", ""])
def test_unknown_artifact_ids_never_resolve(fixed_file, key):
    root, _, _ = fixed_file
    with pytest.raises(KeyError):
        project.artifact(key, root)


def test_artifact_mutation_is_detected_and_not_marked_available(fixed_file):
    root, path, _ = fixed_file
    path.write_bytes(b"changed")
    with pytest.raises(project.IntegrityError):
        project.artifact("fixture", root)
    assert project.materials(root)[0]["unavailable_reason"] == "integrity_mismatch"
    path.unlink()
    assert project.materials(root)[0]["unavailable_reason"] == "missing"


def test_allowlisted_path_cannot_be_replaced_by_symlink(fixed_file):
    root, path, _ = fixed_file
    private = root / "private.txt"
    private.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(private)
    with pytest.raises(ValueError, match="symlink"):
        project.artifact("fixture", root)
    assert project.materials(root)[0]["available"] is False


def test_frozen_source_mutation_fails_instead_of_silently_changing_metrics(tmp_path):
    spec = project.SOURCES["acceptance"]
    path = tmp_path / spec["path"]
    path.parent.mkdir(parents=True)
    path.write_text('{"tests":{"tests":999}}')
    with pytest.raises(project.IntegrityError):
        project.overview(tmp_path)


@pytest.fixture
def http_server(fixed_file, monkeypatch):
    root, _, _ = fixed_file
    monkeypatch.setattr(server, "ROOT", root)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv.server_address[1]
    srv.shutdown()
    srv.server_close()
    thread.join()


def request(port, route, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port)
    conn.request("GET", route, headers=headers or {})
    response = conn.getresponse()
    result = response.status, dict(response.getheaders()), response.read()
    conn.close()
    return result


def test_download_preserves_range_identity_mime_and_filename(http_server, fixed_file):
    _, _, spec = fixed_file
    status, headers, body = request(http_server, "/project-files/fixture", {"Range": "bytes=2-5"})
    assert status == 206 and body == b"2345"
    assert headers["Content-Range"] == "bytes 2-5/10"
    assert headers["Content-Type"] == "application/pdf"
    assert headers["ETag"] == f'"{spec["sha256"]}"'
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert "filename*=UTF-8''%E6%B1%87%E6%8A%A5.pdf" in headers["Content-Disposition"]
    assert request(http_server, "/project-files/fixture", {"Range": "bytes=12-"})[0] == 416


def test_download_host_unknown_missing_and_corrupt_boundaries(http_server, fixed_file):
    _, path, _ = fixed_file
    assert request(http_server, "/project-files/fixture", {"Host": "unrelated.example"})[0] == 403
    assert request(http_server, "/project-files/../private.txt")[0] == 404
    assert request(http_server, "/project-files/%2e%2e%2fprivate.txt")[0] == 404
    path.write_bytes(b"corrupt")
    status, _, body = request(http_server, "/project-files/fixture")
    assert status == 409 and json.loads(body)["error"] == "project_file_integrity_mismatch"
    path.unlink()
    assert request(http_server, "/project-files/fixture")[0] == 404


def test_missing_project_sources_do_not_claim_snapshot_success(http_server):
    status, _, body = request(http_server, "/api/project")
    assert status == 503 and json.loads(body) == {"error": "project_evidence_unavailable"}
    assert request(http_server, "/api/project", {"Host": "unrelated.example"})[0] == 403


def test_project_static_assets_are_explicitly_served(http_server, fixed_file):
    root, _, _ = fixed_file
    (root / "web").mkdir()
    for name in ("project.js", "project.css", "i18n.js"):
        (root / "web" / name).write_text("/* fixture */")
        assert request(http_server, "/" + name)[0] == 200
