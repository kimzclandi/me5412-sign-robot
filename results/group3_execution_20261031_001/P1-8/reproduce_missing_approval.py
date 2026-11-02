"""Read-only P1-8 approval reproducer; exit 2 means approval input is blocked."""
import argparse
import json
import os
from pathlib import Path
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[3])
args = parser.parse_args()
root = args.root.resolve()
sys.path.insert(0, str(root / 'src'))
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[name] = '1'
from sign_robot.pair_contract import freeze_library, load_policy
from sign_robot.pair_windows import load_window_approvals, WindowApprovalError

policy = load_policy(root / 'config/transition_policy_v2.json', supported_versions=(1, 2))
library, _ = freeze_library(root, policy)
try:
    approved = load_window_approvals(root, policy, library)
    print(json.dumps({'approval_count': len(approved), 'state': 'approval_bundle_loaded'}))
except WindowApprovalError as exc:
    print(json.dumps({'type': type(exc).__name__, 'code': exc.code, 'details': exc.details}, ensure_ascii=False))
    sys.exit(2)
