"""Strict 35-word protection import: real sheet equality plus rejection of malformed inputs."""
import importlib.util
import json
import shutil
from unittest.mock import patch
import zipfile

import numpy as np
import pytest

from clips_v2 import on_clips_v2
from sign_robot.motion import ROOT
from sign_robot.pair_contract import file_hash, freeze_library, json_hash, load_policy, read_json
from sign_robot.pair_windows import WindowApprovalError, load_user_protections

SPEC = importlib.util.spec_from_file_location("import_user_protections", ROOT / "scripts/import_user_protections.py")
importer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(importer)

ODS = "data/user_protection/hospital35_20261101/protection_intervals.ods"
ODS_SHA = "4fe5b3bb3f7d12cf4cd4418b8431325dec48fbed3c29a2a1e29447cdf89667e3"
BUNDLE = "config/user_protected_hospital35_v1.json"
POLICY = "config/transition_policy_user_protected_hospital35_v1.json"
PROVENANCE = "config/user_protected_hospital35_v1.provenance.json"
V5 = "config/transition_policy_user_protected_v5.json"
# Bundle v4 binds the same 35 words to Group 2's clips-v2 motions (TASK-29); v1 stays the hospital_v1 record.
REBOUND = "config/user_protected_hospital35_v4.json"
V1_SHA = "d19fec39dcc28dd54fa3d93260dbe0bcbec81062cd190669f74681c5172e3ae0"
OFFICE = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
TABLE = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
TEXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"


def build(root=ROOT, ods=ODS, sha=ODS_SHA):
    return importer.build_outputs(
        root, ods, expected_sha256=sha, sheet="保护区间填写", base_policy_relative=V5, bundle_relative=BUNDLE,
        policy_relative=POLICY, provenance_relative=PROVENANCE, bundle_id=importer.DEFAULTS["bundle_id"],
        window_version=importer.DEFAULTS["window_version"], policy_id=importer.DEFAULTS["policy_id"],
        prefix=importer.DEFAULTS["protection_prefix"])


def real_rows():
    expected = load_policy(ROOT / V5, supported_versions=(2,))["scope"]["expected_glosses"]
    return [[r["gloss"], r["start_value"], r["end_value"]] for r in importer.read_protection_rows(ROOT / ODS, "保护区间填写", expected)]


def text_cell(value):
    return f'<table:table-cell office:value-type="string"><text:p>{value}</text:p></table:table-cell>'


def number_cell(value, shown=None, formula=None):
    extra = f' table:formula="{formula}"' if formula else ""
    return (f'<table:table-cell office:value-type="float" office:value="{value}"{extra}>'
            f'<text:p>{value if shown is None else shown}</text:p></table:table-cell>')


def write_ods(path, rows, *, sheet="保护区间填写", header=("词语", "开始秒数", "结束秒数"), prolog="", raw_rows=()):
    cells = [[text_cell(h) for h in header]]
    for row in rows:
        cells.append([text_cell(row[0]) if row[0] is not None else "<table:table-cell/>",
                      *[c if str(c).startswith("<") else number_cell(c) for c in row[1:]]])
    body = "".join("<table:table-row>" + "".join(row) + "</table:table-row>" for row in cells) + "".join(raw_rows)
    content = (f'<?xml version="1.0" encoding="UTF-8"?>{prolog}<office:document-content xmlns:office="{OFFICE}" '
               f'xmlns:table="{TABLE}" xmlns:text="{TEXT}"><office:body><office:spreadsheet>'
               f'<table:table table:name="{sheet}">{body}</table:table></office:spreadsheet></office:body>'
               f'</office:document-content>')
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/vnd.oasis.opendocument.spreadsheet", compress_type=zipfile.ZIP_STORED)
        archive.writestr("content.xml", content)
    return path


