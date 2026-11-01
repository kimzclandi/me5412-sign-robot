#!/usr/bin/env python3
"""Strictly import the user's 35-word protection sheet into a versioned bundle, pair policy and provenance.

Only stored cell values are read: formulas, empty or non-numeric cells,
non-finite values, duplicate/unknown/missing words, any content outside the
declared range and display text that differs from the stored value are all
rejected. Frames use zero-based inclusive outward rounding
[floor(start*30), ceil(end*30)], computed with Decimal and cross-checked with
the float rule of the existing loader. Outputs are never overwritten; --check
rebuilds them in memory and compares bytes.
"""
from __future__ import annotations

import argparse
import copy
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, InvalidOperation
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

from sign_robot.pair_contract import (
    file_hash, freeze_library, inside, json_hash, load_policy, read_json, read_motion, validate_policy_v2,
)
from sign_robot.pair_windows import load_user_protections

ODS_MIMETYPE = b"application/vnd.oasis.opendocument.spreadsheet"
TABLE = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
OFFICE = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
HEADER = ("词语", "开始秒数", "结束秒数")
MAX_CONTENT_BYTES = 8 * 1024 * 1024
MAX_EXPANDED_CELLS = 4096
_GLOSS = re.compile(r"[A-Z0-9]+(?:-[A-Z0-9]+)*")
DEFAULTS = {
    "bundle_id": "user-protection-hospital35-20261101-v1",
    "window_version": "hospital35-user-protection-20261101-v1",
    "policy_id": "group3-hospital35-user-protected-development-v1",
    "protection_prefix": "hospital35-20261101-v1",
}


class ProtectionImportError(ValueError):
    def __init__(self, code, details):
        super().__init__(f"{code}: {details}")
        self.code, self.details = code, details


def _column_name(index):
    name = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _cell_ref(row, column):
    return f"{_column_name(column)}{row + 1}"


def _is_empty(cell):
    return (not any(key.startswith(f"{{{OFFICE}}}") for key in cell.attrib)
            and f"{{{TABLE}}}formula" not in cell.attrib and len(cell) == 0 and not (cell.text or "").strip())


def _repeat(element, name):
    value = element.get(f"{{{TABLE}}}{name}", "1")
    if not value.isdigit() or int(value) < 1:
        raise ProtectionImportError("ODS_REPEAT_INVALID", value)
    return int(value)


def read_sheet_cells(path, sheet):
    """Return {(row, column): cell} for every non-empty cell of one sheet."""
    try:
        with zipfile.ZipFile(path) as archive:
            if archive.read("mimetype").strip() != ODS_MIMETYPE:
                raise ProtectionImportError("NOT_AN_ODS_SPREADSHEET", str(path))
            info = archive.getinfo("content.xml")
            if info.file_size > MAX_CONTENT_BYTES:
                raise ProtectionImportError("ODS_CONTENT_TOO_LARGE", info.file_size)
            data = archive.read("content.xml")
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        raise ProtectionImportError("ODS_UNREADABLE", str(exc)) from exc
    # The parser must never resolve declared entities from a data file.
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        raise ProtectionImportError("ODS_DECLARATIONS_REJECTED", str(path))
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ProtectionImportError("ODS_XML_INVALID", str(exc)) from exc
    tables = [t for t in root.iter(f"{{{TABLE}}}table") if t.get(f"{{{TABLE}}}name") == sheet]
    if len(tables) != 1:
        raise ProtectionImportError("SHEET_NOT_FOUND_EXACTLY_ONCE", sheet)
    cells, row_index, expanded = {}, 0, 0
    for row in tables[0].iter(f"{{{TABLE}}}table-row"):
        row_repeat = _repeat(row, "number-rows-repeated")
        column_index, entries = 0, []
        for cell in row:
            if cell.tag not in (f"{{{TABLE}}}table-cell", f"{{{TABLE}}}covered-table-cell"):
                continue
            repeat = _repeat(cell, "number-columns-repeated")
            if not _is_empty(cell):
                entries.extend((column_index + k, cell) for k in range(repeat))
                expanded += repeat * row_repeat
                if expanded > MAX_EXPANDED_CELLS:
                    raise ProtectionImportError("ODS_TOO_MANY_FILLED_CELLS", expanded)
            column_index += repeat
        for offset in range(row_repeat if entries else 0):
            for column, cell in entries:
                cells[(row_index + offset, column)] = cell
        row_index += row_repeat
    return cells


