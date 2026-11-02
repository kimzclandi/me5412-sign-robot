# P0-5 v2 轨迹与输入合同

[English](group3-v2-contract.en.md) · [执行报告](../TASK-05.md)

状态：**完成（合同与拒绝逻辑）**。v2 只提供版本化表达、结构检查和完整性绑定；正式窗口、质量、碰撞批准和 `PASS_SIM` 仍未启用。

## 文件与版本分派

- `config/transition_policy.json` 和现有 NPZ/运行器继续走 v1 默认路径；`load_policy()` 默认只接受 schema 1。
- `config/transition_policy_v2.json` 是显式 v2 提案，`load_policy(..., supported_versions=(1, 2))` 才能读取；`formal_acceptance_enabled=false`，三类审批状态均为 pending。
- `contracts/all_pairs_v2.json` 是 hash 绑定的声明合同，策略中的 SHA-256 与实际文件严格匹配。
- `read_pair_trajectory(path, schema_version=1)` 读取原 NPZ；`schema_version=2` 读取 JSON integrity envelope，并验证 `trajectory_hash`。

## v2 表示

每条候选有 53 个命名坐标、30 Hz、两个独立 `word_instances`（自对也保留两次）、顺序 `segments` 和显式 `boundary`。首尾必须是原词 `source_slice_v2`，逐帧范围、动作 SHA-256、保护核心提示、审批 ID/证据哈希和 `time_scale=1.0` 均保留；因此 v2 尚不能偷换原词时序或只改字符串。

中间 `polynomial_v2` 段保存每个关节六个升幂系数，参数为归一化 `u`，按真实时长换算速度/加速度；相邻段必须位置、速度、加速度连续。合同可表达多个连接段和非零边界导数。手指策略固定为 `synchronous`、`early`、`late` 三种版本化相位；耦合恢复和几何检查由后续 P1 任务执行。

每条候选绑定 library/model/code commit/code hash/policy/environment/identity hash；planner method、seed、候选数、碰撞样本、节点、段数、尝试数和墙钟预算均有限。支持 direct、neutral、ik_via1、ik_via2、retract_approach、rrt_connect。P1-7 已将六类方法接入[多候选开发运行器](group3-multicandidate-runner-v2.md)，正式验收仍未启用。

## 拒绝条件

未知版本/表示/段类型、NaN/布尔数值、重复或错序时间、动作或审批哈希格式错误、保护核心不在映射片段、self pair 少于两个实例、原词 `time_scale` 非 1、边界与多项式不一致、C2 断点、预算非正、超出 0.04 rad/1/120 s 采样上限、缺少批准证据或尝试启用正式验收都会明确抛错。审批状态不能单独升级为批准。

## 验证

在 `/tmp/me5412-execution-20261031/restored-baseline` 使用目标 `.venv` 和 `-p no:cacheprovider` 执行：

`tests/test_pair_contract_v2.py tests/test_all_pairs_contract.py tests/test_all_pairs_pipeline.py`，退出 0，**80 passed**。覆盖 v1 继续可读、v2 正例往返、非零边界导数、自对双实例、hash/边界分层破坏、未知版本、NaN/布尔/预算/窗口/策略拒绝，以及旧 pipeline 测试。原始命令和日志在 `results/group3_execution_20261031_001/P0-5/`。

P0-5 没有修改原 v1 策略、旧结果或动作资产，也没有把 v2 合同写成已批准能力。下一任务为 P1-1，先读取真实批准窗口；没有批准材料时应返回明确阻塞。
