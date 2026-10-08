"""Start a detached, loopback-only demo and manage only the process we recorded."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

from .contracts import ROOT


def instance_id(root=ROOT):
    return hashlib.sha256(str(Path(root).resolve()).encode()).hexdigest()[:16]


def probe(port):
    try:
        with build_opener(ProxyHandler({})).open(f"http://127.0.0.1:{port}/api/health", timeout=1) as response:
            value = json.load(response)
        return value if isinstance(value, dict) else None
    except (OSError, URLError, ValueError):
        return None


def matches(value):
    return bool(value and value.get("project_id") == "me5412-sign-robot"
                and value.get("instance_id") == instance_id() and value.get("status") == "ok")


def state_path(port):
    return ROOT / "results/session_logs" / f"service-{port}.json"


@contextmanager
def management_lock(port):
    path = state_path(port).with_suffix(".lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def start(port=5412):
    with management_lock(port):
        status = probe(port)
        if matches(status):
            return {"state": "already_running", "pid": status["pid"], "url": f"http://127.0.0.1:{port}/"}
        # A listener that lacks this project's health identity must be left alone.
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                raise RuntimeError(f"Port {port} is occupied by another or older service; no process was stopped")
        except ConnectionRefusedError:
            pass
        log_path = state_path(port).with_suffix(".log")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
        # Interactive demo always uses the default configuration, never an inherited research override.
        env.pop("SIGN_ROBOT_LLM_CONFIG", None)
        with log_path.open("ab") as log:
            process = subprocess.Popen([sys.executable, "-u", "-m", "sign_robot.server", "--port", str(port)],
                                       cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True, close_fds=True)
        for _ in range(80):
            status = probe(port)
            if matches(status) and status.get("pid") == process.pid:
                state_path(port).write_text(json.dumps({"pid": process.pid, "instance_id": instance_id(),
                                                       "port": port}, indent=2) + "\n", encoding="utf-8")
                return {"state": "started", "pid": process.pid, "url": f"http://127.0.0.1:{port}/",
                        "log": str(log_path.relative_to(ROOT))}
            if process.poll() is not None:
                raise RuntimeError(f"Demo exited during startup. Read {log_path}")
            time.sleep(0.1)
        process.terminate()
        process.wait(timeout=3)
        raise RuntimeError(f"Demo did not become ready. Read {log_path}")


def stop(port=5412):
    with management_lock(port):
        status = probe(port)
        if not status:
            return {"state": "not_running", "port": port}
        path = state_path(port)
        if not matches(status) or not path.is_file():
            raise RuntimeError("This process is not managed by this launcher; no signal was sent")
        saved = json.loads(path.read_text(encoding="utf-8"))
        pid = saved.get("pid")
        if (type(pid) is not int or pid <= 1 or saved.get("instance_id") != instance_id()
                or saved.get("port") != port or pid != status.get("pid")):
            raise RuntimeError("Saved process identity does not match; no signal was sent")
        os.kill(pid, signal.SIGTERM)
        for _ in range(40):
            if not matches(probe(port)):
                path.unlink(missing_ok=True)
                return {"state": "stopped", "pid": pid, "port": port}
            time.sleep(.1)
        raise RuntimeError("Stop requested but the service is still responding; no force kill attempted")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "status", "stop"), nargs="?", default="start")
    parser.add_argument("--port", type=int, default=5412)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    try:
        if args.action == "start":
            value = start(args.port)
        elif args.action == "stop":
            value = stop(args.port)
        else:
            status = probe(args.port)
            value = {"state": "running" if matches(status) else "unavailable",
                     "url": f"http://127.0.0.1:{args.port}/", "health": status}
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0 if value["state"] != "unavailable" else 1
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"演示服务未完成操作：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
