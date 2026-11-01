#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import hashlib
import json
import shutil
import numpy as np

SOURCE = Path('/home/kingderman/Documents/ME5412-github-latest')
STAGE = Path('/tmp/me5412-execution-20261031/restored-baseline')
EV = Path('/home/kingderman/.codex/visualizations/2026/10/30/01a18e26-94c1-7160-ba35-a119ee7cf0fb/group3-execution-20261031-001')
REPO_EV = 'results/group3_execution_20261031_001'

audit = json.loads((SOURCE / 'word_audit.json').read_text())
blockers = json.loads((SOURCE / 'results/group3_all_pairs_startup/endpoint_blockers.json').read_text())
policy = json.loads((SOURCE / 'config/transition_policy.json').read_text())
library = json.loads((SOURCE / 'library_manifest.json').read_text())
library_words = {w['gloss']: w for w in library['words']}
run_id = json.loads((SOURCE / 'results/all_pairs/all_pairs_dev_20261031_v2/manifest.json').read_text())['run_id']
words = list(audit['words'])
blocker_map = defaultdict(list)
for item in blockers:
    blocker_map[item['gloss']].append(item)

def clean_number(value):
    if isinstance(value, float) and abs(value) < 1e-12:
        return 0.0
    return value

rows = []
for gloss in words:
    item = audit['words'][gloss]
    motion_path = SOURCE / library_words[gloss]['motion']
    assert hashlib.sha256(motion_path.read_bytes()).hexdigest() == item['motion_hash'] == library_words[gloss]['motion_sha256']
    with np.load(motion_path, allow_pickle=False) as motion:
        positions = motion['positions']
        times = motion['timestamps_s']
        names = motion['joint_names']
    limits = np.array([policy['constraints']['finger_speed_rad_s'] if str(n).startswith(('L_', 'R_')) else
                       policy['constraints']['arm_speed_rad_s'] if any(p in str(n) for p in ('shoulder', 'elbow', 'wrist')) else
                       policy['constraints']['fixed_joint_speed_rad_s'] for n in names])
    rates = np.abs(np.diff(positions, axis=0)) / np.diff(times)[:, None]
    speed_events = [
        {'frame_interval': [int(i), int(i + 1)], 'time_interval_s': [float(times[i]), float(times[i + 1])],
         'joint_name': str(names[j]), 'measured_rad_s': float(rates[i, j]), 'limit_rad_s': float(limits[j]),
         'excess_rad_s': float(rates[i, j] - limits[j])}
        for i, j in np.argwhere(rates > limits + policy['constraints']['speed_tolerance_rad_s'])
    ]
    endpoint_rows = []
    for entry in blocker_map[gloss]:
        endpoint_rows.append({
            'role': entry['role'], 'frame': entry['frame'],
            'clearance_mm': clean_number(entry['clearance_mm']),
            'affected_edges': entry['affected_edges'],
            'closest_collision_pair': entry['closest_collision_pair'],
            'motion_sha256': entry['motion_hash'],
            'endpoint_status': 'blocked',
            'required_action': 'second_group_endpoint_or_motion_review',
        })
    internal_frames = item.get('original_collision_frames', [])
    speed_excess = float(item.get('speed_limit_excess_rad_s', 0.0) or 0.0)
    source_frame = item['geometric_sign_hint'][1]
    target_frame = item['geometric_sign_hint'][0]
    affected = []
    if any(e['role'] == 'source' for e in endpoint_rows):
        affected.extend(f'{gloss}__{target}' for target in words)
    if any(e['role'] == 'target' for e in endpoint_rows):
        affected.extend(f'{source}__{gloss}' for source in words)
    affected = sorted(set(affected))
    research = []
    for proposal in item.get('research_endpoints', []):
        research.append({
            'id': proposal['id'], 'role': proposal['role'], 'frame': proposal['frame'],
            'motion_sha256': proposal['motion_sha256'],
            'motion_hash_matches_proposal': proposal['motion_hash_matches_proposal'],
            'approval_status': proposal['approval_status'],
            'trim_count': proposal['trim_count'], 'trim_ratio': proposal['trim_ratio'],
            'min_clearance_mm': proposal['min_clearance_mm'],
            'selected_for_scan': proposal['selected_for_scan'],
        })
    issue_codes = []
    if endpoint_rows: issue_codes.append('ENDPOINT_BLOCKED')
    if internal_frames: issue_codes.append('WORD_INTERNAL_COLLISION')
    if speed_excess > 1e-9: issue_codes.append('WORD_SPEED_LIMIT_EXCESS')
    if not issue_codes: issue_codes.append('NO_DETECTED_GEOMETRIC_OR_SPEED_ISSUE')
    rows.append({
        'gloss': gloss,
        'motion_sha256': item['motion_hash'],
        'robot_status': item['robot_status'],
        'robot_note': item.get('robot_note'),
        'frames': item.get('frames'), 'duration_s': item.get('duration_s'),
        'core_frames': item['geometric_core_hint'], 'sign_frames': item['geometric_sign_hint'],
        'target_entry_frame': target_frame, 'source_exit_frame': source_frame,
        'issue_codes': issue_codes, 'endpoint_blockers': endpoint_rows,
        'internal_collision_frames': internal_frames,
        'internal_collision_frame_count': len(internal_frames),
        'word_min_clearance_mm': item.get('min_clearance_mm'),
        'word_closest_collision_pair': item.get('closest_collision_pair'),
        'peak_speed_rad_s': item.get('peak_speed_rad_s'),
        'speed_limit_excess_rad_s': speed_excess,
        'research_endpoints': research,
        'affected_pair_ids_from_endpoint_blockers': affected,
        'second_group_confirmation': {
            'action_motion_sha256': item['motion_hash'],
            'protected_core_frames': None,
            'geometric_core_hint_not_approval': item['geometric_core_hint'],
            'candidate_entry_frame': target_frame,
            'candidate_exit_frame': source_frame,
            'approve_or_replace_window': bool(endpoint_rows or research),
            'approve_repaired_motion_hash_if_changed': True,
            'approve_endpoint_role_and_frame': bool(endpoint_rows),
            'preserve_original_word_time_order': True,
        },
    })
    rows[-1]['speed_limit_frame_events'] = speed_events
    rows[-1]['speed_source_frames'] = sorted({event['frame_interval'][0] for event in speed_events
                                            if event['frame_interval'][1] <= source_frame})
    rows[-1]['speed_target_frames'] = sorted({event['frame_interval'][0] for event in speed_events
                                            if event['frame_interval'][0] >= target_frame})
    rows[-1]['source_kept_collision_frames'] = [f for f in internal_frames if f <= source_frame]
    rows[-1]['target_kept_collision_frames'] = [f for f in internal_frames if f >= target_frame]
    retained = []
    if rows[-1]['source_kept_collision_frames'] or rows[-1]['speed_source_frames']:
        retained.extend(f'{gloss}__{g}' for g in words)
    if rows[-1]['target_kept_collision_frames'] or rows[-1]['speed_target_frames']:
        retained.extend(f'{g}__{gloss}' for g in words)
    rows[-1]['affected_pair_ids_from_retained_word_issues'] = sorted(set(retained))
    rows[-1]['resolution_status'] = ('pending_second_group_repair_or_explanation_and_approval'
                                     if issue_codes != ['NO_DETECTED_GEOMETRIC_OR_SPEED_ISSUE'] else
                                     'no_detected_issue_semantic_core_and_windows_still_unreviewed')

