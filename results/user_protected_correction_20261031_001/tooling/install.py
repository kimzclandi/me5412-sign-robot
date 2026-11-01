"""Install enumerated files atomically after checking every target baseline hash."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

STAGE=Path(__file__).resolve().parents[3]
TARGET=Path('/home/kingderman/Documents/ME5412-github-latest')
OUT=STAGE/'results/user_protected_correction_20261031_001'
baseline=json.loads((OUT/'R1/baseline_inventory.json').read_text())
delivery=json.loads((OUT/'FINAL/delivery_files.json').read_text())
files=delivery['implementation_and_documents']+[str(p.relative_to(STAGE)) for p in sorted(OUT.rglob('*')) if p.is_file()]
assert len(files)==len(set(files))
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
inventory=[]
for rel in files:
    source=STAGE/rel
    target=TARGET/rel
    assert source.is_file() and not source.is_symlink()
    assert target.resolve().is_relative_to(TARGET.resolve())
    expected=baseline.get(rel,{}).get('sha256')
    actual=digest(target) if target.is_file() else None
    assert actual==expected,f'Concurrent target change; no installation performed: {rel}: {actual} != {expected}'
    inventory.append({'relative':rel,'file':str(target),'before_sha256':actual,'after_sha256':digest(source)})
report=OUT/'FINAL/install_manifest.json'
assert not report.exists() and not (TARGET/report.relative_to(STAGE)).exists()
report.write_text(json.dumps({'target':str(TARGET),'files':inventory,
    'all_targets_checked_before_any_write':True,'no_git_asset_or_history_writes':True},indent=2)+'\n')
inventory.append({'relative':str(report.relative_to(STAGE)),'file':str(TARGET/report.relative_to(STAGE)),
    'before_sha256':None,'after_sha256':digest(report)})
for item in inventory:
    source=STAGE/item['relative']
    destination=TARGET/item['relative']
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent,prefix='.'+destination.name+'.',suffix='.install',delete=False) as stream:
        temporary=Path(stream.name)
        stream.write(source.read_bytes())
        stream.flush()
        os.fsync(stream.fileno())
    shutil.copystat(source,temporary)
    os.replace(temporary,destination)
    assert digest(destination)==item['after_sha256']
result={'installed_files':len(inventory),'target':str(TARGET),'every_file_hash_matched':True,
    'original_assets_git_and_historical_results_preserved':True}
(TARGET/OUT.relative_to(STAGE)/'FINAL/install_result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