def test_real_sheet_rebuilds_v1_except_the_clips_v2_motion_binding():
    outputs = build()
    assert sorted(outputs) == sorted([BUNDLE, POLICY, PROVENANCE])
    old = {relative: read_json(ROOT / relative) for relative in outputs}
    new = {relative: json.loads(payload) for relative, payload in outputs.items()}
    current = {r["gloss"]: r["motion_sha256"] for r in read_json(ROOT / REBOUND)["records"]}
    replaced = {r["gloss"] for r in old[BUNDLE]["records"] if r["motion_sha256"] != current[r["gloss"]]}
    assert len(replaced) == 24 and "NURSE" in replaced and "COME" not in replaced
    assert new[BUNDLE]["records"] == [{**r, "motion_sha256": current[r["gloss"]]} for r in old[BUNDLE]["records"]]
    assert {**new[BUNDLE], "records": old[BUNDLE]["records"]} == old[BUNDLE]
    assert new[PROVENANCE]["rows"] == [{**r, "motion_sha256": current[r["gloss"]]} for r in old[PROVENANCE]["rows"]]
    assert new[PROVENANCE]["bundle"]["sha256"] == new[POLICY]["endpoints"]["protection_bundle_sha256"] != V1_SHA
    assert {**new[PROVENANCE], "rows": old[PROVENANCE]["rows"], "bundle": old[PROVENANCE]["bundle"],
            "policy": old[PROVENANCE]["policy"]} == old[PROVENANCE]
    assert {**new[POLICY], "endpoints": {**new[POLICY]["endpoints"], "protection_bundle_sha256": V1_SHA}} == old[POLICY]
    bundle = read_json(ROOT / BUNDLE)
    records = {r["gloss"]: r for r in bundle["records"]}
    assert len(bundle["records"]) == 35 and len(records) == 35
    assert records["COME"]["protected_core_frames"] == [27, 132]
    assert records["NOW"]["protected_core_frames"] == [27, 51]
    assert all(r["retiming_allowed"] is False and r["prior_video_identity_available"] is False for r in records.values())
    provenance = read_json(ROOT / PROVENANCE)
    assert provenance["ods"]["sha256"] == ODS_SHA and provenance["bundle"]["sha256"] == file_hash(ROOT / BUNDLE)
    assert provenance["policy"]["sha256"] == file_hash(ROOT / POLICY)
    assert [row["protected_core_frames"] for row in provenance["rows"]] == [records[r["gloss"]]["protected_core_frames"]
                                                                           for r in provenance["rows"]]


def test_new_policy_changes_only_protection_binding_and_loads_exactly_35_words():
    old = load_policy(ROOT / V5, supported_versions=(2,))
    new = load_policy(ROOT / POLICY, supported_versions=(2,))
    assert json_hash(old) != json_hash(new)
    changed = {key for key in new if new[key] != old[key]}
    assert changed == {"policy_id", "endpoints"}
    assert {k for k in new["endpoints"] if new["endpoints"][k] != old["endpoints"][k]} == {
        "window_version", "protection_file", "protection_bundle_sha256"}
    assert new["formal_acceptance_enabled"] is False and new["quality"] == old["quality"]
    library, _ = freeze_library(ROOT, new)
    assert not library["input_errors"] and not any(w["input_errors"] for w in library["words"])
    with pytest.raises(WindowApprovalError) as caught:
        load_user_protections(ROOT, new, library)
    assert caught.value.code == "STALE_USER_PROTECTION_MOTION"
    new = on_clips_v2(new)
    library, _ = freeze_library(ROOT, new)
    protections = load_user_protections(ROOT, new, library)
    assert sorted(protections) == sorted(new["scope"]["expected_glosses"]) and len(protections) == 35
    assert protections["NOW"].protected_core_frames == (27, 51)
    assert protections["NOW"].exit_window_frames == (51, 103) and protections["NOW"].entry_window_frames == (0, 27)


def test_historical_inputs_are_unchanged():
    assert file_hash(ROOT / V5) == "4a08faee59d0b1dec77fb5106261a7b2f75d66147278d7646eb51061d198261f"
    assert file_hash(ROOT / "config/user_protected_come_now_v2.json") == "251a69c3ed7f26780b5902bcc55a3da1ce7959dac4ff0f485bb911096832dc6c"
    assert file_hash(ROOT / "motions/studio_galt_v1/COME.npz").startswith("75d6455408ce6584")
    assert file_hash(ROOT / "motions/wlasl_video_v1/NOW.npz").startswith("2d494c13fdf1b44b")


def test_synthetic_copy_of_the_real_sheet_reads_identically(tmp_path):
    rows = real_rows()
    path = write_ods(tmp_path / "copy.ods", rows)
    expected = load_policy(ROOT / V5, supported_versions=(2,))["scope"]["expected_glosses"]
    copied = importer.read_protection_rows(path, "保护区间填写", expected)
    assert [[r["gloss"], r["start_value"], r["end_value"]] for r in copied] == rows


def _mutate(rows, gloss, column, value):
    rows = [list(r) for r in rows]
    next(r for r in rows if r[0] == gloss)[column] = value
    return rows


