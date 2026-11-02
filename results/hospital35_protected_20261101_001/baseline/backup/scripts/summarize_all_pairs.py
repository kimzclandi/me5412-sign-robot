#!/usr/bin/env python3
"""Write the human-readable summary for one all-pairs run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sign_robot.all_pairs import summarize_run
from sign_robot.pair_contract import read_json, run_directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--results-root", type=Path, default=ROOT / "results/all_pairs")
    args = parser.parse_args(argv)
    run_dir = run_directory(args.results_root, args.run_id)
    if read_json(run_dir / "manifest.json").get("schema_version") == 2:
        from sign_robot.pair_runner_v2 import summarize_run_v2
        summary = summarize_run_v2(ROOT, run_dir)
    else:
        summary = summarize_run(run_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
