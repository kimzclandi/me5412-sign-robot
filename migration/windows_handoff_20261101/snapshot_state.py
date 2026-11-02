"""Migration snapshot: exact resume state, identities and file hashes (read-only; writes one new JSON + one SHA256 list).

Usage (from the repository root): python migration/windows_handoff_20261101/snapshot_state.py OUTPUT_JSON SHA256_LIST
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(variable, "1")

from sign_robot.pair_contract import environment_record, freeze_library, load_policy, run_identity

R = ROOT / "results/hospital35_protected_20261101_001"
TRACKED = ("src", "scripts", "tests", "config", "contracts", "data/user_protection", "docs", "motions", "assets/robot")
SKIP_PARTS = {"pair_runs", "__pycache__", ".pytest_cache"}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def main(output, sha_list):
    manifest = json.loads((R / "batches/manifest.json").read_text(encoding="utf-8"))
    batches = []
    for batch_id in manifest["order"]:
        logs = sorted((R / "batch_control/pair_batches" / batch_id).glob("invocation_*.json"))
        last = json.loads(logs[-1].read_text(encoding="utf-8")) if logs else None
        batches.append({"batch_id": batch_id, "stop_reason": last["stop_reason"] if last else "NOT_STARTED_OR_INTERRUPTED",
                        "run_id": last["run_id"] if last else None, "invocations": len(logs)})
    runs = []
    for run_dir in sorted((R / "pair_runs").glob("hospital35_protected_20261101_00*")):
        run_manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        files = sorted(p for p in run_dir.rglob("*") if p.is_file())
        listing = hashlib.sha256("".join(f"{p.relative_to(run_dir)}\t{p.stat().st_size}\n" for p in files).encode()).hexdigest()
        runs.append({"run_dir": str(run_dir.relative_to(ROOT)), "run_id": run_manifest["run_id"],
                     "identity_hash": run_manifest["identity"]["identity_hash"], "heads": len(run_manifest["heads"]),
                     "files": len(files), "bytes": sum(p.stat().st_size for p in files), "path_size_listing_sha256": listing})
    policy = load_policy(ROOT / "config/transition_policy_user_protected_hospital35_v1.json", supported_versions=(2,))
    current = run_identity(freeze_library(ROOT, policy)[0], policy)
    frozen = json.loads((R / "freeze/freeze.json").read_text(encoding="utf-8"))["pair_identity"]
    partition = json.loads((R / "P1-3/parallel_partition.json").read_text(encoding="utf-8"))
    by_batch = {b["batch_id"]: b for b in batches}
    remaining = [{"run_id": w["run_id"], "cpu": w["cpu"],
                  "open_batches": [b for b in w["batches"] if by_batch[b]["stop_reason"] != "BATCH_COMPLETE"]}
                 for w in partition["workers"]]
    entries = []
    for top in TRACKED:
        for path in sorted((ROOT / top).rglob("*")):
            if path.is_file() and not SKIP_PARTS & set(path.parts):
                entries.append((str(path.relative_to(ROOT)), sha(path)))
    for path in sorted(R.rglob("*")):
        if path.is_file() and not SKIP_PARTS & set(path.relative_to(R).parts):
            entries.append((str(path.relative_to(ROOT)), sha(path)))
    for path in sorted(ROOT.glob("*.md")):
        entries.append((path.name, sha(path)))
    with open(ROOT / sha_list, "x", encoding="utf-8", newline="\n") as stream:
        stream.writelines(f"{digest}  {name}\n" for name, digest in entries)
    snapshot = {
        "schema_version": 1, "kind": "me5412_migration_snapshot_v1",
        "taken_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git": {"branch": git("branch", "--show-current"), "head": git("rev-parse", "HEAD"),
                "status_lines": len(git("status", "--porcelain").splitlines()),
                "note": "work is uncommitted on purpose: run identity includes the HEAD commit"},
        "environment": environment_record(),
        "identity": {"frozen": frozen, "current": current, "reproduces": current["identity_hash"] == frozen["identity_hash"]},
        "batches": {"total": len(batches), "complete": sum(b["stop_reason"] == "BATCH_COMPLETE" for b in batches),
                    "open": [b for b in batches if b["stop_reason"] != "BATCH_COMPLETE"]},
        "remaining_by_run": remaining, "runs": runs,
        "chain": {"p1_3_final": (R / "P1-3/progress_final.json").exists(),
                  "p1_4": (R / "sequences_full_001/aggregate").exists(),
                  "retry_definitions": (R / "retry_budget_001/definitions.json").exists()},
        "sha256_list": {"path": sha_list, "entries": len(entries)},
        "formal_acceptance_enabled": False}
    with open(ROOT / output, "x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"complete": snapshot["batches"]["complete"], "open": len(snapshot["batches"]["open"]),
                      "identity_reproduces": snapshot["identity"]["reproduces"],
                      "runs": [(r["run_id"][-3:], r["heads"], r["files"]) for r in runs],
                      "remaining": [(w["run_id"][-3:], len(w["open_batches"])) for w in remaining], "hashed_files": len(entries)}))


if __name__ == "__main__":
    main(*sys.argv[1:3])
