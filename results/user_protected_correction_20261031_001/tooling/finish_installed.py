"""Finalize reports only after installed-source checks actually pass."""
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path('/home/kingderman/Documents/ME5412-github-latest')
OUT=ROOT/'results/user_protected_correction_20261031_001'
started=time.monotonic()
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    return json.loads(path.read_text())
def save(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
checks=read(OUT/'FINAL/final_acceptance_checklist.json')
assert checks['engineering_delivery_checks_passed'] and len(checks['checks'])==62 and not checks['goal_complete']
installed=read(OUT/'FINAL/install_result.json')['installed_files']
manifest=read(OUT/'FINAL/install_manifest.json')
expected={x['relative']:x['after_sha256'] for x in manifest['files']}
names=['STATE.md','STATE.en.md','TASK-22.md','TASK-22.en.md']
assert all(digest(ROOT/n)==expected[n] for n in names)
before={n:digest(ROOT/n) for n in names}
cn=f'\n源目录安装与最终验收已实际完成：{installed} 个初始交付文件安装哈希全部匹配；在 `/home/kingderman/Documents/ME5412-github-latest` 执行最终清单退出 0，62 项工程检查通过。465 个原始动作/模型文件及全部基线历史结果保持，8 个保护实例导出姿态 bitwise equal，原相对时序保持。详见 results/user_protected_correction_20261031_001/FINAL/final_acceptance_checklist.json 与 R7/installed_acceptance.command.json/.log。四对数值通过仍为 0/4，goal_complete=false；正式开关关闭。\n'
en=f'\nInstalled-source verification actually completed: all {installed} initial delivery files match installation hashes. Final checks in `/home/kingderman/Documents/ME5412-github-latest` exited 0 with 62 engineering checks passing. All 465 original motion/model files and baseline historical results remain unchanged. All eight exported protected instances have bitwise-equal poses and preserved relative timing. See results/user_protected_correction_20261031_001/FINAL/final_acceptance_checklist.json and R7/installed_acceptance.command.json/.log. Numerical result remains 0/4 and goal_complete=false; formal acceptance stays disabled.\n'
for name in names:
    path=ROOT/name
    path.write_text(path.read_text()+(en if '.en.' in name else cn))
changes=read(OUT/'FINAL/changed_files.json')
patch=[]
by_task={}
for change in changes:
    relative=change['relative']
    old=b''
    for task in ('R1','R2','R7'):
        candidate=OUT/task/'before'/relative
        if candidate.is_file():
            old=candidate.read_bytes()
            break
    else:
        task='R7' if relative.startswith('TASK-22') else 'R2'
    if change['before_sha256'] is not None:
        assert hashlib.sha256(old).hexdigest()==change['before_sha256']
    change['after_sha256']=digest(ROOT/relative)
    by_task.setdefault(task,[]).append(change)
    patch.extend(difflib.unified_diff(old.decode().splitlines(True),(ROOT/relative).read_text().splitlines(True),
        fromfile='a/'+relative,tofile='b/'+relative))
save(OUT/'FINAL/changed_files.json',changes)
(OUT/'FINAL/implementation.patch').write_text(''.join(patch))
for task,entries in by_task.items():
    save(OUT/task/'changes.json',entries)
report=read(OUT/'FINAL/execution_report.json')
report.update(source_install_verified=True,source_acceptance_exit_code=0,source_acceptance_checks=62,
    initial_installed_files=installed,original_motion_model_files_unchanged=465,
    protected_exported_instances_bitwise_equal=8)
save(OUT/'FINAL/execution_report.json',report)
save(OUT/'FINAL/post_install_report_update.json',{'kind':'documentation_updated_after_actual_source_verification',
    'files':[{'relative':n,'before_sha256':before[n],'after_sha256':digest(ROOT/n)} for n in names],
    'code_policy_or_motion_changes':False,'source_acceptance_exit_code':0})
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',MUJOCO_GL='egl')
keys=('PYTHONDONTWRITEBYTECODE','MUJOCO_GL','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')
for key in keys[2:]:
    env[key]='1'
argv=[str(ROOT/'.venv/bin/python'),'results/user_protected_correction_20261031_001/FINAL/acceptance.py',
    '--root',str(ROOT),'--output','results/user_protected_correction_20261031_001/FINAL/post_report_acceptance.json']
log=OUT/'R7/post_report_acceptance.log'
assert not log.exists()
check_started=time.monotonic()
with log.open('w') as stream:
    result=subprocess.run(argv,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
save(log.with_suffix('.command.json'),{'argv':argv,'cwd':str(ROOT),'exit_code':result.returncode,
    'elapsed_s':time.monotonic()-check_started,'environment_overrides':{k:env[k] for k in keys},'log':str(log)})
assert result.returncode==0,log.read_text()
save(OUT/'R7/finalize.command.json',{'argv':['python3',str(Path(__file__).resolve())],
    'cwd':os.getcwd(),'exit_code':0,'elapsed_s':time.monotonic()-started,
    'operation':'append actual installed verification to bilingual reports; regenerate diffs, manifests and final inventory'})
summary={'installed_source_verified':True,'engineering_checks':62,'initial_installed_files':installed,
    'regression_tests_passed':799,'pilot_numerical_pass_count':0,'pilot_denominator':4,'goal_complete':False}
(OUT/'R7/finalize.log').write_text(json.dumps(summary,indent=2)+'\n')
commands=[{'record_file':str(p.relative_to(OUT)),**read(p)} for p in sorted(OUT.rglob('*.command.json'))]
save(OUT/'FINAL/commands.json',commands)
inventory={str(p.relative_to(OUT)):digest(p) for p in sorted(OUT.rglob('*')) if p.is_file()
    and p.name!='delivery_inventory.json'}
save(OUT/'FINAL/delivery_inventory.json',{'files':inventory,'self_excluded':'FINAL/delivery_inventory.json'})
print(json.dumps(summary,indent=2))
