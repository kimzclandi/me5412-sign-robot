"""Protection bundle v4 for group2/clips-v2: the user's new NURSE interval f23-f79, every record bound to the new clips.

Group 2 (2026-11-02) asked Group 3 to continue on a new branch from group2/clips-v2 (85bc230): 24 video-derived clips
changed (NURSE re-derived, 23 others collision-repaired), every frame count unchanged. User decisions in chat
(2026-11-02): the new NURSE is protected f23-f79 (first f23-f80; frame 80 starts the last wrist tap with the right thumb
already on the left wrist, so the user dropped that tap); the other words keep their v3 intervals after the boundary
review in this directory. v3 (round 9 on group3/trajectory-planning: HURT from frame 37) is carried over unchanged. This
writes v4 from v3 with the NURSE record replaced and the 24 changed clips' hashes re-bound, then loads it with the planner's
own loader against this branch's library (in memory, round-8 policy fields only; no policy file is written). Writes, once:
  config/user_protected_hospital35_v4.json
  results/clips_v2_review_20261102/rebinding.json
Run from the repository root: <python> results/clips_v2_review_20261102/make_protection_v4.py
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from sign_robot.pair_contract import freeze_library, load_policy, read_motion  # noqa: E402
from sign_robot.pair_windows import load_user_protections  # noqa: E402

SOURCE = "config/user_protected_hospital35_v3.json"
TARGET = "config/user_protected_hospital35_v4.json"
POLICY = "config/transition_policy_hospital_sentences_fast_v5.json"
CLIPS = "group2/clips-v2 85bc230"
WINDOW_VERSION = "hospital35-user-protection-20261102-v4"
# floor(0.77 * 30) = 23, ceil(2.63 * 30) = 79
NURSE = {"start_s": 0.77, "end_s": 2.63, "frames": [23, 79]}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    path = Path(path)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def main():
    bundle = json.loads((ROOT / SOURCE).read_text(encoding="utf-8"))
    bundle.update(bundle_id="user-protection-hospital35-20261102-v4", window_version=WINDOW_VERSION,
                  source_instruction=bundle["source_instruction"] + (
                      f" v4 (2026-11-02): records bound to the {CLIPS} clips; the user protected the new NURSE f23-f79 "
                      "in chat; every other interval is unchanged from v3 after the user's boundary review."))
    rebound = []
    for record in bundle["records"]:
        path = ROOT / record["motion"]
        if len(read_motion(path)["positions"]) != record["frame_count"]:
            raise SystemExit(f"{record['gloss']}: frame count changed")
        new_hash = sha(path)
        if new_hash != record["motion_sha256"]:
            rebound.append({"gloss": record["gloss"], "motion": record["motion"], "old_sha256": record["motion_sha256"],
                            "new_sha256": new_hash, "interval_frames": record["protected_core_frames"]})
            record.update(motion_sha256=new_hash, protection_id=f"hospital35-20261102-v4-{record['gloss']}",
                          binding_basis=record["binding_basis"] + f"; re-bound to the {CLIPS} motion on 2026-11-02, "
                                                                   "interval unchanged after the user's boundary review")
        if record["gloss"] == "NURSE":
            old = record["user_interval_text"]
            record.update(user_interval_s=[NURSE["start_s"], NURSE["end_s"]], protected_core_frames=NURSE["frames"],
                          user_interval_text=f"{NURSE['start_s']}–{NURSE['end_s']} s (user chat 2026-11-02 on the "
                                             f"{CLIPS} NURSE: f23–f79; the old clip's interval was {old})",
                          binding_basis=f"user chat 2026-11-02 on the {CLIPS} NURSE (sha256 {new_hash}) + inclusive "
                                        "outward rounding; the user first gave f23-f80 and moved the end to f79 "
                                        "(frame 80 starts the last wrist tap, right thumb on the left wrist)")
            rebound[-1]["interval_frames"] = NURSE["frames"]
    write_new(ROOT / TARGET, bundle)

    policy = load_policy(ROOT / POLICY, supported_versions=(1, 2))
    policy["endpoints"].update(window_version=WINDOW_VERSION, protection_file=TARGET,
                               protection_bundle_sha256=sha(ROOT / TARGET))
    library, _ = freeze_library(ROOT, policy)
    protections = load_user_protections(ROOT, policy, library)
    if protections["NURSE"].protected_core_frames != (23, 79) or protections["HURT"].protected_core_frames != (37, 57):
        raise SystemExit("v4 did not load as intended")
    write_new(OUT / "rebinding.json", {
        "schema_version": 1, "bundle": TARGET, "bundle_sha256": sha(ROOT / TARGET), "source_bundle": SOURCE,
        "clips": CLIPS, "loaded_records": len(protections), "rebound_records": rebound})
    print(json.dumps({"bundle_sha256": sha(ROOT / TARGET), "records": len(protections), "rebound": len(rebound),
                      "NURSE": list(protections["NURSE"].protected_core_frames)}))


if __name__ == "__main__":
    main()
