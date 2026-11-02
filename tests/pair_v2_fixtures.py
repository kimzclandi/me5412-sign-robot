"""Synthetic v2 approval files for tests only; never real group-2 approval."""
from datetime import datetime, timedelta, timezone
import json

import numpy as np

from sign_robot.motion import ROOT
from sign_robot.pair_contract import file_hash, json_hash, load_policy
from sign_robot.pair_windows import approval_review_payload

NOW = datetime(2026, 10, 31, 0, 0, tzinfo=timezone.utc)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, allow_nan=False) + "\n")


def synthetic_inputs(root):
    policy = load_policy(ROOT / "config/transition_policy_v2.json", supported_versions=(1, 2))
    names = np.asarray(json.loads((ROOT / "library_manifest.json").read_text())["joint_names"])
    words = []
    records = []
    clips = {}
    for gloss in ("HELLO", "PLEASE"):
        path = root / "motions" / f"{gloss}.npz"
        path.parent.mkdir(parents=True, exist_ok=True)
        q = np.zeros((9, 53))
        motion = {"positions": q, "timestamps_s": np.arange(9) / 30, "joint_names": names}
        np.savez(path, **motion)
        clips[gloss] = motion
        words.append({"gloss": gloss, "motion": str(path.relative_to(root)),
                      "motion_sha256": file_hash(path), "frames": 9, "sign_frames": [2, 6]})
        record = {
            "approval_id": f"synthetic-test-{gloss}", "gloss": gloss,
            "motion_sha256": file_hash(path), "frame_count": 9,
            "protected_core_frames": [3, 5], "entry_window_frames": [1, 2],
            "exit_window_frames": [6, 7], "retiming_allowed": False,
            "status": "approved", "reviewer": "synthetic unit-test fixture; not a real reviewer",
            "reviewed_at": (NOW - timedelta(days=1)).isoformat(),
            "valid_until": (NOW + timedelta(days=2)).isoformat(),
            "evidence_path": f"reviews/{gloss}.json", "evidence_sha256": "0" * 64,
        }
        records.append(record)
    bundle = {"schema_version": 2, "bundle_id": "synthetic-test-only",
              "window_version": policy["endpoints"]["window_version"], "records": records}
    policy["endpoints"]["approval_file"] = "reviews/bundle.json"
    seal_bundle(root, policy, bundle)
    library = {"words": words, "joint_names": names.tolist()}
    return policy, library, clips, bundle


def seal_bundle(root, policy, bundle):
    for record in bundle["records"]:
        evidence = {"schema_version": 2, "kind": "group2_core_window_review",
                    "review": approval_review_payload(record)}
        path = root / record["evidence_path"]
        write_json(path, evidence)
        record["evidence_sha256"] = file_hash(path)
    bundle_path = root / policy["endpoints"]["approval_file"]
    write_json(bundle_path, bundle)
    policy["endpoints"]["approval_bundle_sha256"] = file_hash(bundle_path)
