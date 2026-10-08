#!/usr/bin/env python3
"""Fetch only fixed official How2Sign English annotation TSVs (<25 MB total).

No video/pose downloader, login, agreement acceptance, or training is implemented.
The current WLASL/ASL Citizen/SignAvatars constraints are recorded in the registry.
Use --fetch once for a new output directory; --verify is local and offline.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
REVISION = "f85816c184662406bd8e0f338863b7c243763129"
SCRIPT_URL = f"https://raw.githubusercontent.com/how2sign/how2sign.github.io/{REVISION}/download_how2sign.sh"
FILES = {
    "train": "1dUHSoefk9OxKJnHrHPX--I4tpm9QD0ok",
    "val": "1Vpag7VPfdTCCJSao8Pz14rlPfekRMggI",
    "test": "1AgwBZW26kFHS4CWNMQTCMPGkBPkH3qCu",
}
ALLOWED_HOSTS = {"raw.githubusercontent.com", "drive.google.com", "drive.usercontent.google.com"}
MAX_BYTES = 25_000_000
REQUIRED_COLUMNS = {"VIDEO_ID", "VIDEO_NAME", "SENTENCE_ID", "SENTENCE_NAME", "START_REALIGNED", "END_REALIGNED", "SENTENCE"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked_url(url: str) -> str:
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS
            or parsed.username or parsed.password):
        raise ValueError("Unapproved download/redirect URL; no login or arbitrary media fetching")
    return url


class AllowedRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, checked_url(newurl))


def bounded_get(url: str, remaining: int) -> tuple[bytes, dict]:
    opener = build_opener(AllowedRedirect())
    with opener.open(Request(checked_url(url), headers={"User-Agent": "ME5412-corpus-metadata-audit/1"}), timeout=30) as response:
        size = response.headers.get("Content-Length")
        if size and int(size) > remaining:
            raise ValueError("Download would exceed fixed byte budget")
        data = response.read(remaining + 1)
        if len(data) > remaining:
            raise ValueError("Download exceeded fixed byte budget")
        return data, {"url": url, "final_url": checked_url(response.geturl()),
                      "http_status": response.status, "content_type": response.headers.get("Content-Type"),
                      "bytes": len(data), "sha256": sha(data)}


def parse_annotations(data: bytes, split: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")), delimiter="\t")
    if set(reader.fieldnames or []) != REQUIRED_COLUMNS:
        raise ValueError("Expected official realigned annotation columns; refusing HTML/login/error data")
    rows = []
    for number, row in enumerate(reader, 2):
        start, end = float(row["START_REALIGNED"]), float(row["END_REALIGNED"])
        if not math.isfinite(start) or not math.isfinite(end):
            raise ValueError("Nonfinite timestamp")
        rows.append({"corpus": "how2sign", "split": split, "source_row": number,
                     "video_id": row["VIDEO_ID"], "video_name": row["VIDEO_NAME"],
                     "sentence_id": row["SENTENCE_ID"], "sentence_name": row["SENTENCE_NAME"],
                     "start_s": start, "end_s": end, "english": row["SENTENCE"],
                     "media_availability": "not_checked", "motion_target_available_locally": False})
    if not rows:
        raise ValueError("Empty annotation file")
    return rows


def counts(rows: list[dict]) -> dict:
    words = Counter(word for row in rows for word in re.findall(
        r"[a-z]+(?:'[a-z]+)?", row["english"].casefold().replace("’", "'")))
    return {"annotation_rows": len(rows),
            "unique_sentence_ids": len({r["sentence_id"] for r in rows}),
            "unique_sentence_names": len({r["sentence_name"] for r in rows}),
            "unique_video_ids": len({r["video_id"] for r in rows}),
            "unique_english_strings": len({r["english"] for r in rows}),
            "english_token_types": len(words), "english_token_instances": sum(words.values()),
            "english_tokenization": "ASCII letters, casefold, internal apostrophe retained; not an ASL gloss count",
            "asl_vocabulary_classes": None,
            "blank_english_rows": sum(not r["english"].strip() for r in rows),
            "nonpositive_or_negative_time_rows": sum(r["start_s"] < 0 or r["end_s"] <= r["start_s"] for r in rows),
            "locally_available_motion_targets": 0, "instance_media_checked": 0}


def protected_hashes() -> dict:
    paths = [ROOT / "data" / name for name in ("catalog.json", "source_manifest.json", "eval_dev.jsonl", "eval_test.jsonl")]
    paths += [p for p in (ROOT / "results/evaluation").rglob("*") if p.is_file()]
    return {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in paths}


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def verify(directory: Path) -> dict:
    manifest = json.loads((directory / "download_manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "metadata_only_downloaded":
        raise ValueError("Previous fetch did not complete")
    rows = []
    for split, record in manifest["files"].items():
        data = (directory / record["file"]).read_bytes()
        if sha(data) != record["sha256"]:
            raise ValueError(f"Source byte hash mismatch: {split}")
        parsed = parse_annotations(data, split)
        if counts(parsed) != record["counts"]:
            raise ValueError(f"Counts differ: {split}")
        rows.extend(parsed)
    aggregate = counts(rows)
    if aggregate != manifest["aggregate_counts"]:
        raise ValueError("Aggregate counts differ")
    index = directory / "sentence_index.jsonl"
    if sha(index.read_bytes()) != manifest["index_sha256"]:
        raise ValueError("Derived index hash mismatch")
    for path, expected in manifest["protected_existing_hashes"].items():
        if sha((ROOT / path).read_bytes()) != expected:
            raise ValueError(f"Pre-existing project artifact changed: {path}")
    return {"verified": True, "directory": str(directory), "aggregate_counts": aggregate,
            "all_video_and_pose_files_not_downloaded": True}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fetch", action="store_true")
    mode.add_argument("--verify", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/corpus_index/how2sign_realigned_v1")
    args = parser.parse_args(argv)
    output = args.output_dir.resolve()
    if not output.is_relative_to((ROOT / "data/corpus_index").resolve()):
        raise ValueError("Output must remain inside the new corpus_index directory")
    if args.verify:
        print(json.dumps(verify(output), ensure_ascii=False, indent=2))
        return 0
    before = protected_hashes()
    output.mkdir(parents=True, exist_ok=False)
    manifest = {"schema_version": 1, "dataset": "How2Sign", "status": "started",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "repo_revision": REVISION, "max_download_bytes": MAX_BYTES, "files": {},
                "license": "CC BY-NC 4.0", "license_url": "https://creativecommons.org/licenses/by-nc/4.0/",
                "attribution": "Duarte et al., How2Sign: A Large-scale Multimodal Dataset for Continuous American Sign Language, CVPR 2021.",
                "official_project_url": "https://how2sign.github.io/", "modified": "Original TSV bytes retained; a derived JSONL and count statistics are produced.",
                "modality": "English sentence/ID/timestamp metadata only; no video, poses or robot targets",
                "instance_availability_verified": False, "protected_existing_hashes": before}
    downloaded = 0
    try:
        upstream, provenance = bounded_get(SCRIPT_URL, min(MAX_BYTES, 1_000_000))
        if not all(file_id.encode() in upstream for file_id in FILES.values()):
            raise ValueError("Pinned official downloader does not contain expected annotation IDs")
        downloaded += len(upstream)
        manifest["upstream_script_provenance"] = provenance
        # Audit only: do not execute the upstream script or follow any media URL.
        all_rows = []
        for split, file_id in FILES.items():
            url = f"https://drive.google.com/uc?export=download&id={file_id}"
            data, provenance = bounded_get(url, MAX_BYTES - downloaded)
            downloaded += len(data)
            rows = parse_annotations(data, split)
            name = f"how2sign_realigned_{split}.csv"
            (output / name).write_bytes(data)
            manifest["files"][split] = {**provenance, "file": name, "counts": counts(rows)}
            all_rows.extend(rows)
        index = output / "sentence_index.jsonl"
        with index.open("x", encoding="utf-8") as stream:
            for row in all_rows:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        manifest["index_sha256"] = sha(index.read_bytes())
        manifest["aggregate_counts"] = counts(all_rows)
        manifest["split_sentence_id_overlap"] = {
            f"{first}__{second}": len({r["sentence_id"] for r in all_rows if r["split"] == first}
                & {r["sentence_id"] for r in all_rows if r["split"] == second})
            for first, second in (("train", "val"), ("train", "test"), ("val", "test"))}
        manifest["status"] = "metadata_only_downloaded"
        manifest["downloaded_bytes_including_provenance_script"] = downloaded
        manifest["protected_existing_files_unchanged"] = before == protected_hashes()
        if not manifest["protected_existing_files_unchanged"]:
            raise RuntimeError("Pre-existing protected files changed during fetch")
        write_json(output / "download_manifest.json", manifest)
        print(json.dumps(verify(output), ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        manifest["status"] = "blocked_or_incomplete"
        manifest["error_type"] = type(exc).__name__
        manifest["error"] = str(exc)
        manifest["downloaded_bytes_before_error"] = downloaded
        manifest["protected_existing_files_unchanged"] = before == protected_hashes()
        write_json(output / "download_manifest.json", manifest)
        print(json.dumps({"status": manifest["status"], "error": str(exc), "directory": str(output)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
