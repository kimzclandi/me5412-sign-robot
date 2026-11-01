# TASK-14：FINAL 最终验收与执行报告

[English](TASK-14.en.md) · [项目状态](STATE.md)

日期：2026-10-31（Asia/Shanghai）。任务状态：**完成**。执行目录 `/home/kingderman/Documents/ME5412-github-latest`，分支 `codex/group3-all-pairs-v1`，基线 HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`。

## 修改文件与证据

- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/project_overview.py`
- `/home/kingderman/Documents/ME5412-github-latest/docs/README.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/README.en.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-quality-metrics.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-quality-metrics.en.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-multicandidate-runner-v2.md`
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-multicandidate-runner-v2.en.md`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/archive_integrity.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/archive_integrity.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/archive_integrity.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/before_compatibility/src/sign_robot/project_overview.py`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/documentation_compatibility_change.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/execution_report.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/final_acceptance_check.py`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/final_acceptance_checklist.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/final_integrity_audit.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/final_integrity_audit.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/final_source_v2_diagnosis.py`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/full_pytest.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/full_pytest.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/full_pytest_after_compatibility_fix.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/full_pytest_after_compatibility_fix.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/integrity_audit.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/integrity_audit.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/integrity_audit_with_test_artifacts.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/integrity_audit_with_test_artifacts.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/known_test_outputs.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/project_overview_failure_analysis.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/project_overview_failure_reproduction.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/project_overview_failure_reproduction.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/source_before_resume_hashes.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/source_development_diagnosis.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/source_plan_four.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/source_plan_four.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/source_resume_four.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/source_resume_four.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/source_summarize_four.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/source_summarize_four.log`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/source_verify_four.command.json`
- `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/FINAL/source_verify_four.log`

同时更新本报告、英文版、双语 STATE 与说明索引。每个文件的安装前后 SHA-256 和任务备份见 `/home/kingderman/Documents/ME5412-github-latest/results/group3_execution_20261031_001/TASK-14/changes.json`。只对明确列出的文件安装；安装前校验源内容没有被其他工作改变。

## 执行结论与任务状态

已先核对工作区，再按 ID 串行完成 P0-1～P0-5、P1-1～P1-7 的工程范围；每项有双语 TASK 报告、实际命令与任务级前后哈希。**P1-8 阻塞；P1-9、P2-1～P2-3 未执行；L2 全词对验收未完成。** 本报告是用户要求的最终收尾，不是另一个已完成的计划功能。

| 任务 | 本轮实际出口 | 报告 |
|---|---|---|
| P0-1 | 完整基线归档和恢复比对完成 | TASK-01.md |
| P0-2 | 35 词修复／确认清单完成 | TASK-02.md |
| P0-3 | 碰撞范围、过滤和采样审计完成，提案待批 | TASK-03.md |
| P0-4 | 质量算法、单位与阈值提案完成，正式冻结待批 | TASK-04.md |
| P0-5 | v1/v2 合同与拒绝逻辑完成 | TASK-05.md |
| P1-1 | hash 绑定审批读取／窗口选择／拒绝完成 | TASK-06.md |
| P1-2 | 保存分段曲线独立复核完成 | TASK-07.md |
| P1-3 | 非零 p/v/a 五次求解与每次调时复查完成 | TASK-08.md |
| P1-4 | 同步／提前／延后手指与耦合恢复完成 | TASK-09.md |
| P1-5 | direct、neutral、两类 IK、回撤／接近统一适配完成 | TASK-10.md |
| P1-6 | 通用有限工作／墙钟 RRT、raw 与后处理复查完成 | TASK-11.md |
| P1-7 | 多候选、不可覆盖证据、检查点、恢复、独立选择完成 | TASK-12.md |
| P1-8 | 缺真实审批和修复资产，阻塞／未完成 | TASK-13.md |
| P1-9 | 依赖 P1-8，未进行正式全量验收 | STATE.md |
| P2-1 | 42,875 三词兼容及冻结多词轨迹未完成 | STATE.md |
| P2-2 | 代表视频和真实人工评价未完成 | STATE.md |
| P2-3 | 新建环境复现和最终交付打包未完成 | STATE.md |

## 主要修改的绝对路径与用途

