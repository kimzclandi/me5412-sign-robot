#!/usr/bin/env python3
"""Run the frozen hospital vocabulary's ordered all-pairs development scan.

This entry point is intentionally separate from ``plan_transitions.py --all``:
the latter retains its ten demonstration sentences, while this command owns
35 x 35 = 1,225 ordered pairs, including the 35 self-pairs.
"""
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

from sign_robot.all_pairs import run_scan
from sign_robot.pair_contract import load_policy


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", default="hospital_v1", choices=("hospital_v1",))
    parser.add_argument("--include-self", action="store_true", default=False,
                        help="Required for the frozen 1,225-pair scope")
    parser.add_argument("--policy", type=Path, default=ROOT / "config/transition_policy.json")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--results-root", type=Path, default=ROOT / "results/all_pairs")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-pairs", type=int)
    parser.add_argument("--pair", action="append", dest="pairs",
                        help="Optional pair_id SOURCE__TARGET; may be repeated")
    parser.add_argument("--pairs-file", type=Path, help="JSON object containing a frozen pair_ids list")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    if not args.include_self:
        parser.error("--include-self is required; dropping self-pairs changes the frozen denominator")
    policy = load_policy(args.policy)
    if policy["scope"]["library"] != args.library:
        parser.error("--library does not match the policy")
    selected = set(args.pairs) if args.pairs else None
    if args.pairs_file:
        selected = set(json.loads(args.pairs_file.read_text(encoding="utf-8"))["pair_ids"]) | (selected or set())

    def progress(done, total, record):
        if not args.quiet:
            print(json.dumps({"done": done, "total": total, "pair_id": record["pair_id"],
                              "status": record["status"], "reason_codes": record["reason_codes"]},
                             ensure_ascii=False), flush=True)

    run_dir, summary = run_scan(ROOT, policy, args.run_id, args.results_root,
                                resume=args.resume, max_pairs=args.max_pairs,
                                selected_pairs=selected, progress=progress)
    print(json.dumps({"run_dir": str(run_dir), "summary": summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
