"""Write bilingual correction reports from completed measurements only."""
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'results/user_protected_correction_20261031_001'
TARGET=Path('/home/kingderman/Documents/ME5412-github-latest')

def read(relative):
    return json.loads((OUT/relative).read_text())

analysis=read('R6/run_analysis.json')
plan=read('R4/planning_analysis.json')
verify=read('R5/verification_analysis.json')
acceptance=read('FINAL/stage_acceptance.json')
resume=read('R5/completed_resume.json')
freeze=read('R2/engineering_freeze.json')
assert acceptance['engineering_delivery_checks_passed']
assert verify['total_complete_candidate_verifications']==84 and verify['pilot_numerical_pass_pairs']==0
assert read('R7/full_tests.command.json')['exit_code']==0
assert '799 passed in 67.50s' in (OUT/'R7/full_tests.log').read_text()
for rel in ('STATE.md','STATE.en.md'):
    path=OUT/'R7/before'/rel
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        shutil.copy2(ROOT/rel,path)

def pair_table(english=False):
    header='| Pair | Status | Eligible / reviewed | Full acceleration rad/s² | Full jerk rad/s³ | Full squared-jerk integral rad²/s⁵ | Sampled clearance mm |\n|---|---|---:|---:|---:|---:|---:|\n' if english else '| 词对 | 状态 | 可选 / 独立复核 | 完整加速度 rad/s² | 完整 jerk rad/s³ | 完整平方 jerk 积分 rad²/s⁵ | 采样间隙 mm |\n|---|---|---:|---:|---:|---:|---:|\n'
    rows=[]
    for pair in ('COME__NOW','NOW__COME','COME__COME','NOW__NOW'):
        x=analysis['pairs'][pair]
        m=x['diagnostic_curve_metrics']
        rows.append(f"| {pair.replace('__','→')} | {x['planning_status']} | {x['eligible_candidates']} / {x['independently_verified_candidates']} | {m['peak_acceleration_rad_s2']:.6f} | {m['peak_jerk_rad_s3']:.6f} | {m['jerk_integral_rad2_s5']:.6f} | {x['min_clearance_mm']:.6f} |\n")
    return header+''.join(rows)

video_table='| 词对 / Pair | 原词保留帧 / Retained original slices | 新增过渡 / Added transition | 视频 / Video |\n|---|---|---|---|\n'
for pair in ('COME__NOW','NOW__COME','COME__COME','NOW__NOW'):
    x=analysis['pairs'][pair]
    words='; '.join(f"{w['instance_id']} [{w['source_frames'][0]},{w['source_frames'][1]}]" for w in x['word_instances'])
    start,end=x['transition_time_s']
    video_table+=f"| {pair.replace('__','→')} | {words} | {start:.6f}～{end:.6f}s ({end-start:.6f}s) | [MP4]({x['video']}) |\n"

repro='''```bash
cd /home/kingderman/Documents/ME5412-github-latest
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
import hashlib, json, numpy as np
from pathlib import Path
p = json.loads(Path('config/transition_policy_user_protected_v2.json').read_text())
b = json.loads(Path(p['endpoints']['protection_file']).read_text())
for r in b['records']:
    path = Path(r['motion'])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == r['motion_sha256']
    with np.load(path, allow_pickle=False) as clip:
        t, x = clip['timestamps_s'], clip['positions']
        for _ in range(3):
            x = np.gradient(x, t, axis=0, edge_order=2)
        a, z = r['protected_core_frames']
        interior = slice(a+3, z-2)
        print(r['gloss'], float(np.trapezoid(np.sum(x[interior]**2, axis=1), x=t[interior])),
              p['quality']['limits']['jerk_integral_rad2_s5'])
PY
```
'''
commands='''```bash
.venv/bin/python scripts/screen_user_protected_cuts.py --policy config/transition_policy_user_protected_v2.json --output results/REPRO_NEW_DIR/cuts.json --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW
.venv/bin/python scripts/plan_all_pairs.py --library hospital_v1 --include-self --policy config/transition_policy_user_protected_v2.json --run-id REPRO_NEW_ID --results-root results/REPRO_NEW_DIR/runs --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW
.venv/bin/python scripts/verify_all_pairs.py --run-id REPRO_NEW_ID --results-root results/REPRO_NEW_DIR/runs
.venv/bin/python results/user_protected_correction_20261031_001/R6/fast_render.py --run-dir results/REPRO_NEW_DIR/runs/REPRO_NEW_ID --output results/REPRO_NEW_DIR/videos --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW
.venv/bin/python -m pytest -q -p no:cacheprovider tests
```
'''
env_cn='实际执行目录为 `/tmp/me5412_corrected_intervals_20261031_001/repository`；所有测试/正式运行均通过记录器设置 `PYTHONDONTWRITEBYTECODE=1`、`MUJOCO_GL=egl`，并固定 OMP/OPENBLAS/MKL/NUMEXPR 线程数为 1。复现应使用相同变量；以下模板需新建结果目录和新 run_id，不覆盖本轮结果。全仓测试允许已有测试在临时 127.0.0.1 端口启动服务。CLI 退出 0 只代表计算完成，数值通过须读取验证 JSON。'
env_en='Actual execution cwd was `/tmp/me5412_corrected_intervals_20261031_001/repository`. The command recorder set `PYTHONDONTWRITEBYTECODE=1`, `MUJOCO_GL=egl`, and OMP/OPENBLAS/MKL/NUMEXPR threads to 1 for tests and formal runs. Use those variables, a fresh results directory and a new run_id with these templates. Existing full-suite tests use temporary 127.0.0.1 services. CLI exit 0 means computation completed; read verification JSON for numerical acceptance.'

