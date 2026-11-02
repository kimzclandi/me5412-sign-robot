import json
from pathlib import Path
import shutil

ROOT = Path('/tmp/me5412_corrected_intervals_20261031_001/repository')
OUT = ROOT / 'results/user_protected_correction_20261031_001'
BASE = Path('/home/kingderman/Documents/ME5412/execution_evidence/corrected_intervals_20261031_001')
OUT.mkdir(exist_ok=False)
for name in ('R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'FINAL', 'tooling'):
    (OUT/name).mkdir()
for path in (BASE/'R1').iterdir():
    shutil.copy2(path, OUT/'R1'/path.name)
shutil.copy2('/tmp/me5412_preserve_correction.py', OUT/'tooling')
(OUT/'R1/preservation.command.json').write_text(json.dumps({
    'argv': ['python3', '/tmp/me5412_preserve_correction.py'],
    'cwd': '/home/kingderman/Documents/ME5412', 'exit_code': 0,
    'operation': 'archive current installed repository, restore fresh stage, compare full inventories'
}, indent=2)+'\n')
for name in ('HANDOFF.md', 'HANDOFF.en.md'):
    destination = OUT/'R1/before'/name
    destination.parent.mkdir(exist_ok=True)
    shutil.copy2(ROOT/name, destination)

cn = '''# 当前执行交接

[English](HANDOFF.en.md) · [项目状态](STATE.md) · [本次更正报告](TASK-22.md)

更新：2026-10-31（Asia/Shanghai）。用户最新更正为 **COME 0.93～4.40 秒、NOW 0.13～2.53 秒**，取代此前区间。30 Hz、0 起始、两端包含，向外保护为 **COME [27,132]（0.90～4.40 秒）、NOW [3,76]（0.10～2.533333 秒）**。原姿态、顺序、相对时序保持，不允许修改原词。算法选择保护段之外的裁剪与新过渡；窗口必须标为 algorithm，不是用户或第二组审批。

目标仓库 `/home/kingderman/Documents/ME5412-github-latest`，聊天 cwd 是另一检出。分支 `codex/group3-all-pairs-v1`，HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`。本次从当前已安装状态重新归档并恢复到 `/tmp/me5412_corrected_intervals_20261031_001/repository`，按 R1→R7 串行执行；保留旧配置、旧证据与所有未提交/未跟踪文件。

动作绑定仍是 hospital_v1 实际选中的 COME `motions/studio_galt_v1/COME.npz`（201 帧，SHA-256 `75d6455408ce6584043baedbd0e049cbeabcad534eda65ef561d2c7293b477a4`）和 NOW `motions/wlasl_video_v1/NOW.npz`（104 帧，SHA-256 `2d494c13fdf1b44bb11e97004e7b212ea5c45b7b0f8d0b972bd3589ae63e15e3`）；本次只读核验哈希相同。另一个 COME WLASL 版只有 89 帧，不能容纳保护段，不使用。此前展示视频的字节身份仍不可得，绑定依据为当前用户指令、实际词库和帧范围一致性，不虚构视频身份。

上一轮 TASK-15～21 与 results/user_protected_auto_20261031_001 属于旧区间的历史证据；其 0/4 结论不得当成本次更正的实测结果。现有自动窗口、裁剪、候选与独立验证实现已完成，无须重做。更正必须新增输入/政策版本与 run_id，保持原工程阈值和 formal_acceptance_enabled=false，重新筛选四对、规划、保存文件复核并导出标注视频；试点与 1,225 全词库分母分开统计。

完整更正基线归档 `/home/kingderman/Documents/ME5412/execution_evidence/corrected_intervals_20261031_001/baseline.tar`，SHA-256 `c7386f1b813e51fbd1df0a787f2d5f3182496095876ee41172601bfd9a098e03`，8,726 条目恢复全匹配。新证据目录 results/user_protected_correction_20261031_001。只逐文件安装明确差异并检查原哈希，不 reset/clean、不改 PLAN.md、原动作、模型或历史运行。保护段自身异常必须报告，不能删除或调时以通过。真实几何数值结果不等于连续碰撞证明、ASL 理解或实机审批。
'''
en = '''# Current execution handoff

[中文](HANDOFF.md) · [Project state](STATE.en.md) · [Correction report](TASK-22.en.md)

Updated 2026-10-31 (Asia/Shanghai). The latest user correction is **COME 0.93–4.40 s and NOW 0.13–2.53 s**, superseding the previous intervals. At 30 Hz, zero based and inclusive, outward protection is **COME [27,132] (0.90–4.40 s), NOW [3,76] (0.10–2.533333 s)**. Preserve original poses, order and relative timing. The algorithm chooses external cuts and new transitions; label windows algorithm, never user or group-2 approval.

Target `/home/kingderman/Documents/ME5412-github-latest`; chat cwd is a different checkout. Branch `codex/group3-all-pairs-v1`, HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`. A new archive of the currently installed state was restored to `/tmp/me5412_corrected_intervals_20261031_001/repository`. Execute R1→R7 serially, preserving old configurations, evidence and all uncommitted/untracked work.

Motion bindings remain the actual hospital_v1 selections: COME `motions/studio_galt_v1/COME.npz` (201 frames, SHA-256 `75d6455408ce6584043baedbd0e049cbeabcad534eda65ef561d2c7293b477a4`) and NOW `motions/wlasl_video_v1/NOW.npz` (104 frames, SHA-256 `2d494c13fdf1b44bb11e97004e7b212ea5c45b7b0f8d0b972bd3589ae63e15e3`). Read-only checks confirmed both hashes. The alternative 89-frame WLASL COME cannot contain the protected range and is excluded. Byte identity of the earlier displayed video remains unavailable; binding uses the current instruction, selected library and frame-range compatibility, without inventing video identity.

TASK-15–21 and results/user_protected_auto_20261031_001 are historical evidence for the old intervals. Their 0/4 result is not the measured correction result. Existing automatic-window, cut, route and independent-verification implementation is already present. Create new input/policy versions and run_id, keep engineering thresholds and formal_acceptance_enabled=false, and rerun screening, four real pairs, saved-file verification and annotated videos. Count the pilot separately from the 1,225-pair universe.

Correction baseline archive: `/home/kingderman/Documents/ME5412/execution_evidence/corrected_intervals_20261031_001/baseline.tar`, SHA-256 `c7386f1b813e51fbd1df0a787f2d5f3182496095876ee41172601bfd9a098e03`; all 8,726 restored entries match. New evidence: results/user_protected_correction_20261031_001. Install only enumerated files with baseline-hash checks. No reset/clean or edits to PLAN.md, original motions/models or historical runs. Report intrinsic protected-source failures without deletion or retiming. Real-geometry numerical checks do not certify continuous collision safety, ASL comprehension or hardware approval.
'''
(ROOT/'HANDOFF.md').write_text(cn)
(ROOT/'HANDOFF.en.md').write_text(en)
print(json.dumps({'R1': 'complete', 'archive_verified_entries': 8726,
    'updated_files': ['HANDOFF.md', 'HANDOFF.en.md'], 'target_untouched': True}))
