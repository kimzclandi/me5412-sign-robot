# TASK-10：P1-5 确定性候选适配

[English](TASK-10.en.md) · [项目状态](STATE.md)

日期：2026-10-31（Asia/Shanghai）。任务状态：**完成**。执行目录 `/home/kingderman/Documents/ME5412-github-latest`，分支 `codex/group3-all-pairs-v1`，基线 HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`。

## 修改文件与证据

- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_routes.py`
- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_timing.py`
- `/home/kingderman/Documents/ME5412-github-latest/tests/test_pair_routes_v2.py`
- `/home/kingderman/Documents/ME5412-github-latest/contracts/all_pairs_v2.json`
- `/home/kingderman/Documents/ME5412-github-latest/config/transition_policy_v2.json`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-deterministic-routes-v2.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-deterministic-routes-v2.en.md`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-5/pytest_routes_final.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-5/pytest_routes_final.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-5/pytest_routes_initial.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-5/pytest_routes_initial.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-5/pytest_routes_reviewed.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-5/pytest_routes_reviewed.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-5/route_summary.json`

同时更新本报告、英文版、双语 STATE 与说明索引。每个文件的安装前后 SHA-256 和任务备份见 `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/TASK-10/changes.json`。只对明确列出的文件安装；安装前校验源内容没有被其他工作改变。

## 关键决策、实际命令和结果

复用现有几何 primitive，统一 v2 方法/手指/时间/预算与失败证据，不复用旧 PASS 或宽松 floor。回撤/接近的完整原几何片段先查，再检查最终时间曲线；失败保留且不升级。TimingResult 现保留每个调时曲线以供 P1-7 逐次保存。

在恢复副本执行 `.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pair_routes_v2.py tests/test_pair_timing_v2.py tests/test_pair_verification_v2.py tests/test_pair_contract_v2.py`，最终退出 0，73 passed in 12.88s；各轮日志已保存。真实输入仍缺审批，未做正式矩阵扫描。下一任务 P1-6。

## 与原计划的偏差

未扩大任务范围；原资产、v1 政策及旧运行保持原样。

## 回滚和最终状态

仅按本任务 changes.json 撤回本任务改动；已有文件恢复 before 副本，新增文件先另行保全，不使用 reset --hard、clean 或整目录覆盖。L2 全词对目标仍为未完成，批准材料不能由执行模型伪造。
