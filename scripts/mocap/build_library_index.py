"""Write motions/studio_galt_v1/index.json: one entry per word for Groups 1 and 3.

    .venv/bin/python scripts/mocap/build_library_index.py

IDs follow Group 1's recommended_vocabulary.csv order (1-based). Review status is
the Group 2 visual/quantitative grade from results/mocap_previews (not ASL review).
"""
from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parents[2]
CLIPS = ROOT / "motions/studio_galt_v1"

# Group 2 review of overview.png, per-word sheets and summary.json.
APPROXIMATE = {
    "BALL": "two-hand shape: robot hands only touch, fingers cannot curve around a ball",
    "BOOK": "two-hand contact kept as touching; hands larger than human",
    "BUY": "right hand rests on, not in, the left palm",
    "CALM": "two hands close together; positions offset up to 5 cm",
    "CLEAN": "wiping contact kept as touching",
    "CLOSE": "hands meet edge to edge; offset up to 4 cm",
    "COOK": "flipping hand on palm kept as touching",
    "CUSTOMER": "hands near chest appear near the face (short robot neck)",
    "EVERYONE": "hands touch briefly; wrist offset up to 7 cm at that moment",
    "TWO": "index and middle cannot spread (reads as U-like two fingers)",
    "THREE": "fingers cannot spread; three raised digits still visible",
    "BABY": "crossed-forearm cradle is clear; large hands cannot reach the opposite elbow (orientation off ~0.8 rad)",
    "BEFORE": "hands stacked front-to-back at the midline as in the source; hand orientation off ~0.7 rad",
}
POOR = {}


def main():
    vocab = list(csv.DictReader(open(ROOT / "data/mocap/studio_galt_v1/recommended_vocabulary.csv", encoding="utf-8-sig")))
    entries = []
    for i, row in enumerate(vocab, start=1):
        word = row["word"]
        meta = json.loads((CLIPS / f"{word}.json").read_text())
        status = "poor" if word in POOR else "approximate" if word in APPROXIMATE else "usable"
        entries.append({
            "id": i, "gloss": word, "part_of_speech": row["part_of_speech"],
            "motion": f"motions/studio_galt_v1/{word}.npz", "duration_s": round(meta["duration_s"], 3),
            "core_frames": meta["core_frames"], "robot_status": status,
            "robot_note": POOR.get(word) or APPROXIMATE.get(word),
            "asl_reviewed": False,
        })
    index = {"schema_version": 1, "fps": 30, "neutral_start_end": True,
             "source": "Studio Galt Sign Language Mocap Archive (CC0-1.0), commit eb9046596fffcc6e92ee91d021372961f3d4fcaa",
             "status_scale": {"usable": "motion, position and handshape match the source",
                              "approximate": "recognisable, with a known robot limitation",
                              "poor": "noticeably wrong; fix or replace before a demo"},
             "words": entries}
    (CLIPS / "index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
    counts = {s: sum(e["robot_status"] == s for e in entries) for s in index["status_scale"]}
    print(f"{len(entries)} words: {counts}")


if __name__ == "__main__":
    main()