manifest = {
    'schema_version': 1, 'task': 'P0-2', 'date': '2026-10-31', 'run_id': run_id,
    'library_version': audit['library_version'], 'word_count': len(words),
    'endpoint_blocker_count': len(blockers),
    'endpoint_blocker_role_count': len(blockers),
    'words_with_endpoint_blockers': sum(bool(r['endpoint_blockers']) for r in rows),
    'words_with_internal_collision': sum(bool(r['internal_collision_frames']) for r in rows),
    'words_with_speed_excess': sum(r['speed_limit_excess_rad_s'] > 1e-9 for r in rows),
    'words_without_detected_issue': sum(r['issue_codes'] == ['NO_DETECTED_GEOMETRIC_OR_SPEED_ISSUE'] for r in rows),
    'affected_pair_ids_unique_from_endpoint_blockers': sorted({pair for r in rows for pair in r['affected_pair_ids_from_endpoint_blockers']}),
    'words': rows,
    'required_second_group_materials': [
        'versioned action or repaired motion file plus SHA-256',
        'protected core frame range for each word',
        'approved source exit and target entry windows with role and frame ranges',
        'approval of any exception or exact-frame proposal, including NURSE f80/f81',
        'confirmation that original word time order remains unchanged',
    ],
    'policy_status': {
        'review_status': policy['endpoints']['review_status'],
        'quality_freeze_status': policy['quality']['freeze_status'],
        'window_strategy': policy['endpoints']['strategy'],
    },
    'input_files': {name: hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() for name in
                    ('word_audit.json', 'library_manifest.json', 'config/transition_policy.json',
                     'results/group3_all_pairs_startup/endpoint_blockers.json')},
}

