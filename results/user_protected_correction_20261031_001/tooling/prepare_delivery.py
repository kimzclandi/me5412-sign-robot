"""Package only the corrected-input increment and its new evidence."""
import difflib
import hashlib
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
TARGET=Path('/home/kingderman/Documents/ME5412-github-latest')
OUT=ROOT/'results/user_protected_correction_20261031_001'
baseline=json.loads((OUT/'R1/baseline_inventory.json').read_text())
groups={'R1':['HANDOFF.md','HANDOFF.en.md'],
    'R2':['config/user_protected_come_now_v2.json','config/transition_policy_user_protected_v2.json',
        'tests/test_user_protected_correction.py','docs/README.md','docs/README.en.md','src/sign_robot/project_overview.py'],
    'R7':['TASK-22.md','TASK-22.en.md','STATE.md','STATE.en.md']}
files=[p for values in groups.values() for p in values]
def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
unexpected=[]
ignored=[]
for rel,entry in baseline.items():
    if entry['kind']=='file' and rel not in files:
        path=ROOT/rel
        if not path.is_file() or digest(path)!=entry['sha256']:
            (ignored if rel.startswith('results/session_logs/') else unexpected).append(rel)
    elif entry['kind']=='symlink' and (not (ROOT/rel).is_symlink() or os.readlink(ROOT/rel)!=entry['target']):
        unexpected.append(rel)
new=[]
for directory,dirs,names in os.walk(ROOT,followlinks=False):
    for name in dirs+names:
        path=Path(directory)/name
        rel=str(path.relative_to(ROOT))
        if rel not in baseline and rel not in files and path.is_file() and not path.is_relative_to(OUT):
            (ignored if rel.startswith('results/session_logs/') else new).append(rel)
assert not unexpected,unexpected
assert not new,new
changes=[]
patch=[]
for task,relatives in groups.items():
    task_changes=[]
    for rel in relatives:
        previous=b''
        expected=baseline.get(rel,{}).get('sha256')
        if expected is not None:
            before=OUT/task/'before'/rel
            assert before.is_file() and digest(before)==expected,rel
            previous=before.read_bytes()
        record={'relative':rel,'file':str(TARGET/rel),'before_sha256':expected,'after_sha256':digest(ROOT/rel)}
        changes.append(record)
        task_changes.append(record)
        patch.extend(difflib.unified_diff(previous.decode().splitlines(True),(ROOT/rel).read_text().splitlines(True),
            fromfile='a/'+rel,tofile='b/'+rel))
    (OUT/task/'changes.json').write_text(json.dumps(task_changes,indent=2)+'\n')
for task in ('R3','R4','R5','R6'):
    (OUT/task/'changes.json').write_text('[]\n')
(OUT/'FINAL/changed_files.json').write_text(json.dumps(changes,indent=2)+'\n')
(OUT/'FINAL/implementation.patch').write_text(''.join(patch))
(OUT/'FINAL/scope_audit.json').write_text(json.dumps({'passed':True,'changed_or_new_delivery_files':files,
    'unexpected_baseline_changes':unexpected,'unexpected_new_files':new,
    'staging_test_session_log_changes_excluded_from_install':ignored,
    'original_assets_old_configs_and_historical_runs_unchanged':True},indent=2)+'\n')
commands=[]
for path in sorted(OUT.rglob('*.command.json')):
    commands.append({'record_file':str(path.relative_to(OUT)),**json.loads(path.read_text())})
(OUT/'FINAL/commands.json').write_text(json.dumps(commands,indent=2,ensure_ascii=False)+'\n')
(OUT/'FINAL/delivery_files.json').write_text(json.dumps({'implementation_and_documents':files,
    'evidence_prefix':str(OUT.relative_to(ROOT)),'target':str(TARGET)},indent=2)+'\n')
print(json.dumps({'scope_check_passed':True,'changed_or_new_repo_files':len(files),
    'new_evidence_files':sum(p.is_file() for p in OUT.rglob('*')),'excluded_test_logs':ignored}))
