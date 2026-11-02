"""P0-1 evidence: freeze the working tree state, the original ODS and the 35 selected sources.

Writes only under results/hospital35_protected_20261101_001/baseline/ and the
byte-identical ODS input copy under data/user_protection/hospital35_20261101/.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np

ROOT = Path("/home/kingderman/Documents/ME5412-github-latest")
OUT = ROOT / "results/hospital35_protected_20261101_001/baseline"
ODS = Path("/home/kingderman/Documents/ME5412/outputs/01a18d89-c53d-7340-b2b8-0f8ddfd306f2/手势保护区间填写表.ods")
ODS_SHA = "4fe5b3bb3f7d12cf4cd4418b8431325dec48fbed3c29a2a1e29447cdf89667e3"
ODS_COPY = ROOT / "data/user_protection/hospital35_20261101/protection_intervals.ods"


def sha(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def run(*args):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=True).stdout


def tree(relative, exclude=()):
    base = ROOT / relative
    rows = {}
    for path in sorted(base.rglob("*")):
        rel = str(path.relative_to(ROOT))
        if path.is_file() and not any(rel.startswith(e) for e in exclude):
            rows[rel] = sha(path)
    return rows


def main():
    if OUT.exists():
        sys.exit("baseline exists; keep it")
    if sha(ODS) != ODS_SHA:
        sys.exit("ODS hash differs from STATE")
    OUT.mkdir(parents=True)
    (OUT / "git_head.txt").write_text(
        f"branch {run('git', 'branch', '--show-current').strip()}\nHEAD {run('git', 'rev-parse', 'HEAD').strip()}\n")
    (OUT / "git_status.txt").write_text(run("git", "status", "--porcelain=v1", "-uall"))
    (OUT / "git_diff_tracked.patch").write_text(run("git", "diff", "--binary"))
    planned = [
        "STATE.md", "STATE.en.md", "HANDOFF.md", "HANDOFF.en.md", "README.md", "README.en.md",
        "docs/README.md", "docs/README.en.md", "src/sign_robot/project_overview.py",
        *[str(p.relative_to(ROOT)) for p in sorted((ROOT / "src/sign_robot").glob("pair_*.py"))],
        *[str(p.relative_to(ROOT)) for p in sorted((ROOT / "src/sign_robot").glob("sequence_*.py"))],
        "scripts/plan_all_pairs.py", "scripts/verify_all_pairs.py", "scripts/summarize_all_pairs.py",
        "scripts/screen_user_protected_cuts.py", "scripts/plan_sequences.py", "scripts/verify_sequences.py",
        "scripts/render_sequences.py", "tests/test_sequence_v1.py", "tests/test_pair_runner_v2.py",
        "tests/test_user_protected_windows.py",
    ]
    backup = OUT / "backup"
    lines = []
    for relative in planned:
        source = ROOT / relative
        target = backup / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        lines.append(f"{sha(source)}  {relative}")
    (OUT / "backup_sha256.txt").write_text("\n".join(lines) + "\n")
    ODS_COPY.parent.mkdir(parents=True, exist_ok=True)
    if ODS_COPY.exists():
        sys.exit("ODS input copy exists; keep it")
    shutil.copyfile(ODS, ODS_COPY)
    if sha(ODS_COPY) != ODS_SHA:
        sys.exit("ODS copy differs")
    library = json.loads((ROOT / "motions/hospital_v1_motions.json").read_text(encoding="utf-8"))
    sources = []
    for word in library["glosses"]:
        path = ROOT / word["motion"]
        with np.load(path, allow_pickle=False) as data:
            times, positions, names = data["timestamps_s"], data["positions"], data["joint_names"]
        meta = path.with_suffix(".json")
        sources.append({
            "gloss": word["gloss"], "library": word["library"], "motion": word["motion"],
            "motion_sha256": sha(path), "metadata": str(meta.relative_to(ROOT)),
            "metadata_sha256": sha(meta) if meta.is_file() else None,
            "frame_count": int(len(positions)), "joint_count": int(len(names)),
            "last_frame_time_s": float(times[-1]),
            "timestamps_equal_arange_over_30": bool(np.allclose(times, np.arange(len(positions)) / 30, atol=1e-10, rtol=0)),
            "planned_source": word.get("planned_source"),
        })
    manifest = {
        "schema_version": 1,
        "ods": {"original_path": str(ODS), "sha256": ODS_SHA, "bytes": ODS.stat().st_size,
                "sheet": "保护区间填写", "header_cells": "A1:C1", "record_cells": "A2:C36",
                "repository_copy": str(ODS_COPY.relative_to(ROOT)), "repository_copy_sha256": sha(ODS_COPY)},
        "hospital_mapping": {"path": "motions/hospital_v1_motions.json",
                             "sha256": sha(ROOT / "motions/hospital_v1_motions.json")},
        "source_count": len(sources),
        "mocap_glosses": [s["gloss"] for s in sources if s["library"] == "motions/studio_galt_v1"],
        "video_glosses": [s["gloss"] for s in sources if s["library"] == "motions/wlasl_video_v1"],
        "sources": sources,
    }
    (OUT / "source_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    trees = {
        "results": tree("results", exclude=("results/hospital35_protected_20261101_001",)),
        "motions": tree("motions"), "config": tree("config"), "contracts": tree("contracts"),
        "assets_robot": tree("assets/robot"),
    }
    (OUT / "protected_trees_sha256.json").write_text(json.dumps(
        {name: {"file_count": len(rows), "tree_hash": hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest(),
                "files": rows} for name, rows in trees.items()}, indent=1) + "\n")
    print(json.dumps({"backup_files": len(lines), "sources": len(sources),
                      "mocap": manifest["mocap_glosses"], "video_count": len(manifest["video_glosses"]),
                      "trees": {k: len(v) for k, v in trees.items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