assert len(words) == len(set(words)) == 35
assert len(blockers) == 10
assert manifest['words_with_internal_collision'] == 30
assert manifest['words_with_speed_excess'] == 8
assert len(manifest['affected_pair_ids_unique_from_endpoint_blockers']) == 326
assert sum(bool(r['speed_limit_frame_events']) for r in rows) == 8
actual_blocked = {json.loads(p.read_text())['record']['pair_id']
                  for p in (SOURCE/'results/all_pairs/all_pairs_dev_20261031_v2/checkpoints').glob('*.json')
                  if json.loads(p.read_text())['record']['status'] == 'BLOCKED_ENDPOINT'}
assert actual_blocked == set(manifest['affected_pair_ids_unique_from_endpoint_blockers'])
for b in blockers:
    endpoint = audit['words'][b['gloss']]['endpoints'][b['role']]
    assert endpoint['engineering_valid'] is False
    assert endpoint['frame'] == b['frame']
    assert np.isclose(endpoint['min_clearance_mm'], b['clearance_mm'], atol=1e-12, rtol=0)
    assert b['motion_hash'] == audit['words'][b['gloss']]['motion_hash']
for r in rows:
    assert all(0 <= f < r['frames'] for f in r['internal_collision_frames'])
    assert bool(r['speed_limit_frame_events']) == (r['speed_limit_excess_rad_s'] > 1e-9)
    worst = r['word_closest_collision_pair']
    assert worst is not None and 0 <= worst['frame'] < r['frames']

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')

dump(STAGE / f'{REPO_EV}/P0-2/word_issue_manifest.json', manifest)
dump(STAGE / f'{REPO_EV}/P0-2/group2_review_template.json', {
    'schema_version': 1, 'approval_status': 'pending',
    'warning': 'Template only. Nulls and pending status are not approval.',
    'words': [{
        'gloss': r['gloss'], 'baseline_motion_sha256': r['motion_sha256'],
        'reviewed_motion_sha256': None, 'repaired_motion_path': None,
        'protected_core_frames': None, 'entry_window_frames': None, 'exit_window_frames': None,
        'retiming_permission': None, 'exceptions': [], 'decision': 'pending',
        'reviewer': None, 'reviewed_at': None, 'evidence_path': None, 'evidence_sha256': None,
        'resolution_notes': None,
    } for r in rows],
})

def pair_count(r):
    return len(r['affected_pair_ids_from_endpoint_blockers'])

