from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path('/tmp/me5412_corrected_intervals_20261031_001/repository')
OUT = ROOT/'results/user_protected_correction_20261031_001'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, value):
    assert not path.exists(), path
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n')

old_bundle_path = ROOT/'config/user_protected_come_now_v1.json'
old_policy_path = ROOT/'config/transition_policy_user_protected_v1.json'
new_bundle_path = ROOT/'config/user_protected_come_now_v2.json'
new_policy_path = ROOT/'config/transition_policy_user_protected_v2.json'
old_bundle = json.loads(old_bundle_path.read_text())
bundle = deepcopy(old_bundle)
bundle['bundle_id'] = 'user-correction-come-now-20261031-v2'
bundle['window_version'] = 'come-now-user-protection-20261031-v2'
bundle['source_instruction'] = ('User correction (verbatim): 我要更正一下，COME是0.93～4.40s，NOW是0.13～2.53s. '
    'Supersedes config/user_protected_come_now_v1.json. Outward rounding remains an engineering safeguard. '
    'The algorithm chooses external cuts and windows; no user/group-2 window approval is supplied.')
for record in bundle['records']:
    gloss = record['gloss']
    record['protection_id'] = f'user-correction-20261031-v2-{gloss}'
    record['user_interval_text'] = '0.93～4.40s' if gloss == 'COME' else '0.13～2.53s'
    record['user_interval_s'] = [0.93, 4.40] if gloss == 'COME' else [0.13, 2.53]
    record['protected_core_frames'] = [27, 132] if gloss == 'COME' else [3, 76]
    record['binding_basis'] = 'latest user correction + unchanged actual hospital_v1 selected motion SHA-256 + inclusive outward rounding'
    assert sha(ROOT/record['motion']) == record['motion_sha256']
save(new_bundle_path, bundle)
policy = json.loads(old_policy_path.read_text())
policy['policy_id'] = 'group3-come-now-user-protected-development-v2'
policy['endpoints'].update(window_version=bundle['window_version'],
    protection_file=str(new_bundle_path.relative_to(ROOT)), protection_bundle_sha256=sha(new_bundle_path))
save(new_policy_path, policy)
unchanged = ['constraints','quality','validation','planner','fps','joint_count','finger_strategies','scope']
original_development = json.loads((ROOT/'config/transition_policy_v2.json').read_text())
assert all(policy[k] == original_development[k] for k in unchanged)
save(OUT/'R2/engineering_freeze.json', {
    'policy_file': str(new_policy_path.relative_to(ROOT)), 'policy_file_sha256': sha(new_policy_path),
    'baseline': 'config/transition_policy_v2.json', 'unchanged_fields': unchanged,
    'formal_acceptance_enabled': False, 'frozen_for_development_before_pilot': True,
    'input_version_changed_without_threshold_changes': True,
    'contract_reused': 'contracts/all_pairs_user_protected_v1.json',
    'contract_semantics_unchanged': True})
save(OUT/'R2/correction_binding.json', {
    'user_correction_verbatim': '我要更正一下，COME是0.93～4.40s，NOW是0.13～2.53s',
    'previous_bundle': str(old_bundle_path.relative_to(ROOT)), 'previous_bundle_sha256': sha(old_bundle_path),
    'new_bundle': str(new_bundle_path.relative_to(ROOT)), 'new_bundle_sha256': sha(new_bundle_path),
    'previous_policy': str(old_policy_path.relative_to(ROOT)), 'previous_policy_sha256': sha(old_policy_path),
    'new_policy': str(new_policy_path.relative_to(ROOT)), 'new_policy_sha256': sha(new_policy_path),
    'rounding': 'floor(start_s * 30), ceil(end_s * 30); zero-based inclusive',
    'records': bundle['records'], 'previous_records': old_bundle['records'],
    'human_window_approval_created': False})
line = '| 用户更正保护区间与四对复核 / Corrected protection intervals and four-pair rerun | [中文](../TASK-22.md) | [English](../TASK-22.en.md) |\n'
overview = ROOT/'src/sign_robot/project_overview.py'
before = overview.read_text()
after = before
for rel in ('docs/README.md', 'docs/README.en.md'):
    path = ROOT/rel
    backup = OUT/'R2/before'/rel
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup)
    old_hash = sha(path)
    text = path.read_text()
    marker = '| R7 用户保护自动裁剪任务记录 / User-protected automatic cuts task record | [中文](../TASK-21.md) | [English](../TASK-21.en.md) |\n'
    assert text.count(marker) == 1 and line not in text
    path.write_text(text.replace(marker, marker+line))
    assert after.count(old_hash) == 1
    after = after.replace(old_hash, sha(path))
backup = OUT/'R2/before/src/sign_robot/project_overview.py'
backup.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(overview, backup)
overview.write_text(after)
for name in ('me5412_init_correction.py','me5412_correction_command.py','me5412_configure_correction.py'):
    shutil.copy2(Path('/tmp')/name, OUT/'tooling'/name)
print(json.dumps({'new_bundle': str(new_bundle_path), 'new_policy': str(new_policy_path),
    'unchanged_thresholds': True, 'source_change': 'two documentation index SHA literals only'}))
