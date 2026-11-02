# TASK-12：P1-7 多候选运行器与续跑

[English](TASK-12.en.md) · [项目状态](STATE.md)

日期：2026-10-31（Asia/Shanghai）。任务状态：**完成**。执行目录 `/home/kingderman/Documents/ME5412-github-latest`，分支 `codex/group3-all-pairs-v1`，基线 HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`。

## 修改文件与证据

- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_runner_v2.py`
- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/all_pairs.py`
- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_verification.py`
- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_verification_v2.py`
- `/home/kingderman/Documents/ME5412-github-latest/scripts/plan_all_pairs.py`
- `/home/kingderman/Documents/ME5412-github-latest/scripts/verify_all_pairs.py`
- `/home/kingderman/Documents/ME5412-github-latest/scripts/summarize_all_pairs.py`
- `/home/kingderman/Documents/ME5412-github-latest/tests/test_pair_runner_v2.py`
- `/home/kingderman/Documents/ME5412-github-latest/contracts/all_pairs_v2.json`
- `/home/kingderman/Documents/ME5412-github-latest/config/transition_policy_v2.json`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-multicandidate-runner-v2.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-multicandidate-runner-v2.en.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-v2-contract.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-v2-contract.en.md`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/pytest_runner_initial.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/pytest_runner_initial.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/runner_fault_cases.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/runner_fault_cases.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/runner_fault_cases_v2.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/runner_fault_cases_v2.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/runner_pre_review.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/runner_pre_review.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/runner_summary.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/v1_pipeline_regression.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/v1_pipeline_regression.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/v2_integration_tests.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/v2_integration_tests.log`

同时更新本报告、英文版、双语 STATE 与说明索引。每个文件的安装前后 SHA-256 和任务备份见 `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/TASK-12/changes.json`。只对明确列出的文件安装；安装前校验源内容没有被其他工作改变。

## 关键决策和实际操作

按 P1-7 顺序在恢复副本实施并测试，保留原三个 CLI，通过显式 schema 2 分派接入六类候选方法。新增不可覆盖的 attempt／所有调时曲线／最终候选，追加 journal 哈希链与 manifest head；独立复核全部 eligible 候选后，以实际连接时长、方法顺序、轨迹哈希及 ID 选择。无候选只保存输入／端点独立诊断。分母固定 1,225／1,190／35，正式判定保持关闭。

续跑核对代码、提交、模型、动作／审批、政策和环境身份；完整孤立 journal／attempt 可恢复。已完成内容只校验复用。未完成重放忽略耗时字段后比较真实曲线指纹，不同则拒绝混写，保留证据；墙钟耗尽附近可能发生这种拒绝。模拟中断不等于已验证物理断电持久性。

## 命令、退出码和验证

工作目录 `/tmp/me5412-execution-20261031/restored-baseline`，解释器为源仓库 `.venv/bin/python`；每次 pytest 使用 `-q -p no:cacheprovider`、`PYTHONDONTWRITEBYTECODE=1` 及四个计算库线程数 1。精确 argv、cwd、退出码与日志见上述 `.command.json`：

- `runner_fault_cases_v2`：退出 0，**38 passed in 11.35s**。覆盖版本变化拒绝、三类进程中断、已完成结果字节保持、重放不同和重复尝试拒绝、曲线／冻结文件／复核破坏、假 PASS、证据不完整、选择重算、无候选诊断及预算。
- `v2_integration_tests`：退出 0，**160 passed in 26.49s**，包括上述 38 项以及合同、窗口、独立复核、调时、手指、确定性路线和 RRT 测试。
- `v1_pipeline_regression`：退出 0，**296 passed in 6.32s**，包括全词对合同／pipeline、plan_transitions、端点门禁和 RRT 回归。
- `runner_fault_cases` 首轮退出 1，31 passed／1 failed；缺失已配置审批文件被正确分类为 `INVALID_APPROVAL_INPUT`，测试误期望 `MISSING_APPROVAL_BUNDLE`，已拆分两种负例，失败日志保留，未修改审批门槛。

合成正例调用真实独立复核函数，实际读取 NPZ、审批与保存曲线，freeze/model/clearance 边界使用测试夹具；合成审批从未导入正式输入。原词、核心、窗口、原词时序、v1 政策和旧运行均未改。

## 当前出口

P1-7 代码与上述验证完成。源仓库小规模开发扫描将在安装后以全新 `handoff_v2_dev_20261031_001` 执行，实际结果另存最终执行报告；本报告不预报成功。P1-8 仍需要第二组真实输入、正式质量及碰撞批准。L2 未完成。

说明见 [多候选运行器](docs/group3-multicandidate-runner-v2.md)。

## 与原计划的偏差

未扩大任务范围；原资产、v1 政策及旧运行保持原样。

## 回滚和最终状态

仅按本任务 changes.json 撤回本任务改动；已有文件恢复 before 副本，新增文件先另行保全，不使用 reset --hard、clean 或整目录覆盖。L2 全词对目标仍为未完成，批准材料不能由执行模型伪造。

## 安装后的源仓库验证（由 TASK-13 留存）

安装 33 个明确文件后，源仓库 v2 整合回归退出 0，160 passed in 25.68s。新运行 `handoff_v2_dev_20261031_001` 的 plan／verify／summarize／resume 四条命令均退出 0：4 BLOCKED_INPUT（MISSING_APPROVAL_BUNDLE）、1,221 NOT_RUN、0 候选、4 独立输入诊断、0 PASS_SIM；分母 1,225／1,190／35。续跑前后全部 32 个运行文件 SHA-256 不变。精确命令和哈希比较见 `results/group3_execution_20261031_001/P1-7/source_*.command.json` 与 `source_development_diagnosis.json`。该运行未验证真实词对的可行轨迹；P1-7 工程测试与真实正式通过分开记录。
