"""Localize raw-source limit/coupling violations under corrected protection."""
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'src'))
from sign_robot.motion import load_model
from sign_robot.pair_contract import atomic_json, coordinate_errors, file_hash, read_motion, rate_limits, load_policy

folder = Path(__file__).resolve().parent
policy_path = ROOT/'config/transition_policy_user_protected_v2.json'
policy = load_policy(policy_path, supported_versions=(1, 2))
bundle = json.loads((ROOT/policy['endpoints']['protection_file']).read_text())
model = load_model(ROOT)
couplings = json.loads((ROOT/'assets/robot/model_info.json').read_text())['couplings']
results = {}
for record in bundle['records']:
    clip = read_motion(ROOT/record['motion'])
    q, t, names = clip['positions'], clip['timestamps_s'], clip['joint_names']
    c0, c1 = record['protected_core_frames']
    limits = []
    for j, name in enumerate(names):
        joint = model.joint(str(name))
        if not joint.limited[0]:
            continue
        lower, upper = map(float, joint.range)
        errors = np.maximum(np.maximum(lower-q[c0:c1+1, j], q[c0:c1+1, j]-upper), 0)
        for local in np.flatnonzero(errors > policy['constraints']['joint_limit_tolerance_rad']):
            frame = int(c0+local)
            limits.append({'source_frame': frame, 'original_time_s': float(t[frame]), 'joint': str(name),
                'position_rad': float(q[frame,j]), 'limits_rad': [lower,upper], 'error_rad': float(errors[local])})
    rates = rate_limits(names, policy)
    speed = abs(np.diff(q[c0:c1+1], axis=0)/np.diff(t[c0:c1+1])[:,None])
    index = np.unravel_index(int(np.argmax(speed/rates)), speed.shape)
    speed_frame = int(c0+index[0])
    results[record['gloss']] = {'protected_core_frames': [c0,c1],
        'motion_sha256': file_hash(ROOT/record['motion']),
        'coordinate_errors': coordinate_errors(q[c0:c1+1], names, model, couplings),
        'joint_limit_violations': limits,
        'peak_internal_speed': {'ratio': float((speed/rates)[index]), 'value_rad_s': float(speed[index]),
            'limit_rad_s': float(rates[index[1]]), 'source_edge_frames': [speed_frame,speed_frame+1],
            'original_time_s': float(t[speed_frame]), 'joint': str(names[index[1]])}}
path = folder/'protected_coordinate_locations.json'
assert not path.exists()
atomic_json(path, {'policy_file_sha256': file_hash(policy_path), 'script_sha256': file_hash(__file__), 'words': results})
print(json.dumps(results, indent=2))
