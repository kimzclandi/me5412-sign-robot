"""Read-only engineering closeout; formal L2 criteria are reported separately."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root',type=Path,required=True)
parser.add_argument('--baseline',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--test-artifacts',type=Path,required=True)
parser.add_argument('--supplemental-evidence',type=Path)
args=parser.parse_args()
root=args.root.resolve()
def sha(path):
 if not path.is_file(): return None
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for part in iter(lambda:stream.read(1024*1024),b''): h.update(part)
 return h.hexdigest()
def load(path): return json.loads(path.read_text())
evidence=root/'results/group3_execution_20261031_001'
known_test_outputs=load(args.test_artifacts)['files']
known_test_map={row['path']:row['sha256'] for row in known_test_outputs}
entries=load(args.baseline)['entries']
latest={}
specs=[]
for path in sorted(evidence.glob('TASK-*/changes.json')):
 spec=load(path); specs.append(str(path.relative_to(root)))
 for change in spec['changes']: latest[change['path']]=change['after_sha256']
missing=[]; altered=[]; unexpected=[]; asset_count=0; asset_bad=[]; symlink_bad=[]; type_bad=[]
for relative,item in entries.items():
 p=root/relative
 if item['kind']=='file':
  actual=sha(p)
  if actual is None: missing.append(relative)
  elif actual!=item['sha256']:
   altered.append(relative)
   if relative not in latest: unexpected.append(relative)
  if relative.startswith(('assets/','motions/')):
   asset_count+=1
   if actual!=item['sha256']: asset_bad.append(relative)
 elif item['kind']=='symlink':
  expected=item.get('target',item.get('link_target'))
  if not p.is_symlink() or os.readlink(p)!=expected: symlink_bad.append(relative)
 elif item['kind']=='directory' and not p.is_dir(): type_bad.append(relative)
installed_mismatches=[relative for relative,digest in latest.items() if sha(root/relative)!=digest]
new_files=[]; new_unexpected=[]
for p in root.rglob('*'):
 if p.is_file() and not p.is_symlink():
  relative=str(p.relative_to(root))
  if relative not in entries:
   new_files.append(relative)
   if relative not in latest and not relative.startswith(('results/group3_execution_20261031_001/','results/all_pairs/handoff_v2_dev_20261031_002/','results/all_pairs/handoff_v2_dev_20261031_001/')) and relative not in known_test_map:
    new_unexpected.append(relative)
legacy=root/'results/all_pairs/all_pairs_dev_20261031_v2'
old_manifest=load(legacy/'manifest.json')
old_bad=[]
for relative,item in old_manifest['files'].items():
 p=legacy/relative
 if sha(p)!=item['sha256'] or not p.is_file() or p.stat().st_size!=item['bytes']: old_bad.append(relative)
records=[]
for p in sorted((legacy/'checkpoints').glob('*.json')):
 data=load(p); records.append(data.get('record',data))
old_counts=Counter(r['status'] for r in records)
old_pairs={r['pair_id'] for r in records}
new_run=root/'results/all_pairs/handoff_v2_dev_20261031_002'
manifest=load(new_run/'manifest.json'); summary=load(new_run/'summary.json')
new_bad=[relative for relative,digest in manifest['files'].items() if sha(new_run/relative)!=digest]
final_evidence=args.supplemental_evidence or evidence/'FINAL'
resume=load(final_evidence/'source_development_diagnosis.json')
resume_bad=[relative for relative,digest in load(final_evidence/'source_before_resume_hashes.json').items() if sha(new_run/relative)!=digest]
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[name]='1'
sys.path.insert(0,str(root/'src'))
from sign_robot.pair_contract import freeze_library,load_policy,run_identity
from sign_robot.pair_runner_v2 import V2RunStore
policy=load_policy(root/'config/transition_policy_v2.json',supported_versions=(1,2))
library,_=freeze_library(root,policy)
identity_matches=run_identity(library,policy)==manifest['identity']
V2RunStore.load(root,new_run).verify()
retained_run=root/'results/all_pairs/handoff_v2_dev_20261031_001'
retained_hashes=load(evidence/'P1-7/source_before_resume_hashes.json')
retained_bad=[name for name,digest in retained_hashes.items() if sha(retained_run/name)!=digest]
checklist={
 'known_test_outputs_match_explicit_hashes':all(sha(root/path)==digest for path,digest in known_test_map.items()),
 'prior_development_run_001_preserved':not retained_bad,
 'baseline_files_preserved_except_explicit_changes':not missing and not unexpected and not type_bad and not symlink_bad,
 'all_changes_match_latest_task_install_hashes':not installed_mismatches,
 'no_unexpected_new_files':not new_unexpected,
 'original_assets_and_motions_unchanged':not asset_bad,
 'legacy_3378_files_intact':len(old_manifest['files'])==3378 and not old_bad,
 'legacy_1225_unique_pairs_intact':len(records)==len(old_pairs)==1225 and sum(r['source_gloss']==r['target_gloss'] for r in records)==35,
 'legacy_status_counts_preserved':dict(old_counts)=={'BLOCKED_ENDPOINT':326,'FAILED_SEARCH':386,'FAILED_QUALITY':513},
 'development_run_inventory_intact':not new_bad,
 'development_run_resume_32_files_unchanged':len(resume_bad)==0 and resume['checked_file_count']==32 and not resume['changed_files_after_resume'],
 'development_run_identity_matches_installed_code_and_inputs':identity_matches,
 'development_denominators_fixed':[summary['groups'][g]['denominator'] for g in ('all','non_self','self')]==[1225,1190,35],
 'development_4_blocked_1221_not_run_zero_pass':summary['groups']['all']['status_counts']['BLOCKED_INPUT']==4 and summary['groups']['all']['status_counts']['NOT_RUN']==1221 and summary['groups']['all']['status_counts']['PASS_SIM']==0,
 'formal_acceptance_remains_disabled':policy['formal_acceptance_enabled'] is False and policy['endpoints']['review_status']=='pending' and policy['quality']['freeze_status']=='pending' and policy['validation']['approval_status']=='pending',
}
result={'scope':'engineering closeout, not formal all-pairs acceptance','checklist':checklist,
 'engineering_integrity_passed':all(checklist.values()),
 'baseline':{'entries':len(entries),'original_asset_and_motion_files_checked':asset_count,'missing_files':missing,
 'altered_files':altered,'unauthorized_alterations':unexpected,'type_mismatches':type_bad,'symlink_mismatches':symlink_bad,
 'new_file_count':len(new_files),'unexpected_new_files':new_unexpected,'installed_output_hash_mismatches':installed_mismatches},
 'known_test_outputs':known_test_outputs,'retained_development_run_001':{'file_count':len(retained_hashes),'bad_files':retained_bad},'task_install_specs':specs,'legacy':{'checked_files':len(old_manifest['files']),'bad_files':old_bad,'unique_pairs':len(old_pairs),'status_counts':dict(old_counts)},
 'development_run':{'run_id':manifest['run_id'],'identity':manifest['identity'],'bad_files':new_bad,'resume_changed_files':resume_bad,'summary':summary},
 'formal_acceptance':{'L2_complete':False,'all_1225_pass_sim':False,'actual_approval_inputs_present':False,'triple_42875_compatibility_complete':False,
 'frozen_multiword_sequences_passed':False,'actual_human_review_complete':False,'fresh_environment_reproduction_complete':False},
 'head':subprocess.run(['git','rev-parse','HEAD'],cwd=root,text=True,capture_output=True,check=True).stdout.strip()}
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
print(json.dumps({'engineering_integrity_passed':result['engineering_integrity_passed'],'checklist':checklist,'baseline':result['baseline'],
                  'legacy':result['legacy'],'formal_acceptance':result['formal_acceptance']},ensure_ascii=False,indent=2))
sys.exit(0 if all(checklist.values()) else 1)
