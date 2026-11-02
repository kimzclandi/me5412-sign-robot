# TASK-04：P0-4 质量指标与阈值提案

[English](TASK-04.en.md) · [项目状态](STATE.md)

日期：2026-10-31（Asia/Shanghai）。任务状态：**完成**。执行目录 `/home/kingderman/Documents/ME5412-github-latest`，分支 `codex/group3-all-pairs-v1`，基线 HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`。

## 修改文件与证据

- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-quality-metrics.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-quality-metrics.en.md`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-4/analytic_metric_checks.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-4/audit_evidence.py`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-4/quality_audit.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-4/quality_audit.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-4/quality_metrics_recomputed.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-4/quality_threshold_proposal.json`

同时更新本报告、英文版、双语 STATE 与说明索引。每个文件的安装前后 SHA-256 和任务备份见 `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/TASK-04/changes.json`。只对明确列出的文件安装；安装前校验源内容没有被其他工作改变。

## 关键决策与操作

从 pair_contract.py 的边界导数和 pair_verification.py 的 trajectory_metrics 实现出发，固定单位、时间基准、有限差分与解析连接器两条路径。重算 899 候选并保存逐条结果；阈值状态保持 pending。

## 与原计划的偏差

未扩大任务范围；原资产、v1 政策及旧运行保持原样。

## 回滚和最终状态

仅按本任务 changes.json 撤回本任务改动；已有文件恢复 before 副本，新增文件先另行保全，不使用 reset --hard、clean 或整目录覆盖。L2 全词对目标仍为未完成，批准材料不能由执行模型伪造。

## 实际命令、退出码与验证

在目标仓库执行 `.venv/bin/python /tmp/me5412-execution-20261031/audit_p0_4.py`，退出 0；日志 quality_audit.log、命令 quality_audit.command.json。899/899 候选指标与历史统计匹配，35 原词差分统计保存，3 个解析检查通过。一次前置只读统计误用系统 python3，报 ModuleNotFoundError: numpy；改用已有 .venv 解释器后成功。未运行或声称新几何扫描。
