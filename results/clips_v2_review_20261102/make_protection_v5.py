"""Protection bundle v5: the user's new INTERPRETER interval f19-f40 on the group2/clips-v2 clip; HAVE keeps f24-f54.

User decisions in chat (2026-11-02), after watching the clips-v2 renders of the two sentence words whose v4 boundary poses
had changed: INTERPRETER is protected f19-f40 (was f30-f60); HAVE keeps its interval. Every other record is v4's (NURSE
f23-f79, HURT f37-f57, MORNING f26-f37, all bound to the clips-v2 motions). This writes v5 from v4 and loads it with the
planner's own loader against this branch's library (in memory; no policy file is written). Writes, once:
  config/user_protected_hospital35_v5.json
Run from the repository root: <python> results/clips_v2_review_20261102/make_protection_v5.py
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sign_robot.pair_contract import freeze_library, load_policy  # noqa: E402
from sign_robot.pair_windows import load_user_protections  # noqa: E402

SOURCE = "config/user_protected_hospital35_v4.json"
TARGET = "config/user_protected_hospital35_v5.json"
POLICY = "config/transition_policy_hospital_sentences_fast_v5.json"
WINDOW_VERSION = "hospital35-user-protection-20261102-v5"
# floor(0.64 * 30) = 19, ceil(1.33 * 30) = 40
INTERPRETER = {"start_s": 0.64, "end_s": 1.33, "frames": [19, 40]}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    bundle = json.loads((ROOT / SOURCE).read_text(encoding="utf-8"))
    bundle.update(bundle_id="user-protection-hospital35-20261102-v5", window_version=WINDOW_VERSION,
                  source_instruction=bundle["source_instruction"] + (
                      " v5 (2026-11-02): after re-rendering the two sentence words whose boundary poses changed on "
                      "clips-v2, the user protected INTERPRETER f19-f40 and kept HAVE f24-f54."))
    for record in bundle["records"]:
        if record["gloss"] == "INTERPRETER":
            old = record["user_interval_text"]
            record.update(protection_id="hospital35-20261102-v5-INTERPRETER",
                          user_interval_s=[INTERPRETER["start_s"], INTERPRETER["end_s"]],
                          protected_core_frames=INTERPRETER["frames"],
                          user_interval_text=f"{INTERPRETER['start_s']}–{INTERPRETER['end_s']} s (user chat 2026-11-02 on "
                                             f"the group2/clips-v2 clip: f19–f40; was {old})",
                          binding_basis=record["binding_basis"] + "; interval re-set by the user in chat on 2026-11-02 "
                                                                   "after watching the clips-v2 render")
    with (ROOT / TARGET).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n")

    policy = load_policy(ROOT / POLICY, supported_versions=(1, 2))
    policy["endpoints"].update(window_version=WINDOW_VERSION, protection_file=TARGET,
                               protection_bundle_sha256=sha(ROOT / TARGET))
    library, _ = freeze_library(ROOT, policy)
    protections = load_user_protections(ROOT, policy, library)
    expected = {"INTERPRETER": (19, 40), "HAVE": (24, 54), "NURSE": (23, 79), "HURT": (37, 57), "MORNING": (26, 37)}
    if any(protections[g].protected_core_frames != frames for g, frames in expected.items()):
        raise SystemExit("v5 did not load as intended")
    print(json.dumps({"bundle_sha256": sha(ROOT / TARGET), "records": len(protections),
                      **{g: list(protections[g].protected_core_frames) for g in expected}}))


if __name__ == "__main__":
    main()