def md_cn():
    lines = [
        '# P0-2 逐词问题与第二组确认清单', '',
        f'运行基线：`{run_id}`；词库版本：`{audit["library_version"]}`。本清单只读取冻结审计和端点问题证据，不改变动作、保护核心、窗口或原词时序。', '',
        '## 汇总', '',
        f'- 35 个词；端点角色问题 {len(blockers)} 条，涉及 {manifest["words_with_endpoint_blockers"]} 个词。',
        f'- 词内碰撞问题 {manifest["words_with_internal_collision"]} 个词；速率超限问题 {manifest["words_with_speed_excess"]} 个词。',
        f'- 端点阻塞直接影响的唯一词对 {len(manifest["affected_pair_ids_unique_from_endpoint_blockers"])} 条；影响按 source 出边或 target 入边计算，未删除自对。',
        f'- 当前正式批准状态仍为 `review_status={policy["endpoints"]["review_status"]}`、`quality.freeze_status={policy["quality"]["freeze_status"]}`。', '',
        '## 逐词清单', '',
        '| 词 | 动作哈希 | 几何核心提示（未批准） | 原入口/出口帧 | 问题 | 影响端点词对 | 历史研究端点（均待批） |',
        '|---|---|---:|---:|---|---:|---|',
    ]
    for r in rows:
        codes = '<br>'.join(r['issue_codes'])
        research = ', '.join(f"{x['id']} f{x['frame']}" for x in r['research_endpoints']) or '无'
        lines.append(f"| {r['gloss']} | `{r['motion_sha256']}` | {r['core_frames'][0]}–{r['core_frames'][1]} | {r['target_entry_frame']} / {r['source_exit_frame']} | {codes} | {pair_count(r)} | {research} |")
    lines += ['', '## 端点角色问题', '', '| 词 | 角色 | 帧 | 端点间隙 mm | 最近碰撞对 | 影响词对 | 动作哈希 |', '|---|---|---:|---:|---|---:|---|']
    for b in blockers:
        bodies = ' × '.join(b['closest_collision_pair']['bodies'])
        affected = f"{b['gloss']}__*（source）" if b['role'] == 'source' else f"*__{b['gloss']}（target）"
        lines.append(f"| {b['gloss']} | {b['role']} | {b['frame']} | {b['clearance_mm']:.6f} | {bodies} | 35（{affected}） | `{b['motion_hash']}` |")
    lines += ['', '## 内部问题的帧与影响', '', '几何审计保存每帧最小间隙和整个词的最坏碰撞对；下表不虚构每个问题帧的全部碰撞对。各词最坏碰撞对、精确帧和速率逐关节区间见 JSON。影响词对只计实际保留前缀/后缀包含问题帧或速率区间的角色。', '', '| 词 | 词内碰撞帧（审计采样） | 最小间隙 mm | 速率超限 rad/s | 保留词片段受影响词对数 |', '|---|---|---:|---:|---:|']
    for r in rows:
        if r['internal_collision_frames'] or r['speed_limit_excess_rad_s'] > 1e-9:
            frame_text = ', '.join(map(str, r['internal_collision_frames'])) if r['internal_collision_frames'] else '无'
            lines.append(f"| {r['gloss']} | {frame_text} | {r['word_min_clearance_mm']:.6f} | {r['speed_limit_excess_rad_s']:.6f} | {len(r['affected_pair_ids_from_retained_word_issues'])} |")
    lines += ['', '## 速率问题帧区间', '', '| 词 | 超限区间数量（含每个关节） | 起帧（区间为 f→f+1） |', '|---|---:|---|']
    for r in rows:
        if r['speed_limit_frame_events']:
            lines.append(f"| {r['gloss']} | {len(r['speed_limit_frame_events'])} | {', '.join(map(str,sorted({e['frame_interval'][0] for e in r['speed_limit_frame_events']})))} |")
    lines += ['', '## 第二组确认模板', '', '每个词至少需要逐项返回以下内容：', '',
              '1. 与本清单动作哈希一致的批准动作，或修复动作的新文件与 SHA-256。',
              '2. 保护核心帧范围，明确是否允许任何入口/出口窗口，分别给出 source exit 与 target entry 的范围。',
              '3. 对每个端点异常给出角色、帧、几何/语义理由和批准人/版本；未批准时保持阻塞。',
              '4. NURSE f80 与 f81 必须分别给出确认；f80 当前研究提案裁剪 8/79，f81 另有独立端点结果，不能合并。',
              '5. 确认原词时间顺序和核心不被执行模型擅自改变；记录真实评审人、时间、证据文件和哈希。', '',
              '所有 35 词仍需核心/窗口审批；表中“无”仅表示没有历史替代端点提案。机器可读待填模板：[`group2_review_template.json`](../results/group3_execution_20261031_001/P0-2/group2_review_template.json)。', '',
              '逐词结构化材料见 [`word_issue_manifest.json`](../results/group3_execution_20261031_001/P0-2/word_issue_manifest.json)。', '',
              '本任务只完成问题定位和材料模板；不代表任何词已获得批准或可进入 `PASS_SIM`。']
    return '\n'.join(lines) + '\n'

