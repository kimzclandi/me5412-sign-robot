# TASK-22 — 用户更正保护区间后的 R1～R7 复核

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

| 词对 | 状态 | 可选 / 独立复核 | 完整加速度 rad/s² | 完整 jerk rad/s³ | 完整平方 jerk 积分 rad²/s⁵ | 采样间隙 mm |
|---|---|---:|---:|---:|---:|---:|
| COME→NOW | TIMEOUT | 0 / 0 | 206.817407 | 4889.644865 | 42085845.013944 | 7.803863 |
| NOW→COME | FAILED_QUALITY | 20 / 20 | 206.817407 | 4889.644865 | 40424094.846729 | 8.085210 |
| COME→COME | FAILED_QUALITY | 64 / 64 | 97.143139 | 2196.390448 | 5154693.781190 | 8.702362 |
| NOW→NOW | TIMEOUT | 0 / 0 | 206.817407 | 4889.644865 | 79085919.079298 | 4.705174 |

84 个可选候选的连接边界、限位、耦合、密集几何和保护完整性完成独立复核；全部失败。COME→COME 64 个均因完整积分超限，积分范围 5,149,697.094075～5,521,526.772797；NOW→COME 20 个均因保护源加速度/jerk/积分超限，积分 40,208,751.485404～40,458,815.416845。所有可选候选的采样间隙最低 3.490302 mm（>2 mm），不等于连续碰撞证明。超时两对的展示曲线另有连接积分/峰值问题，COME→NOW 还存在连接解析限位违反，详见每对 independent_verification.json，未标为合格解。

根因重新计算：COME 仅原保护内部 f30～129 的平方 jerk 积分 1,479,272.694631，NOW f6～73 为 38,213,419.338553，单实例即超过 1,000,000 上限；积分非负且三帧差分模板完全在保护内，新过渡无法抵消。四对下界分别 39,692,692.033184、39,692,692.033184、2,958,545.389262、76,426,838.677107。该论证限定原 30 Hz 差分/积分定义及不改变原姿态/时序的约束，不是搜索完备性声明。保护段限位/耦合误差均为 0；内部速度满足原容差。NOW 原 f31/1.033333s 的 right_wrist_roll_joint 加速度 206.817407>120，f37/1.233333s 的 R_pinky_proximal_joint jerk 4,889.644865>3000。COME 最大积分功率在 f56/1.866667s，NOW 在 f44/1.466667s。具体关节、原帧与两个视频行的时间映射见 R5/protected_source_quality.json、protected_coordinate_locations.json、protected_source_lower_bound.json 和 R6/run_analysis.json。

| 词对 / Pair | 原词保留帧 / Retained original slices | 新增过渡 / Added transition | 视频 / Video |
|---|---|---|---|
| COME→NOW | COME#0 [27,145]; NOW#1 [1,76] | 3.933333～4.233333s (0.300000s) | [MP4](results/user_protected_correction_20261031_001/videos/COME__NOW/comparison.mp4) |
| NOW→COME | NOW#0 [3,77]; COME#1 [23,132] | 2.466667～2.966667s (0.500000s) | [MP4](results/user_protected_correction_20261031_001/videos/NOW__COME/comparison.mp4) |
| COME→COME | COME#0 [27,177]; COME#1 [23,132] | 5.000000～5.300000s (0.300000s) | [MP4](results/user_protected_correction_20261031_001/videos/COME__COME/comparison.mp4) |
| NOW→NOW | NOW#0 [3,82]; NOW#1 [2,76] | 2.633333～2.933333s (0.300000s) | [MP4](results/user_protected_correction_20261031_001/videos/NOW__NOW/comparison.mp4) |

四套目录各含 comparison.mp4、trajectory.json、replay.npz、baseline.npz、trajectory_evidence.csv、independent_verification.json、contact_sheet.png、report.json。原始行在上、算法行在下，正面在左、侧面在右；短行结尾保持，不做时间拉伸。颜色：绿保护、蓝保留、红裁剪、黄新增、灰保持。四组截图已由执行模型通过图像工具核对；不是真人目视、ASL 理解或第二组审批。快速画面只关闭抗锯齿/阴影/反射，不改几何、轨迹或验证；脚本和冻结 renderer 哈希在 videos/render_configuration.json。

所有工程数值与旧开发政策一致：2 mm 间隙、15/10 rad/s 臂/指速度、1e-6 位置容差、1e-8 限位/耦合容差、120 rad/s² 加速度、3000 rad/s³ jerk、1,000,000 rad²/s⁵ 平方 jerk 积分、6s 最大过渡、原搜索/验证预算。运行前文件 SHA 冻结在 R2/engineering_freeze.json。正式 quality.freeze_status/validation.approval_status 仍 pending，因此验证理由保留 QUALITY_THRESHOLDS_NOT_FROZEN 等正式审批缺项；开发数值冻结不冒充人工审批。

