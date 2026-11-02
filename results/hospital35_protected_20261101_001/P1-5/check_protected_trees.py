"""P1-5 check: every baseline file is unchanged; list files added since the baseline (read only)."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path("/home/kingderman/Documents/ME5412-github-latest")
RUN = "results/hospital35_protected_20261101_001"


def sha(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main(output):
    baseline = json.loads((ROOT / RUN / "baseline/protected_trees_sha256.json").read_text())
    roots = {"results": "results", "motions": "motions", "config": "config", "contracts": "contracts", "assets_robot": "assets/robot"}
    report = {}
    for name, tree in baseline.items():
        changed = [p for p, h in tree["files"].items() if not (ROOT / p).is_file() or sha(ROOT / p) != h]
        current = {str(p.relative_to(ROOT)) for p in (ROOT / roots[name]).rglob("*") if p.is_file()
                   and not str(p.relative_to(ROOT)).startswith(RUN)}
        added = sorted(current - set(tree["files"]))
        report[name] = {"baseline_files": tree["file_count"], "unchanged": tree["file_count"] - len(changed),
                        "changed_or_missing": changed, "added_outside_new_run": added}
    backups = {}
    for line in (ROOT / RUN / "baseline/backup_sha256.txt").read_text().splitlines():
        digest, relative = line.split("  ", 1)
        backups[relative] = "unchanged" if sha(ROOT / relative) == digest else "changed"
    report["edited_files_vs_backup"] = backups
    ods = Path("/home/kingderman/Documents/ME5412/outputs/01a18d89-c53d-7340-b2b8-0f8ddfd306f2/手势保护区间填写表.ods")
    report["original_ods_unchanged"] = sha(ods) == "4fe5b3bb3f7d12cf4cd4418b8431325dec48fbed3c29a2a1e29447cdf89667e3"
    with open(ROOT / output, "x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: ({kk: (len(vv) if isinstance(vv, list) else vv) for kk, vv in v.items()} if isinstance(v, dict) and k != "edited_files_vs_backup" else v)
                      for k, v in report.items() if k != "edited_files_vs_backup"}, ensure_ascii=False))
    print(json.dumps({k: v for k, v in backups.items() if v == "changed"}))


if __name__ == "__main__":
    main(sys.argv[1])
