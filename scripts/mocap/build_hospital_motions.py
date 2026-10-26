"""Map Group 1's 35-gloss hospital vocabulary to Group 2's motion library.

    .venv/bin/python scripts/mocap/build_hospital_motions.py [--vocab PATH]

Reads the hospital vocabulary (default: the snapshot of Group 1's
data/vocab/hospital_v1.json in data/mocap/) and motions/studio_galt_v1/index.json,
and writes motions/hospital_v1_motions.json: one entry per gloss with its clip,
frames and grade. motion_ready is true only when a clip exists and is not graded
poor; Group 1 copies these flags into their vocabulary for demo_only mode.
"""
from pathlib import Path
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "data/mocap/hospital_v1_vocab_snapshot.json"
LIBRARY = ROOT / "motions/studio_galt_v1/index.json"
OUT = ROOT / "motions/hospital_v1_motions.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vocab", type=Path, default=SNAPSHOT)
    args = parser.parse_args()
    vocab = json.loads(args.vocab.read_text(encoding="utf-8"))
    library = {w["gloss"]: w for w in json.loads(LIBRARY.read_text())["words"]}
    entries = []
    for item in vocab:
        gloss = item["gloss"]
        clip = library.get(gloss)
        ready = clip is not None and clip["robot_status"] != "poor"
        entries.append({
            "gloss": gloss, "motion_ready": ready, "planned_source": item.get("source"),
            "motion": clip["motion"] if clip else None,
            "core_frames": clip["core_frames"] if clip else None,
            "sign_frames": clip["sign_frames"] if clip else None,
            "robot_status": clip["robot_status"] if clip else "missing",
            "robot_note": clip["robot_note"] if clip else None,
        })
    ready = [e["gloss"] for e in entries if e["motion_ready"]]
    out = {"schema_version": 1, "vocab_file": args.vocab.name,
           "vocab_sha256": hashlib.sha256(args.vocab.read_bytes()).hexdigest(),
           "motion_library": str(LIBRARY.relative_to(ROOT)), "fps": 30,
           "motion_ready_count": len(ready), "glosses": entries}
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"{len(ready)}/{len(entries)} motion_ready: {' '.join(ready)}")
    print("missing:", " ".join(e["gloss"] for e in entries if not e["motion_ready"]))


if __name__ == "__main__":
    main()