def _text(cell):
    return "".join(cell.itertext())


def _string_cell(cells, row, column):
    cell = cells.get((row, column))
    reference = _cell_ref(row, column)
    if cell is None:
        raise ProtectionImportError("EMPTY_CELL", reference)
    if f"{{{TABLE}}}formula" in cell.attrib:
        raise ProtectionImportError("FORMULA_REJECTED", reference)
    if cell.get(f"{{{OFFICE}}}value-type") != "string":
        raise ProtectionImportError("NOT_A_TEXT_CELL", reference)
    text = _text(cell)
    if not text or text != text.strip():
        raise ProtectionImportError("INVALID_TEXT_CELL", reference)
    return text


def _number_cell(cells, row, column):
    cell = cells.get((row, column))
    reference = _cell_ref(row, column)
    if cell is None:
        raise ProtectionImportError("EMPTY_CELL", reference)
    if f"{{{TABLE}}}formula" in cell.attrib:
        raise ProtectionImportError("FORMULA_REJECTED", reference)
    if cell.get(f"{{{OFFICE}}}value-type") != "float" or cell.get(f"{{{OFFICE}}}value") is None:
        raise ProtectionImportError("NOT_A_NUMBER_CELL", reference)
    stored = cell.get(f"{{{OFFICE}}}value")
    try:
        value, shown = Decimal(stored), Decimal(_text(cell).strip())
    except InvalidOperation as exc:
        raise ProtectionImportError("NUMBER_NOT_PARSEABLE", reference) from exc
    if not value.is_finite() or not shown.is_finite():
        raise ProtectionImportError("NON_FINITE_NUMBER", reference)
    if value != shown:
        raise ProtectionImportError("DISPLAY_DIFFERS_FROM_STORED_VALUE", reference)
    return stored, value


def read_protection_rows(path, sheet, expected_glosses):
    """Exactly A1:C1 headers plus one row per expected gloss; nothing else filled."""
    cells = read_sheet_cells(path, sheet)
    count = len(expected_glosses)
    for column, title in enumerate(HEADER):
        if _string_cell(cells, 0, column) != title:
            raise ProtectionImportError("HEADER_MISMATCH", _cell_ref(0, column))
    outside = sorted(_cell_ref(r, c) for r, c in cells if r > count or c > 2)
    if outside:
        raise ProtectionImportError("CONTENT_OUTSIDE_DECLARED_RANGE", outside[:10])
    rows, seen = [], set()
    for row in range(1, count + 1):
        gloss = _string_cell(cells, row, 0)
        if _GLOSS.fullmatch(gloss) is None or gloss not in expected_glosses:
            raise ProtectionImportError("UNKNOWN_GLOSS", f"{_cell_ref(row, 0)}={gloss}")
        if gloss in seen:
            raise ProtectionImportError("DUPLICATE_GLOSS", f"{_cell_ref(row, 0)}={gloss}")
        seen.add(gloss)
        (start_text, start), (end_text, end) = _number_cell(cells, row, 1), _number_cell(cells, row, 2)
        rows.append({"row": row + 1, "cells": {"gloss": _cell_ref(row, 0), "start": _cell_ref(row, 1), "end": _cell_ref(row, 2)},
                     "gloss": gloss, "start_value": start_text, "end_value": end_text, "start": start, "end": end})
    missing = [g for g in expected_glosses if g not in seen]
    if missing:
        raise ProtectionImportError("MISSING_GLOSS", missing)
    return rows


