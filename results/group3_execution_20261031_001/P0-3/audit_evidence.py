"""Read-only collision implementation audit and real saved-curve counterexamples."""
from pathlib import Path
import json
import math
import sys
import xml.etree.ElementTree as ET
import mujoco
import numpy as np
from sign_robot.motion import load_model
from sign_robot.transitions import MujocoClearance, same_hand
from sign_robot.pair_contract import read_motion
from execution_support import SOURCE, STAGE, EVIDENCE_REL, json_write, sha

folder = STAGE / EVIDENCE_REL / 'P0-3'
folder.mkdir(parents=True, exist_ok=True)
library = json.loads((SOURCE/'library_manifest.json').read_text())
model = load_model(SOURCE)
names = np.asarray(library['joint_names'])
checker = MujocoClearance(model, names, library_path=SOURCE/'motions/hospital_v1_motions.json')
geoms = [{'id': g, 'name': model.geom(g).name or f'geom_{g}',
          'body': model.body(int(model.geom_bodyid[g])).name,
          'contype': int(model.geom_contype[g]), 'conaffinity': int(model.geom_conaffinity[g]),
          'group': int(model.geom_group[g]), 'margin_m': float(model.geom_margin[g])}
         for g in range(model.ngeom)]
original_margin = model.geom_margin.copy()
original_pair_margin = model.pair_margin.copy()
native_contacts = {}
try:
    margin = checker.derivation['vendor_detection_margin_m']
    model.geom_margin[:] = np.maximum(original_margin, margin)
    model.pair_margin[:] = np.maximum(original_pair_margin, margin)
    mujoco.mj_collision(model, checker.data)
    for contact in checker.data.contact[:checker.data.ncon]:
        pair = tuple(sorted(map(int, contact.geom)))
        bodies = [model.body(int(model.geom_bodyid[g])).name for g in pair]
        body_ids = tuple(sorted(int(model.geom_bodyid[g]) for g in pair))
        classification = ('same_hand_excluded' if same_hand(bodies) else
                          'static_measured_separately' if body_ids[0] == body_ids[1] or body_ids in checker.static_body_pairs
                          else 'moving_gated')
        native_contacts[pair] = {'geom_ids': list(pair), 'bodies': bodies, 'classification': classification}
finally:
    model.geom_margin[:] = original_margin
    model.pair_margin[:] = original_pair_margin
assert np.array_equal(model.geom_margin, original_margin)
assert np.array_equal(model.pair_margin, original_pair_margin)
xml = ET.parse(SOURCE/'assets/robot/scene.xml').getroot()
from collections import Counter
inventory = {
    'schema_version': 1, 'task': 'P0-3', 'approval_status': 'pending',
    'model_hash': library['model_hash'], 'mujoco_version': mujoco.__version__,
    'scene_sha256': sha(SOURCE/'assets/robot/scene.xml'),
    'transitions_sha256': sha(SOURCE/'src/sign_robot/transitions.py'),
    'geoms': geoms, 'geom_count': int(model.ngeom), 'body_count': int(model.nbody),
    'joints': int(model.njnt), 'compiled_explicit_pairs': int(model.npair),
    'compiled_exclusions': int(model.nexclude),
    'xml_exclusions': [dict(node.attrib) for node in xml.iter('exclude')],
    'xml_pairs': [dict(node.attrib) for node in xml.iter('pair')],
    'disableflags': int(model.opt.disableflags),
    'derivation': checker.derivation,
    'static_body_pairs': [[model.body(a).name, model.body(b).name] for a,b in sorted(checker.static_body_pairs)],
    'vendor_structural_gaps': checker.vendor_structural_gaps,
    'reference_pose_native_contacts': list(native_contacts.values()),
    'reference_pose_classification_counts': dict(Counter(x['classification'] for x in native_contacts.values())),
    'reference_pose_inventory_limitation': 'expanded-margin contacts at reference pose; not a proof that every native-eligible pair is enumerated at every pose',
}
json_write(folder/'collision_inventory.json', inventory)

run = SOURCE/'results/all_pairs/all_pairs_dev_20261031_v2'
known = json.loads((SOURCE/'results/group3_all_pairs_startup/dense_additional_failures.json').read_text())
assert len(known) == 11
failures = []
for item in known:
    record = json.loads((run/'checkpoints'/f"{item['pair_id']}.json").read_text())['record']
    motion = read_motion(run/record['trajectory_file'])
    saved = motion['positions'][record['transition_start_frame']:record['transition_end_frame']+1]
    coarse = checker(saved).min_distance_m
    a,b = saved[0],saved[-1]
    resolutions = []
    for factor in (1,2,4):
        count = max((len(saved)-1)*factor, math.ceil(1.875*np.abs(b-a).max()/0.04))
        u = np.linspace(0,1,count+1)[:,None]
        progress = 10*u**3 - 15*u**4 + 6*u**5
        curve = a+(b-a)*progress
        curve[0],curve[-1] = a,b
        result = checker(curve)
        resolutions.append({'factor':factor,'sample_count':len(curve),
                            'min_clearance_mm':result.min_distance_m*1000,
                            'worst_contact':result.worst_contact})
    dense = min(r['min_clearance_mm'] for r in resolutions)
    assert coarse >= 0.002 and dense < 2.0, item['pair_id']
    failures.append({'pair_id':item['pair_id'],'coarse_clearance_mm':coarse*1000,
                     'measured_dense_clearance_mm':dense,'historical_dense_clearance_mm':item['dense_min_clearance_mm'],
                     'dense_matches_historical_atol_mm_1e_6':abs(dense-item['dense_min_clearance_mm'])<=1e-6,
                     'resolutions':resolutions})
    print(item['pair_id'],f'playback={coarse*1000:.6f} mm',f'dense={dense:.6f} mm',flush=True)
assert all(f['dense_matches_historical_atol_mm_1e_6'] for f in failures)
json_write(folder/'dense_counterexample_recheck.json',{'rechecked':len(failures),'failures':failures,
           'scope':'analytic v1 connectors only; not an all-pairs rerun or continuous collision certification'})
print(json.dumps({'geom_count':len(geoms),'static_body_pairs':len(checker.static_body_pairs),
                  'measured_vendor_pairs':len(checker.vendor_structural_gaps),
                  'reference_contact_classes':inventory['reference_pose_classification_counts'],
                  'dense_counterexamples_reproduced':len(failures)},indent=2),flush=True)
