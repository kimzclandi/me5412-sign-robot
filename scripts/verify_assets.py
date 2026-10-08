#!/usr/bin/env python3
"""Verify local assets against the recorded pinned upstream hashes."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def main():
    checks = []
    for manifest_rel, folder, key in [
        ("assets/robot/upstream_manifest.json", "assets/robot/vendor", "file"),
        ("config/embedding_download_manifest.json", "models/all-MiniLM-L6-v2", "path"),
    ]:
        manifest = json.loads((ROOT / manifest_rel).read_text(encoding="utf-8"))
        for item in manifest["files"]:
            path = ROOT / folder / item[key]
            actual = digest(path) if path.is_file() else None
            checks.append({"path": str(path.relative_to(ROOT)), "expected": item["sha256"],
                           "actual": actual, "passed": actual == item["sha256"]})
    source = json.loads((ROOT / "data/source_manifest.json").read_text(encoding="utf-8"))
    for split in ("dev", "test"):
        path = ROOT / f"data/eval_{split}.jsonl"
        expected = source["evaluation"][f"{split}_sha256"]
        checks.append({"path": str(path.relative_to(ROOT)), "expected": expected,
                       "actual": digest(path), "passed": digest(path) == expected})
    report = {"scope": "Pinned robot assets, embedding weights and frozen input sets",
              "checks": checks, "passed": all(c["passed"] for c in checks),
              "total": len(checks), "failed": sum(not c["passed"] for c in checks)}
    (ROOT / "results/asset_verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "checks"}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