def protected_frames(start, end, frame_count):
    """Decimal outward rounding, cross-checked against the loader's float rule."""
    last = Decimal(frame_count - 1) / Decimal(30)
    if not Decimal(0) <= start < end <= last:
        raise ProtectionImportError("INVALID_TIME_RANGE", {"start": str(start), "end": str(end), "last_frame_time_s": str(last)})
    if not 0 <= float(start) < float(end) <= (frame_count - 1) / 30:
        raise ProtectionImportError("FLOAT_TIME_RANGE_DISAGREES", {"start": str(start), "end": str(end)})
    exact = (int((start * 30).to_integral_value(ROUND_FLOOR)), int((end * 30).to_integral_value(ROUND_CEILING)))
    floating = (math.floor(float(start) * 30), math.ceil(float(end) * 30))
    if exact != floating:
        raise ProtectionImportError("ROUNDING_AMBIGUOUS", {"decimal": exact, "float": floating})
    if not 0 <= exact[0] <= exact[1] <= frame_count - 1:
        raise ProtectionImportError("FRAME_OUT_OF_BOUNDS", exact)
    return exact, {"start_times_30": str(start * 30), "end_times_30": str(end * 30), "decimal_frames": list(exact),
                   "float_frames": list(floating), "last_frame_time_s": str(last)}


def bind_sources(root, rows):
    """Bind each row to the actual hospital_v1 library/motion; never to a preview duplicate."""
    root = Path(root).resolve()
    mapping_path = root / "motions/hospital_v1_motions.json"
    mapping = read_json(mapping_path)
    words = {w["gloss"]: w for w in mapping["glosses"]}
    bound = []
    for row in rows:
        word = words.get(row["gloss"])
        if word is None or not word.get("motion_ready") or not isinstance(word.get("motion"), str):
            raise ProtectionImportError("SOURCE_NOT_READY", row["gloss"])
        if (word["library"] not in mapping["motion_libraries"] or Path(word["motion"]).parent != Path(word["library"])
                or Path(word["motion"]).name != f"{row['gloss']}.npz"):
            raise ProtectionImportError("SOURCE_NOT_IN_SELECTED_LIBRARY", row["gloss"])
        path = inside(root, word["motion"])
        clip = read_motion(path)
        count = len(clip["positions"])
        if count < 2 or not np.allclose(clip["timestamps_s"], np.arange(count) / 30, atol=1e-10, rtol=0):
            raise ProtectionImportError("SOURCE_TIMING_NOT_30HZ", row["gloss"])
        frames, audit = protected_frames(row["start"], row["end"], count)
        bound.append({**row, "motion": word["motion"], "library": word["library"], "motion_sha256": file_hash(path),
                      "frame_count": count, "protected_core_frames": list(frames), "rounding_audit": audit,
                      "hospital_core_frames_hint": word.get("core_frames"), "hospital_sign_frames_hint": word.get("sign_frames")})
    return bound, {"path": str(mapping_path.relative_to(root)), "sha256": file_hash(mapping_path)}


def build_bundle(bound, policy_order, *, ods_sha256, sheet, bundle_id, window_version, prefix):
    order = {gloss: index for index, gloss in enumerate(policy_order)}
    records = []
    for item in sorted(bound, key=lambda value: order[value["gloss"]]):
        records.append({
            "protection_id": f"{prefix}-{item['gloss']}",
            "gloss": item["gloss"],
            "motion": item["motion"],
            "motion_sha256": item["motion_sha256"],
            "frame_count": item["frame_count"],
            "fps": 30,
            "user_interval_text": f"{item['start_value']}–{item['end_value']} s ({sheet}!{item['cells']['start']}:{item['cells']['end']})",
            "user_interval_s": [float(item["start"]), float(item["end"])],
            "protected_core_frames": item["protected_core_frames"],
            "retiming_allowed": False,
            "binding_basis": (f"user sheet row {item['row']} of ODS sha256 {ods_sha256} + unchanged actual hospital_v1 "
                              "selected motion SHA-256 + inclusive outward rounding"),
            "prior_video_identity_available": False,
        })
    return {
        "schema_version": 1, "kind": "user_protected_intervals_v1", "bundle_id": bundle_id, "window_version": window_version,
        "source_instruction": (
            f"User-filled sheet {sheet} (A2:C{len(records) + 1}) of the ODS with SHA-256 {ods_sha256}, imported by "
            "scripts/import_user_protections.py. It supplies the semantic fragment the user requires for each word; "
            "outward rounding remains an engineering safeguard. The algorithm chooses external cuts and windows; no "
            "human window approval is supplied. Earlier COME/NOW bundles stay unchanged for their historical runs."),
        "records": records,
    }