cn='''# TASK-22 — 用户更正保护区间后的 R1～R7 复核

[English](TASK-22.en.md) · [当前状态](STATE.md)

**更正已实施，四对已重新运行；数值通过 0/4，动作目标仍未完成。** 799 项回归测试通过，恢复副本 62 项最终工程检查通过；工程交付与动作验收分别报告，正式开关保持 false。

用户原话：“我要更正一下，COME是0.93～4.40s，NOW是0.13～2.53s”。30 Hz 向外取整、0 起始、两端包含：COME [27,132]（106 帧，0.90～4.40s），NOW [3,76]（74 帧，0.10～2.533333s）。取代旧保护 [27,141]/[3,102]，旧 v1 配置、TASK-15～21 和旧运行全部保留。v2 是输入/政策版本；保护数据 schema 仍是 1，轨迹 schema 仍是 2，不需要新合同格式。

目标 `/home/kingderman/Documents/ME5412-github-latest`，分支 `codex/group3-all-pairs-v1`，HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`。实际 cwd 与目标不同，先恢复当前已安装状态再执行，最终逐文件安装。已存在上一轮自动窗口实现，因此本次不重做或重构算法，只更新必要输入/测试/报告。

| 任务 ID | 修改文件或模型 | 关键决策与命令/操作 | 验证结果 | 原计划偏差 |
|---|---|---|---|---|
| R1 | HANDOFF.md/.en.md；新 R1 证据 | me5412_preserve_correction.py 完整归档当前目录含 Git、未提交/未跟踪文件和历史结果，恢复新副本 | 8,726 条目匹配；源未变；退出 0 | 本次基线是上一轮已安装成果，不复用旧副本 |
| R2 | config/user_protected_come_now_v2.json、transition_policy_user_protected_v2.json；tests/test_user_protected_correction.py；docs/README 双语和 project_overview.py 两处 SHA | 新 bundle/policy/protection ID 与原话/哈希绑定；旧合同保持；冻结相同阈值；运行窗口/合同专项 | 82 passed，退出 0；新旧输入可区分，旧审批仍兼容 | 无算法代码重写；必要下载哈希同步 |
| R3 | 新 R3 筛选/检查证据；无生产修改 | screen_user_protected_cuts.py 四对真实几何筛选；check_endpoint_screen.py 核对逐点边界状态 | COME 出/入 65/28 有效，NOW 27/3；19 passed；全部退出 0 | 复用已有筛选实现 |
| R4 | 新运行与 R4 统计；无原动作修改 | plan_all_pairs.py：direct→neutral/IK/retract→有界 RRT；相同 30s/128 候选预算，仅新增过渡调时 | 126 次尝试、342 份调时曲线与84个候选文件（共426）；四对实际尝试六类方法；43 passed；规划退出 0 | NOW→COME 新增 20 可选候选；统计辅助脚本曾失败并修复，见下文 |
| R5 | 新 R5 独立验证、源审计与续跑证据 | verify_all_pairs.py 从保存文件重建；重新计算源内部积分与具体帧；旧/新轨迹互套政策负例；完成续跑哈希检查 | 84/84 候选完整复核，0 通过；两对仅输入诊断；37 passed；784 个运行文件续跑不变；全部退出 0 | 新保护段仍有固有质量冲突，未删帧、未调时、未放宽阈值 |
| R6 | videos/ 四套视频/轨迹/CSV/截图/复核；R6/run_analysis.json | 快速栅格包装调用冻结 renderer；每个展示曲线再独立复核，逐帧比对导出保护段并映射失败到视频 | 四 MP4 可解码，305/305/402/208 帧，30 Hz；8 保护实例 bitwise equal；2 passed；全部退出 0 | 直接沿用上轮快速画面配置，未先跑慢渲染；不是人工审批 |
| R7 | TASK-22 中英、STATE 中英、FINAL 清单/差异/命令/执行报告 | 全仓 pytest、acceptance.py、安装前原哈希检查及安装后源目录验收 | 799 passed in 67.50s，退出 0；副本 62 项通过；源安装结果见末尾 | 只交付更正增量；四对试点与全词库分开 |

下表指标来自**视频对应的已保存失败诊断曲线**，不是选用解。候选列为该对所有可选候选及已独立复核数；没有可选候选的两对额外复核了视频曲线，不能把输入诊断当成完整数值通过。

'''+pair_table()+'''
84 个可选候选的连接边界、限位、耦合、密集几何和保护完整性完成独立复核；全部失败。COME→COME 64 个均因完整积分超限，积分范围 5,149,697.094075～5,521,526.772797；NOW→COME 20 个均因保护源加速度/jerk/积分超限，积分 40,208,751.485404～40,458,815.416845。所有可选候选的采样间隙最低 3.490302 mm（>2 mm），不等于连续碰撞证明。超时两对的展示曲线另有连接积分/峰值问题，COME→NOW 还存在连接解析限位违反，详见每对 independent_verification.json，未标为合格解。

根因重新计算：COME 仅原保护内部 f30～129 的平方 jerk 积分 1,479,272.694631，NOW f6～73 为 38,213,419.338553，单实例即超过 1,000,000 上限；积分非负且三帧差分模板完全在保护内，新过渡无法抵消。四对下界分别 39,692,692.033184、39,692,692.033184、2,958,545.389262、76,426,838.677107。该论证限定原 30 Hz 差分/积分定义及不改变原姿态/时序的约束，不是搜索完备性声明。保护段限位/耦合误差均为 0；内部速度满足原容差。NOW 原 f31/1.033333s 的 right_wrist_roll_joint 加速度 206.817407>120，f37/1.233333s 的 R_pinky_proximal_joint jerk 4,889.644865>3000。COME 最大积分功率在 f56/1.866667s，NOW 在 f44/1.466667s。具体关节、原帧与两个视频行的时间映射见 R5/protected_source_quality.json、protected_coordinate_locations.json、protected_source_lower_bound.json 和 R6/run_analysis.json。

'''+video_table+'''
四套目录各含 comparison.mp4、trajectory.json、replay.npz、baseline.npz、trajectory_evidence.csv、independent_verification.json、contact_sheet.png、report.json。原始行在上、算法行在下，正面在左、侧面在右；短行结尾保持，不做时间拉伸。颜色：绿保护、蓝保留、红裁剪、黄新增、灰保持。四组截图已由执行模型通过图像工具核对；不是真人目视、ASL 理解或第二组审批。快速画面只关闭抗锯齿/阴影/反射，不改几何、轨迹或验证；脚本和冻结 renderer 哈希在 videos/render_configuration.json。

所有工程数值与旧开发政策一致：2 mm 间隙、15/10 rad/s 臂/指速度、1e-6 位置容差、1e-8 限位/耦合容差、120 rad/s² 加速度、3000 rad/s³ jerk、1,000,000 rad²/s⁵ 平方 jerk 积分、6s 最大过渡、原搜索/验证预算。运行前文件 SHA 冻结在 R2/engineering_freeze.json。正式 quality.freeze_status/validation.approval_status 仍 pending，因此验证理由保留 QUALITY_THRESHOLDS_NOT_FROZEN 等正式审批缺项；开发数值冻结不冒充人工审批。

测试日期依赖在上一轮已通过注入测试时钟修复，本次保持该实现，生产仍使用真实 UTC。新增 15 项更正回归，覆盖新边界、旧版本保存、政策身份变化、旧 bundle 即使重新签文件哈希也不能混用、真实自对两次 106 帧，以及误删、伪造审批、保护引用错误与调时负例。各专项集合重叠，不相加；全仓实际为 799 项。

'''+env_cn+'\n\n'+commands+'''
正式执行命令、实际 cwd、环境、耗时、退出码与日志在 FINAL/commands.json 和各 R 目录 *.command.json/.log。规划 123.559s、独立候选复核 593.832s、渲染 90.227s。R4/analyze_plan_failed_v1.py 对包含空方法名（端点筛选）的计数字典做 sorted JSON 导出，触发 TypeError: '<' not supported between instances of 'str' and 'NoneType'，退出 1；改用 endpoint_screen 字符串后 analysis_fixed 退出 0。原脚本/失败日志保留，未改轨迹或阈值。一次只读进度查询也因运行中未生成 method_coverage 出现 KeyError，改为 get 后恢复，不影响运行。

失败最小只读复现如下，预期输出 COME 1479272.6946308068、NOW 38213419.33855339，阈值均 1000000。它不创建或覆盖结果。

'''+repro+'''
建议下一步：由工程侧先审查当前全动作质量指标与不可修改保护段的冲突，若提出有依据的指标/输入处置，必须另建版本并冻结、回归；不能为通过临时提高阈值。用户无需填写技术参数。当前原姿态、原时序与这些上限同时保持时，四对数值目标受阻。全词库 1,225（1,190 非自对/35 自对）仅执行四对：2 FAILED_QUALITY、2 TIMEOUT、1,221 NOT_RUN、0 PASS_SIM；全库 L2、三词/多词兼容、人工交叉评审、新环境复现和实机仍未完成。

保全归档 `/home/kingderman/Documents/ME5412/execution_evidence/corrected_intervals_20261031_001/baseline.tar`（894,515,200 bytes），SHA-256 `c7386f1b813e51fbd1df0a787f2d5f3182496095876ee41172601bfd9a098e03`；恢复 8,726 条目全匹配。动作绑定仍是 201 帧 Studio Galt COME 与 104 帧 WLASL NOW，SHA 见 HANDOFF.md 与新 bundle；两个文件本次重新核验，未用 89 帧 COME 替换。先前展示视频字节身份仍不可得，不虚构关联。所有旧动作/模型、旧配置/合同、TASK-01～21、PLAN.md、历史结果保留，未提交/推送/发布；按用户明确约束单代理串行执行。

最终文本差异 FINAL/implementation.patch；逐文件绝对路径、before/after SHA 见 FINAL/changed_files.json 和 install_manifest.json。回滚前先保全本次证据，再从本次归档只恢复 manifest 中已存在的修改文件，新增配置/测试/报告先移到另一个保全目录；不用 reset/clean 或全目录覆盖。验收清单将工程完整性与 goal_complete=false 分开输出。安装后源目录复核结果另附下方，不把准备安装写成完成。
'''

