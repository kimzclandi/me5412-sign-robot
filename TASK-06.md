# TASK-06：P1-1 批准窗口读取与选择

[English](TASK-06.en.md) · [项目状态](STATE.md)

日期：2026-10-31（Asia/Shanghai）。任务状态：**完成**。执行目录 `/home/kingderman/Documents/ME5412-github-latest`，分支 `codex/group3-all-pairs-v1`，基线 HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`。

## 修改文件与证据

- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_windows.py`
- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_contract.py`
- `/home/kingderman/Documents/ME5412-github-latest/contracts/all_pairs_v2.json`
- `/home/kingderman/Documents/ME5412-github-latest/config/transition_policy_v2.json`
- `/home/kingderman/Documents/ME5412-github-latest/tests/pair_v2_fixtures.py`
- `/home/kingderman/Documents/ME5412-github-latest/tests/test_pair_windows_v2.py`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-window-approval.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-window-approval.en.md`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-1/approval_state.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-1/pytest_windows_final.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-1/pytest_windows_final.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-1/pytest_windows_initial.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-1/pytest_windows_initial.log`

同时更新本报告、英文版、双语 STATE 与说明索引。每个文件的安装前后 SHA-256 和任务备份见 `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/TASK-06/changes.json`。只对明确列出的文件安装；安装前校验源内容没有被其他工作改变。

## 关键决策、实际命令和结果

实现实际审核证据与动作 hash 双重绑定、带时区审批有效期、核心完整保留和角色帧枚举；没有自动继承旧裁剪或例外。证据文件完整性不被夸大为人类身份验证。

在恢复副本使用目标 `.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pair_windows_v2.py tests/test_pair_contract_v2.py tests/test_all_pairs_contract.py`，最终退出 0、72 passed in 0.23s。命令与日志在 P1-1/pytest_windows_final.*。真实策略缺批准时返回 MISSING_APPROVAL_BUNDLE，保持 BLOCKED_INPUT。

与计划一致：实现读取/拒绝逻辑和合成正反例，不代替第二组审批；v2 合同补充有效期和证据格式，并同步策略 hash。下一任务 P1-2。

## 与原计划的偏差

未扩大任务范围；原资产、v1 政策及旧运行保持原样。

## 回滚和最终状态

仅按本任务 changes.json 撤回本任务改动；已有文件恢复 before 副本，新增文件先另行保全，不使用 reset --hard、clean 或整目录覆盖。L2 全词对目标仍为未完成，批准材料不能由执行模型伪造。
