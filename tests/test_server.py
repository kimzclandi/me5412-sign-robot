"""Exercise actual HTTP boundaries, including selection and byte-range playback."""
import http.client
import json
from threading import Thread
from http.server import ThreadingHTTPServer
import pytest
from sign_robot import server


@pytest.fixture
def http_server(tmp_path, monkeypatch):
    # Isolate logs and media while retaining the actual candidate catalog.
    (tmp_path / "data").mkdir()
    for name in ("catalog.json", "source_manifest.json"):
        (tmp_path / "data" / name).write_bytes((server.ROOT / "data" / name).read_bytes())
    (tmp_path / "results/previews").mkdir(parents=True)
    (tmp_path / "results/previews/HELLO.mp4").write_bytes(b"0123456789")
    monkeypatch.setattr(server, "ROOT", tmp_path)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv.server_address[1]
    srv.shutdown(); srv.server_close(); thread.join()


def request(port, route, payload=None, headers=None):
    client = http.client.HTTPConnection("127.0.0.1", port)
    body = None if payload is None else json.dumps(payload)
    client.request("GET" if payload is None else "POST", route, body=body, headers=headers or {})
    response = client.getresponse()
    data = response.read()
    result = response.status, dict(response.getheaders()), data
    client.close()
    return result


def test_http_selection_requires_review(http_server):
    status, _, data = request(http_server, "/api/select", {"text": "Thank you.", "method": "exact"})
    result = json.loads(data)
    assert status == 200 and result["selection"]["action_id"] == "THANK_YOU"
    assert result["execution"]["state"] == "review_required"


@pytest.mark.parametrize("payload", [{"action_id": "../../secret"}, {"action_id": "HELLO", "allow_candidate_preview": "false"}])
def test_invalid_action_never_executes(http_server, payload):
    assert request(http_server, "/api/action", payload)[0] == 400


def test_cross_origin_is_rejected(http_server):
    assert request(http_server, "/api/select", {"text": "hello"}, {"Origin": "https://example.com"})[0] == 403


def test_video_range_and_path_whitelist(http_server):
    status, headers, data = request(http_server, "/media/HELLO.mp4", headers={"Range": "bytes=2-5"})
    assert status == 206 and data == b"2345" and headers["Content-Range"] == "bytes 2-5/10"
    assert request(http_server, "/media/../../data/catalog.json")[0] == 404


def test_unsupported_input_has_no_preview(http_server):
    status, _, data = request(http_server, "/api/select", {"text": "Please wait and take two pills.", "method": "exact", "allow_candidate_preview": True})
    result = json.loads(data)
    assert status == 200 and result["selection"]["status"] != "execute"
    assert result["execution"]["preview_url"] is None


def test_health_identifies_local_project(http_server):
    status, _, data = request(http_server, "/api/health")
    health=json.loads(data)
    assert status == 200 and health["status"] == "ok"
    assert health["project_id"] == "me5412-sign-robot" and health["pid"] > 1


def test_missing_inspection_and_path_escape(http_server):
    assert json.loads(request(http_server, "/api/inspection")[2])["actions"] == {}
    assert request(http_server, "/api/inspection/../../data/catalog.json")[0] == 404
    assert request(http_server, "/inspection-media/HELLO/../../data/catalog.json")[0] == 404


def test_inspection_urls_pin_run_across_manifest_update(http_server):
    entries = []
    base = server.ROOT / "results/inspection"
    for run_id, content in (("1111111111111111", b"old frame"), ("2222222222222222", b"new frame")):
        folder = base / "HELLO" / run_id
        folder.mkdir(parents=True)
        prefix = f"results/inspection/HELLO/{run_id}/"
        (folder / "telemetry.json").write_text(json.dumps({"action_id": "HELLO", "trajectory_sha256": run_id}))
        for ext in ("mp4", "png"):
            (folder / f"front.{ext}").write_bytes(content)
        entries.append({"action_id": "HELLO", "run_id": run_id, "trajectory_sha256": run_id,
                        "telemetry": prefix + "telemetry.json",
                        "views": {"front": {"mp4": prefix + "front.mp4", "png": prefix + "front.png"}}})
    def publish(latest):
        (base / "manifest.json").write_text(json.dumps({"schema_version": 1, "actions": {"HELLO": latest}, "runs": entries}))
    publish(entries[0])
    old = json.loads(request(http_server, "/api/inspection")[2])["actions"]["HELLO"]
    publish(entries[1])
    status, _, body = request(http_server, old["telemetry_url"])
    assert status == 200 and json.loads(body)["run_id"] == entries[0]["run_id"]
    status, _, body = request(http_server, old["views"]["front"]["video_url"], headers={"Range": "bytes=0-2"})
    assert status == 206 and body == b"old"
    assert request(http_server, "/api/inspection/HELLO")[0] == 404
    assert request(http_server, "/inspection-media/HELLO/front.mp4")[0] == 404
    assert request(http_server, "/api/inspection/HELLO/3333333333333333")[0] == 404


def test_learning_routes_enforce_host_and_origin(http_server):
    assert request(http_server, "/api/learning", headers={"Host": "example.com"})[0] == 403
    payload = {"text": "Hello", "duration_scale": 1.0}
    assert request(http_server, "/api/learning/generate", payload,
                   {"Host": "example.com"})[0] == 403
    assert request(http_server, "/api/learning/generate", payload,
                   {"Origin": "https://example.com"})[0] == 403


@pytest.mark.parametrize("payload", [[], {}, {"text": 1}, {"text": "x" * 1001},
    {"text": "Hello", "duration_scale": "1.2"}, {"text": "Hello", "duration_scale": True},
    {"text": "Hello", "duration_scale": 1.1}])
def test_learning_request_schema_rejected_before_missing_model(http_server, payload):
    status, _, body = request(http_server, "/api/learning/generate", payload)
    assert status == 400 and "error" in json.loads(body)
    assert "kinematics" not in json.loads(body)


def test_learning_missing_model_is_unavailable_without_fallback(http_server):
    status, _, body = request(http_server, "/api/learning")
    assert status == 503 and json.loads(body)["error"] == "learning_experiment_unavailable"
    # The shared server error handler currently returns 500 for an absent
    # experiment during generation; the client must clear its prior result.
    status, _, body = request(http_server, "/api/learning/generate", {"text": "Hello"})
    result = json.loads(body)
    assert status == 500 and result["error"] == "FileNotFoundError"
    assert "positions_rad" not in result and "kinematics" not in result


def test_learning_rejection_works_even_without_model(http_server):
    status, _, body = request(http_server, "/api/learning/generate",
                              {"text": "Please wait and take two pills."})
    result = json.loads(body)
    assert status == 200 and result["accepted"] is False
    assert result["positions_rad"] is None and "kinematics" not in result
