import difflib
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

ROOT=Path('/home/kingderman/Documents/ME5412-github-latest')
OUT=ROOT/'results/user_protected_auto_20261031_001'
ARCHIVE=Path('/home/kingderman/Documents/ME5412/execution_evidence/auto_cuts_20261031_001/baseline.tar')
baseline=json.loads((OUT/'R1/baseline_inventory.json').read_text())
checks=json.loads((OUT/'FINAL/final_acceptance_checklist.json').read_text())
assert checks['engineering_delivery_checks_passed'] and not checks['goal_complete']
assert len(checks['checks'])==40
install=json.loads((OUT/'FINAL/install_manifest.json').read_text())
expected={x['relative']:x['after_sha256'] for x in install['files']}
names=['STATE.md','STATE.en.md','TASK-21.md','TASK-21.en.md']
for name in names:
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected[name],name
before={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}
cn='\n源目录安装与最终验收已实际完成：977 个初始交付文件安装哈希全部匹配；在 /home/kingderman/Documents/ME5412-github-latest 执行最终清单退出 0，40 项工程检查通过。465 个原始动作/模型文件及全部基线历史结果未变；8 个保护实例的导出姿态 bitwise equal（最大姿态误差 0），相对时序保持。JSON：results/user_protected_auto_20261031_001/FINAL/final_acceptance_checklist.json；命令与日志：R7/installed_acceptance.command.json、.log。动作数值仍 0/4，goal_complete=false。\n'
en='\nInstalled-source verification actually completed: all 977 initial delivery files match installation hashes. Final checks in /home/kingderman/Documents/ME5412-github-latest exited 0, with 40 engineering checks passing. All 465 original motion/model files and baseline historical results are unchanged. All eight exported protected instances have bitwise-equal poses (maximum position error zero) and preserved relative timing. See results/user_protected_auto_20261031_001/FINAL/final_acceptance_checklist.json and R7/installed_acceptance.command.json/.log. Numerical result remains 0/4 and goal_complete=false.\n'
for name in names:
    p=ROOT/name
    p.write_text(p.read_text()+(en if '.en.' in name else cn))
for name in names:
    assert (ROOT/name).read_text().endswith(en if '.en.' in name else cn)
with tarfile.open(ARCHIVE) as tar:
    old_files={}
    changes=json.loads((OUT/'FINAL/changed_files.json').read_text())
    for entry in changes:
        relative=entry['relative']
        old_files[relative]=tar.extractfile('repository/'+relative).read() if relative in baseline else b''
    for task,relatives in [('R1',['HANDOFF.md','HANDOFF.en.md']),('R7',['STATE.md','STATE.en.md'])]:
        entries=[]
        before_hashes={}
        for rel in relatives:
            p=OUT/task/'before'/rel
            p.parent.mkdir(parents=True,exist_ok=True)
            original=old_files[rel]
            p.write_bytes(original)
            digest=hashlib.sha256(original).hexdigest()
            assert digest==baseline[rel]['sha256']
            before_hashes[rel]=digest
            entries.append({'file':str(ROOT/rel),'relative':rel,'before_sha256':digest,
                            'after_sha256':hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()})
        (OUT/task/'before_hashes.json').write_text(json.dumps(before_hashes,indent=2)+'\n')
        (OUT/task/'changes.json').write_text(json.dumps(entries,indent=2)+'\n')
patch=[]
for entry in changes:
    relative=entry['relative']
    entry['after_sha256']=hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()
    patch.extend(difflib.unified_diff(old_files[relative].decode().splitlines(True),
                 (ROOT/relative).read_text().splitlines(True),fromfile='a/'+relative,tofile='b/'+relative))
(OUT/'FINAL/changed_files.json').write_text(json.dumps(changes,indent=2)+'\n')
(OUT/'FINAL/implementation.patch').write_text(''.join(patch))
report=json.loads((OUT/'FINAL/execution_report.json').read_text())
report.update(source_install_verified=True,source_acceptance_exit_code=0,source_acceptance_checks=40,
              initial_installed_files=977,original_motion_model_files_unchanged=465,protected_exported_instances_bitwise_equal=8)
(OUT/'FINAL/execution_report.json').write_text(json.dumps(report,indent=2)+'\n')
update={'kind':'documentation_after_actual_source_verification','files':[{'relative':name,'before_sha256':before[name],
        'after_sha256':hashlib.sha256((ROOT/name).read_bytes()).hexdigest()} for name in names],
        'production_code_or_policy_changes':False,'source_acceptance_exit_code':0}
(OUT/'FINAL/post_install_report_update.json').write_text(json.dumps(update,indent=2)+'\n')
(OUT/'R7/install.command.json').write_text(json.dumps({'argv':['python3','/tmp/me5412_install_auto.py'],
    'cwd':'/home/kingderman/Documents/ME5412','exit_code':0,'installed_files':977},indent=2)+'\n')
for name in ['me5412_verify_installed.py','me5412_finish_installed.py']:
    shutil.copy2(Path('/tmp')/name,OUT/'tooling'/name)
commands=[]
for p in sorted(OUT.rglob('*.command.json')):
    commands.append({'file':str(p.relative_to(OUT)),**json.loads(p.read_text())})
(OUT/'FINAL/commands.json').write_text(json.dumps(commands,indent=2,ensure_ascii=False)+'\n')
integrity={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.rglob('*') if p.is_file()}
(OUT/'FINAL/delivery_inventory.json').write_text(json.dumps(integrity,indent=2)+'\n')
print(json.dumps({'source_verified':True,'checks':40,'original_assets_unchanged':465,'protected_instances_exact':8,
                  'report_updates':len(names),'pilot_numerical_pass':0,'pilot_denominator':4,'goal_complete':False}))
