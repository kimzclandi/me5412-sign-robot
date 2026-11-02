# P1-7 多候选运行器与续跑

[English](group3-multicandidate-runner-v2.en.md) · [执行报告](../TASK-12.md)

状态：开发运行器已实现，正式验收仍关闭。三个原 CLI 按政策／manifest schema 分派；v1 的政策、NPZ、旧运行和默认读取保持原样。

每个 v2 运行冻结 `policy.json`、`contract.json`、`library_manifest.json`、完整 `pair_universe.json`。代码内容／提交、模型资产、动作与元数据、审批文件、政策和依赖环境均绑定身份；任何变化都须新 run_id。选择 `--pair` 或 `--max-pairs` 仅限制本次执行，汇总分母始终为 **1,225／1,190／35**，其余词对仍为 `NOT_RUN`。

`attempts/PAIR/attempt_NNNNN.json` 保留每次方法、参数、端点、种子、预算和诊断。所有已求出的调时曲线保存在 `timing_attempts/`；最终可供复核的候选保存在 `candidates/`，两类分别列出哈希和资格。生成器的失败与 RRT raw/shortcut 路径留在诊断中。确定性路线和 RRT 共享每词对的有限工作及墙钟预算；超时或搜索耗尽不等于无解证明。

检查点按 `checkpoints/PAIR/checkpoint_NNNNN.json` 追加，记录前一文件哈希与序号，manifest 保存最新 head。进程中断后可接纳完整但尚未登记到 manifest 的 journal，或完整但尚未写检查点的 attempt。只有曲线写成时，确定性重放必须产生相同内容才可复用。未完成词对固定种子重放，比较诊断与全部实际曲线的逻辑指纹，忽略耗时字段但保留原文件字节；重放不同则拒绝混写并保留现场。墙钟触发的尝试序列可能不同，这种情况需保留旧运行并使用新 run_id。已完成规划或复核只读取校验，不重新计算或覆盖。此处验证的是模拟进程中断，未验证物理断电后的存储持久性。

独立入口逐一读取所有最终候选。只有完整的合同、审批、核心、原词切片、两次词实例、全轨迹数值检查以及相同候选／身份哈希才能参与选择。排名依次为实际连接时长、`planner.methods` 顺序、规范化轨迹哈希、尝试 ID；保存选择后可重新计算核对。数值通过的开发候选仍为 `FAILED_QUALITY`、`playback_eligible=false`。无候选时重新冻结输入、读取真实审批文件并在预算内复查许可端点，只保存 `DIAGNOSIS_ONLY`，不得称为曲线复核通过。

汇总导出 35×35 `matrix.csv`、1,225 行 `pairs.jsonl`、`summary.json` 和文件哈希 inventory。导出前先标记 summary stale，导出中断可重新生成，不更改已保存规划和复核证据。

以下命令用于本轮开发诊断，结果见最终执行报告。重新创建运行时必须换未使用的 run_id；仅 --resume 可复用既有编号，版本变化也须换号。命令结束不代表正式验收：

```bash
TASK_REPO=/home/kingderman/Documents/ME5412-github-latest
TASK_RUN_ID=handoff_v2_dev_20261031_002
cd "$TASK_REPO"
"$TASK_REPO/.venv/bin/python" scripts/plan_all_pairs.py --include-self \
  --policy config/transition_policy_v2.json --run-id "$TASK_RUN_ID" \
  --pair HELLO__PLEASE --pair PLEASE__HELLO --pair HELLO__HELLO --pair NURSE__NURSE
"$TASK_REPO/.venv/bin/python" scripts/verify_all_pairs.py --run-id "$TASK_RUN_ID"
"$TASK_REPO/.venv/bin/python" scripts/summarize_all_pairs.py --run-id "$TASK_RUN_ID"
"$TASK_REPO/.venv/bin/python" scripts/plan_all_pairs.py --include-self \
  --policy config/transition_policy_v2.json --run-id "$TASK_RUN_ID" --resume \
  --pair HELLO__PLEASE --pair PLEASE__HELLO --pair HELLO__HELLO --pair NURSE__NURSE
```

实际命令、退出码、失败与修复日志见 `results/group3_execution_20261031_001/P1-7/`。测试使用明确标注的合成审批；它们不构成第二组真实确认。正式判定、1,225 全量通过、多词组合、人工评价和新环境复现仍未完成。
