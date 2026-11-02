from pathlib import Path
import difflib
import hashlib
import json
import sys

sys.path.insert(0,'/tmp')
from me5412_auto_report import ROOT,OUT,SOURCE,finish

def main():
    videos=OUT/'videos_complete'
    media=json.loads((videos/'summary.json').read_text())
    assert len(media['pairs'])==4
    run=OUT/'runs/user_protected_pilot_20261031_001'
    summary=json.loads((run/'summary.json').read_text())
    manifest=json.loads((run/'manifest.json').read_text())
    intrinsic=json.loads((OUT/'R6/protected_source_quality.json').read_text())
    analysis={'identity':manifest['identity'],'pairs':{},'four_pair_numerical_pass_count':0,
              'formal_acceptance_enabled':False,'full_library_not_run':1221}
    cn_rows=[]
    en_rows=[]
    for report in media['pairs']:
        pair=report['pair_id']
        record=json.loads((run/manifest['heads'][pair]['path']).read_text())['record']
        evidence=json.loads((videos/pair/'independent_verification.json').read_text())
        mapping=[]
        original_offset=0
        for w,segment in zip(report['word_instances'],(json.loads((videos/pair/'trajectory.json').read_text())['trajectory']['segments'][0],
                   json.loads((videos/pair/'trajectory.json').read_text())['trajectory']['segments'][-1])):
            original_frames=201 if w['gloss']=='COME' else 104
            for f in intrinsic['words'][w['gloss']]['top_power_frames'][:1]:
                frame=f['source_frame']
                mapping.append({'instance_id':w['instance_id'],'metric':'largest original squared-jerk contribution',
                    'source_frame':frame,'source_time_s':frame/30,'comparison_original_row_time_s':original_offset+frame/30,
                    'comparison_algorithm_row_time_s':segment['start_time_s']+(frame-w['source_frames'][0])/30})
            for metric in intrinsic['words'][w['gloss']]['peak_metrics']:
                if metric['value']>metric['limit']:
                    frame=metric['source_frame']
                    mapping.append({**metric,'instance_id':w['instance_id'],'comparison_original_row_time_s':original_offset+frame/30,
                        'comparison_algorithm_row_time_s':segment['start_time_s']+(frame-w['source_frames'][0])/30})
            original_offset+=original_frames/30
        analysis['pairs'][pair]={'planning_status':record['status'],'eligible_candidates':record['candidate_count'],
            'attempts':len(record['attempts']),'independent_review_state':record['verification_state'],
            'methods_attempted':[m for m,v in record['method_coverage'].items() if v['attempted']],
            'diagnostic_curve_full_verification_complete':evidence['validation_complete'],
            'diagnostic_curve_numerical_checks_passed':evidence['numerical_checks_passed'],
            'protected_instance_checks':evidence['protected_instance_checks'],'diagnostic_curve_metrics':evidence['metrics'],
            'min_clearance_mm':evidence['min_clearance_mm'],'reason_codes':evidence['reason_codes'],
            'word_instances':report['word_instances'],'transition_time_s':report['transition_time_s'],
            'video':str((videos/pair/'comparison.mp4').relative_to(ROOT)),
            'failure_video_locations':mapping}
        m=evidence['metrics']
        row=f"| {pair.replace('__','→')} | {record['status']} | {record['candidate_count']} | {m['peak_acceleration_rad_s2']:.6f} | {m['peak_jerk_rad_s3']:.6f} | {m['jerk_integral_rad2_s5']:.6f} | {evidence['min_clearance_mm']:.6f} |"
        cn_rows.append(row);en_rows.append(row)
    (OUT/'R6/run_analysis.json').write_text(json.dumps(analysis,ensure_ascii=False,indent=2)+'\n')
    commands=[]
    for p in sorted(OUT.rglob('*.command.json')):
        v=json.loads(p.read_text())
        commands.append({'file':str(p.relative_to(OUT)),'exit_code':v['exit_code'],'argv':v.get('argv'),'cwd':v.get('cwd')})
    (OUT/'FINAL/commands.json').write_text(json.dumps(commands,indent=2,ensure_ascii=False)+'\n')
    table_cn='| 词对 | 规划状态 | 可选候选 | 完整峰值加速度 rad/s² | 完整峰值 jerk rad/s³ | 完整平方 jerk 积分 rad²/s⁵ | 采样最小间隙 mm |\n|---|---|---:|---:|---:|---:|---:|\n'+'\n'.join(cn_rows)
    table_en='| Pair | Planning status | Eligible candidates | Full peak acceleration rad/s² | Full peak jerk rad/s³ | Full squared-jerk integral rad²/s⁵ | Sampled min gap mm |\n|---|---|---:|---:|---:|---:|---:|\n'+'\n'.join(en_rows)
    cn='''状态：四对执行和失败诊断交付完成，**数值验收未通过（0/4）**。未获得合格衔接，不把本任务标成算法目标完成。正式开关始终 false，未改变原始动作、保护段或阈值。

运行 user_protected_pilot_20261031_001：117 次尝试，64 个可选候选全部属于 COME→COME，64 份独立完整曲线复核全部因平方 jerk 积分超限失败；另三对规划 TIMEOUT、0 可选候选，保存输入诊断。四对均实际尝试 direct、neutral、ik_via1、ik_via2、retract_approach 和 rrt_connect。有限搜索失败不证明几何无解。

四个视频各另选一条已保存失败曲线，重新从文件完成完整动作独立复核（均 validation_complete=true、numerical_checks_passed=false）。这些是诊断曲线，不是可选解。下表为视频对应曲线的完整指标；它们与规划状态分列，避免把输入诊断误当完整验证。

'''+table_cn+'''

保护段根因：不含任何新增连接的原动作内部，COME f30～138 平方 jerk 积分 1,850,853.261494；NOW f6～99 为 38,239,278.289876；均超过冻结上限 1,000,000。NOW f31（1.033333 秒）右手腕 roll 加速度 206.817407 >120，f37（1.233333 秒）右小指近端 jerk 4,889.644865 >3000。只使用保护边界内至少 3 帧距离的原始差分模板，因此外部裁剪/连接不能移除该非负积分贡献。复现脚本 R6/audit_protected_sources.py，退出 0 表示计算完成；JSON 的 exceeds_frozen_limit=true 是失败判定。每个实例在对照视频的具体时间见 R6/run_analysis.json 的 failure_video_locations。

视频：results/user_protected_auto_20261031_001/videos_complete/{COME__NOW,NOW__COME,COME__COME,NOW__NOW}/comparison.mp4。每对同时有 trajectory.json、replay.npz、baseline.npz、trajectory_evidence.csv、独立验证 JSON、contact_sheet.png 和 report.json。原始两词上排、算法下排，左正面/右侧面；同一真实时间轴，较短一排结束保持。绿=保护、蓝=保留、红=裁剪、黄=新增。持续显示 FAILED DIAGNOSTIC/未选用、算法窗口、运动学回放。

命令与退出码：plan_four 0；verify_four 0；resume_four 0；renderer_probe 0；render_four 143（SIGTERM，原因未确认，完整首视频及部分第二视频、日志保留）；render_four_fast 0。快速重导出仅关闭阴影/反射和抗锯齿，原轨迹代码、模型几何、碰撞规则和身份不变；R6/fast_render.py 及 videos_complete/render_configuration.json 分别记录脚本和渲染配置，输出使用新目录。完整 argv、工作目录、耗时和日志在对应 *.command.json 与 FINAL/commands.json。

验证：全仓 .venv/bin/python -m pytest -q -p no:cacheprovider tests，退出 0，784 passed in 61.04s；已有本机 HTTP 测试使用临时 127.0.0.1 端口。恢复副本测试，不冒充新环境复现。续跑前后 790 个运行文件字节哈希不变。四对分母 4，完整词库仍 1,225（1,190 异词、35 自对），1,221 NOT_RUN、0 PASS_SIM、L2 未完成。正式质量/碰撞审核 pending 与工程数值按政策哈希冻结是独立事实。

修改/操作：新增真实对照视频导出、标注测试；自动模式代码冻结纳入两个新 CLI；预登记本轮报告索引并仅同步 project_overview.py 的两个下载 SHA。未修改其已有其他改动。偏差：R3 切向筛选回补见 TASK-18；导出中断后另建快速画面目录，不重写旧文件；动作验收失败保留并交回审查，不放宽上限。
'''
    en='''Status: four-pair execution and failure-diagnostic delivery complete; **numerical acceptance failed (0/4)**. No qualifying connector was obtained. Formal acceptance stays false. Source motions, protected intervals and limits remain unchanged.

Run user_protected_pilot_20261031_001: 117 attempts, 64 eligible candidates, all COME→COME. All 64 independent complete-curve reviews failed the squared-jerk integral cap. The other three pairs have planning TIMEOUT, no eligible candidates and saved input diagnoses. Every pair actually attempted direct, neutral, ik_via1, ik_via2, retract_approach and rrt_connect. Bounded failure is not a geometric infeasibility proof.

Each video separately selects a saved failed curve and completes a fresh full-motion saved-file verification: validation_complete=true and numerical_checks_passed=false for all four. These diagnostic curves are not eligible solutions. Their full metrics follow, separate from planner status.

'''+table_en+'''

Intrinsic protected-source cause: without any connector, COME frames 30–138 contribute squared jerk 1,850,853.261494 and NOW frames 6–99 contribute 38,239,278.289876, exceeding the frozen 1,000,000 cap. NOW frame 31 (1.033333 s), right wrist roll, acceleration 206.817407 >120; frame 37 (1.233333 s), right proximal pinky, jerk 4,889.644865 >3000. Original difference stencils remain at least three frames inside protection, so external cuts/connectors cannot remove this nonnegative contribution. Reproduce with R6/audit_protected_sources.py. Exit 0 means computation completed; exceeds_frozen_limit=true is failure. Per-instance comparison-video times are in R6/run_analysis.json failure_video_locations.

Videos: results/user_protected_auto_20261031_001/videos_complete/{COME__NOW,NOW__COME,COME__COME,NOW__NOW}/comparison.mp4. Each folder includes trajectory.json, replay.npz, baseline.npz, trajectory_evidence.csv, independent verification, contact_sheet.png and report.json. Original pair above, algorithm below; front left/side right. Common real time, shorter row holds its end. Green protection, blue retained, red cut, yellow added. Persistent FAILED DIAGNOSTIC/not-selected, algorithm-window and kinematic-replay labels.

Command exits: plan_four 0; verify_four 0; resume_four 0; renderer_probe 0; render_four 143 (SIGTERM, cause unknown; first complete video, partial second video and logs preserved); render_four_fast 0. Fast raster export disables shadows/reflections and antialiasing only. Trajectory code, model geometry, collision rules and run identity remain unchanged. R6/fast_render.py and videos_complete/render_configuration.json record provenance; a new output directory preserves earlier output. Exact argv, cwd, timing and logs are in *.command.json and FINAL/commands.json.

Validation: .venv/bin/python -m pytest -q -p no:cacheprovider tests exited 0: 784 passed in 61.04s. Existing HTTP tests use temporary loopback ports. This is the restored workspace, not a newly installed environment. All 790 run-file hashes remain identical after completed resume. Four-pair denominator 4; full library remains 1,225 (1,190 non-self/35 self), 1,221 NOT_RUN, zero PASS_SIM, L2 incomplete. Pending formal quality/collision approval is separate from development values frozen by policy hash.

Changes: real comparison exporter and label tests; automatic-mode code freeze includes both new CLIs. Pre-registered report links and updated only two download SHA literals in project_overview.py, preserving earlier changes. Deviations: tangent screening correction is documented in TASK-18; interrupted rendering led to a separate fast raster output; failed acceptance is retained for review without relaxing limits.
'''
    finish('R6',20,cn,en,['scripts/render_user_protected_pairs.py','tests/test_user_protected_render.py',
        'src/sign_robot/pair_contract.py','src/sign_robot/project_overview.py','docs/README.md','docs/README.en.md'])
    state_cn=f'''# 项目执行状态

[English](STATE.en.md) · [本轮最终执行报告](TASK-21.md) · [四对试点/视频](TASK-20.md) · [历史最终报告](TASK-14.md)

更新：2026-10-31（Asia/Shanghai）。目标目录 `{SOURCE}`，分支 codex/group3-all-pairs-v1，HEAD 2875e499d79b7264b3fe0414318b30ca8aab1f4d。当前聊天 cwd 是另一检出；本轮单代理串行工作，先完整归档并在恢复副本实施。

**目标未完成：四对真实动作数值通过 0/4，正式 PASS_SIM=0。** 工程实现、回归与失败交付完成。自动窗口只标为 algorithm；用户保护独立于人工审批，COME [27,141]、NOW [3,102] 姿态/顺序/相对时序保持。保护段自身超过冻结质量上限，不能靠新增连接消除。原始动作、模型和旧运行未改，正式开关 false。

| ID | 实际状态 | 报告 |
|---|---|---|
| R1 | 完成，7,585 基线条目归档/恢复匹配 | TASK-15.md |
| R2 | 完成，用户保护与算法窗口分离，旧审批兼容、日期测试稳定 | TASK-16.md |
| R3 | 完成，逐点真实几何/限位/耦合/p-v-a 筛选；补充切向检查 | TASK-17.md、TASK-18.md |
| R4 | 工程实现完成；未得到四对合格解 | TASK-18.md |
| R5 | 独立完整动作验证实现完成，实际数值结果失败 | TASK-19.md、TASK-20.md |
| R6 | 四对已执行并输出四个失败诊断视频；数值验收未通过 | TASK-20.md |
| R7 | 报告/验收清单交付，工程完整性与动作目标分开 | TASK-21.md |

本轮实际全仓测试退出 0：784 passed in 61.04s。原 749/589 是历史；专项集合有重叠，不能相加。运行 user_protected_pilot_20261031_001 有 117 次尝试、64 候选、64 完整独立候选复核和 3 输入诊断；64 候选均 COME→COME、均平方 jerk 积分超限。其余三对规划 TIMEOUT，不是无解证明。四个视频另有完整失败曲线独立验证。续跑前后 790 文件 SHA 全同。

COME 保护内部积分 1,850,853.261494，NOW 38,239,278.289876，冻结上限 1,000,000 rad²/s⁵。NOW 另有 f31 加速度 206.817407>120、f37 jerk 4,889.644865>3000。具体原帧、指标和视频时间见 R6/run_analysis.json、protected_source_quality.json。

全词库仍 1,225/1,190/35：1 FAILED_QUALITY、3 TIMEOUT、1,221 NOT_RUN、0 PASS_SIM。L2、42,875 三词兼容、冻结多词验收、语言理解、人工交叉评审、新环境复现和实机均未完成。旧 P0/P1 工程历史见 TASK-14；旧 P1-8 人工审批阻塞仍适用于旧模式，不再阻塞本轮两个词的自动开发。

代码 SHA `{manifest['identity']['code_hash']}`；政策内容 SHA `{manifest['identity']['policy_hash']}`。绑定的实际动作完整哈希、先前展示视频身份缺失限制见 HANDOFF.md。基线归档和回滚见 TASK-15。下轮应先处理保护段质量与冻结指标的矛盾，建立有依据的新版本；本轮不代填技术阈值、不偷偷修改保护动作。
'''
    state_en=f'''# Project execution state

[中文](STATE.md) · [Current final report](TASK-21.en.md) · [Four-pair pilot/videos](TASK-20.en.md) · [Historical final report](TASK-14.en.md)

Updated October 31, 2026 (Asia/Shanghai). Target `{SOURCE}`, branch codex/group3-all-pairs-v1, HEAD 2875e499d79b7264b3fe0414318b30ca8aab1f4d. Chat cwd is another checkout. One agent worked serially after a complete archive and restore.

**Goal incomplete: 0/4 real pairs pass numerical acceptance; zero formal PASS_SIM.** Engineering implementation, regression and failure delivery are complete. Automatic windows are labelled algorithm, separate from human approval. COME [27,141] and NOW [3,102] retain original poses/order/relative timing. Intrinsic protected quality exceeds frozen caps and cannot be fixed by adding a connector. Original motions, models and historical runs remain unchanged; formal flag false.

| ID | Actual state | Report |
|---|---|---|
| R1 | Complete, all 7,585 baseline entries archive/restore match | TASK-15.en.md |
| R2 | Complete, user protection/algorithm windows separated, legacy approval and deterministic date tests retained | TASK-16.en.md |
| R3 | Complete, real geometry/limits/coupling/p-v-a screening with tangent correction | TASK-17.en.md, TASK-18.en.md |
| R4 | Engineering complete; no four-pair qualifying solution | TASK-18.en.md |
| R5 | Independent full-motion verifier implemented; actual numerical acceptance failed | TASK-19.en.md, TASK-20.en.md |
| R6 | Four real pairs and four failed-diagnostic videos delivered; acceptance failed | TASK-20.en.md |
| R7 | Reports/checklist delivered, engineering integrity separate from motion goal | TASK-21.en.md |

Actual full tests: exit 0, 784 passed in 61.04s. Historical 749/589 are not this run; overlapping focused suites cannot be added. user_protected_pilot_20261031_001 has 117 attempts, 64 candidates, 64 complete independent candidate reviews and three input diagnoses. All candidates are COME→COME and fail squared-jerk integral. Other planners time out; no infeasibility proof. All four video curves have additional complete failed-curve reviews. Resume preserved all 790 run-file hashes.

Protected-interior integral: COME 1,850,853.261494; NOW 38,239,278.289876; frozen cap 1,000,000 rad²/s⁵. NOW frame 31 acceleration 206.817407>120; frame 37 jerk 4,889.644865>3000. Original frames, metrics and video times are in R6/run_analysis.json and protected_source_quality.json.

Full library stays 1,225/1,190/35: one FAILED_QUALITY, three TIMEOUT, 1,221 NOT_RUN, zero PASS_SIM. L2, 42,875 three-word compatibility, frozen multiword acceptance, language comprehension, human cross-review, fresh-environment reproduction and hardware remain incomplete. Previous P0/P1 engineering history is in TASK-14; legacy P1-8 approval dependencies do not block this two-word automatic development mode.

Code SHA `{manifest['identity']['code_hash']}`; policy content SHA `{manifest['identity']['policy_hash']}`. Full motion bindings and absent prior displayed-video identity are documented in HANDOFF.en.md. Archive/rollback: TASK-15. Next work must resolve protected quality versus frozen metric requirements with a justified new version; no technical limits were weakened and no protected motion was silently edited.
'''
    (ROOT/'STATE.md').write_text(state_cn)
    (ROOT/'STATE.en.md').write_text(state_en)
    body_cn='''执行结论：**本轮工程实现与失败证据交付完成，动作目标未完成，数值通过 0/4。** 正式开关保持关闭。TASK-15～TASK-20 按 R1～R6 记录文件、决策、命令、验证和偏差；STATE.md 已更新且有对应英文版。

'''+table_cn+'''

这四个数值均来自视频对应的已保存完整曲线独立验证。COME→COME 的规划器另有 64 个可选候选，全部完成独立复核、全部失败；其余三对 0 可选候选、规划超时，视频是保存的失败曲线，不是通过解。四对均实际尝试全部六类方法。全部保护实例在导出轨迹内的逐帧姿态和原相对时序另由最终清单检查；自对保留两次。

根本阻塞为不可修改保护段自身的质量：COME 仅原保护内部 f30～138 的平方 jerk 积分就有 1,850,853.261494，NOW f6～99 为 38,239,278.289876，均大于 1,000,000。NOW 还在 f31/1.033333s 超加速度、f37/1.233333s 超 jerk。非负积分贡献完全在保护段内部，扩大外部裁剪或改变连接不能消除；未据结果回调阈值或改原词。完整根因、最大贡献关节、原帧、原秒和视频时间映射见 results/user_protected_auto_20261031_001/R6/protected_source_quality.json 与 run_analysis.json。

修改范围：pair_contract.py（显式新输入模式/冻结）、pair_windows.py（独立用户保护/算法来源/时钟）、pair_routes.py（逐点筛选/有限组合/路线）、pair_search.py（保护裁剪时间偏移/短名单）、pair_verification_v2.py（保存文件完整验证/保护/原时序/根因）、pair_runner_v2.py（新模式独立证据/平滑优先排名/试点统计）；新增 2 个 config、1 份合同、2 个 CLI、固定时钟和 5 个专项测试文件。HANDOFF/STATE/7 份 TASK 双语同步；docs 索引及 project_overview.py 仅同步报告链接与两处下载哈希。其已有其他改动保持。逐文件绝对路径和 before/after SHA 在 FINAL/install_manifest.json；文本差异在 FINAL/implementation.patch，任务 before 副本与 changes.json 分列。新证据位于 results/user_protected_auto_20261031_001/，没有覆盖旧运行。

实际全仓测试命令（恢复副本工作目录 /tmp/me5412_auto_cuts_20261031_001/repository）：

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider tests
```

退出 0，784 passed in 61.04s；本机 HTTP/service 测试以临时 127.0.0.1 端口运行。测试日期依赖用注入测试时钟修复，生产仍使用真实 UTC。覆盖保护误删、版本不符、重复词丢失、算法伪装审批、时序修改、曲线篡改和旧审批模式。完整命令/退出码在 FINAL/commands.json；R2/R3/R4/R5 专项分别有最终 129/40/104/75 项通过，存在重叠，不能相加。未修改基线全仓实际 749 passed；首次沙箱 socket 失败也保留。

运行命令可在目标仓库用新 run_id 重现，不能覆盖本轮结果：

```bash
.venv/bin/python scripts/plan_all_pairs.py --library hospital_v1 --include-self --policy config/transition_policy_user_protected_v1.json --run-id REPRO_NEW_ID --results-root results/user_protected_repro --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW
.venv/bin/python scripts/verify_all_pairs.py --run-id REPRO_NEW_ID --results-root results/user_protected_repro
.venv/bin/python results/user_protected_auto_20261031_001/R6/audit_protected_sources.py
```

最后一条审计脚本为不可覆盖证据，直接重复会拒绝已有 JSON；复现时复制脚本到新证据位置并保持正确 ROOT，或读取其已保存 argv/日志。最小只读复现可运行同脚本公式读取原 NPZ 的 gradient/积分；源路径和所有模板在脚本与 JSON 中完整记录。CLI 退出 0 表示完成计算，不能替代 JSON 的质量失败判定。各失败日志（脚本 SyntaxError、测试错误成功假设、np.bool 序列化、渲染 SIGTERM）均保留原命令与退出码；修复及原因在各 TASK。

视频位于 results/user_protected_auto_20261031_001/videos_complete/ 下四个词对目录，文件 comparison.mp4；各有原始/算法正侧面对照、保护/保留/裁剪/新增/保持标注，持续 FAILED DIAGNOSTIC/未选用。每对同时有轨迹 JSON、回放/原始 NPZ、指标 CSV、独立完整复核 JSON、截图与文件 SHA。原有阴影导出被 SIGTERM(143) 中断，部分目录 videos/ 原样保留；新画面配置关闭阴影/反射/抗锯齿，只改栅格画面，不改几何/轨迹/碰撞。配置及包装脚本哈希明确记录。视频不是 ASL 理解、连续碰撞或实机批准。

完整词库固定分母 1,225/1,190/35，当前仅四对执行：1 FAILED_QUALITY、3 TIMEOUT、1,221 NOT_RUN、0 PASS_SIM；四对试点分母 4、0 数值通过。64 候选已完整独立复核，另三对输入诊断不能冒充完整通过；四个视频又分别复核实际展示曲线。续跑前后全部 790 个运行文件 SHA 不变。采样间隙满足 2 mm 不代表完整动作限位/质量通过，也不证明连续碰撞安全。

最终验收使用 FINAL/acceptance.py：核对冻结数值、实际代码/模型/环境身份、固定分母、完整独立证据、四个视频可解码/哈希、导出轨迹中的保护姿态与原时序、两次实例、原始模型/动作/历史结果和双语报告。工程清单与“动作目标通过”单独输出；后者明确 false。安装后的源目录复核另记录 FINAL/final_acceptance_checklist.json，不以测试通过冒充动作通过。

保全与恢复：完整基线归档 /home/kingderman/Documents/ME5412/execution_evidence/auto_cuts_20261031_001/baseline.tar，SHA 501e2e75d05bad81f93a70e24b76b121370c345f45ee4973dd33ec6ea733d22f；7,585 条目恢复全匹配。修改仅从副本逐文件安装，安装前检查所有目标原哈希，存在并发变动即整体拒绝；不用 reset --hard/clean。回滚先另存本轮新证据，再按 manifest 与 before 恢复任务文件，新增文件先移到保全目录，不整体覆盖他人工作。.venv 外部符号链接保留，不是可移植新环境复现。

偏差与限制：实际 cwd 与计划目标不同，使用恢复副本；COME 有两套动作，本轮绑定实际词库 201 帧 Studio Galt 版，89 帧 WLASL 版无法容纳保护终点。当前消息缺先前展示视频身份，无法虚构逐字节关联；完整 SHA/依据已记录。R4 发现并回补 R3 限位外向切线检查；快速画面另目录导出；必要文档下载哈希同步不扩展产品功能。未修改原资产、旧政策、PLAN.md、旧运行或正式开关，未虚构人工审批、缩小全库分母或降低阈值。本轮单代理，无实机/上传/发布。

建议下一步：先由规划/执行工程侧对保护段质量与当前差分/积分定义冲突作有依据的处置，并在新版本重新冻结、回归；若必须原姿态和原时序且沿用这些上限，则此四对不能验收。用户不需要填写技术阈值。全词库 L2、多词兼容、人工评价、新环境复现仍未完成。本次交回失败审查，不宣布最终目标完成。
'''
    body_en='''Outcome: **engineering implementation and failure evidence delivered; motion goal incomplete, 0/4 numerical passes.** Formal acceptance remains disabled. TASK-15–TASK-20 record R1–R6 files, decisions, commands, verification and deviations. STATE and every new report have matching Chinese/English versions.

'''+table_en+'''

Metrics come from independent saved-file verification of the complete displayed diagnostic curves. COME→COME also has 64 eligible planned candidates, all independently reviewed and failed. Other pairs have no eligible candidate and planning timeouts; their videos are diagnostic saved curves. All six route families were actually attempted for every pair. Final checks separately inspect exported protected poses/timing and two self-pair instances.

Blocking cause is intrinsic protected quality: COME frames 30–138 contribute squared jerk 1,850,853.261494 and NOW frames 6–99 contribute 38,239,278.289876, above 1,000,000. NOW also violates acceleration at frame 31/1.033333 s and jerk at frame 37/1.233333 s. The nonnegative contributions lie entirely within protection; changing external cuts or connectors cannot remove them. No limits or original words were retuned. Full frame/joint/time/video attribution is in results/user_protected_auto_20261031_001/R6/protected_source_quality.json and run_analysis.json.

Changed pair_contract.py (explicit new mode/freeze), pair_windows.py (user protection/algorithm provenance/clock), pair_routes.py (screening/shortlist/routes), pair_search.py (cropped timing/shortlist), pair_verification_v2.py (fresh complete-curve/protection/timing/localization), pair_runner_v2.py (applicable independent evidence/smoothness ranking/pilot counts). Added two configs, one contract, two CLIs, fixed-clock fixture and five focused test files. HANDOFF/STATE/seven TASK reports are bilingual; documentation indexes and only two project_overview.py download hashes were synchronized, preserving prior edits. Absolute paths and before/after SHA values are in FINAL/install_manifest.json; text diff FINAL/implementation.patch; per-task before/changes are retained. New evidence lives in results/user_protected_auto_20261031_001 without overwriting history.

Actual full test command in the restored /tmp/me5412_auto_cuts_20261031_001/repository workspace:

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider tests
```

Exit 0: 784 passed in 61.04s, including existing temporary loopback HTTP/service tests. Test clock injection removes date dependence while production retains real UTC checks. Negative tests cover removed protection, mismatched versions, lost repeats, forged approval, retiming and tampering; legacy review remains compatible. FINAL/commands.json records commands/exits. Focused final suites have 129/40/104/75 passes with overlap; do not add them. Unchanged baseline actually had 749 passes; the initial socket-restricted failure is preserved.

Reproduce planning/verification from the target using a fresh run ID:

```bash
.venv/bin/python scripts/plan_all_pairs.py --library hospital_v1 --include-self --policy config/transition_policy_user_protected_v1.json --run-id REPRO_NEW_ID --results-root results/user_protected_repro --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW
.venv/bin/python scripts/verify_all_pairs.py --run-id REPRO_NEW_ID --results-root results/user_protected_repro
```

The intrinsic audit formula and original input paths are in R6/audit_protected_sources.py and its saved command/log. Its output is immutable; direct repetition refuses an existing JSON. Copy it to a fresh evidence location with correct ROOT to rerun, or execute its documented original-NPZ gradient/integral formula read-only. CLI exit 0 means calculation completed, not numerical acceptance. Original SyntaxError, mistaken test-success assumption, np.bool serialization and SIGTERM(143) logs remain with their corrections documented in the atomic reports.

Four comparison.mp4 files are under results/user_protected_auto_20261031_001/videos_complete/<pair>/. Each compares original/algorithm front/side views and marks protection/retained/cut/added/hold phases with persistent FAILED DIAGNOSTIC/not-selected labels. Companion curve JSON, replay/original NPZ, metrics CSV, independent complete verification, contact sheet and hashes are retained. Interrupted shadow rendering remains in videos/. The separate fast raster variant disables shadows/reflections/antialiasing only; geometry, trajectory and collision are unchanged, with explicit wrapper/config hashes. Neither video nor sampled geometry is ASL comprehension, continuous-collision or hardware approval.

Full-library denominator remains 1,225/1,190/35: one FAILED_QUALITY, three TIMEOUT, 1,221 NOT_RUN, zero PASS_SIM. Pilot denominator four, numerical pass zero. All 64 eligible candidates have complete independent reviews; three input diagnoses cannot be presented as curve passes. Four displayed diagnostic curves have additional complete rechecks. Resume leaves all 790 run-file hashes unchanged. A sampled gap over 2 mm does not make a limit/quality-failed complete motion pass.

FINAL/acceptance.py checks frozen values, actual code/model/environment identity, denominators, independent evidence, four decodable videos/hashes, protected exported poses/timing, two instances, baseline assets/history and bilingual reports. Engineering integrity and motion-goal success are distinct; goal_complete stays false. Installed-source verification is separately recorded in FINAL/final_acceptance_checklist.json.

Preservation: /home/kingderman/Documents/ME5412/execution_evidence/auto_cuts_20261031_001/baseline.tar, SHA 501e2e75d05bad81f93a70e24b76b121370c345f45ee4973dd33ec6ea733d22f. All 7,585 entries match the restore. Installation checks every original target hash before changing any enumerated file and refuses concurrent differences. No reset --hard/clean. Rollback first preserves new evidence, then restores listed existing files from before/archive and moves new files aside; do not replace unrelated work. The external .venv symlink remains, so this is not portable fresh-environment reproduction.

Deviations/limits: actual cwd differs from target, so a restored copy was used. COME has two sources; the actual 201-frame Studio Galt library motion is bound, since 89-frame WLASL cannot contain protection. The current handoff lacks the prior displayed-video identity; byte-level association is not invented. Full hashes/binding basis are recorded. R4 corrected R3 outward-limit tangent screening. A separate fast raster export follows interrupted rendering. Required download-hash maintenance does not expand product scope. No raw assets, historical policy, PLAN.md, old runs or formal flags were changed; no forged reviews, denominator reduction or weakened caps. One agent; no hardware, uploads or publication.

Next: planning/execution engineers must resolve protected-source quality versus the current difference/integral definitions with justified versioned decisions, then freeze and regress a new policy. If original protected poses/timing and existing caps are mandatory, these four pairs cannot pass. The user need not supply technical thresholds. Full-library L2, multiword compatibility, human evaluation and fresh-environment reproduction remain incomplete. This is a failure handback, not final goal completion.
'''
    (OUT/'R7').mkdir(exist_ok=True)
    finish('R7',21,body_cn,body_en,['STATE.md','STATE.en.md'])
    # Final text diff contains code/config/tests and documentation, including new files.
    baseline=json.loads((OUT/'R1/baseline_inventory.json').read_text())
    relatives=['HANDOFF.md','HANDOFF.en.md','STATE.md','STATE.en.md','docs/README.md','docs/README.en.md',
       'src/sign_robot/pair_contract.py','src/sign_robot/pair_windows.py','src/sign_robot/pair_routes.py',
       'src/sign_robot/pair_search.py','src/sign_robot/pair_runner_v2.py','src/sign_robot/pair_verification_v2.py',
       'src/sign_robot/project_overview.py','config/user_protected_come_now_v1.json','config/transition_policy_user_protected_v1.json',
       'contracts/all_pairs_user_protected_v1.json','scripts/screen_user_protected_cuts.py','scripts/render_user_protected_pairs.py',
       'tests/conftest.py','tests/test_user_protected_windows.py','tests/test_user_protected_cuts.py','tests/test_user_protected_routes.py',
       'tests/test_user_protected_verification.py','tests/test_user_protected_render.py']
    relatives += [f'TASK-{n:02d}{lang}.md' for n in range(15,22) for lang in ('','.en')]
    diff=[]
    changed=[]
    for rel in relatives:
        old=(SOURCE/rel).read_text() if rel in baseline and (SOURCE/rel).is_file() else ''
        new=(ROOT/rel).read_text()
        diff.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
        changed.append({'relative':rel,'file':str(SOURCE/rel),'before_sha256':baseline.get(rel,{}).get('sha256'),
                        'after_sha256':hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()})
    (OUT/'FINAL/implementation.patch').write_text(''.join(diff))
    (OUT/'FINAL/changed_files.json').write_text(json.dumps(changed,indent=2)+'\n')
    print(json.dumps({'reports_written':list(range(15,22)),'implementation_files':len(relatives),'numerical_pass':0,'pilot_denominator':4}))


if __name__=='__main__':
    main()
