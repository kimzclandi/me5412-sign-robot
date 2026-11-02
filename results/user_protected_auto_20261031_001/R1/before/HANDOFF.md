# 执行模型简化交接指令

[English](HANDOFF.en.md) · [完整任务规划](PLAN.md)

========== HANDOFF BEGIN ==========

## 项目

ME5412 医院场景机器人动作衔接项目。

## 任务目标

让冻结词库中的 35 个词形成全部 1,225 个有向词对（含 35 个同词重复）的合格衔接。生成轨迹、保存证据、独立复核，并完成规定的多词组合与新环境复现。工程目标为 L2 仿真验收；语言理解与实机状态单独记录。

本文件是执行指令摘要，不代表已经执行或自动获得新增范围的授权。收到执行指令后，按任务顺序推进；详细输入、完成定义和依赖以 PLAN.md 为准。

## 当前状态

以下为 2026-10-31 的本地基线快照；开工时重新核对。

- **已完成：**L1 开发扫描、逐词审计、检查点、保存和复核；1,225 对都有记录，899 条候选已保存，1,225 条记录已复核。此前只读检查核对了运行清单的 3,378 个文件，大小和哈希一致。
- **未完成：**批准核心／窗口合同、正式质量冻结、通用候选与搜索、多候选续跑、多词组合、人工评价、新环境复现及实机验证。既有两词检查包含自对，不等于多词组合完成。
- **已知问题：**326 BLOCKED_ENDPOINT、386 FAILED_SEARCH、513 FAILED_QUALITY，PASS_SIM 为 0；10 个端点角色、30 个原词间隙问题、8 个原词速率问题。当前新入口仅生成直接五次曲线，验证器也只支持该表示。
- **测试证据：**已有日志记录 589 passed；这是历史运行证据，执行模型须报告自己实际运行的测试。12 条完整两词预览通过已执行的数值检查，仍不是 PASS_SIM，全部候选 playback_eligible=false。
- **当前分支或版本：**codex/group3-all-pairs-v1；HEAD 为 2875e499d79b7264b3fe0414318b30ca8aab1f4d；运行 all_pairs_dev_20261031_v2。
- **当前工作目录：**/home/kingderman/Documents/ME5412-github-latest。含未提交和未跟踪文件，只恢复 HEAD 会丢失当前实现。

## 执行顺序

1. **[P0-1] 保全基线：**先读 AGENTS.md、PLAN.md，核对结构和可写位置，保全未提交／未跟踪文件及版本哈希。
2. **[P0-2] 生成逐词问题单：**列出端点、原词缺陷、帧号、动作哈希、影响词对和需要第二组确认的内容。
3. **[P0-3] 审计碰撞规则：**记录过滤、同手排除、静态对、采样范围与终止条件。
4. **[P0-4] 定义质量指标：**明确算法、单位、阈值依据和待批事项；未经确认保持 pending。
5. **[P0-5] 实现 v2 合同：**定义分段轨迹、边界、核心、窗口、手指策略、预算和版本分派，保留 v1。
6. **[P1-1] 实现窗口选择：**校验动作哈希、审批有效性、帧范围和保护核心；无效输入明确拒绝。
7. **[P1-2] 实现独立复核：**从保存文件重建实际曲线，检查帧间几何、原词片段、边界和质量。
8. **[P1-3] 实现时间参数化：**处理非零边界导数；调整时间后重新求解、检查。
9. **[P1-4] 实现手指策略：**覆盖同步／提前／延后和纯手指变化，保持端点及耦合。
10. **[P1-5] 接入确定性候选：**统一直接、neutral、IK、回撤／接近的输出和失败证据。
11. **[P1-6] 接入有界 RRT：**对所有有效词对开放；设置有限工作与时间预算，后处理后重新验证。
12. **[P1-7] 整合多候选运行器：**保存每次尝试、选择理由、哈希、检查点和续跑身份。
13. **[P1-8] 冻结并启用正式判定：**导入真实批准材料及修复动作；重新审计；完整独立复核后才允许 PASS_SIM。
14. **[P1-9] 执行全量验收：**新 run_id 扫描 1,225 对；按根因返修；未全通过不得宣布最终完成。
15. **[P2-1] 验证多词组合：**检查全部 42,875 个三词组合的窗口兼容，并验证冻结的三词、五词和重复词轨迹集。
16. **[P2-2] 输出视频与人工评价：**关联轨迹证据，区分工程、语言和硬件评价；不得虚构评审。
17. **[P2-3] 交付并复现：**整理资源、双语说明、日志和结果清单，在新建环境复现。

## 执行规则

- 每个任务完成后先运行对应验证，保存命令、退出码和日志，再进入依赖任务；整合后运行全仓测试。
- 不扩大范围，不重构无关模块，不使用子代理；共享文件的修改串行进行。
- 实际结构、分支或接口与计划不一致时，先报告差异；有影响的任务等待澄清，可继续不受影响的工作。
- 不把计划或未经核验的报告写成已完成能力；未知接口先查文件，不凭空假定。
- 保全 v1、原始资产和旧运行。代码、输入、模型、环境或政策变化后使用新 run_id，不混写旧检查点。
- 未经第二组确认，不改变保护核心、窗口或原词时序；NURSE f80 例外仍需绑定动作版本确认。
- 禁止靠修改 approved 字符串、缩小分母、删除碰撞对或放宽阈值制造通过；搜索失败不等于无解证明。
- 验证器独立读取和重建轨迹；采样通过不等于连续碰撞证明、语言理解或实机安全。
- 说明文档按 AGENTS.md 同步中英文和索引；不推送、发布、删除原始资产或执行实机动作。
- 遇到阻塞时保留现场，报告期望／实际行为、版本、命令、退出码、日志及最小复现步骤；继续不依赖该阻塞的任务。

