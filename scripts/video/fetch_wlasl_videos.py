"""Download public ASL dictionary videos listed in WLASL for the given glosses.

    .venv/bin/python scripts/video/fetch_wlasl_videos.py [GLOSS ...] [--per-gloss 4]

WLASL (https://github.com/dxli94/WLASL, C-UDA licence, academic use) indexes
sign videos hosted by third-party ASL dictionaries. Only direct-file sources
that still respond are used (no YouTube). Videos are kept locally in
data/video/wlasl/raw/<GLOSS>/ (gitignored, never committed); only their URL,
source, WLASL ids, frame range and SHA-256 go into data/video/wlasl/manifest.json.
"""
from pathlib import Path
import argparse
import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
INDEX_URL = "https://raw.githubusercontent.com/dxli94/WLASL/master/start_kit/WLASL_v0.3.json"
INDEX = ROOT / "data/video/wlasl/WLASL_v0.3.json"
RAW = ROOT / "data/video/wlasl/raw"
MANIFEST = ROOT / "data/video/wlasl/manifest.json"
# Single-signer dictionary hosts that served files in Oct 2026, in preference order.
SOURCES = ("files.startasl.com", "media.spreadthesign.com", "media.asldeafined.com",
           "signstock.blob.core.windows.net", "aslbricks.org")
HOSPITAL_MISSING = ["THANK-YOU", "SORRY", "YES", "NO", "YOUR", "ME", "DEAF", "DOCTOR", "NURSE",
                    "INTERPRETER", "MEDICINE", "STOMACH", "HEADACHE", "HAVE", "NEED", "WAIT", "HURT",
                    "UNDERSTAND", "WRITE", "NOT", "NOW", "SOON", "LATER", "TOMORROW", "MORNING", "NIGHT"]
VALIDATION = ["YOU", "COME", "TAKE", "HELLO", "PLEASE", "WHERE"]  # also have mocap clips


def source_of(url):
    host = urllib.parse.urlparse(url).netloc
    path = urllib.parse.urlparse(url).path
    if host.startswith("s3-") and "/files.startasl.com/" in path:
        return "files.startasl.com"
    return host


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research; WLASL index)"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content = response.read()
    except (urllib.error.URLError, TimeoutError):
        return None
    return content if content[4:8] == b"ftyp" else None  # an MP4 container, not an error page


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("glosses", nargs="*")
    parser.add_argument("--per-gloss", type=int, default=4)
    args = parser.parse_args()
    if not INDEX.exists():
        INDEX.parent.mkdir(parents=True, exist_ok=True)
        INDEX.write_bytes(urllib.request.urlopen(INDEX_URL, timeout=60).read())
    wlasl = {e["gloss"]: e["instances"] for e in json.loads(INDEX.read_text())}
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {
        "index": INDEX_URL, "index_sha256": hashlib.sha256(INDEX.read_bytes()).hexdigest(), "videos": {}}
    for gloss in [g.upper() for g in args.glosses] or HOSPITAL_MISSING + VALIDATION:
        instances = [i for i in wlasl[gloss.lower().replace("-", " ")] if source_of(i["url"]) in SOURCES]
        instances.sort(key=lambda i: SOURCES.index(source_of(i["url"])))
        got = manifest["videos"].setdefault(gloss, [])
        for inst in instances:
            if len(got) >= args.per_gloss or any(v["video_id"] == inst["video_id"] for v in got):
                continue
            content = fetch(inst["url"])
            if content is None:
                continue
            target = RAW / gloss / f"{inst['video_id']}.mp4"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            got.append({"video_id": inst["video_id"], "url": inst["url"], "source": source_of(inst["url"]),
                        "signer_id": inst.get("signer_id"), "frame_start": inst["frame_start"],
                        "frame_end": inst["frame_end"], "fps": inst.get("fps"),
                        "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
        print(f"{gloss:12s} {len(got)} videos: {', '.join(v['source'] for v in got)}")
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
