"""Local-only demo server. Inference is local; media is MuJoCo-rendered offline."""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone
from threading import Lock

from .contracts import ROOT, load_catalog
from .pipeline import run_selection, resolve_execution
from . import inspection
from .service import instance_id

LOG_LOCK = Lock()


def project_status() -> dict:
    catalog = load_catalog()
    return {
        "project": "ME5412 robot ASL research prototype",
        "catalog": catalog,
        "sources": json.loads((ROOT / "data/source_manifest.json").read_text(encoding="utf-8"))["sources"],
        "motions": {a["action_id"]: {
            "trajectory": (ROOT / f'motions/{a["action_id"]}.npz').is_file(),
            "preview": (ROOT / f'results/previews/{a["action_id"]}.mp4').is_file(),
            "poster": (ROOT / f'results/previews/{a["action_id"]}.png').is_file(),
        } for a in catalog},
        "limits": ["候选 ASL 动作未经使用者评审", "运动学回放不证明动力学控制可行", "仅支持登记的完整含义"],
    }


class Handler(BaseHTTPRequestHandler):
    def send_json(self, value, code=200):
        data = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def allowed_host(self):
        host = self.headers.get("Host", "")
        port = self.server.server_address[1]
        return host in {f"127.0.0.1:{port}", f"localhost:{port}"}

    def do_GET(self):
        if not self.allowed_host():
            return self.send_json({"error": "invalid_host"}, 403)
        route = urlparse(self.path).path
        if route == "/api/health":
            return self.send_json({"project_id": "me5412-sign-robot", "status": "ok", "pid": os.getpid(),
                                   "instance_id": instance_id(ROOT), "server_revision": "learning-v1"})
        if route == "/api/status":
            return self.send_json(project_status())
        if route == "/api/evidence":
            path = ROOT / "results/acceptance.json"
            return self.send_json(json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"status": "in_progress"})
        if route == "/api/learning":
            from .learning_api import status
            try:
                return self.send_json(status(ROOT))
            except (OSError, ValueError, KeyError):
                return self.send_json({"error": "learning_experiment_unavailable"}, 503)
        if route == "/api/inspection" or route.startswith("/api/inspection/"):
            try:
                if route == "/api/inspection":
                    value = inspection.inventory(ROOT)
                else:
                    matched = re.fullmatch(r"/api/inspection/([A-Z_]+)/([0-9a-f]{16})", route)
                    if not matched:
                        return self.send_json({"error": "not_found"}, 404)
                    action_id, run_id = matched.groups()
                    value = inspection.telemetry(action_id, ROOT, run_id=run_id)
                return self.send_json(value)
            except (ValueError, KeyError, OSError) as exc:
                return self.send_json({"error": "inspection_unavailable", "message": str(exc)}, 404)
        static = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css", "/inspector.js": "inspector.js", "/learning.js": "learning.js"}
        if route in static:
            path = ROOT / "web" / static[route]
        elif route.startswith("/inspection-media/"):
            matched = re.fullmatch(r"/inspection-media/([A-Z_]+)/([0-9a-f]{16})/(front|right_side)\.(mp4|png)", route)
            if not matched:
                return self.send_json({"error": "not_found"}, 404)
            try:
                action_id, run_id, view, extension = matched.groups()
                path = inspection.media(action_id, view, extension, root=ROOT, run_id=run_id)
            except (ValueError, KeyError, OSError) as exc:
                return self.send_json({"error": "inspection_unavailable", "message": str(exc)}, 404)
        else:
            valid_media = {f'/media/{a["action_id"]}.{ext}': ROOT / f'results/previews/{a["action_id"]}.{ext}'
                           for a in load_catalog() for ext in ("mp4", "png")}
            if route not in valid_media:
                return self.send_json({"error": "not_found"}, 404)
            path = valid_media[route]
        if not path.is_file():
            return self.send_json({"error": "not_generated"}, 404)
        # Byte ranges permit seeking in locally rendered videos.
        size = path.stat().st_size
        start, end, partial = 0, size - 1, False
        requested = self.headers.get("Range", "")
        if requested:
            match = re.fullmatch(r"bytes=(\d+)-(\d*)", requested)
            if not match:
                return self.send_json({"error": "invalid_range"}, 416)
            start = int(match[1]); end = min(int(match[2]) if match[2] else size - 1, size - 1)
            if start > end:
                return self.send_json({"error": "invalid_range"}, 416)
            partial = True
        self.send_response(206 if partial else 200)
        self.send_header("Content-Type", mimetypes.guess_type(str(path))[0] or "application/octet-stream")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("X-Content-Type-Options", "nosniff")
        if partial:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with path.open("rb") as stream:
            stream.seek(start)
            self.wfile.write(stream.read(end - start + 1))

    def do_POST(self):
        if not self.allowed_host():
            return self.send_json({"error": "invalid_host"}, 403)
        port = self.server.server_address[1]
        origin = self.headers.get("Origin")
        if origin is not None and origin not in {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}:
            return self.send_json({"error": "invalid_origin"}, 403)
        if self.path not in {"/api/select", "/api/action", "/api/learning/generate"}:
            return self.send_json({"error": "not_found"}, 404)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 8192:
                return self.send_json({"error": "invalid_length"}, 413)
            req = json.loads(self.rfile.read(length))
            if not isinstance(req, dict):
                raise ValueError("Expected JSON object")
            if self.path == "/api/learning/generate":
                from .learning_api import generate_request
                return self.send_json(generate_request(req, ROOT))
            allow = req.get("allow_candidate_preview", False)
            if type(allow) is not bool:
                raise ValueError("allow_candidate_preview must be boolean")
            if self.path == "/api/select":
                if not isinstance(req.get("text"), str) or len(req["text"]) > 1000:
                    raise ValueError("text must be a string of at most 1000 characters")
                if req.get("method", "exact") not in {"exact", "embedding", "llm"}:
                    raise ValueError("Unknown method")
                result = run_selection(req["text"], req.get("method", "exact"), allow)
            else:
                selection = {"status": "execute", "action_id": req.get("action_id"),
                             "method": "button", "reason_code": "explicit_phrase_choice", "latency_ms": 0}
                result = {"selection": selection,
                          "execution": resolve_execution(selection, allow_candidate_preview=allow)}
            log = {"time_utc": datetime.now(timezone.utc).isoformat(), "request": req, "result": result}
            with LOG_LOCK:
                folder = ROOT / "results/session_logs"
                folder.mkdir(exist_ok=True, parents=True)
                with (folder / "demo.jsonl").open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(log, ensure_ascii=False) + "\n")
            return self.send_json(result)
        except (ValueError, TypeError, KeyError) as exc:
            return self.send_json({"error": str(exc)}, 400)
        except Exception as exc:
            # No fallback action is permitted on an inference or model error.
            return self.send_json({"error": type(exc).__name__, "message": str(exc)}, 500)

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5412)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"ME5412 demo: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
