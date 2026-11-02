# TASK-05：P0-5 v2 轨迹与输入合同

[English](TASK-05.en.md) · [项目状态](STATE.md)

日期：2026-10-31（Asia/Shanghai）。任务状态：**完成**。执行目录 `/home/kingderman/Documents/ME5412-github-latest`，分支 `codex/group3-all-pairs-v1`，基线 HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`。

## 修改文件与证据

- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_contract.py`
- `/home/kingderman/Documents/ME5412-github-latest/config/transition_policy_v2.json`
- `/home/kingderman/Documents/ME5412-github-latest/contracts/all_pairs_v2.json`
- `/home/kingderman/Documents/ME5412-github-latest/tests/test_pair_contract_v2.py`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-v2-contract.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-v2-contract.en.md`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-5/pytest_contract_final.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-5/pytest_contract_final.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-5/pytest_contract_initial.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-5/pytest_contract_initial.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P0-5/v2_hash_manifest.json`

同时更新本报告、英文版、双语 STATE 与说明索引。每个文件的安装前后 SHA-256 和任务备份见 `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/TASK-05/changes.json`。只对明确列出的文件安装；安装前校验源内容没有被其他工作改变。

## 关键决策与操作

在 pair_contract.py 中增加严格 v2 policy/trajectory 校验、显式 schema dispatch、版本化段和预算/审批/身份合同；默认 v1 入口拒绝 v2，防止旧 runner 误读新表示。新增 v2 policy、声明合同、正反例测试和 hash manifest。

## 与原计划的偏差

未扩大任务范围；原资产、v1 政策及旧运行保持原样。

## 回滚和最终状态

仅按本任务 changes.json 撤回本任务改动；已有文件恢复 before 副本，新增文件先另行保全，不使用 reset --hard、clean 或整目录覆盖。L2 全词对目标仍为未完成，批准材料不能由执行模型伪造。

## 实际验证结果

在 `/tmp/me5412-execution-20261031/restored-baseline` 运行目标 `.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pair_contract_v2.py tests/test_all_pairs_contract.py tests/test_all_pairs_pipeline.py`，最终退出 0，80 passed in 3.19s。首轮 78 passed 后补充非零边界与真实合同 hash 冻结测试，再运行最终 80 项；两轮日志均保留。安装仍以任务文件哈希作独立核对，未重新写入旧运行。
