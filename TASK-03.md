# TASK-03：P0-3 碰撞范围与采样审计

[English](TASK-03.en.md) · [项目状态](STATE.md)

日期：2026-10-31（Asia/Shanghai）。任务状态：**完成**。执行目录 `/home/kingderman/Documents/ME5412-github-latest`，分支 `codex/group3-all-pairs-v1`，基线 HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`。

## 修改文件与证据

- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-collision-scope.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-collision-scope.en.md`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-3/audit_evidence.py`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-3/collision_audit.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-3/collision_audit.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-3/collision_inventory.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-3/dense_counterexample_recheck.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-3/pytest_collision_scope.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-3/pytest_collision_scope.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-3/sampling_proposal.json`

同时更新本报告、英文版、双语 STATE 与说明索引。每个文件的安装前后 SHA-256 和任务备份见 `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/TASK-03/changes.json`。只对明确列出的文件安装；安装前校验源内容没有被其他工作改变。

## 关键决策与操作

读取 transitions.py 的 MujocoClearance、same_hand 和静态派生，all_pairs.py 和 pair_verification.py 的采样路径及当前政策。新增双语覆盖表和待批 v2 采样规范；不修改过滤或旧政策。同手排除覆盖全部同侧指间/腕组合；静态对单独报告，任何未来改变常量关节的输入都必须重新派生或拒绝。新增验证预算提案保持 pending。

## 实际命令和验证

工作目录为本仓库。通过 .venv/bin/python 运行 /tmp/me5412-execution-20261031/audit_p0_3.py，退出 0；实际模型 122 geoms、136 静态 body 对、47 独立 vendor geom 对。11/11 历史帧间反例从真实保存曲线重现。命令及完整日志为 collision_audit.command.json / collision_audit.log。

运行 .venv/bin/python -m pytest -q tests/test_plan_transitions.py tests/test_transition_endpoint_gate.py，退出 0：230 passed，1 条只读 pytest 缓存警告。第一遍未持久化原始输出，随后为保存完整命令与日志重复运行；不将两遍相加作为 460 项测试。pytest_collision_scope.command.json 与 .log 保存实际第二遍输出。后续使用 -p no:cacheprovider 防止该警告。

P0-3 完成的是审计、规范提案和几何案例复核；采样预算尚未实现，正式碰撞覆盖尚未人工冻结。

## 与原计划的偏差

未扩大任务范围；原资产、v1 政策及旧运行保持原样。

## 回滚和最终状态

仅按本任务 changes.json 撤回本任务改动；已有文件恢复 before 副本，新增文件先另行保全，不使用 reset --hard、clean 或整目录覆盖。L2 全词对目标仍为未完成，批准材料不能由执行模型伪造。
