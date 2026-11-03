"""Frozen hospital35 scope: exclusive pair batches, the 111 sequence cases and code identity coverage."""
import pytest

import sign_robot.pair_contract as contract
from sign_robot.batch_control import load_batch_manifest
from sign_robot.motion import ROOT
from sign_robot.pair_contract import file_hash, freeze_library, load_policy, pair_universe, read_json, run_identity
from sign_robot.sequence_contract import load_sequence_policy, sequence_glosses

RUN = "results/hospital35_protected_20261101_001"
PAIR_POLICY = "config/transition_policy_user_protected_hospital35_v1.json"
SEQUENCE_POLICY = "config/sequence_policy_hospital35_v1.json"
NEW_SCRIPTS = ("scripts/import_user_protections.py", "scripts/preflight_hospital35.py", "scripts/run_hospital35_batches.py")


def test_pair_batches_are_exclusive_bounded_and_cover_the_universe():
    policy = load_policy(ROOT / PAIR_POLICY, supported_versions=(2,))
    universe = [p["pair_id"] for p in pair_universe(policy["scope"]["expected_glosses"])]
    path = f"{RUN}/batches/manifest.json"
    manifest, batches = load_batch_manifest(ROOT, path, file_hash(ROOT / path), universe, PAIR_POLICY)
    groups = {}
    for batch in batches.values():
        groups.setdefault(batch["group"], []).extend(batch["pair_ids"])
        assert len(batch["pair_ids"]) <= 16
    assert {g: len(p) for g, p in groups.items()} == {"regression": 4, "self": 33, "hub": 132, "rest": 1056}
    assert sorted(sum(groups.values(), [])) == sorted(universe) and len(universe) == 1225
    assert groups["regression"] == ["COME__NOW", "NOW__COME", "COME__COME", "NOW__NOW"]
    assert all(p.split("__")[0] == p.split("__")[1] not in ("COME", "NOW") for p in groups["self"])
    assert all(("COME" in p.split("__")) != ("NOW" in p.split("__")) for p in groups["hub"])
    assert manifest["order"][0] == "regression_001" and len(manifest["order"]) == 79
    assert manifest["limits"] == {"max_pairs_per_batch": 16, "soft_wall_time_s": 7200, "min_free_gib": 5}


def test_sequence_policy_freezes_111_cases_bound_to_the_new_pair_policy():
    policy, pair_policy = load_sequence_policy(ROOT, SEQUENCE_POLICY)
    old, _ = load_sequence_policy(ROOT, "config/sequence_policy_user_protected_v1.json")
    assert policy["pair_policy"] == {"path": PAIR_POLICY, "sha256": file_hash(ROOT / PAIR_POLICY)}
    assert policy["cases"][:12] == old["cases"] and len(policy["cases"]) == 111 == len(set(policy["cases"]))
    others = [g for g in pair_policy["scope"]["expected_glosses"] if g not in ("COME", "NOW")]
    assert policy["cases"][12:] == [c for w in others for c in (f"COME__{w}__NOW", f"NOW__{w}__COME", f"{w}__{w}__{w}")]
    words = [sequence_glosses(case, policy) for case in policy["cases"]]
    assert sum(map(len, words)) == 44 + 99 * 3 == 341
    assert sum(len(w) - 1 for w in words) == 32 + 99 * 2 == 230
    for key in ("words", "assembly", "quality", "validation"):
        assert policy[key] == old[key]
    assert policy["formal_acceptance_enabled"] is False and pair_policy["formal_acceptance_enabled"] is False


def test_code_identity_covers_new_entry_points_and_detects_their_change(monkeypatch):
    policy = load_policy(ROOT / PAIR_POLICY, supported_versions=(2,))
    library, _ = freeze_library(ROOT, policy)
    expected = {*NEW_SCRIPTS, "src/sign_robot/batch_control.py", "src/sign_robot/sequence_batches.py",
                "tests/test_hospital35_freeze.py", "tests/test_hospital35_batches.py"}
    assert expected <= set(library["code_files"])
    for relative in expected:
        assert library["code_files"][relative] == file_hash(ROOT / relative)
    original = contract.file_hash
    monkeypatch.setattr(contract, "file_hash", lambda path: "0" * 64 if str(path).endswith(NEW_SCRIPTS[2]) else original(path))
    changed, _ = freeze_library(ROOT, policy)
    assert changed["code_hash"] != library["code_hash"]
    assert run_identity(changed, policy)["identity_hash"] != run_identity(library, policy)["identity_hash"]


def test_old_come_now_runs_keep_their_own_frozen_identity_records():
    path = ROOT / "results/sequence_pilot_20261031_001/pair_runs/sequence_pilot_pairs_20261031_001/manifest.json"
    if not path.exists():
        pytest.skip("raw pair stores are not published on this branch (.gitignore)")
    manifest = read_json(path)
    assert manifest["identity"]["code_hash"] == "4080b98e73a121c866115882483ef5b7631532d9add4bed4ff5dfbe214ad9cef"
    policy = load_policy(ROOT / PAIR_POLICY, supported_versions=(2,))
    library, _ = freeze_library(ROOT, policy)
    assert run_identity(library, policy) != manifest["identity"]


@pytest.mark.parametrize("relative", ["config/user_protected_hospital35_v1.json", PAIR_POLICY, SEQUENCE_POLICY])
def test_new_inputs_are_registered_or_bound_by_hash(relative):
    policy = load_policy(ROOT / PAIR_POLICY, supported_versions=(2,))
    library, _ = freeze_library(ROOT, policy)
    if relative == "config/user_protected_hospital35_v1.json":
        assert library["files"][relative]["sha256"] == file_hash(ROOT / relative)
    elif relative == SEQUENCE_POLICY:
        assert read_json(ROOT / relative)["pair_policy"]["sha256"] == file_hash(ROOT / PAIR_POLICY)
    else:
        assert policy["endpoints"]["protection_bundle_sha256"] == file_hash(ROOT / "config/user_protected_hospital35_v1.json")