下列路径均以 `/home/kingderman/Documents/ME5412-github-latest/` 为实际仓库根；精确逐文件绝对路径、最终内容 SHA 和用途分类见 `results/group3_execution_20261031_001/FINAL/changed_files.json`，每次安装的 before/after 在 `TASK-*/changes.json`，原文件在相应 before 目录。

- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_contract.py`：显式 v2 表示、合同、冻结身份与版本读取；保留 v1。
- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_windows.py`：真实审批文件、动作哈希、有效期、保护核心和端点选择。
- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_verification_v2.py`：独立保存曲线重建、完整原词片段、解析／差分量、真实几何、预算及无候选诊断。
- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_timing.py`、`pair_fingers.py`、`pair_routes.py`、`pair_search.py`：边界匹配调时、三种手指策略、五类确定性路线及通用有界 RRT。
- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/pair_runner_v2.py`：每次尝试和调时曲线、不可覆盖文件、journal 链、版本续跑和独立选择；`all_pairs.py`、`pair_verification.py` 及原三个 scripts 只作版本分派适配。
- `/home/kingderman/Documents/ME5412-github-latest/config/transition_policy_v2.json`、`contracts/all_pairs_v2.json`：hash 绑定的开发政策／合同；全部正式审核状态仍 pending，formal flag 为 false。
- `/home/kingderman/Documents/ME5412-github-latest/tests/test_pair_*_v2.py`、`tests/pair_v2_fixtures.py`：数学、合成审批、几何反例、存储中断、版本变化、篡改及端到端回归；测试审批没有导入正式输入。
- `/home/kingderman/Documents/ME5412-github-latest/docs/group3-*.md` 及英文配对、`TASK-01.md`～`TASK-14.md` 及英文版、`STATE.md/.en.md`、两个 docs 索引：问题单、规范、操作与实际报告。
- `/home/kingderman/Documents/ME5412-github-latest/src/sign_robot/project_overview.py`：收尾仅同步两个 docs 索引固定下载 SHA-256；原有 16 行未提交改动保留。与保全副本的最终差异仅两个哈希字面量。

原始 motions/assets、v1 政策、旧运行和另一个 ME5412 检出未作本任务修改。新运行位于独立目录；完整证据在本轮 results 目录，6 个既有服务测试产生的日志／空锁副产物逐个检验并记录于 `known_test_outputs.json`，予以保留。

## 最终实际测试、命令和退出码

最终源仓库命令（工作目录即本报告执行目录）：

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider tests
```

使用 `PYTHONDONTWRITEBYTECODE=1`、四个计算库线程数 1，既有 HTTP/service 测试仅绑定 127.0.0.1 临时端口。**最终退出 0，749 passed in 51.42s**；日志 `results/group3_execution_20261031_001/FINAL/full_pytest_after_compatibility_fix.log`。先前全仓运行退出 1，748 passed／1 failed in 50.97s，失败最小复现为 `tests/test_project_overview.py::test_real_overview_preserves_data_units_and_snapshot_scope`（单例重现退出 1）；两次失败日志均保留。

失败原因是两个 docs 索引与下载白名单的固定哈希不符；保全基线本身已不符。同步两处静态哈希后全仓通过，未删除或弱化测试、未更改轨迹门槛。另将双语质量报告 acceleration_jump p50 的六位小数改为 `104.735394`，原始值 `104.73539413070189` 和冻结 JSON 未变。因代码身份变化，保留运行 001，并新建 002；不续写旧版本。

P1-7 恢复副本另有 38 项运行器、160 项 v2 整合和 296 项旧入口回归，安装后源仓库又通过 160 项；这些集合重叠，不能相加代替全仓 749。首次运行器故障测试 31 passed／1 failed 的错误预期与修正均见 TASK-12。历史 `589 passed` 只属于旧证据。

运行 002 实际四条 plan／verify／summarize／resume 命令详见 `FINAL/source_*.command.json`（全部退出 0），选择 HELLO→PLEASE、PLEASE→HELLO、HELLO→HELLO、NURSE→NURSE。结果：