def md_en():
    lines = [
        '# P0-2 per-word issue and second-group confirmation list', '',
        f'Baseline run: `{run_id}`; library: `{audit["library_version"]}`. This list reads frozen audit and endpoint evidence only; it does not change motions, protected cores, windows or source timing.', '',
        '## Counts', '',
        f'- 35 words; {len(blockers)} endpoint-role issues across {manifest["words_with_endpoint_blockers"]} words.',
        f'- Internal collision issues affect {manifest["words_with_internal_collision"]} words; speed excess affects {manifest["words_with_speed_excess"]} words.',
        f'- Endpoint blockers directly touch {len(manifest["affected_pair_ids_unique_from_endpoint_blockers"])} unique pairs, counted as source outgoing or target incoming edges with self-pairs retained.',
        f'- Formal approval remains `review_status={policy["endpoints"]["review_status"]}` and `quality.freeze_status={policy["quality"]["freeze_status"]}`.', '',
        '## Per-word table', '',
        '| Word | Motion hash | Geometric core hint (unapproved) | Original entry/exit | Issues | Endpoint pairs | Historical endpoint proposals (pending) |',
        '|---|---|---:|---:|---|---:|---|',
    ]
    for r in rows:
        codes = '<br>'.join(r['issue_codes'])
        research = ', '.join(f"{x['id']} f{x['frame']}" for x in r['research_endpoints']) or 'none'
        lines.append(f"| {r['gloss']} | `{r['motion_sha256']}` | {r['core_frames'][0]}–{r['core_frames'][1]} | {r['target_entry_frame']} / {r['source_exit_frame']} | {codes} | {pair_count(r)} | {research} |")
    lines += ['', '## Endpoint-role issues', '', '| Word | Role | Frame | Endpoint clearance mm | Closest pair | Affected edges | Motion hash |', '|---|---|---:|---:|---|---:|---|']
    for b in blockers:
        bodies = ' × '.join(b['closest_collision_pair']['bodies'])
        affected = f"{b['gloss']}__* (source)" if b['role'] == 'source' else f"*__{b['gloss']} (target)"
        lines.append(f"| {b['gloss']} | {b['role']} | {b['frame']} | {b['clearance_mm']:.6f} | {bodies} | 35 ({affected}) | `{b['motion_hash']}` |")
    lines += ['', '## Internal issue frames and retained slices', '', 'The audit stores minimum clearance per frame and the worst pair for the entire word. It does not enumerate all colliding pairs at every failing frame. Exact worst-pair frames and per-joint speed intervals are in the JSON. Affected pairs include only source prefixes / target suffixes that retain the offending frame or interval.', '', '| Word | Collision frames (audit samples) | Minimum clearance mm | Speed excess rad/s | Affected retained-slice pairs |', '|---|---|---:|---:|---:|']
    for r in rows:
        if r['internal_collision_frames'] or r['speed_limit_excess_rad_s'] > 1e-9:
            frame_text = ', '.join(map(str, r['internal_collision_frames'])) if r['internal_collision_frames'] else 'none'
            lines.append(f"| {r['gloss']} | {frame_text} | {r['word_min_clearance_mm']:.6f} | {r['speed_limit_excess_rad_s']:.6f} | {len(r['affected_pair_ids_from_retained_word_issues'])} |")
    lines += ['', '## Speed-limit frame intervals', '', '| Word | Per-joint violation count | Starting frames (interval f to f+1) |', '|---|---:|---|']
    for r in rows:
        if r['speed_limit_frame_events']:
            lines.append(f"| {r['gloss']} | {len(r['speed_limit_frame_events'])} | {', '.join(map(str,sorted({e['frame_interval'][0] for e in r['speed_limit_frame_events']})))} |")
    lines += ['', '## Confirmation template', '',
              'For every word, the second group should return:', '',
              '1. The approved motion matching the listed hash, or a repaired motion file with a new SHA-256.',
              '2. The protected core frame range and any permitted source-exit / target-entry window ranges.',
              '3. For each endpoint anomaly, role, frame, geometric/semantic rationale and approval version; keep it blocked without approval.',
              '4. Separate confirmation for NURSE f80 and f81. f80 currently proposes 8/79 trimming; f81 has a different endpoint result and cannot be merged.',
              '5. Confirmation that source timing order and protected cores remain unchanged, with actual reviewer, time, evidence file and hash.', '',
              'All 35 words still require core/window review; none in the table only means no historical alternative endpoint proposal. Pending machine-readable template: [`group2_review_template.json`](../results/group3_execution_20261031_001/P0-2/group2_review_template.json).', '',
              'Structured evidence: [`word_issue_manifest.json`](../results/group3_execution_20261031_001/P0-2/word_issue_manifest.json).', '',
              'This task locates issues and prepares the approval template; no word is approved or eligible for `PASS_SIM`.']
    return '\n'.join(lines) + '\n'

