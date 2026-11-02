# TASK-21 — R7

[English](TASK-21.en.md)

执行结论：**本轮工程实现与失败证据交付完成，动作目标未完成，数值通过 0/4。** 正式开关保持关闭。TASK-15～TASK-20 按 R1～R6 记录文件、决策、命令、验证和偏差；STATE.md 已更新且有对应英文版。

| 词对 | 规划状态 | 可选候选 | 完整峰值加速度 rad/s² | 完整峰值 jerk rad/s³ | 完整平方 jerk 积分 rad²/s⁵ | 采样最小间隙 mm |
|---|---|---:|---:|---:|---:|---:|
| COME→NOW | TIMEOUT | 0 | 206.817407 | 4889.644865 | 42109091.946263 | 4.730808 |
| NOW→COME | TIMEOUT | 0 | 206.817407 | 4889.644865 | 40474415.433381 | 4.730808 |
| COME→COME | FAILED_QUALITY | 64 | 97.143139 | 2196.390448 | 5634160.454384 | 8.702362 |
| NOW→NOW | TIMEOUT | 0 | 206.817407 | 4889.644865 | 76503824.684449 | 4.730808 |

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
mkdir -p results/user_protected_repro_diag_001/R6
cp results/user_protected_auto_20261031_001/R6/audit_protected_sources.py results/user_protected_repro_diag_001/R6/
.venv/bin/python results/user_protected_repro_diag_001/R6/audit_protected_sources.py
```

审计脚本为不可覆盖证据，上述命令复制到新的同层级目录，保留正确 ROOT；若该复现目录已经使用，应换新编号。最小只读复现可运行同脚本公式读取原 NPZ 的 gradient/积分；源路径和所有模板在脚本与 JSON 中完整记录。CLI 退出 0 表示完成计算，不能替代 JSON 的质量失败判定。各失败日志（脚本 SyntaxError、测试错误成功假设、np.bool 序列化、渲染 SIGTERM）均保留原命令与退出码；修复及原因在各 TASK。

视频位于 results/user_protected_auto_20261031_001/videos_complete/ 下四个词对目录，文件 comparison.mp4；各有原始/算法正侧面对照、保护/保留/裁剪/新增/保持标注，持续 FAILED DIAGNOSTIC/未选用。每对同时有轨迹 JSON、回放/原始 NPZ、指标 CSV、独立完整复核 JSON、截图与文件 SHA。原有阴影导出被 SIGTERM(143) 中断，部分目录 videos/ 原样保留；新画面配置关闭阴影/反射/抗锯齿，只改栅格画面，不改几何/轨迹/碰撞。配置及包装脚本哈希明确记录。视频不是 ASL 理解、连续碰撞或实机批准。

完整词库固定分母 1,225/1,190/35，当前仅四对执行：1 FAILED_QUALITY、3 TIMEOUT、1,221 NOT_RUN、0 PASS_SIM；四对试点分母 4、0 数值通过。64 候选已完整独立复核，另三对输入诊断不能冒充完整通过；四个视频又分别复核实际展示曲线。续跑前后全部 790 个运行文件 SHA 不变。采样间隙满足 2 mm 不代表完整动作限位/质量通过，也不证明连续碰撞安全。

最终验收使用 FINAL/acceptance.py：核对冻结数值、实际代码/模型/环境身份、固定分母、完整独立证据、四个视频可解码/哈希、导出轨迹中的保护姿态与原时序、两次实例、原始模型/动作/历史结果和双语报告。工程清单与“动作目标通过”单独输出；后者明确 false。安装后的源目录复核另记录 FINAL/final_acceptance_checklist.json，不以测试通过冒充动作通过。

保全与恢复：完整基线归档 /home/kingderman/Documents/ME5412/execution_evidence/auto_cuts_20261031_001/baseline.tar，SHA 501e2e75d05bad81f93a70e24b76b121370c345f45ee4973dd33ec6ea733d22f；7,585 条目恢复全匹配。修改仅从副本逐文件安装，安装前检查所有目标原哈希，存在并发变动即整体拒绝；不用 reset --hard/clean。回滚先另存本轮新证据，再按 manifest 与 before 恢复任务文件，新增文件先移到保全目录，不整体覆盖他人工作。.venv 外部符号链接保留，不是可移植新环境复现。

偏差与限制：实际 cwd 与计划目标不同，使用恢复副本；COME 有两套动作，本轮绑定实际词库 201 帧 Studio Galt 版，89 帧 WLASL 版无法容纳保护终点。当前消息缺先前展示视频身份，无法虚构逐字节关联；完整 SHA/依据已记录。R4 发现并回补 R3 限位外向切线检查；快速画面另目录导出；必要文档下载哈希同步不扩展产品功能。未修改原资产、旧政策、PLAN.md、旧运行或正式开关，未虚构人工审批、缩小全库分母或降低阈值。本轮单代理，无实机/上传/发布。

建议下一步：先由规划/执行工程侧对保护段质量与当前差分/积分定义冲突作有依据的处置，并在新版本重新冻结、回归；若必须原姿态和原时序且沿用这些上限，则此四对不能验收。用户不需要填写技术阈值。全词库 L2、多词兼容、人工评价、新环境复现仍未完成。本次交回失败审查，不宣布最终目标完成。


最终恢复副本验收实际退出 0：40 项工程交付检查通过（FINAL/stage_acceptance.json）；goal_complete=false，四对数值通过仍为 0。四组截图已由执行模型通过图像工具逐一核对标签与正侧面对照；这是本轮执行工程检查，不是 ASL 或第二组审批。

源目录安装与最终验收已实际完成：977 个初始交付文件安装哈希全部匹配；在 /home/kingderman/Documents/ME5412-github-latest 执行最终清单退出 0，40 项工程检查通过。465 个原始动作/模型文件及全部基线历史结果未变；8 个保护实例的导出姿态 bitwise equal（最大姿态误差 0），相对时序保持。JSON：results/user_protected_auto_20261031_001/FINAL/final_acceptance_checklist.json；命令与日志：R7/installed_acceptance.command.json、.log。动作数值仍 0/4，goal_complete=false。
