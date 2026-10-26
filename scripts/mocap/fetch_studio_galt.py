"""Download Studio Galt "No Mesh Full" FBX files from the pinned archive commit.

    .venv/bin/python scripts/mocap/fetch_studio_galt.py [WORD ...]

Files go to data/mocap/studio_galt_v1/raw/<WORD>/ (gitignored). The archive is
CC0-1.0. Each download is checked to be binary FBX and its SHA-256 recorded in
data/mocap/studio_galt_v1/fetch_manifest.json; an existing file must match it.
Group 1's original 27 words came in their archive and are not listed here.
"""
from pathlib import Path
import hashlib
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/mocap/studio_galt_v1/raw"
MANIFEST = ROOT / "data/mocap/studio_galt_v1/fetch_manifest.json"
COMMIT = "eb9046596fffcc6e92ee91d021372961f3d4fcaa"
BASES = (f"https://raw.githubusercontent.com/StudioGalt/Sign-Language-Mocap-Archive/{COMMIT}/",
         f"https://media.githubusercontent.com/media/StudioGalt/Sign-Language-Mocap-Archive/{COMMIT}/")  # if stored in LFS
D = "SG ASL Dictionary"
# Hospital-vocabulary words available in Studio Galt (gloss names as in hospital_v1.json).
SOURCES = {
    "HELLO": f"{D}/ASL H/SG ASL Hello 2024-6-9 Upload/FBX Files/Research/SG ASL Hello 2024-6-9 No Mesh Full.fbx",
    "PLEASE": f"{D}/ASL P/SG ASL Please 2024-10-13 Upload/FBX Files/Research/SG ASL Please 2024-10-13 No Mesh Full.fbx",
    "APPOINTMENT": f"{D}/ASL A/SG ASL Appointment 1 2023-7-29 Upload/SG ASL Appointment 1 2023-7-29 No Mesh Full.fbx",
    "BREATHE-DEEP": f"{D}/ASL B/SG ASL Breathe Deep 2024-7-24 Upload/FBX Files/Research/SG ASL Breathe Deep 2024-7-24 No Mesh Full.fbx",
    "BLOOD-DRAW": f"{D}/ASL B/SG ASL Blood Draw 2 2024-5-15 Upload/FBX Files/Research/SG ASL Blood Draw 2 2024-5-15 No Mesh Full.fbx",
    "WHERE": f"{D}/ASL W/SG ASL Where Var 2025-7-24 Upload/FBX Files/Full/SG ASL Where Var 2025-7-24 No Mesh Full.fbx",
}


def download(path):
    for base in BASES:
        try:
            with urllib.request.urlopen(base + urllib.parse.quote(path), timeout=120) as response:
                content = response.read()
        except urllib.error.HTTPError:
            continue
        if content.startswith(b"Kaydara FBX Binary"):
            return content
    raise RuntimeError(f"Not a binary FBX (LFS pointer?): {path}")


def main():
    words = [w.upper() for w in sys.argv[1:]] or list(SOURCES)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"repository_commit": COMMIT, "files": {}}
    for word in words:
        path = SOURCES[word]
        target = RAW / word / Path(path).name
        if target.exists():
            content = target.read_bytes()
        else:
            content = download(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        recorded = manifest["files"].get(word, {}).get("sha256")
        if recorded and recorded != digest:
            raise ValueError(f"{word}: file differs from recorded SHA-256")
        manifest["files"][word] = {"repository_path": path, "bytes": len(content), "sha256": digest}
        print(f"{word}: {len(content):,} bytes {digest[:12]}")
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
