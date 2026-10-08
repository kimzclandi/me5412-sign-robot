"""Lifecycle checks address the actual disappeared-server failure."""
import json
import socket
import pytest
from sign_robot import service


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def test_detached_service_survives_start_and_reuses_identity():
    port = free_port()
    started = service.start(port)
    try:
        assert started["state"] == "started"
        assert service.matches(service.probe(port))
        reused = service.start(port)
        assert reused["state"] == "already_running" and reused["pid"] == started["pid"]
        stopped = service.stop(port)
        assert stopped["state"] == "stopped" and stopped["pid"] == started["pid"]
        assert service.probe(port) is None
    finally:
        if service.matches(service.probe(port)):
            service.stop(port)


def test_occupied_port_is_not_replaced():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0)); listener.listen()
        port = listener.getsockname()[1]
        with pytest.raises(RuntimeError, match="occupied"):
            service.start(port)


def test_stop_requires_matching_saved_pid(tmp_path, monkeypatch):
    path=tmp_path / "process.json"
    path.write_text(json.dumps({"pid": 123, "instance_id": service.instance_id(), "port": 5499}))
    monkeypatch.setattr(service, "state_path", lambda port:path)
    monkeypatch.setattr(service, "probe", lambda port:{"project_id":"me5412-sign-robot", "status":"ok", "instance_id":service.instance_id(), "pid":456})
    def do_not_kill(*args):
        raise AssertionError("Must not signal a mismatched process")
    monkeypatch.setattr(service.os, "kill", do_not_kill)
    with pytest.raises(RuntimeError, match="does not match"):
        service.stop(5499)