(STAGE / 'docs/group3-all-pairs-word-issues.md').write_text(md_cn())
(STAGE / 'docs/group3-all-pairs-word-issues.en.md').write_text(md_en())

# Copy already installed state/index files to stage before editing them for TASK-02.
for relative in ['STATE.md','STATE.en.md','docs/README.md','docs/README.en.md','TASK-01.md','TASK-01.en.md']:
    target = SOURCE / relative
    staged = STAGE / relative
    staged.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, staged)

task_cn = f'''# TASK-02：P0-2 逐词问题与确认清单

[English](TASK-02.en.md) · [项目状态](STATE.md) · [问题清单](docs/group3-all-pairs-word-issues.md)

日期：2026-10-31（Asia/Shanghai）。任务 P0-2：完成。读取 `{SOURCE / 'word_audit.json'}`、`{SOURCE / 'results/group3_all_pairs_startup/endpoint_blockers.json'}` 和开发运行 `{run_id}`，生成 35 词结构化清单与双语审阅模板。

## 修改与关键决策

- 新增 `docs/group3-all-pairs-word-issues.md`、`.en.md`，以及 `results/group3_execution_20261031_001/P0-2/word_issue_manifest.json`。
- 明确记录 {len(blockers)} 条端点角色问题（{manifest['words_with_endpoint_blockers']} 个词）、{manifest['words_with_internal_collision']} 个词的词内碰撞、{manifest['words_with_speed_excess']} 个词的速率超限；端点问题关联 {len(manifest['affected_pair_ids_unique_from_endpoint_blockers'])} 个唯一词对，保留 35 个自对。
- 记录每个词的动作哈希、保护核心提示、原始入口/出口帧、问题帧、最近碰撞对、研究端点和待确认材料。没有改变任何动作、窗口或时序。
- NURSE f80/f81、HURT f66、MEDICINE f73、INTERPRETER f25 等研究端点仍为 pending；审批输入必须绑定动作哈希，不能只改 `approved` 字符串。

## 执行命令与验证

工作目录：`{SOURCE}`。执行 `{SOURCE}/.venv/bin/python /tmp/me5412-execution-20261031/generate_p0_2.py`（生成器只写入 `/tmp` 恢复副本）并对 JSON 结构、35 词计数、端点数量、问题词数量、动作哈希和影响词对做断言；退出码 0。然后用任务级 hash-guarded installer 写入目标仓库，退出码 0，备份和清单在 `results/group3_execution_20261031_001/TASK-02/`。

P0-2 证据：[`word_issue_manifest.json`](results/group3_execution_20261031_001/P0-2/word_issue_manifest.json)。未运行 pytest；本任务是冻结证据的只读派生，并从原动作重算速率区间。正式质量阈值、保护核心/窗口和修复动作仍待第二组确认。几何证据包含每帧间隙、词级最坏碰撞对；没有逐帧枚举所有碰撞对，不将此任务当作新几何审计。

## 偏差与状态

计划要求逐词列出端点、原词缺陷、帧号、动作哈希、影响词对和第二组确认内容，已全部覆盖。计划中的“问题单”没有规定文件名，因此采用双语 docs 文件和结构化 JSON；不扩大代码范围。P0-2 完成，P0-3 为下一个原子任务；L2 仍未完成。
'''
task_en = f'''# TASK-02: P0-2 per-word issue and confirmation list

[中文](TASK-02.md) · [Project state](STATE.en.md) · [Issue list](docs/group3-all-pairs-word-issues.en.md)

Date: 2026-10-31 (Asia/Shanghai). P0-2: complete. Read `word_audit.json`, `endpoint_blockers.json` and development run `{run_id}` to generate a 35-word structured issue list and bilingual review templates.

## Changes and decisions

Added paired docs and `results/group3_execution_20261031_001/P0-2/word_issue_manifest.json`. It records {len(blockers)} endpoint-role issues across {manifest['words_with_endpoint_blockers']} words, internal collisions in {manifest['words_with_internal_collision']} words, speed excess in {manifest['words_with_speed_excess']} words, and {len(manifest['affected_pair_ids_unique_from_endpoint_blockers'])} unique endpoint-affected pairs with all 35 self-pairs retained. Each word includes motion hash, protected-core hint, original entry/exit frame, issue frames, closest pair, research endpoints and required confirmations. No motion, window or timing changed. Research endpoints including NURSE f80/f81, HURT f66, MEDICINE f73 and INTERPRETER f25 remain pending and must be hash-bound.

## Commands and verification

Working directory: `{SOURCE}`. Ran `{SOURCE}/.venv/bin/python /tmp/me5412-execution-20261031/generate_p0_2.py`, which writes only to the restored staging tree, and asserted the JSON structure, 35-word count, endpoint count, issue-word counts, motion hashes and affected pairs; exit 0. The hash-guarded installer then wrote the target checkout; exit 0. Backups/manifests are under `results/group3_execution_20261031_001/TASK-02/`. No pytest ran; this task derives frozen evidence and recalculates speed intervals from source arrays. Formal thresholds, protected cores/windows and repaired motions remain second-group dependencies. Geometry evidence provides per-frame clearances and each word's worst pair, not every collision pair at every frame.

## Deviation and state

All P0-2 requested fields are covered. The plan did not prescribe filenames, so paired docs plus structured JSON were used without expanding code scope. P0-2 complete; P0-3 is next; L2 remains incomplete.
'''
(STAGE/'TASK-02.md').write_text(task_cn)
(STAGE/'TASK-02.en.md').write_text(task_en)