测试日期依赖在上一轮已通过注入测试时钟修复，本次保持该实现，生产仍使用真实 UTC。新增 15 项更正回归，覆盖新边界、旧版本保存、政策身份变化、旧 bundle 即使重新签文件哈希也不能混用、真实自对两次 106 帧，以及误删、伪造审批、保护引用错误与调时负例。各专项集合重叠，不相加；全仓实际为 799 项。

实际执行目录为 `/tmp/me5412_corrected_intervals_20261031_001/repository`；所有测试/正式运行均通过记录器设置 `PYTHONDONTWRITEBYTECODE=1`、`MUJOCO_GL=egl`，并固定 OMP/OPENBLAS/MKL/NUMEXPR 线程数为 1。复现应使用相同变量；以下模板需新建结果目录和新 run_id，不覆盖本轮结果。全仓测试允许已有测试在临时 127.0.0.1 端口启动服务。CLI 退出 0 只代表计算完成，数值通过须读取验证 JSON。

```bash
.venv/bin/python scripts/screen_user_protected_cuts.py --policy config/transition_policy_user_protected_v2.json --output results/REPRO_NEW_DIR/cuts.json --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW
.venv/bin/python scripts/plan_all_pairs.py --library hospital_v1 --include-self --policy config/transition_policy_user_protected_v2.json --run-id REPRO_NEW_ID --results-root results/REPRO_NEW_DIR/runs --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW
.venv/bin/python scripts/verify_all_pairs.py --run-id REPRO_NEW_ID --results-root results/REPRO_NEW_DIR/runs
.venv/bin/python results/user_protected_correction_20261031_001/R6/fast_render.py --run-dir results/REPRO_NEW_DIR/runs/REPRO_NEW_ID --output results/REPRO_NEW_DIR/videos --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW
.venv/bin/python -m pytest -q -p no:cacheprovider tests
```

正式执行命令、实际 cwd、环境、耗时、退出码与日志在 FINAL/commands.json 和各 R 目录 *.command.json/.log。规划 123.559s、独立候选复核 593.832s、渲染 90.227s。R4/analyze_plan_failed_v1.py 对包含空方法名（端点筛选）的计数字典做 sorted JSON 导出，触发 TypeError: '<' not supported between instances of 'str' and 'NoneType'，退出 1；改用 endpoint_screen 字符串后 analysis_fixed 退出 0。原脚本/失败日志保留，未改轨迹或阈值。一次只读进度查询也因运行中未生成 method_coverage 出现 KeyError，改为 get 后恢复，不影响运行。

失败最小只读复现如下，预期输出 COME 1479272.6946308068、NOW 38213419.33855339，阈值均 1000000。它不创建或覆盖结果。

```bash
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

建议下一步：由工程侧先审查当前全动作质量指标与不可修改保护段的冲突，若提出有依据的指标/输入处置，必须另建版本并冻结、回归；不能为通过临时提高阈值。用户无需填写技术参数。当前原姿态、原时序与这些上限同时保持时，四对数值目标受阻。全词库 1,225（1,190 非自对/35 自对）仅执行四对：2 FAILED_QUALITY、2 TIMEOUT、1,221 NOT_RUN、0 PASS_SIM；全库 L2、三词/多词兼容、人工交叉评审、新环境复现和实机仍未完成。

保全归档 `/home/kingderman/Documents/ME5412/execution_evidence/corrected_intervals_20261031_001/baseline.tar`（894,515,200 bytes），SHA-256 `c7386f1b813e51fbd1df0a787f2d5f3182496095876ee41172601bfd9a098e03`；恢复 8,726 条目全匹配。动作绑定仍是 201 帧 Studio Galt COME 与 104 帧 WLASL NOW，SHA 见 HANDOFF.md 与新 bundle；两个文件本次重新核验，未用 89 帧 COME 替换。先前展示视频字节身份仍不可得，不虚构关联。所有旧动作/模型、旧配置/合同、TASK-01～21、PLAN.md、历史结果保留，未提交/推送/发布；按用户明确约束单代理串行执行。

最终文本差异 FINAL/implementation.patch；逐文件绝对路径、before/after SHA 见 FINAL/changed_files.json 和 install_manifest.json。回滚前先保全本次证据，再从本次归档只恢复 manifest 中已存在的修改文件，新增配置/测试/报告先移到另一个保全目录；不用 reset/clean 或全目录覆盖。验收清单将工程完整性与 goal_complete=false 分开输出。安装后源目录复核结果另附下方，不把准备安装写成完成。

源目录安装与最终验收已实际完成：956 个初始交付文件安装哈希全部匹配；在 `/home/kingderman/Documents/ME5412-github-latest` 执行最终清单退出 0，62 项工程检查通过。465 个原始动作/模型文件及全部基线历史结果保持，8 个保护实例导出姿态 bitwise equal，原相对时序保持。详见 results/user_protected_correction_20261031_001/FINAL/final_acceptance_checklist.json 与 R7/installed_acceptance.command.json/.log。四对数值通过仍为 0/4，goal_complete=false；正式开关关闭。