def build_policy(base_policy, *, policy_id, window_version, bundle_path, bundle_sha256):
    policy = copy.deepcopy(base_policy)
    policy["policy_id"] = policy_id
    policy["endpoints"].update(window_version=window_version, protection_file=bundle_path,
                               protection_bundle_sha256=bundle_sha256)
    return validate_policy_v2(policy)


def document_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _loader_glosses(root, policy, bundle_bytes):
    """Run the real loader against a scratch root holding the bundle and actual source copies."""
    with tempfile.TemporaryDirectory(prefix="protection_import_") as scratch:
        scratch = Path(scratch)
        target = scratch / policy["endpoints"]["protection_file"]
        target.parent.mkdir(parents=True)
        target.write_bytes(bundle_bytes)
        mapping = read_json(Path(root) / "motions/hospital_v1_motions.json")
        library_words = []
        for word in mapping["glosses"]:
            copy_path = scratch / word["motion"]
            copy_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(root) / word["motion"], copy_path)
            with np.load(copy_path, allow_pickle=False) as data:
                frames = len(data["positions"])
            library_words.append({"gloss": word["gloss"], "motion": word["motion"],
                                  "motion_sha256": file_hash(copy_path), "frames": frames})
        return sorted(load_user_protections(scratch, policy, {"words": library_words}))