@pytest.mark.parametrize("change,code", [
    (lambda rows: _mutate(rows, "HELLO", 1, number_cell("0.9", formula="of:=0.3*3")), "FORMULA_REJECTED"),
    (lambda rows: _mutate(rows, "HELLO", 1, "<table:table-cell/>"), "EMPTY_CELL"),
    (lambda rows: _mutate(rows, "HELLO", 1, text_cell("0.9")), "NOT_A_NUMBER_CELL"),
    (lambda rows: _mutate(rows, "HELLO", 1, number_cell("NaN")), "NON_FINITE_NUMBER"),
    (lambda rows: _mutate(rows, "HELLO", 2, number_cell("Infinity")), "NON_FINITE_NUMBER"),
    (lambda rows: _mutate(rows, "HELLO", 1, number_cell("0.9", shown="1")), "DISPLAY_DIFFERS_FROM_STORED_VALUE"),
    (lambda rows: _mutate(rows, "PLEASE", 0, "HELLO"), "DUPLICATE_GLOSS"),
    (lambda rows: _mutate(rows, "PLEASE", 0, "PLEASE2"), "UNKNOWN_GLOSS"),
    (lambda rows: _mutate(rows, "PLEASE", 0, " PLEASE"), "INVALID_TEXT_CELL"),
    (lambda rows: rows[:-1], "EMPTY_CELL"),
    (lambda rows: [*rows, ["HELLO", "0.9", "2.2"]], "CONTENT_OUTSIDE_DECLARED_RANGE"),
    (lambda rows: [[*rows[0], "note"], *rows[1:]], "CONTENT_OUTSIDE_DECLARED_RANGE"),
])
def test_sheet_level_rejections(tmp_path, change, code):
    rows = change(real_rows())
    rows = [[r[0], *[c for c in r[1:3]], *[text_cell(c) for c in r[3:]]] for r in rows]
    path = write_ods(tmp_path / "bad.ods", rows)
    expected = load_policy(ROOT / V5, supported_versions=(2,))["scope"]["expected_glosses"]
    with pytest.raises(importer.ProtectionImportError) as caught:
        importer.read_protection_rows(path, "保护区间填写", expected)
    assert caught.value.code == code


def test_missing_word_and_wrong_layout_are_rejected(tmp_path):
    expected = load_policy(ROOT / V5, supported_versions=(2,))["scope"]["expected_glosses"]
    rows = real_rows()
    swapped = [*rows[:-1], ["HELLO", "0.9", "2.2"]]
    cases = [
        (write_ods(tmp_path / "dup.ods", swapped), "DUPLICATE_GLOSS"),
        (write_ods(tmp_path / "header.ods", rows, header=("词语", "开始", "结束秒数")), "HEADER_MISMATCH"),
        (write_ods(tmp_path / "sheet.ods", rows, sheet="Sheet1"), "SHEET_NOT_FOUND_EXACTLY_ONCE"),
        (write_ods(tmp_path / "dtd.ods", rows, prolog='<!DOCTYPE x [<!ENTITY a "b">]>'), "ODS_DECLARATIONS_REJECTED"),
        (write_ods(tmp_path / "row37.ods", rows, raw_rows=['<table:table-row>' + text_cell("EXTRA") + '</table:table-row>']),
         "CONTENT_OUTSIDE_DECLARED_RANGE"),
    ]
    for path, code in cases:
        with pytest.raises(importer.ProtectionImportError) as caught:
            importer.read_protection_rows(path, "保护区间填写", expected)
        assert caught.value.code == code, path.name
    short = [r for r in rows if r[0] != "WHERE"]
    with pytest.raises(importer.ProtectionImportError) as caught:
        importer.read_protection_rows(write_ods(tmp_path / "short.ods", short), "保护区间填写", expected[:-1] + ["WHERE"])
    assert caught.value.code in ("EMPTY_CELL", "MISSING_GLOSS")


@pytest.fixture(scope="module")
def source_root(tmp_path_factory):
    """Scratch root with the selected sources, a same-name preview duplicate and the actual mapping."""
    root = tmp_path_factory.mktemp("sources")
    mapping = read_json(ROOT / "motions/hospital_v1_motions.json")
    for relative in ["motions/hospital_v1_motions.json", *[w["motion"] for w in mapping["glosses"]],
                     "motions/wlasl_video_v1/HELLO.npz", ODS]:
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, root / relative)
    return root


