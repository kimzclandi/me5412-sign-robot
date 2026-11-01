import sys
sys.path.insert(0,'/tmp/me5412-execution-20261031')
from execution_support import *
run_id='handoff_v2_dev_20261031_002'
run_dir=SOURCE/'results/all_pairs'/run_id
if run_dir.exists(): raise SystemExit('Run already exists; preserve it and choose a new run_id')
folder=STAGE/EVIDENCE_REL/'FINAL'
plan_args=[PYTHON,str(SOURCE/'scripts/plan_all_pairs.py'),'--include-self','--policy',str(SOURCE/'config/transition_policy_v2.json'),'--run-id',run_id]
for pair in ('HELLO__PLEASE','PLEASE__HELLO','HELLO__HELLO','NURSE__NURSE'): plan_args += ['--pair',pair]
for name,args in [
 ('source_plan_four',plan_args),
 ('source_verify_four',[PYTHON,str(SOURCE/'scripts/verify_all_pairs.py'),'--run-id',run_id]),
 ('source_summarize_four',[PYTHON,str(SOURCE/'scripts/summarize_all_pairs.py'),'--run-id',run_id])]:
 result=run('FINAL',name,args,cwd=SOURCE,timeout=50)
 if result.returncode: raise SystemExit(result.returncode)
before={str(p.relative_to(run_dir)):sha(p) for p in sorted(run_dir.rglob('*')) if p.is_file()}
json_write(folder/'source_before_resume_hashes.json',before)
result=run('FINAL','source_resume_four',[*plan_args,'--resume'],cwd=SOURCE,timeout=50)
if result.returncode: raise SystemExit(result.returncode)
after={str(p.relative_to(run_dir)):sha(p) for p in sorted(run_dir.rglob('*')) if p.is_file()}
diffs=[p for p in sorted(set(before)|set(after)) if before.get(p)!=after.get(p)]
summary=__import__('json').loads((run_dir/'summary.json').read_text())
manifest=__import__('json').loads((run_dir/'manifest.json').read_text())
checks={
 'fixed_denominators':[summary['groups'][k]['denominator'] for k in ('all','non_self','self')]==[1225,1190,35],
 'four_blocked_input':summary['groups']['all']['status_counts']['BLOCKED_INPUT']==4,
 '1221_not_run':summary['groups']['all']['status_counts']['NOT_RUN']==1221,
 'zero_pass':summary['groups']['all']['status_counts']['PASS_SIM']==0,
 'zero_candidates':summary['saved_candidates']==0,
 'four_independent_diagnoses':summary['verified_records']==4,
 'all_run_bytes_unchanged_on_resume':not diffs,
 'formal_acceptance_disabled':summary['formal_acceptance_enabled'] is False,
}
result={'run_id':run_id,'run_dir':str(run_dir),'identity':manifest['identity'],'summary':summary,
        'checked_file_count':len(before),'changed_files_after_resume':diffs,'checks':checks,
        'state':'PASS_DIAGNOSTIC_AND_RESUME' if all(checks.values()) else 'ERROR',
        'L2_complete':False}
json_write(folder/'source_development_diagnosis.json',result)
print(__import__('json').dumps(result,ensure_ascii=False,indent=2),flush=True)
if not all(checks.values()): raise SystemExit(1)
