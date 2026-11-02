#!/usr/bin/env python3
"""Create the T00/T02 frozen manifest and per-word audit."""
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

from sign_robot.all_pairs import build_context
from sign_robot.pair_contract import atomic_json, freeze_library, load_policy


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=ROOT / "config/transition_policy.json")
    parser.add_argument("--manifest", type=Path, default=ROOT / "library_manifest.json")
    parser.add_argument("--audit", type=Path, default=ROOT / "word_audit.json")
    args = parser.parse_args(argv)
    policy = load_policy(args.policy)
    library, clips = freeze_library(ROOT, policy)
    context = build_context(ROOT, policy, library=library, clips=clips)
    atomic_json(args.manifest, library)
    atomic_json(args.audit, context.audit)
    result = {"manifest": str(args.manifest), "audit": str(args.audit), "word_count": library["word_count"],
              "pair_count": library["pair_count"], "input_errors": library["input_errors"],
              "environment": library["environment"]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