def build_outputs(root, ods_relative, *, expected_sha256, sheet, base_policy_relative, bundle_relative,
                  policy_relative, provenance_relative, bundle_id, window_version, policy_id, prefix):
    root = Path(root).resolve()
    ods = inside(root, ods_relative)
    actual = file_hash(ods)
    if actual != expected_sha256:
        raise ProtectionImportError("ODS_HASH_MISMATCH", {"expected": expected_sha256, "actual": actual})
    base_path = inside(root, base_policy_relative)
    base = load_policy(base_path, supported_versions=(2,))
    if base["endpoints"]["strategy"] != "user_protected_auto_windows_v1" or base["formal_acceptance_enabled"] is not False:
        raise ProtectionImportError("BASE_POLICY_NOT_USER_PROTECTED_DEVELOPMENT", base_policy_relative)
    expected = base["scope"]["expected_glosses"]
    rows = read_protection_rows(ods, sheet, expected)
    bound, mapping = bind_sources(root, rows)
    bundle = build_bundle(bound, expected, ods_sha256=actual, sheet=sheet, bundle_id=bundle_id,
                          window_version=window_version, prefix=prefix)
    bundle_bytes = document_bytes(bundle)
    bundle_sha256 = hashlib.sha256(bundle_bytes).hexdigest()
    policy = build_policy(base, policy_id=policy_id, window_version=window_version, bundle_path=bundle_relative,
                          bundle_sha256=bundle_sha256)
    policy_bytes = document_bytes(policy)
    loaded = _loader_glosses(root, policy, bundle_bytes)
    if loaded != sorted(expected) or len(loaded) != 35:
        raise ProtectionImportError("LOADER_SCOPE_MISMATCH", loaded)
    if json_hash(policy) == json_hash(base):
        raise ProtectionImportError("POLICY_IDENTITY_NOT_NEW", policy_relative)
    provenance = {
        "schema_version": 1, "kind": "user_protection_import_provenance_v1",
        "importer": {"path": "scripts/import_user_protections.py",
                     "sha256": file_hash(Path(__file__).resolve())},
        "ods": {"path": ods_relative, "sha256": actual, "sheet": sheet, "header_cells": {"A1": HEADER[0], "B1": HEADER[1], "C1": HEADER[2]},
                "record_cells": f"A2:C{len(rows) + 1}", "read": "stored office:value only; formulas, empty, non-finite and display/value mismatches rejected"},
        "hospital_mapping": mapping,
        "base_policy": {"path": base_policy_relative, "sha256": file_hash(base_path)},
        "bundle": {"path": bundle_relative, "sha256": bundle_sha256, "bundle_id": bundle_id, "window_version": window_version,
                   "record_count": len(bundle["records"])},
        "policy": {"path": policy_relative, "sha256": hashlib.sha256(policy_bytes).hexdigest(), "policy_id": policy_id,
                   "changed_fields": ["policy_id", "endpoints.window_version", "endpoints.protection_file",
                                      "endpoints.protection_bundle_sha256"]},
        "rounding": "zero-based inclusive [floor(start*30), ceil(end*30)]; Decimal and the loader's float rule must agree",
        "sheet_order_equals_policy_order": [r["gloss"] for r in rows] == list(expected),
        "rows": [{key: item[key] for key in ("row", "cells", "gloss", "start_value", "end_value", "library", "motion",
                                             "motion_sha256", "frame_count", "protected_core_frames", "rounding_audit",
                                             "hospital_core_frames_hint", "hospital_sign_frames_hint")}
                 | {"protected_frame_count": item["protected_core_frames"][1] - item["protected_core_frames"][0] + 1}
                 for item in bound],
        "loader_check": {"function": "sign_robot.pair_windows.load_user_protections", "glosses_loaded": len(loaded),
                         "equals_policy_scope": True},
        "window_provenance": "algorithm", "formal_acceptance_enabled": False,
        "semantic_status": "user-selected fragments; not verified ASL; no human or cross-group review recorded",
    }
    return {bundle_relative: bundle_bytes, policy_relative: policy_bytes, provenance_relative: document_bytes(provenance)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ods", required=True, help="Repository-relative ODS copy")
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--sheet", default="保护区间填写")
    parser.add_argument("--base-policy", default="config/transition_policy_user_protected_v5.json")
    parser.add_argument("--bundle-output", default="config/user_protected_hospital35_v1.json")
    parser.add_argument("--policy-output", default="config/transition_policy_user_protected_hospital35_v1.json")
    parser.add_argument("--provenance-output", default="config/user_protected_hospital35_v1.provenance.json")
    parser.add_argument("--bundle-id", default=DEFAULTS["bundle_id"])
    parser.add_argument("--window-version", default=DEFAULTS["window_version"])
    parser.add_argument("--policy-id", default=DEFAULTS["policy_id"])
    parser.add_argument("--protection-prefix", default=DEFAULTS["protection_prefix"])
    parser.add_argument("--check", action="store_true", help="Rebuild in memory and compare with existing outputs")
    args = parser.parse_args(argv)
    try:
        outputs = build_outputs(ROOT, args.ods, expected_sha256=args.expected_sha256, sheet=args.sheet,
                                base_policy_relative=args.base_policy, bundle_relative=args.bundle_output,
                                policy_relative=args.policy_output, provenance_relative=args.provenance_output,
                                bundle_id=args.bundle_id, window_version=args.window_version,
                                policy_id=args.policy_id, prefix=args.protection_prefix)
    except ProtectionImportError as exc:
        print(json.dumps({"status": "REJECTED", "code": exc.code, "details": str(exc.details)}, ensure_ascii=False))
        return 2
    paths = {relative: inside(ROOT, relative) for relative in outputs}
    if args.check:
        differences = [r for r, p in paths.items() if not p.is_file() or p.read_bytes() != outputs[r]]
        result = {"status": "MATCH" if not differences else "DIFFERS", "differences": differences}
        if not differences:
            result["installed_check"] = installed_check(ROOT, args.policy_output)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if not differences else 1
    existing = [r for r, p in paths.items() if p.exists()]
    if existing:
        parser.error(f"Outputs exist and are never overwritten: {existing}")
    for relative, payload in outputs.items():
        with open(paths[relative], "xb") as stream:
            stream.write(payload)
    print(json.dumps({"status": "WRITTEN", "files": {r: file_hash(p) for r, p in paths.items()},
                      "installed_check": installed_check(ROOT, args.policy_output)}, ensure_ascii=False))
    return 0


def installed_check(root, policy_relative):
    """Re-read the installed files through the frozen-library path every run uses."""
    policy = load_policy(inside(root, policy_relative), supported_versions=(2,))
    library, _ = freeze_library(root, policy)
    words = {w["gloss"]: w for w in library["words"]}
    protections = load_user_protections(root, policy, library)
    return {"input_errors": library["input_errors"],
            "word_input_errors": {g: w["input_errors"] for g, w in words.items() if w["input_errors"]},
            "glosses_loaded": len(protections),
            "equals_policy_scope": sorted(protections) == sorted(policy["scope"]["expected_glosses"]),
            "COME": list(protections["COME"].protected_core_frames), "NOW": list(protections["NOW"].protected_core_frames)}


if __name__ == "__main__":
    raise SystemExit(main())
