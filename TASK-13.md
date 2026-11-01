# TASK-13：P1-8 真实审批依赖阻塞

[English](TASK-13.en.md) · [项目状态](STATE.md)

日期：2026-10-31（Asia/Shanghai）。任务状态：**阻塞**。执行目录 `/home/kingderman/Documents/ME5412-github-latest`，分支 `codex/group3-all-pairs-v1`，基线 HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`。

## 修改文件与证据

- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_before_resume_hashes.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_development_diagnosis.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_plan_four.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_plan_four.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_post_install_regression.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_post_install_regression.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_resume_four.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_resume_four.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_summarize_four.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_summarize_four.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_verify_four.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-7/source_verify_four.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-8/approval_dependency_audit.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-8/approval_dependency_audit.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-8/approval_dependency_audit.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-8/minimal_reproduction.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-8/minimal_reproduction.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/P1-8/reproduce_missing_approval.py`
- `/home/kingderman/Documents/ME5412-github-latest/TASK-12.md`
- `/home/kingderman/Documents/ME5412-github-latest/TASK-12.en.md`

同时更新本报告、英文版、双语 STATE 与说明索引。每个文件的安装前后 SHA-256 和任务备份见 `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/TASK-13/changes.json`。只对明确列出的文件安装；安装前校验源内容没有被其他工作改变。

## 期望、实际行为和阻塞

P1-8 要求先导入真实第二组核心／窗口批准与修复动作，再冻结质量、原词线性回放导数解释、碰撞过滤覆盖与采样预算，最后实现并验证严格正式判定。实际政策仍为 `endpoints.review_status=pending`、`approval_file=null`、`quality.freeze_status=pending`、`validation.approval_status=pending`，三类 evidence 均未配置；`formal_acceptance_enabled=false`。真实加载返回：

`WindowApprovalError: MISSING_APPROVAL_BUNDLE — No actual group-2 review bundle is configured`。

本轮核对的 35 个动作哈希全部与保全基线一致，未发现已返回的修复资产。仓库中存在问题单、未填审核模板和明确标注的合成测试夹具，不能代替真实审核。未尝试改 approved 字符串、复制合成审批、放宽阈值或裁剪原词。P1-8 **阻塞／未完成**；正式 PASS 出口尚未实现并启用，不是只差运行全量命令。

## 最小复现和实际命令

工作目录 `/home/kingderman/Documents/ME5412-github-latest`，分支和 HEAD 见本报告开头，代码内容身份见 `approval_dependency_audit.json`。已实际执行只读审批依赖审计与独立的最小复现，两者退出 **2**（预期阻塞），完整 stdout/stderr 和 argv/cwd/退出码见本任务证据 `.log` 与 `.command.json`。仓库内可复现命令：

```bash
cd /home/kingderman/Documents/ME5412-github-latest
.venv/bin/python results/group3_execution_20261031_001/P1-8/reproduce_missing_approval.py
```

期望输出上述 `MISSING_APPROVAL_BUNDLE`，进程退出 2。原三个 CLI 的 4 对开发诊断可正常结束（退出 0），但每对为 BLOCKED_INPUT；它们的退出 0 不能表示正式通过。

## 已尝试与所需下一步

已核对政策、问题单、审核模板和当前动作哈希，并实际调用真实审批读取器；P1-7 安装后的规划、独立输入复查及续跑也再次检出同一缺失材料。保留开发运行及所有失败／阻塞日志。

需要返回：35 词的动作版本／帧数／保护核心／入口出口窗口／有效期和审核人证据文件；修复版动作及元数据，或针对每个原词缺陷的真实版本绑定处置；正式质量阈值及线性回放导数范围批准；碰撞过滤、静态对覆盖和验证预算批准；NURSE f80 精确动作哈希绑定的决定。材料到位后先只读核对，再以新 run_id 重新审计和完成 P1-8 的正式判定代码与正负例，随后才可执行 P1-9／P2。模型不能替代这些人工决定。

## 保留状态

本任务仅增加阻塞证据与双语报告，并把安装后源仓库 P1-7 诊断归档。没有修改政策、动作、核心、窗口、阈值或代码。P1-9、P2-1、P2-2、P2-3 均未执行；最终整仓测试和交付验收清单将作为独立收尾操作执行，不能据此升级 L2。

## 与原计划的偏差

计划前置的真实批准与修复资产缺失，故未导入或启用正式判定。遵循阻塞规则保留现场，后续依赖任务未执行；没有制造替代批准。

## 回滚和最终状态

仅按本任务 changes.json 撤回本任务改动；已有文件恢复 before 副本，新增文件先另行保全，不使用 reset --hard、clean 或整目录覆盖。L2 全词对目标仍为未完成，批准材料不能由执行模型伪造。
