# P1-2 v2 独立复核

[English](group3-independent-verifier-v2.en.md) · [任务报告](../TASK-07.md)

`src/sign_robot/pair_verification_v2.py` 只从保存的 v2 integrity envelope、原词 NPZ 和声明多项式重建曲线；不调用规划器、候选生成器或旧 v1 通过状态。它刷新模型/碰撞检查器，重新检查词片段、审批 hash、边界、限位、耦合、速度、质量和加密几何。

复核入口明确区分：

- `BLOCKED_INPUT`：动作/审批缺失或版本不一致；
- `ERROR`：JSON、hash、段连续性、边界或重建合同损坏；
- `TIMEOUT`：pose、native-call、细分深度或墙钟预算不足，`validation_complete=false`；
- `FAILED_SEARCH`：重新采样发现连接碰撞；
- `FAILED_QUALITY`：数值检查完成但质量或正式批准仍不满足。

每个段按最大时间步 `1/120 s`、坐标步长 `0.04 rad` 和解析速度上界细分；每批碰撞查询先预留预算，再记录 segment/factor/curve time/worst pair。保存全轨迹 canonical hash、边界端点、重建帧数、端点最小间隙和活动进度。即使有限采样全部通过，`continuous_collision_certified=false` 仍保持。

解析连接器独立计算位置范围、速度/加速度/jerk 极值和平方 jerk 积分；原词线性回放仍用实际 30 Hz 的有限差分，内部折点不被表述为连续导数。quality limits、window approvals 和 collision scope 为 pending 时，数值完成也不能变为 `PASS_SIM`。

## 实际验证

在恢复副本使用目标 `.venv/bin/python -m pytest -q -p no:cacheprovider` 运行 `tests/test_pair_verification_v2.py tests/test_pair_contract_v2.py tests/test_pair_windows_v2.py tests/test_all_pairs_pipeline.py`，最终退出 0：**91 passed in 3.39s**。覆盖有效重建；本任务没有重跑 P0-3 的 11 条真实反例，而是新增独立 synthetic between-frame collision、非零预算、墙钟中止、动作 hash 变化、审批变化、unknown representation、C2/边界和 A→A 两实例。历史全量 v1 运行不被升级。

真实 v2 策略仍没有 `approval_file`，所以真实输入会在审批阶段返回 `MISSING_APPROVAL_BUNDLE`；本轮没有宣称真实词对 PASS。P1-2 完成代码和失败证据闭环，P1-3 继续实现边界导数/时间参数化。