@pytest.mark.parametrize("gloss,start,end,code", [
    ("HELLO", "2.2", "2.2", "INVALID_TIME_RANGE"),
    ("HELLO", "2.3", "2.2", "INVALID_TIME_RANGE"),
    ("HELLO", "-0.1", "2.2", "INVALID_TIME_RANGE"),
    ("LATER", "0.9", "2.8", "INVALID_TIME_RANGE"),
    ("HELLO", "0.033333333333333332", "2.2", "ROUNDING_AMBIGUOUS"),
])
def test_time_range_and_rounding_rejections(source_root, gloss, start, end, code):
    rows = [{"row": 2, "cells": {}, "gloss": gloss, "start_value": start, "end_value": end,
             "start": importer.Decimal(start), "end": importer.Decimal(end)}]
    with pytest.raises(importer.ProtectionImportError) as caught:
        importer.bind_sources(source_root, rows)
    assert caught.value.code == code


def test_source_binding_rejects_wrong_library_and_bad_timing(tmp_path, source_root):
    root = tmp_path / "root"
    shutil.copytree(source_root, root)
    rows = [{"row": 2, "cells": {}, "gloss": "HELLO", "start_value": "0.9", "end_value": "2.2",
             "start": importer.Decimal("0.9"), "end": importer.Decimal("2.2")}]
    mapping_path = root / "motions/hospital_v1_motions.json"
    mapping = read_json(mapping_path)
    hello = next(w for w in mapping["glosses"] if w["gloss"] == "HELLO")
    hello["motion"] = "motions/wlasl_video_v1/HELLO.npz"
    mapping_path.write_text(json.dumps(mapping))
    with pytest.raises(importer.ProtectionImportError) as caught:
        importer.bind_sources(root, rows)
    assert caught.value.code == "SOURCE_NOT_IN_SELECTED_LIBRARY"
    shutil.copyfile(source_root / "motions/hospital_v1_motions.json", mapping_path)
    clip = root / "motions/studio_galt_v1/HELLO.npz"
    with np.load(clip, allow_pickle=False) as data:
        values = {key: data[key].copy() for key in data.files}
    values["timestamps_s"] = values["timestamps_s"] * 1.01
    np.savez_compressed(clip, **values)
    with pytest.raises(importer.ProtectionImportError) as caught:
        importer.bind_sources(root, rows)
    assert caught.value.code == "SOURCE_TIMING_NOT_30HZ"


def test_hash_mismatch_is_rejected_before_reading():
    with pytest.raises(importer.ProtectionImportError) as caught:
        build(sha="0" * 64)
    assert caught.value.code == "ODS_HASH_MISMATCH"


@pytest.mark.parametrize("mutation,code", [
    (lambda r: r.update(motion_sha256="0" * 64), "STALE_USER_PROTECTION_MOTION"),
    (lambda r: r.update(frame_count=r["frame_count"] - 1), "USER_PROTECTION_FRAME_COUNT_MISMATCH"),
    (lambda r: r.update(protected_core_frames=[r["protected_core_frames"][0] + 1, r["protected_core_frames"][1]]),
     "USER_PROTECTION_NOT_CONSERVATIVE"),
    (lambda r: r.update(motion="motions/wlasl_video_v1/HELLO.npz",
                        motion_sha256=file_hash(ROOT / "motions/wlasl_video_v1/HELLO.npz")), "STALE_USER_PROTECTION_MOTION"),
])
def test_installed_loader_rejects_stale_or_wrong_same_name_sources(tmp_path, mutation, code):
    policy = load_policy(ROOT / POLICY, supported_versions=(2,))
    library, _ = freeze_library(ROOT, policy)
    bundle = read_json(ROOT / BUNDLE)
    mutation(next(r for r in bundle["records"] if r["gloss"] == "HELLO"))
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle, ensure_ascii=False))
    # Only the bundle is relocated; motion reads stay bound to the repository root.
    import sign_robot.pair_windows as windows
    original = windows.inside
    with patch.object(windows, "inside", lambda root, rel: path if rel == "test-bundle.json" else original(root, rel)):
        policy["endpoints"].update(protection_file="test-bundle.json", protection_bundle_sha256=file_hash(path))
        with pytest.raises(WindowApprovalError) as caught:
            load_user_protections(ROOT, policy, library)
    assert caught.value.code == code


def test_cli_never_overwrites_and_check_matches(capsys):
    args = ["--ods", ODS, "--expected-sha256", ODS_SHA]
    with pytest.raises(SystemExit):
        importer.main(args)
    capsys.readouterr()
    # On clips-v2 the sheet no longer rebuilds the installed v1 files; the check reports them and changes nothing.
    assert importer.main([*args, "--check"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "DIFFERS" and sorted(result["differences"]) == sorted([BUNDLE, POLICY, PROVENANCE])
    assert file_hash(ROOT / BUNDLE) == V1_SHA