en='''# TASK-22 — R1–R7 rerun after the user corrected protected intervals

[中文](TASK-22.md) · [Current state](STATE.en.md)

**Correction implemented and all four pairs rerun; numerical pass 0/4, motion objective remains unmet.** All 799 regression tests passed, and 62 staging engineering checks passed. Engineering delivery and motion acceptance are separate. Formal acceptance remains false.

User wording: “我要更正一下，COME是0.93～4.40s，NOW是0.13～2.53s”. Outward rounding at 30 Hz, zero based and inclusive: COME [27,132] (106 frames, 0.90–4.40 s), NOW [3,76] (74 frames, 0.10–2.533333 s). These supersede [27,141]/[3,102]. Old v1 configurations, TASK-15–21 and runs remain unchanged. v2 is the new input/policy version; protection schema stays 1 and trajectory schema 2. Contract semantics do not change.

Target `/home/kingderman/Documents/ME5412-github-latest`, branch `codex/group3-all-pairs-v1`, HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`. Chat cwd differs from the target. A fresh restored copy of the currently installed repository was used before enumerated installation. Existing automatic-window implementation was already present, so this correction updates necessary inputs, tests and reports without algorithm refactoring.

| Task | Files/models changed | Decision and command/operation | Verification | Deviation |
|---|---|---|---|---|
| R1 | HANDOFF.md/.en.md; new R1 evidence | me5412_preserve_correction.py archives current Git, uncommitted/untracked files and results, then restores a fresh stage | All 8,726 entries match; source unchanged; exit 0 | Baseline is the installed previous delivery, not the stale prior stage |
| R2 | New user_protected_come_now_v2.json and transition_policy_user_protected_v2.json; test_user_protected_correction.py; bilingual docs indexes and two project_overview.py SHAs | Bind new IDs to exact correction and motion hashes; keep contract; freeze identical limits; run window/contract tests | 82 passed, exit 0; versions distinct, legacy approval compatible | No algorithm rewrite; required download-hash updates only |
| R3 | New R3 screening/check evidence; no production changes | screen_user_protected_cuts.py on four real pairs; check_endpoint_screen.py audits every saved boundary state | Valid exit/entry: COME 65/28, NOW 27/3; 19 passed; all exit 0 | Reuse existing screening implementation |
| R4 | New run and R4 analysis; original motions unchanged | plan_all_pairs.py direct→neutral/IK/retract→bounded RRT; same 30 s/128-candidate budget; retime new transitions only | 126 attempts, 342 timing curves plus84 candidate files (426 total); all six families attempted per pair; 43 passed; planning exit 0 | NOW→COME gains 20 eligible candidates; auxiliary analysis error fixed with original failure retained |
| R5 | New R5 independent proofs, source audit and resume evidence | verify_all_pairs.py rebuilds saved curves; recompute intrinsic integral/frame locations; cross-version negatives; completed-resume hash check | 84/84 complete candidate checks, zero numerical passes; two diagnosis-only pairs; 37 passed; all 784 run files unchanged by resume; all exit 0 | Corrected protection still conflicts with quality limits; no deletion, retiming or relaxation |
| R6 | Four video/trajectory/CSV/still/proof exports in videos/; R6/run_analysis.json | Fast raster wrapper calls frozen renderer; reverify displayed curves, compare exported protection and map failures to video time | Four decodable MP4s, 305/305/402/208 frames at 30 Hz; eight bitwise-equal protected instances; 2 passed; all exit 0 | Reuse prior fast raster settings directly; no human approval claimed |
| R7 | Bilingual TASK-22 and STATE; final checklist/diff/commands/report | Full pytest, acceptance.py, baseline-hash-checked installation and installed-source verification | 799 passed in 67.50 s, exit 0; 62 staging checks passed; installed results appended below | Correction increment only; pilot and full-library counts separate |

Metrics below describe the **saved failed diagnostic curves shown in the videos**, not selected solutions. Candidate counts include all eligible candidates and independent candidate reviews. The two zero-candidate pairs additionally have full verification for their displayed diagnostic curve; input diagnosis alone is not full-curve acceptance.

'''+pair_table(True)+'''
All 84 eligible candidates completed independent boundary, limit, coupling, dense-geometry and protection checks. All failed. Every COME→COME candidate fails the full integral, ranging 5,149,697.094075–5,521,526.772797. Every NOW→COME candidate fails intrinsic source acceleration/jerk/integral, with full integral 40,208,751.485404–40,458,815.416845. The minimum sampled clearance across eligible candidates is 3.490302 mm (>2 mm), without continuous-collision certification. Displayed timeout diagnostics also have connector integral/peak failures; COME→NOW additionally violates analytic connector joint limits. See each independent_verification.json; none is labeled acceptable.

Recomputed cause: COME protected interior f30–129 contributes 1,479,272.694631 squared jerk integral; NOW f6–73 contributes 38,213,419.338553. Each single instance exceeds 1,000,000. These are nonnegative contributions whose three-frame stencils remain entirely inside protection; a connector cannot cancel them. Four-pair lower bounds are 39,692,692.033184, 39,692,692.033184, 2,958,545.389262 and 76,426,838.677107. This conclusion uses the frozen 30-Hz finite-difference/integral definition and unchanged source poses/timing, not a search-completeness claim. Protected joint-limit and coupling errors are zero; internal speed satisfies existing tolerances. NOW source f31/1.033333 s has right_wrist_roll_joint acceleration 206.817407>120; f37/1.233333 s has R_pinky_proximal_joint jerk 4,889.644865>3000. Largest squared-jerk power occurs at COME f56/1.866667 s and NOW f44/1.466667 s. Exact joints/frames and both video-row time mappings are in R5/protected_source_quality.json, protected_coordinate_locations.json, protected_source_lower_bound.json and R6/run_analysis.json.

'''+video_table+'''
Each folder contains comparison.mp4, trajectory.json, replay.npz, baseline.npz, trajectory_evidence.csv, independent_verification.json, contact_sheet.png and report.json. Original row is above algorithm row; front is left and side is right. The shorter row holds its end without time warping. Green=protected, blue=retained, red=cut, yellow=added, gray=hold. The execution model inspected all four contact sheets using the image tool; this is not human/group-2 review or ASL comprehension. Fast raster settings disable multisampling/shadows/reflections only; geometry, trajectories and verification are unchanged. Wrapper and frozen renderer hashes are in videos/render_configuration.json.

All engineering values match the prior development policy: 2 mm clearance, 15/10 rad/s arm/finger speed, 1e-6 position tolerance, 1e-8 limit/coupling tolerance, 120 rad/s² acceleration, 3000 rad/s³ jerk, 1,000,000 rad²/s⁵ squared jerk integral, 6 s maximum transition and unchanged search/verification budgets. The file SHA was frozen before running in R2/engineering_freeze.json. Formal quality.freeze_status and validation.approval_status remain pending, so formal approval reasons such as QUALITY_THRESHOLDS_NOT_FROZEN remain in evidence. A development hash freeze does not fabricate human review.

The prior round already fixed test date dependence by injecting a test clock; that implementation is retained while production uses real UTC. Fifteen added correction tests cover new bounds, historical version retention, distinct policy identity, old-bundle rejection even after replacing its file hash, two real 106-frame self instances, deletion, forged review, wrong protection reference and retiming. Targeted sets overlap and must not be added together. The full suite actually passed 799 tests.

'''+env_en+'\n\n'+commands+'''
Actual commands, cwd, environment, durations, exit codes and logs are in FINAL/commands.json and per-task *.command.json/.log. Planning took 123.559 s, independent candidate verification 593.832 s, rendering 90.227 s. R4/analyze_plan_failed_v1.py tried sorted JSON with a mixed None/string method-count key from endpoint screening and failed with TypeError: '<' not supported between instances of 'str' and 'NoneType', exit 1. Replacing the empty method label with endpoint_screen made analysis_fixed exit 0. The failed script/log remain; no trajectory or threshold changed. A read-only live-progress query also encountered KeyError before method_coverage existed during planning; using get resolved it without affecting the run.

Minimal read-only failure reproduction follows. Expected intrinsic values are COME 1479272.6946308068 and NOW 38213419.33855339 against 1000000. It creates no outputs.

'''+repro+'''
Recommended next step: engineering review of the full-action quality metric versus immutable protection. Any justified input/metric disposition must use a new frozen version and regression run; do not raise limits just to pass. The user need not supply technical parameters. Retaining both original poses/timing and these caps blocks the four-pair numerical objective. The full universe remains 1,225 (1,190 nonself/35 self): only four executed, 2 FAILED_QUALITY, 2 TIMEOUT, 1,221 NOT_RUN and 0 PASS_SIM. Full-library L2, three/multiword compatibility, human cross-review, fresh-environment reproduction and hardware remain unfinished.

Preservation archive: `/home/kingderman/Documents/ME5412/execution_evidence/corrected_intervals_20261031_001/baseline.tar` (894,515,200 bytes), SHA-256 `c7386f1b813e51fbd1df0a787f2d5f3182496095876ee41172601bfd9a098e03`; all 8,726 restored entries match. Bindings remain the 201-frame Studio Galt COME and 104-frame WLASL NOW; complete hashes are in HANDOFF and the new bundle, rechecked this round. The 89-frame alternative COME was not substituted. Earlier displayed-video byte identity remains unavailable and is not invented. Original motions/models, old configurations/contract, TASK-01–21, PLAN.md and historical results remain unchanged. No commit/push/publication; execution remained single agent under the explicit task constraint.

Text diff: FINAL/implementation.patch. Absolute file paths and before/after SHAs: FINAL/changed_files.json and install_manifest.json. Before rollback, preserve this round’s evidence; restore only pre-existing changed files from this round’s archive, and move new configuration/test/report files into a separate preservation folder. Do not reset/clean or overwrite the full tree. Final checks separate engineering completeness from goal_complete=false. Actual installed-source verification is appended below after execution, without calling preparation completion.
'''

