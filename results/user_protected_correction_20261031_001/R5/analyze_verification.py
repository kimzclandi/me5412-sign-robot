"""Audit every independent result in the corrected four-pair saved run."""
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'src'))
from sign_robot.pair_contract import atomic_json, read_json
from sign_robot.pair_runner_v2 import V2RunStore

out = ROOT/'results/user_protected_correction_20261031_001'
store = V2RunStore.load(ROOT, out/'runs/user_protected_corrected_pilot_20261031_001')
pairs = {}
expected_counts = {'COME': 106, 'NOW': 74}
for pair in ('COME__NOW', 'NOW__COME', 'COME__COME', 'NOW__NOW'):
    record = store._head_record(pair)
    assert record['independent_review_recorded']
    assert len(record['verifications']) == record['candidate_count']
    results = [read_json(store.run_dir/v['path'])['evidence'] for v in record['verifications']]
    for evidence in results:
        assert evidence['validation_complete'] and evidence['artifact_contract_passed']
        assert evidence['input_checks_passed'] and not evidence['approval_checks_passed']
        assert evidence['window_provenance'] == 'algorithm'
        assert evidence['protected_core_preserved'] and evidence['original_word_slices_preserved']
        assert evidence['word_occurrences'] == 2
        instances = evidence['protected_instance_checks']
        assert len(instances) == len({w['instance_id'] for w in instances}) == 2
        assert all(w['protected_frame_count'] == expected_counts[w['gloss']] and w['poses_bitwise_equal']
                   and w['max_relative_timing_error_s'] <= 1e-10 for w in instances)
    diagnosis = read_json(store.run_dir/record['diagnosis_file'])['evidence'] if not results else None
    if diagnosis:
        assert diagnosis['verification_scope'] == 'no_trajectory_diagnosis'
        assert diagnosis['validation_complete'] is False
    keys = sorted(set(k for e in results for k in e.get('metrics', {})))
    pairs[pair] = {'status': record['status'], 'candidate_count': record['candidate_count'],
        'independently_verified_candidates': len(results),
        'complete_candidate_verifications': sum(e['validation_complete'] for e in results),
        'numerical_pass_candidates': sum(e.get('numerical_checks_passed') is True for e in results),
        'selected_candidate_id': record['selected_candidate_id'], 'verification_state': record['verification_state'],
        'reason_counts': dict(Counter(code for e in results for code in e['reason_codes'])),
        'metric_ranges': {k: {'minimum': min(e['metrics'][k] for e in results),
                              'maximum': max(e['metrics'][k] for e in results)} for k in keys},
        'min_clearance_mm': min((e['min_clearance_mm'] for e in results), default=None),
        'diagnosis_scope': diagnosis['verification_scope'] if diagnosis else None,
        'diagnosis_reason_codes': diagnosis['reason_codes'] if diagnosis else None}
path = out/'R5/verification_analysis.json'
assert not path.exists()
atomic_json(path, {'identity': store.manifest['identity'], 'pairs': pairs,
    'total_independently_verified_candidates': sum(x['independently_verified_candidates'] for x in pairs.values()),
    'total_complete_candidate_verifications': sum(x['complete_candidate_verifications'] for x in pairs.values()),
    'total_numerical_pass_candidates': sum(x['numerical_pass_candidates'] for x in pairs.values()),
    'pilot_numerical_pass_pairs': sum(x['selected_candidate_id'] is not None for x in pairs.values()),
    'pilot_denominator': 4, 'formal_acceptance_enabled': False})
print(json.dumps({p: {k:v for k,v in x.items() if k in ('status','candidate_count','complete_candidate_verifications','numerical_pass_candidates','verification_state')} for p,x in pairs.items()}, indent=2))
