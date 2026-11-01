"""Check saved corrected-range screening evidence without rerunning the planner."""
import json
from pathlib import Path
import numpy as np

folder = Path(__file__).resolve().parent
evidence = json.loads((folder/'endpoint_screen.json').read_text())
assert evidence['window_provenance'] == 'algorithm'
cores = {'COME': [27, 132], 'NOW': [3, 76]}
results = {}
for pair, record in evidence['pairs'].items():
    pair_result = {}
    for role, gloss in zip(('source', 'target'), pair.split('__')):
        item = record['selection'][role]
        assert item['protected_core_frames'] == cores[gloss]
        assert item['window_provenance'] == 'algorithm'
        assert item['window_version'] == 'come-now-user-protection-20261031-v2'
        assert 'approval_id' not in item
        assert len(item['endpoint_checks']) == len(item['allowed_frames'])
        assert {c['frame'] for c in item['endpoint_checks']} == set(item['allowed_frames'])
        for check in item['endpoint_checks']:
            assert check['frame'] >= cores[gloss][1] if role == 'source' else check['frame'] <= cores[gloss][0]
            assert all(k in check for k in ('min_clearance_mm', 'joint_limit_error', 'coupling_error', 'worst_contact'))
            assert set(check['boundary_state']) == {'position','velocity','acceleration'}
            assert all(len(v) == 53 and np.isfinite(v).all() for v in check['boundary_state'].values())
            if not check['boundary_limit_viable']:
                assert not check['engineering_valid'] and check['outward_limit_joints']
        assert set(item['valid_frames']) == {c['frame'] for c in item['endpoint_checks'] if c['engineering_valid']}
        pair_result[role] = {'screened': len(item['allowed_frames']), 'valid': len(item['valid_frames']),
            'protected_core_frames': cores[gloss], 'valid_frames': item['valid_frames']}
    assert record['selection']['source']['instance_id'] != record['selection']['target']['instance_id']
    results[pair] = pair_result
output = folder/'endpoint_screen_checks.json'
assert not output.exists()
output.write_text(json.dumps({'passed': True, 'pairs': results}, indent=2)+'\n')
print(json.dumps({'passed': True, 'pairs': results}, indent=2))
