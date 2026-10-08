#!/usr/bin/env python3
"""Launch an existing read-only local MLX model on 127.0.0.1:5413."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    config_path = ROOT / "config/local_runtime.json"
    if not config_path.is_file():
        raise SystemExit("Set existing local paths in config/local_runtime.json; see local_runtime.example.json. Nothing is downloaded automatically.")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    # Preserve the venv executable path: resolving its symlink would invoke the
    # base interpreter and lose the existing mlx-lm environment.
    python = Path(config["python"]).expanduser().absolute()
    model = Path(config["model_path"]).expanduser().resolve()
    if not python.is_file() or not (model / "model.safetensors").is_file():
        raise SystemExit("Configured local Python or model.safetensors does not exist. No installation was attempted.")
    digest = hashlib.sha256()
    with (model / "model.safetensors").open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    if digest.hexdigest() != config["expected_model_sha256"]:
        raise SystemExit("Existing model hash differs from local_runtime.json; refusing an unrecorded model change.")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 5413)) == 0:
            raise SystemExit("Port 5413 already has a listener. Reuse or stop that service explicitly; no process was replaced.")
    # Keep existing runtime/model files unchanged; disable bytecode, downloads,
    # implicit authentication, and hub telemetry for this local-only process.
    environment = os.environ.copy()
    environment.update({"PYTHONDONTWRITEBYTECODE": "1", "HF_HUB_OFFLINE": "1",
                        "TRANSFORMERS_OFFLINE": "1", "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1",
                        "HF_HUB_DISABLE_TELEMETRY": "1", "DO_NOT_TRACK": "1"})
    command = [str(python), "-m", "mlx_lm.server", "--model", str(model),
               "--host", "127.0.0.1", "--port", "5413", "--temp", "0",
               "--max-tokens", "100", "--log-level", "INFO"]
    os.chdir(ROOT)
    print("Starting existing local MLX model on http://127.0.0.1:5413; Ctrl+C stops it.", flush=True)
    print("API model alias: default_model. Existing weights and environment are not modified.", flush=True)
    os.execve(python, command, environment)


if __name__ == "__main__":
    main()
