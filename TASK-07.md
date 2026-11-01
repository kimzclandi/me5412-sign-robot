# TASK-07：P1-2 v2 独立复核

[English](TASK-07.en.md) · [项目状态](STATE.md)

日期：2026-10-31（Asia/Shanghai）。任务状态：**完成**。执行目录 `/home/kingderman/Documents/ME5412-github-latest`，分支 `codex/group3-all-pairs-v1`，基线 HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`。

## 修改文件与证据

- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_verification_v2.py`
- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_verification.py`
- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_contract.py`
- `/home/kingderman/Documents/ME5412-github-latest/contracts/all_pairs_v2.json`
- `/home/kingderman/Documents/ME5412-github-latest/config/transition_policy_v2.json`
- `/home/kingderman/Documents/ME5412-github-latest/tests/test_pair_verification_v2.py`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-independent-verifier-v2.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-independent-verifier-v2.en.md`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-2/pytest_verifier_final.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-2/pytest_verifier_final.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-2/pytest_verifier_initial.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-2/pytest_verifier_initial.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-2/pytest_verifier_reviewed.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-2/pytest_verifier_reviewed.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-2/pytest_verifier_reviewed_final.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-2/pytest_verifier_reviewed_final.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-2/verifier_contract_hashes.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-2/verifier_evidence_summary.json`

同时更新本报告、英文版、双语 STATE 与说明索引。每个文件的安装前后 SHA-256 和任务备份见 `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/TASK-07/changes.json`。只对明确列出的文件安装；安装前校验源内容没有被其他工作改变。

## 关键决策、实际命令和结果

新增独立保存文件复核器，限制规划器依赖；按 v2 合同重建 source_slice/polynomial 段，先做 hash/审批/帧片段校验，再做解析质量与有界几何采样。预算不足保存 TIMEOUT，状态不会转成通过。更新 v2 合同 verifier dispatch 并同步 policy hash。

恢复副本最终命令：`.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pair_verification_v2.py tests/test_pair_contract_v2.py tests/test_pair_windows_v2.py tests/test_all_pairs_pipeline.py`，退出 0，91 passed in 3.39s。首次 89 passed 后增加端点/进度/hash、解析极值和自对测试，修正浮点容差后最终 91 项；日志均保留。真实输入因无批准 bundle 阻塞。

与计划一致：独立重建、帧间加密、原词片段、边界/质量/预算证据完成；真实审批和正式 PASS 留给 P1-8。

## 与原计划的偏差

未扩大任务范围；原资产、v1 政策及旧运行保持原样。

## 回滚和最终状态

仅按本任务 changes.json 撤回本任务改动；已有文件恢复 before 副本，新增文件先另行保全，不使用 reset --hard、clean 或整目录覆盖。L2 全词对目标仍为未完成，批准材料不能由执行模型伪造。