| 范围 | 固定分母 | BLOCKED_INPUT | NOT_RUN | PASS_SIM |
|---|---:|---:|---:|---:|
| 全部 | 1,225 | 4 | 1,221 | 0 |
| 异词 | 1,190 | 2 | 1,188 | 0 |
| 自对 | 35 | 2 | 33 | 0 |

无候选，保存 4 个尝试和 4 份独立输入诊断，均为 `MISSING_APPROVAL_BUNDLE`；诊断不是曲线通过。续跑前后全部 **32 文件 SHA 不变**。当前代码 SHA `66ad34ae22b633f1956edd5abdf0e0dded6bed3274f29cbdaf65aeef908b67c8`，身份 SHA `184918f52da32f087bb63841f7e1e98cf844a812b4525d3e075b8494601f566c`，完整模型／政策／环境身份在新运行 manifest。CLI 返回 0 只表示命令完成。

## 最终验收清单与未通过项

已执行 `final_acceptance_check.py`，退出 0。机器可读清单见 `FINAL/final_acceptance_checklist.json`：15 项工程完整性检查通过，覆盖显式任务文件哈希、无额外资产修改、固定分母、候选和 journal 完整性、新旧运行及续跑哈希、当前代码身份和正式出口关闭。基线全部 7,052 条目无丢失／类型／链接差异，465 个原始模型／动作文件哈希不变；旧运行 3,378 个文件全匹配，1,225 唯一记录仍为 326 BLOCKED_ENDPOINT／386 FAILED_SEARCH／513 FAILED_QUALITY／0 PASS_SIM。899 旧候选和 1,225 复核保留。

基线归档复核退出 0：858,275,840 字节，SHA `a4c6732f38b25939e407bbbe06c57c9350f7cae98460a07052d976dfd3f29e70`。这是同环境工程完整性，不是 P2-3 新环境复现。

正式清单保持失败／未完成：真实 35 词审批与修复输入、正式质量和碰撞冻结、1,225 全 PASS、42,875 三词兼容、冻结三词／五词／重复词实际轨迹、真实人工评价、新建环境复现均未取得。采样几何不是连续碰撞证明；原词线性回放的连续导数、ASL 理解及硬件状态不由本轮代码测试证明。独立复核算法与本轮自动化由同一执行工程师运行；未参与调参的同学交叉评审仍未完成。

## 阻塞、复现、偏差与继续条件

P1-8 审计与最小复现退出 2，`MISSING_APPROVAL_BUNDLE`，完整原始错误／命令在 TASK-13。需要第二组返回真实版本绑定的 35 词核心／窗口及审核证据、修复资产或缺陷处置、质量阈值／线性导数解释、碰撞覆盖／预算批准和 NURSE f80 决定。到位后重新只读核对，完成 P1-8 正式判定代码与正负例，再用新 run_id 执行 P1-9；当前不能声明全任务完成。

主要偏差：实际聊天 cwd 是另一检出，先完整保全目标仓库再在恢复副本实施、按清单安装；只用 audit_handoff 做真实只读目录／完成状态核查（用户全局 AGENTS 与 HANDOFF 不用代理冲突已在 TASK-01 报告）；主代理负责所有修改、测试、整合。收尾增加两个必需文档下载哈希同步及一处报告舍入修正，既有项目改动完整保留。没有修改正式审核字符串、缩小分母、删碰撞对、放宽阈值或执行发布／实机。

回滚时先保留新运行证据，按任务清单逆序撤回，保全其他人的改动。最终索引同步前的完整 project_overview.py 在 `FINAL/before_compatibility/`，兼容安装前后哈希在 `TASK-14-COMPAT/changes.json`；先核对当前哈希，再仅恢复本任务内容。归档恢复到新空目录校验，不覆盖原检出。外部 .venv 符号链接不是可移植交付环境。


## 与原计划的偏差

P1-8 外部依赖导致正式全量和 P2 未执行。最终测试发现两份 docs 索引固定下载哈希陈旧，仅同步两个字面量，保留既有改动，并按新代码身份新建开发运行 002。收尾工程验收完成不等于 L2 完成。

## 回滚和最终状态

仅按本任务 changes.json 撤回本任务改动；已有文件恢复 before 副本，新增文件先另行保全，不使用 reset --hard、clean 或整目录覆盖。L2 全词对目标仍为未完成，批准材料不能由执行模型伪造。
