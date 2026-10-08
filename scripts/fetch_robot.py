"""Fetch only pinned official model dependencies; preserve all originals in vendor/."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "5994d4faef0a9cadd3287f8de0199a67eeb2a259"
REPO = "https://github.com/unitreerobotics/unitree_ros"
BASE = f"https://raw.githubusercontent.com/unitreerobotics/unitree_ros/{COMMIT}"
MODEL = "g1_29dof_rev_1_0_with_inspire_hand_DFQ.urdf"
VENDOR = ROOT / "assets/robot/vendor"
MANIFEST = VENDOR.parent / "upstream_manifest.json"
EXPECTED = {}


def fetch(rel, upstream=None):
    path = VENDOR / rel
    url = BASE + "/" + (upstream or "robots/g1_description/" + rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with urllib.request.urlopen(url, timeout=60) as response:
            content = response.read()
        path.write_bytes(content)
    content = path.read_bytes()
    digest = sha256(content).hexdigest()
    if rel in EXPECTED and digest != EXPECTED[rel]:
        raise ValueError(f"Cached upstream file differs from recorded hash: {rel}; original vendor must remain unchanged")
    return {"file": rel, "url": url, "bytes": len(content), "sha256": digest}


def main():
    global EXPECTED
    if MANIFEST.exists():
        previous = json.loads(MANIFEST.read_text())
        if previous['commit'] != COMMIT:
            raise ValueError("Existing model has a different pinned commit; use a separate vendor directory")
        EXPECTED = {entry['file']: entry['sha256'] for entry in previous['files']}
    files = [fetch(MODEL), fetch("UPSTREAM_LICENSE", "LICENSE"), fetch("UPSTREAM_README.md", "robots/g1_description/README.md")]
    root = ET.parse(VENDOR / MODEL).getroot()
    meshes = sorted({mesh.get("filename") for mesh in root.findall(".//mesh")})
    with ThreadPoolExecutor(max_workers=6) as pool:
        files.extend(pool.map(fetch, meshes))
    manifest = {"repository": REPO, "commit": COMMIT, "model": MODEL, "files": files}
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Pinned {len(files)} files; {sum(f['bytes'] for f in files):,} bytes; commit {COMMIT}")


if __name__ == "__main__":
    main()
