# TASK-09：P1-4 手指时间策略与耦合

[English](TASK-09.en.md) · [项目状态](STATE.md)

日期：2026-10-31（Asia/Shanghai）。任务状态：**完成**。执行目录 `/home/kingderman/Documents/ME5412-github-latest`，分支 `codex/group3-all-pairs-v1`，基线 HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`。

## 修改文件与证据

- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_fingers.py`
- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_timing.py`
- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_verification_v2.py`
- `/home/kingderman/Documents/ME5412-github-latest/tests/test_pair_fingers_v2.py`
- `/home/kingderman/Documents/ME5412-github-latest/tests/test_pair_verification_v2.py`
- `/home/kingderman/Documents/ME5412-github-latest/contracts/all_pairs_v2.json`
- `/home/kingderman/Documents/ME5412-github-latest/config/transition_policy_v2.json`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-finger-strategies-v2.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-finger-strategies-v2.en.md`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-4/finger_summary.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-4/pytest_fingers_final.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-4/pytest_fingers_final.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-4/pytest_fingers_initial.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-4/pytest_fingers_initial.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-4/pytest_fingers_polynomial.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-4/pytest_fingers_polynomial.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-4/pytest_fingers_reviewed.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-4/pytest_fingers_reviewed.log`

同时更新本报告、英文版、双语 STATE 与说明索引。每个文件的安装前后 SHA-256 和任务备份见 `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/TASK-09/changes.json`。只对明确列出的文件安装；安装前校验源内容没有被其他工作改变。

## 关键决策、实际命令和结果

保留手臂多项式曲线、手指路由节点、边界 p/v/a 与原词核心；按拓扑恢复耦合 child，禁止把其当独立驱动。非零边界下的提前/延后使用同位置导数匹配前缀/尾段，额外曲线也进入限位、质量和几何检查。独立复核不信策略标签，重读相位状态。

最终恢复副本命令 `.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pair_fingers_v2.py tests/test_pair_timing_v2.py tests/test_pair_verification_v2.py tests/test_pair_contract_v2.py`，退出 0，81 passed in 0.53s。初始测试夹具的线性预览预期和非法端点已修正，日志保留；未放宽阈值。真实批准仍缺失，正式 PASS 继续禁用。下一任务 P1-5。

## 与原计划的偏差

未扩大任务范围；原资产、v1 政策及旧运行保持原样。

## 回滚和最终状态

仅按本任务 changes.json 撤回本任务改动；已有文件恢复 before 副本，新增文件先另行保全，不使用 reset --hard、clean 或整目录覆盖。L2 全词对目标仍为未完成，批准材料不能由执行模型伪造。
