"""Group 2's clips-v2 replaced 24 word clips, so protection bundles v1-v3 are stale on this branch.

Tests of a historical policy rebind it in memory to bundle v5, the user's intervals on these clips (TASK-29); every
other policy field stays as frozen and no policy file is rewritten.
"""
import copy
import json

from sign_robot.motion import ROOT
from sign_robot.pair_contract import file_hash
from sign_robot.sequence_contract import load_sequence_policy

BUNDLE = "config/user_protected_hospital35_v5.json"


def on_clips_v2(policy):
    rebound = copy.deepcopy(policy)
    window = json.loads((ROOT / BUNDLE).read_text(encoding="utf-8"))["window_version"]
    rebound["endpoints"].update(window_version=window, protection_file=BUNDLE,
                                protection_bundle_sha256=file_hash(ROOT / BUNDLE))
    return rebound


def load_sequence_policy_on_clips_v2(root, path):
    policy, pair_policy = load_sequence_policy(root, path)
    return policy, on_clips_v2(pair_policy)