(ROOT/'TASK-22.md').write_text(cn)
(ROOT/'TASK-22.en.md').write_text(en)
state_cn='''# 项目执行状态

[English](STATE.en.md) · [本次更正执行报告与四对视频](TASK-22.md) · [旧区间历史报告](TASK-21.md)

更新：2026-10-31（Asia/Shanghai）。目标 `/home/kingderman/Documents/ME5412-github-latest`，分支 codex/group3-all-pairs-v1，HEAD 2875e499d79b7264b3fe0414318b30ca8aab1f4d。用户最新更正 COME 0.93～4.40s、NOW 0.13～2.53s；30 Hz 向外保护为 **COME [27,132]（106 帧）、NOW [3,76]（74 帧）**。该范围取代旧输入，旧记录保持历史身份。

**当前动作目标未完成：四对数值通过 0/4，正式 PASS_SIM=0。** 更正实现、回归、真实运行、视频与失败证据已完成；源目录安装状态见末尾。新 bundle/policy 均为 v2，算法/合同语义不变，阈值未放宽，formal_acceptance_enabled=false；不伪造用户或第二组窗口审批。

| ID | 本次实际进展 |
|---|---|
| R1 | 当前安装状态 8,726 条目完整归档并恢复匹配；中英 HANDOFF 更新 |
| R2 | 新输入/政策/保护 ID、原话与动作 SHA 绑定；新增 15 项更正测试；旧版本可读 |
| R3 | 真实几何逐点筛选，COME 有效出/入65/28，NOW27/3；边界不越保护段 |
| R4 | 四对各六类方法；126 次尝试、342 调时曲线与84候选文件，仅新过渡调时 |
| R5 | 84 候选全完成保存文件独立复核且全失败；2 输入诊断；续跑784文件不变 |
| R6 | 四个失败诊断对照视频及轨迹证据；8 保护实例导出姿态 bitwise equal，时序保持 |
| R7 | 799 passed in 67.50s，退出0；副本62工程检查通过；报告/差异/命令已生成 |

'''+pair_table()+'''
表中数值为视频对应失败曲线，TIMEOUT 不等于无解证明。COME→COME 64、NOW→COME20 候选全部完整独立复核，均不通过。所有候选采样间隙满足2mm，但原词质量失败。保护内部积分重新计算：COME f30～129 为 1,479,272.694631，NOW f6～73 为38,213,419.338553，均超过1,000,000；NOW 原f31加速度206.817407>120、f37 jerk4889.644865>3000。具体帧、关节与视频时间在新证据 R5/R6 JSON。保护姿态、顺序、相对时序没有改变。

新运行 user_protected_corrected_pilot_20261031_001，证据 results/user_protected_correction_20261031_001/。完整词库分母仍1225/1190/35：2 FAILED_QUALITY、2 TIMEOUT、1221 NOT_RUN、0 PASS_SIM；试点分母单列4，0数值通过。全库L2、多词兼容、ASL理解、人工交叉评审、新环境复现、实机均未完成。

本轮代码SHA `'''+plan['identity']['code_hash']+'''`，政策内容SHA `'''+plan['identity']['policy_hash']+'''`。动作哈希/先前视频身份缺失限制见HANDOFF；保全与回滚、命令与失败最小复现见TASK-22。旧TASK-15～21/旧v1结果不替代本次测量。单代理串行，无原始资产或历史结果修改。
'''
state_en='''# Project execution state

[中文](STATE.md) · [Correction report and four videos](TASK-22.en.md) · [Historical old-interval report](TASK-21.en.md)

Updated 2026-10-31 (Asia/Shanghai). Target `/home/kingderman/Documents/ME5412-github-latest`, branch codex/group3-all-pairs-v1, HEAD 2875e499d79b7264b3fe0414318b30ca8aab1f4d. Latest correction: COME 0.93–4.40 s, NOW 0.13–2.53 s. Outward protection at 30 Hz: **COME [27,132] (106 frames), NOW [3,76] (74 frames)**, superseding old inputs while historical records remain unchanged.

**Motion goal remains unmet: numerical pass 0/4, formal PASS_SIM=0.** Correction implementation, regression, real runs, videos and failure evidence completed. Installed-source state is appended below. New bundle/policy versions are v2; algorithm/contract semantics remain unchanged, limits are not relaxed, and formal_acceptance_enabled=false. No user/group-2 window review is fabricated.

| ID | Actual correction progress |
|---|---|
| R1 | Complete archive/restore matches all 8,726 installed baseline entries; bilingual HANDOFF updated |
| R2 | New input/policy/protection IDs bind correction and motion hashes; 15 correction tests added; old versions remain readable |
| R3 | Real-geometry point checks; valid exit/entry COME65/28, NOW27/3; no protection crossing |
| R4 | Six families per pair; 126 attempts, 342 timing curves plus84 candidate files; new transitions alone retimed |
| R5 | All 84 saved candidates independently and completely verified, all fail; 2 diagnoses; 784 files unchanged by resume |
| R6 | Four failed diagnostic comparisons with trajectory evidence; 8 bitwise-equal exported protected instances, timing preserved |
| R7 | 799 passed in 67.50 s, exit0; 62 staging engineering checks passed; reports/diff/commands generated |

'''+pair_table(True)+'''
Metrics describe displayed failed diagnostic curves. TIMEOUT is not an infeasibility proof. All 64 COME→COME and 20 NOW→COME candidates completed independent verification and failed. Candidate sampled clearance satisfies2mm, while original-word quality fails. Recomputed protected interior integral: COME f30–129=1,479,272.694631, NOW f6–73=38,213,419.338553, both above1,000,000. NOW source f31 acceleration206.817407>120 and f37 jerk4889.644865>3000. Exact frame/joint/video mappings are in new R5/R6 JSON. Protected poses, order and relative timing remain unchanged.

New run user_protected_corrected_pilot_20261031_001; evidence results/user_protected_correction_20261031_001/. Full denominators remain1225/1190/35: 2 FAILED_QUALITY, 2 TIMEOUT, 1221 NOT_RUN, 0 PASS_SIM. Pilot denominator4, zero numerical passes. Full-library L2, multiword compatibility, ASL comprehension, human cross-review, fresh-environment reproduction and hardware remain unfinished.

Code SHA `'''+plan['identity']['code_hash']+'''`; policy-content SHA `'''+plan['identity']['policy_hash']+'''`. Motion hashes and unavailable earlier-video identity are in HANDOFF. Preservation/rollback, commands and minimal failure reproduction are in TASK-22. Historical TASK-15–21/v1 results do not substitute for corrected measurements. Single-agent serial execution; original assets and historical results unchanged.
'''
(ROOT/'STATE.md').write_text(state_cn)
(ROOT/'STATE.en.md').write_text(state_en)
report={'date':'2026-10-31','timezone':'Asia/Shanghai','target':str(TARGET),'single_agent':True,
    'user_correction':{'COME':[.93,4.40],'NOW':[.13,2.53]},'protected_frames':{'COME':[27,132],'NOW':[3,76]},
    'engineering_delivery_checks_passed':True,'goal_complete':False,'pilot_numerical_pass_count':0,'pilot_denominator':4,
    'formal_pass_sim_count':0,'full_library_denominator':1225,'not_run':1221,
    'tests':{'full_passed':799,'elapsed_s':67.50,'exit_code':0,'workspace':'fresh restored staging checkout'},
    'run_id':'user_protected_corrected_pilot_20261031_001','attempts':126,'timing_curves':342,'saved_curve_files':426,'eligible_candidates':84,
    'independently_verified_candidates':84,'run_files_unchanged_on_resume':resume['file_count'],
    'stage_acceptance_checks':len(acceptance['checks']),'task_reports':['TASK-22.md','TASK-22.en.md'],
    'original_motion_model_or_historical_run_edits':False,'source_install_verified':False,
    'blocking_cause':'corrected protected-source quality exceeds unchanged frozen engineering limits',
    'identity':plan['identity'],'unchanged_threshold_policy_file_sha256':freeze['policy_file_sha256']}
(OUT/'FINAL/execution_report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'reports_written':['TASK-22.md','TASK-22.en.md','STATE.md','STATE.en.md'],
    'tests_passed':799,'stage_checks':62,'numerical_pass_pairs':0,'target_installed':False}))