# Update state and indexes while preserving bilingual pairings.
state_cn = (STAGE/'STATE.md').read_text()
state_en = (STAGE/'STATE.en.md').read_text()
state_cn = state_cn.replace('| P0-2 | 未完成 | 下一个原子任务：逐词问题及审批模板 |', '| P0-2 | 完成 | TASK-02.md；35 词问题、端点角色、帧、动作哈希和影响词对清单 |')
state_cn = state_cn.replace('| P0-3 | 未完成 | 碰撞范围审计与采样提案 |', '| P0-3 | 未完成 | 下一个原子任务：碰撞范围审计与采样提案 |')
state_en = state_en.replace('| P0-2 | Incomplete | Next atomic task: per-word issues and review templates |', '| P0-2 | Complete | TASK-02.en.md; 35-word issues, endpoint roles, frames, hashes and affected pairs |')
state_en = state_en.replace('| P0-3 | Incomplete | Collision coverage audit and sampling proposal |', '| P0-3 | Incomplete | Next atomic task: collision coverage audit and sampling proposal |')
(STAGE/'STATE.md').write_text(state_cn)
(STAGE/'STATE.en.md').write_text(state_en)
for relative in ['docs/README.md','docs/README.en.md']:
    p=STAGE/relative
    t=p.read_text()
    anchor='| P0-1 基线保全 / Baseline preservation |'
    idx=t.index('\n',t.index(anchor))+1
    line='| P0-2 逐词问题清单 / Per-word issue list | [中文](group3-all-pairs-word-issues.md) | [English](group3-all-pairs-word-issues.en.md) |\n'
    p.write_text(t[:idx]+line+t[idx:])

files = [
    'TASK-02.md','TASK-02.en.md','STATE.md','STATE.en.md',
    'docs/README.md','docs/README.en.md','docs/group3-all-pairs-word-issues.md',
    'docs/group3-all-pairs-word-issues.en.md',
    f'{REPO_EV}/P0-2/word_issue_manifest.json',
    f'{REPO_EV}/P0-2/group2_review_template.json',
]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
changes=[]
for relative in files:
    changes.append({'path':relative,'before_sha256':sha(SOURCE/relative),'after_sha256':sha(STAGE/relative)})
Path('/tmp/me5412-execution-20261031/TASK-02-changes.json').write_text(json.dumps({'task':'TASK-02','changes':changes},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'task':'P0-2','word_count':len(words),'endpoint_blockers':len(blockers),
                  'words_with_internal_collision':manifest['words_with_internal_collision'],
                  'words_with_speed_excess':manifest['words_with_speed_excess'],
                  'affected_pairs':len(manifest['affected_pair_ids_unique_from_endpoint_blockers']),
                  'files':files},ensure_ascii=False,indent=2))
