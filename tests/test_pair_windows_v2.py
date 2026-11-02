from datetime import timedelta
import json

import pytest

from sign_robot.motion import ROOT
from sign_robot.pair_contract import file_hash, load_policy
from sign_robot.pair_windows import WindowApprovalError, load_window_approvals, select_pair_windows
from pair_v2_fixtures import NOW, seal_bundle, synthetic_inputs, write_json


def test_actual_policy_missing_approvals_stays_explicitly_blocked():
    policy = load_policy(ROOT / "config/transition_policy_v2.json", supported_versions=(1, 2))
    library = json.loads((ROOT / "library_manifest.json").read_text())
    with pytest.raises(WindowApprovalError) as error:
        load_window_approvals(ROOT, policy, library, now=NOW)
    assert error.value.code == "MISSING_APPROVAL_BUNDLE"


def test_valid_reviewed_windows_enumerate_and_self_pairs_keep_two_instances(tmp_path):
    policy, library, _, _ = synthetic_inputs(tmp_path)
    approvals = load_window_approvals(tmp_path, policy, library, now=NOW)
    selected = select_pair_windows("HELLO", "PLEASE", approvals, library, now=NOW)
    assert selected["source"]["allowed_frames"] == [6, 7]
    assert selected["target"]["allowed_frames"] == [2, 1]
    self_pair = select_pair_windows("HELLO", "HELLO", approvals, library, now=NOW)
    assert self_pair["word_occurrences"] == 2
    assert self_pair["source"]["instance_id"] != self_pair["target"]["instance_id"]
    assert self_pair["source"]["approval_sha256"] == self_pair["target"]["approval_sha256"]


@pytest.mark.parametrize("field,value,code", [
    ("status", "pending", "UNAPPROVED_WINDOW"),
    ("reviewer", " ", "UNAPPROVED_WINDOW"),
    ("motion_sha256", "0" * 64, "STALE_MOTION_APPROVAL"),
    ("frame_count", 10, "APPROVAL_FRAME_COUNT_MISMATCH"),
    ("protected_core_frames", [3, 9], "APPROVAL_FRAME_OUT_OF_BOUNDS"),
    ("entry_window_frames", [1, 4], "WINDOW_REMOVES_PROTECTED_CORE"),
    ("exit_window_frames", [4, 7], "WINDOW_REMOVES_PROTECTED_CORE"),
    ("valid_until", (NOW - timedelta(hours=1)).isoformat(), "EXPIRED_APPROVAL"),
    ("reviewed_at", (NOW + timedelta(days=1)).isoformat(), "APPROVAL_FROM_FUTURE"),
    ("reviewed_at", "2026-10-30T00:00:00", "INVALID_APPROVAL_TIME"),
])
def test_invalid_review_or_core_is_rejected(tmp_path, field, value, code):
    policy, library, _, bundle = synthetic_inputs(tmp_path)
    bundle["records"][0][field] = value
    seal_bundle(tmp_path, policy, bundle)
    with pytest.raises(WindowApprovalError) as error:
        load_window_approvals(tmp_path, policy, library, now=NOW)
    assert error.value.code == code


@pytest.mark.parametrize("corrupt", ["bundle", "evidence", "evidence_content", "actual_motion"])
def test_status_or_refreshed_hash_alone_cannot_hide_tampering(tmp_path, corrupt):
    policy, library, _, bundle = synthetic_inputs(tmp_path)
    if corrupt == "bundle":
        path = tmp_path / policy["endpoints"]["approval_file"]
        path.write_text(path.read_text() + " ")
    elif corrupt.startswith("evidence"):
        path = tmp_path / bundle["records"][0]["evidence_path"]
        value = json.loads(path.read_text())
        value["review"]["protected_core_frames"] = [2, 4]
        write_json(path, value)
        if corrupt == "evidence_content":
            bundle["records"][0]["evidence_sha256"] = file_hash(path)
            bundle_path = tmp_path / policy["endpoints"]["approval_file"]
            write_json(bundle_path, bundle)
            policy["endpoints"]["approval_bundle_sha256"] = file_hash(bundle_path)
    else:
        path = tmp_path / library["words"][0]["motion"]
        path.write_bytes(path.read_bytes() + b"mutation")
    with pytest.raises(WindowApprovalError) as error:
        load_window_approvals(tmp_path, policy, library, now=NOW)
    expected = {"bundle": "APPROVAL_BUNDLE_HASH_MISMATCH", "evidence": "APPROVAL_EVIDENCE_HASH_MISMATCH",
                "evidence_content": "APPROVAL_EVIDENCE_CONTENT_MISMATCH", "actual_motion": "STALE_MOTION_APPROVAL"}
    assert error.value.code == expected[corrupt]


def test_expiry_is_rechecked_at_selection_after_loading(tmp_path):
    policy, library, _, _ = synthetic_inputs(tmp_path)
    approvals = load_window_approvals(tmp_path, policy, library, now=NOW)
    with pytest.raises(WindowApprovalError, match="EXPIRED_APPROVAL"):
        select_pair_windows("HELLO", "PLEASE", approvals, library, now=NOW + timedelta(days=3))


def test_plain_dictionary_approved_string_is_not_an_approval_object(tmp_path):
    _, library, _, bundle = synthetic_inputs(tmp_path)
    with pytest.raises(WindowApprovalError, match="MISSING_WORD_APPROVAL"):
        select_pair_windows("HELLO", "PLEASE", {"HELLO": bundle["records"][0]}, library, now=NOW)


def test_unknown_word_and_duplicate_review_are_rejected(tmp_path):
    policy, library, _, bundle = synthetic_inputs(tmp_path)
    bundle["records"].append(dict(bundle["records"][0]))
    seal_bundle(tmp_path, policy, bundle)
    with pytest.raises(WindowApprovalError, match="DUPLICATE_APPROVAL"):
        load_window_approvals(tmp_path, policy, library, now=NOW)
    with pytest.raises(WindowApprovalError, match="UNKNOWN_GLOSS"):
        select_pair_windows("UNKNOWN", "PLEASE", {}, library, now=NOW)


def test_stale_window_version_and_escape_paths_fail(tmp_path):
    policy, library, _, bundle = synthetic_inputs(tmp_path)
    bundle["window_version"] = "stale"
    seal_bundle(tmp_path, policy, bundle)
    with pytest.raises(WindowApprovalError, match="STALE_WINDOW_VERSION"):
        load_window_approvals(tmp_path, policy, library, now=NOW)
    policy["endpoints"]["approval_file"] = "../outside.json"
    with pytest.raises(WindowApprovalError, match="INVALID_APPROVAL_INPUT"):
        load_window_approvals(tmp_path, policy, library, now=NOW)
