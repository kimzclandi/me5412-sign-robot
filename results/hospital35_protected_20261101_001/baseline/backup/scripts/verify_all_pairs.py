#!/usr/bin/env python3
"""Independently re-read all saved development candidates."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

from sign_robot.pair_contract import read_json, run_directory
from sign_robot.pair_verification import verify_run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--results-root", type=Path, default=ROOT / "results/all_pairs")
    parser.add_argument("--max-pairs", type=int)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    if args.max_pairs is not None and args.max_pairs < 0:
        parser.error("--max-pairs must be non-negative")
    run_dir = run_directory(args.results_root, args.run_id)
    def progress(done, total, record):
        if not args.quiet and (done % 25 == 0 or done == total):
            print(json.dumps({"verified": done, "total": total, "pair_id": record["pair_id"],
                              "status": record["status"]}), flush=True)
    verify = verify_run
    if read_json(run_dir / "manifest.json").get("schema_version") == 2:
        from sign_robot.pair_runner_v2 import verify_run_v2
        verify = verify_run_v2
    summary = verify(ROOT, run_dir, max_pairs=args.max_pairs, progress=progress)
    print(json.dumps({"run_dir": str(run_dir), "summary": summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
