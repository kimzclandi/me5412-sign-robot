"""Install only enumerated, baseline-hash-checked task files; preserve history."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

STAGE=Path('/tmp/me5412_auto_cuts_20261031_001/repository')
TARGET=Path('/home/kingderman/Documents/ME5412-github-latest')
EVIDENCE=STAGE/'results/user_protected_auto_20261031_001'
baseline=json.loads((EVIDENCE/'R1/baseline_inventory.json').read_text())
files=['HANDOFF.md','HANDOFF.en.md','STATE.md','STATE.en.md','docs/README.md','docs/README.en.md',
       'src/sign_robot/pair_contract.py','src/sign_robot/pair_windows.py','src/sign_robot/pair_routes.py',
       'src/sign_robot/pair_search.py','src/sign_robot/pair_runner_v2.py','src/sign_robot/pair_verification_v2.py',
       'src/sign_robot/project_overview.py','config/user_protected_come_now_v1.json',
       'config/transition_policy_user_protected_v1.json','contracts/all_pairs_user_protected_v1.json',
       'scripts/screen_user_protected_cuts.py','scripts/render_user_protected_pairs.py',
       'tests/conftest.py','tests/test_user_protected_windows.py','tests/test_user_protected_cuts.py',
       'tests/test_user_protected_routes.py','tests/test_user_protected_verification.py','tests/test_user_protected_render.py']
files += [f'TASK-{n:02d}{lang}.md' for n in range(15,22) for lang in ('','.en')]
files += [str(p.relative_to(STAGE)) for p in sorted(EVIDENCE.rglob('*')) if p.is_file()]
assert len(files)==len(set(files))

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()

inventory=[]
for relative in files:
    source=STAGE/relative
    target=TARGET/relative
    assert source.is_file() and not source.is_symlink(),relative
    assert target.resolve().is_relative_to(TARGET.resolve()),relative
    expected=baseline.get(relative,{}).get('sha256')
    actual=digest(target) if target.is_file() else None
    if actual!=expected:
        raise ValueError(f'Concurrent target change; nothing installed: {relative} expected {expected} actual {actual}')
    inventory.append({'file':str(target),'relative':relative,'before_sha256':actual,'after_sha256':digest(source)})
report=EVIDENCE/'FINAL/install_manifest.json'
report.write_text(json.dumps({'target':str(TARGET),'files':inventory,'no_git_or_original_asset_writes':True},indent=2)+'\n')
inventory.append({'relative':str(report.relative_to(STAGE)),'file':str(TARGET/report.relative_to(STAGE)),
                  'before_sha256':None,'after_sha256':digest(report)})
assert not (TARGET/report.relative_to(STAGE)).exists()
for entry in inventory:
    relative=entry['relative']
    source=STAGE/relative
    destination=TARGET/relative
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent,prefix='.'+destination.name+'.',suffix='.install',delete=False) as f:
        temporary=Path(f.name)
        f.write(source.read_bytes())
        f.flush()
        os.fsync(f.fileno())
    shutil.copystat(source,temporary)
    os.replace(temporary,destination)
    assert digest(destination)==entry['after_sha256']
result={'installed_files':len(inventory),'target':str(TARGET),'every_file_hash_matched':True,
        'source_tree_git_motions_assets_and_history_preserved':True}
(TARGET/'results/user_protected_auto_20261031_001/FINAL/install_result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
