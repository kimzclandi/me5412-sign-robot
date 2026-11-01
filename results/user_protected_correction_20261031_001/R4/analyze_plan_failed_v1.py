"""Summarize the corrected frozen four-pair planning run."""
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'src'))
from sign_robot.pair_contract import atomic_json
from sign_robot.pair_runner_v2 import V2RunStore

out = ROOT/'results/user_protected_correction_20261031_001'
store = V2RunStore.load(ROOT, out/'runs/user_protected_corrected_pilot_20261031_001')
pairs = {}
for pair in ('COME__NOW', 'NOW__COME', 'COME__COME', 'NOW__NOW'):
    record = store._head_record(pair)
    assert record['completed']
    assert set(record['method_coverage']) == set(store.policy['planner']['methods'])
    assert all(x['attempted'] for x in record['method_coverage'].values())
    saved = [store._read_attempt(a, pair) for a in record['attempts']]
    pairs[pair] = {'planning_status': record['status'], 'candidate_count': record['candidate_count'],
        'attempt_count': len(record['attempts']), 'methods': record['method_coverage'],
        'attempts_by_method': dict(Counter(a['method'] for a in record['attempts'])),
        'artifact_count': sum(len(a['artifacts']) for a in saved),
        'eligible_artifact_count': sum(x['eligible_for_selection'] for a in saved for x in a['artifacts']),
        'selection': record['selected_candidate_id'], 'independent_verification_pending': True}
path = out/'R4/planning_analysis.json'
assert not path.exists()
atomic_json(path, {'identity': store.manifest['identity'], 'pairs': pairs,
    'total_attempts': sum(p['attempt_count'] for p in pairs.values()),
    'total_eligible_candidates': sum(p['candidate_count'] for p in pairs.values()),
    'all_six_families_actually_attempted_for_every_pair': True,
    'formal_acceptance_enabled': False})
print(json.dumps({p: {k: v for k,v in r.items() if k in ('planning_status','candidate_count','attempt_count','artifact_count')} for p,r in pairs.items()}, indent=2))
