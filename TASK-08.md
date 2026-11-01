# TASK-08：P1-3 边界导数与时间参数化

[English](TASK-08.en.md) · [项目状态](STATE.md)

日期：2026-10-31（Asia/Shanghai）。任务状态：**完成**。执行目录 `/home/kingderman/Documents/ME5412-github-latest`，分支 `codex/group3-all-pairs-v1`，基线 HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`。

## 修改文件与证据

- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_timing.py`
- `/home/kingderman/Documents/ME5412-github-latest/tests/test_pair_timing_v2.py`
- `/home/kingderman/Documents/ME5412-github-latest/tests/test_pair_verification_v2.py`
- `/home/kingderman/Documents/ME5412-github-latest/contracts/all_pairs_v2.json`
- `/home/kingderman/Documents/ME5412-github-latest/config/transition_policy_v2.json`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-pair-timing-v2.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-pair-timing-v2.en.md`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-3/pytest_timing_final.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-3/pytest_timing_final.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-3/pytest_timing_initial.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-3/pytest_timing_initial.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-3/pytest_timing_reviewed.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-3/pytest_timing_reviewed.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-3/timing_summary.json`

同时更新本报告、英文版、双语 STATE 与说明索引。每个文件的安装前后 SHA-256 和任务备份见 `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/TASK-08/changes.json`。只对明确列出的文件安装；安装前校验源内容没有被其他工作改变。

## 关键决策、实际命令和结果

实现固定非零边界 p/v/a 的五次系数求解、30 Hz 时长量化和有限重试；每次调时重新求解并重新检查限位、耦合、解析速率/质量与可选几何回调。没有几何回调的输出明确是候选，原词保持原数组与原时序。

最终在恢复副本运行 `.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pair_timing_v2.py tests/test_pair_verification_v2.py tests/test_pair_contract_v2.py`，退出 0，61 passed in 0.38s。初始测试自身的矩阵方向错误已修复，日志保留。新增实际非零边界的定时→保存→独立复核案例通过；真实批准仍待 P1-8。下一任务 P1-4。

## 与原计划的偏差

未扩大任务范围；原资产、v1 政策及旧运行保持原样。

## 回滚和最终状态

仅按本任务 changes.json 撤回本任务改动；已有文件恢复 before 副本，新增文件先另行保全，不使用 reset --hard、clean 或整目录覆盖。L2 全词对目标仍为未完成，批准材料不能由执行模型伪造。
