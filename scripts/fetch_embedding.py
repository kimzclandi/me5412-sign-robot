#!/usr/bin/env python3
"""Explicit anonymous download of one pinned public model; no token/cache lookup."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import ssl
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
FILES = ["config.json", "config_sentence_transformers.json", "modules.json",
         "sentence_bert_config.json", "special_tokens_map.json", "tokenizer.json",
         "tokenizer_config.json", "vocab.txt", "1_Pooling/config.json", "README.md",
         "model.safetensors"]


def load_expected(path: Path) -> dict | None:
    """Use the committed manifest as expectations, never as download output."""
    if not path.exists():
        return None
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("model_id") != MODEL_ID or manifest.get("revision") != REVISION:
        raise ValueError("Existing embedding manifest has a different model/revision")
    entries = manifest.get("files")
    if not isinstance(entries, list) or len(entries) != len(FILES):
        raise ValueError("Existing embedding manifest has an invalid file list")
    if any(not isinstance(item, dict) for item in entries):
        raise ValueError("Existing embedding manifest has an invalid file entry")
    if sorted(item.get("path", "") for item in entries) != sorted(FILES):
        raise ValueError("Existing embedding manifest paths differ from the pinned file list")
    for item in entries:
        if (not isinstance(item.get("sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
                or type(item.get("bytes")) is not int or item["bytes"] < 0):
            raise ValueError("Existing embedding manifest has an invalid hash/size")
    return manifest


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch_file(destination: Path, relative: str, expected: dict | None, context) -> dict:
    if relative not in FILES or (expected is not None and expected["path"] != relative):
        raise ValueError("File path is not in the pinned manifest")
    target = destination / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://huggingface.co/{MODEL_ID}/resolve/{REVISION}/{relative}"
    if expected is not None and target.exists():
        if target.stat().st_size != expected["bytes"] or file_digest(target) != expected["sha256"]:
            raise ValueError(f"Existing asset differs from recorded hash: {relative}; preserved unchanged")
        print(f"Verified existing {relative}", flush=True)
        return expected
    if target.exists():
        raise ValueError(f"No recorded hash for existing asset: {relative}; preserved unchanged")
    temporary = None
    try:
        print(f"Downloading {relative}", flush=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=target.name + ".", suffix=".part", delete=False) as output:
            temporary = Path(output.name)
            with urllib.request.urlopen(url, timeout=60, context=context) as response:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
        entry = {"path": relative, "bytes": temporary.stat().st_size,
                 "sha256": file_digest(temporary), "url": url}
        if expected is not None and any(entry[key] != expected[key] for key in ("bytes", "sha256")):
            raise ValueError(f"Downloaded asset differs from recorded hash: {relative}")
        temporary.replace(target)
        return expected if expected is not None else entry
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    manifest_path = ROOT / "config/embedding_download_manifest.json"
    expected_manifest = load_expected(manifest_path)
    destination = ROOT / "models/all-MiniLM-L6-v2"
    destination.mkdir(parents=True, exist_ok=True)
    try:
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        context = ssl.create_default_context()
    manifest = expected_manifest or {"model_id": MODEL_ID, "revision": REVISION,
                "source": f"https://huggingface.co/{MODEL_ID}/tree/{REVISION}",
                "download_mode": "anonymous HTTPS; no credential or HF cache access",
                "manifest_provenance": "First-time bootstrap from pinned revision; hashes newly recorded, not independently verified", "files": []}
    expected = {item["path"]: item for item in manifest["files"]}
    if expected_manifest is None:
        print("No recorded manifest: bootstrapping hashes from the fixed revision; this is not independent hash verification.", flush=True)
    for relative in FILES:
        entry = fetch_file(destination, relative, expected.get(relative), context)
        if expected_manifest is None:
            manifest["files"].append(entry)
    serialized = json.dumps(manifest, indent=2) + "\n"
    (destination / "download_manifest.json").write_text(serialized, encoding="utf-8")
    # Never rewrite committed expectations during restoration.
    if expected_manifest is None:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with manifest_path.open("x", encoding="utf-8") as stream:
            stream.write(serialized)
    print(f"Pinned model ready at {destination}; recorded expectations preserved", flush=True)


if __name__ == "__main__":
    main()