## 关键文件

- [完整任务表与依赖](PLAN.md)、[仓库规则](AGENTS.md)。
- [输入与版本合同](src/sign_robot/pair_contract.py)、[运行器](src/sign_robot/all_pairs.py)、[独立复核](src/sign_robot/pair_verification.py)。
- [现有运动原语](src/sign_robot/transitions.py)、[当前政策](config/transition_policy.json)、[动作索引](motions/hospital_v1_motions.json)。
- [逐词审计](word_audit.json)、[端点清单](results/group3_all_pairs_startup/endpoint_blockers.json)、[运行报告](results/group3_all_pairs_startup/final_report.json)、[测试日志](results/group3_all_pairs_startup/final_pytest.txt)。
- [规划入口](scripts/plan_all_pairs.py)、[验证入口](scripts/verify_all_pairs.py)、[汇总入口](scripts/summarize_all_pairs.py)、[现有测试](tests/)。

## 关键命令

按任务阶段选择执行，不能将下面的块不加判断地整段运行。写入前确认权限并完成 P0-1；本地 .venv 不是可移植交付环境。

```bash
TASK_REPO=/home/kingderman/Documents/ME5412-github-latest
cd "$TASK_REPO"
git --no-optional-locks status --short --branch
git log -1 --format='%H%n%s'
```

任务对应的新增测试也须运行；以下为现有专项回归及整合后的全仓测试：

```bash
"$TASK_REPO/.venv/bin/python" -m pytest -q \
  "$TASK_REPO/tests/test_all_pairs_contract.py" \
  "$TASK_REPO/tests/test_all_pairs_pipeline.py" \
  "$TASK_REPO/tests/test_plan_transitions.py" \
  "$TASK_REPO/tests/test_transition_endpoint_gate.py" \
  "$TASK_REPO/tests/test_rrt_connect.py"

"$TASK_REPO/.venv/bin/python" -m pytest -q "$TASK_REPO/tests"
```

以下仅演示**当前直接连接开发基线**。先确认 run_id 未使用；已存在时换新编号，不覆盖。v2 实现后应改为经验证、真实存在的 v2 政策路径；当前政策不会产生正式 PASS_SIM。新轨迹表示不得交给旧验证器。

```bash
TASK_RUN_ID=handoff_direct_baseline_001
"$TASK_REPO/.venv/bin/python" "$TASK_REPO/scripts/plan_all_pairs.py" \
  --library hospital_v1 --include-self \
  --policy "$TASK_REPO/config/transition_policy.json" \
  --run-id "$TASK_RUN_ID"
"$TASK_REPO/.venv/bin/python" "$TASK_REPO/scripts/verify_all_pairs.py" \
  --run-id "$TASK_RUN_ID"
"$TASK_REPO/.venv/bin/python" "$TASK_REPO/scripts/summarize_all_pairs.py" \
  --run-id "$TASK_RUN_ID"
```

旧入口 scripts/plan_transitions.py 的 --all 表示固定十句，不是 1,225 对扫描。缺少人工批准时可以运行开发诊断，但不能将其作为正式验收。

## 验收标准

- 1,225 条唯一主记录，异词 1,190、同词 35；每条记录绑定冻结输入、代码、政策和环境。
- 最终 L2 完成必须 **1,225/1,225 全部 PASS_SIM**，阻塞、失败、超时、错误、未运行和 SOURCE_NEAR 均为零；阶段交付如未达成必须明确写“未完成”。
- 通过候选有真实核心／窗口批准记录，满足冻结的限位、耦合、几何、边界、速度、加速度、jerk 和时长规则，并由保存文件独立复核。
- A→B、B→A、A→A 分别验收，自对保留两次动作；42,875 个三词窗口兼容检查和冻结多词轨迹测试通过。
- 中断恢复不改变已完成结果；完整证据可取得；新环境复现符合冻结容差。独立测试结果与未验证限制均报告。

## 已知风险

- 原词缺陷和未批准窗口可能使任何连接方法都无法获得正式通过；第三组不能单靠搜索消除这些问题。
- 多段曲线、手指时序和后处理可能引入帧间碰撞；两两通过不能推出整句通过。
- RRT 成本、碰撞过滤和差分导数解释可能影响结论，必须冻结预算和验收范围。
- 未提交文件、被忽略的结果目录和本地 .venv 链接可能造成交付不完整。

## 回滚方案

- 修改前保全当前内容、未提交／未跟踪文件和运行 manifest；使用任务级变更清单。
- 只回退本任务的变更到已保全的内容，不回退其他人的工作；仅切回 HEAD 不足以恢复当前基线。
- 新代码和政策显式版本化，旧结果不覆盖；失败运行保留，新尝试使用新目录。
- 禁止 git reset --hard、git clean 或整目录覆盖；接口不兼容时停止相关路径并保留失败证据。

## 执行完成后必须报告

1. 修改了哪些文件：绝对路径及用途。
2. 每个任务的完成状态：完成／未完成／阻塞／证据不足，并对照 PLAN.md 的完成定义。
3. 执行过哪些命令：工作目录、版本、退出码和日志位置。
4. 测试或检查结果：实际测试、运行 ID、1,225/1,190/35 分母、状态统计、轨迹及复核证据。
5. 与计划有哪些偏差：原因、影响及人工确认情况。
6. 仍然存在什么风险：未验证限制、外部依赖、失败的最小复现步骤及回滚方法。

========== HANDOFF END ==========

