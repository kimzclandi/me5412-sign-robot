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
