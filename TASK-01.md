# TASK-01：P0-1 基线保全

[English](TASK-01.en.md) · [项目状态](STATE.md)

日期：2026-10-31（Asia/Shanghai）。任务 P0-1：完成。执行仓库为 `/home/kingderman/Documents/ME5412-github-latest`，分支 `codex/group3-all-pairs-v1`，HEAD `2875e499d79b7264b3fe0414318b30ca8aab1f4d`。当前聊天工作区 ME5412 是另一个检出，不在其上实施本计划。

## 修改与关键决策

- 新增 TASK-01.md、TASK-01.en.md、STATE.md、STATE.en.md，更新 docs/README.md 与 docs/README.en.md 索引，并新增独立执行证据目录 `results/group3_execution_20261031_001`。未改代码、模型、动作、政策或旧运行。
- 保全整个检出，包括 Git 元数据、未提交/未跟踪/忽略文件。归档 `/home/kingderman/.codex/visualizations/2026/10/30/01a18e26-94c1-7160-ba35-a119ee7cf0fb/group3-execution-20261031-001/baseline.tar`，SHA-256 `a4c6732f38b25939e407bbbe06c57c9350f7cae98460a07052d976dfd3f29e70`，858,275,840 字节。
- 内容清单 `/home/kingderman/.codex/visualizations/2026/10/30/01a18e26-94c1-7160-ba35-a119ee7cf0fb/group3-execution-20261031-001/baseline-content.json`：7,052 个条目，6,919 个常规文件，845,766,665 字节。清单 SHA-256 `3937cca12139306465932570bb4035cae529a806948b4e8e9d309deb42d58481`。
- 恢复演练位于 `/tmp/me5412-execution-20261031/restored-baseline`；所有条目的类型、模式、文件哈希/大小、链接目标与源一致，Git 状态一致。后续只在计划指定仓库串行实施；已通过沙箱授权创建独立证据目录。
- `.venv` 仅保全符号链接，外部目标 `/home/kingderman/Documents/Codex/2026-10-13/new-chat/me5412-sign-robot/.venv` 不是可移植环境；P2-3 仍须新建环境。

## 命令、退出码与验证

工作目录 `/home/kingderman/Documents/ME5412-github-latest`。只读命令为 `pwd`、`ls -la`、`rg --files`、`git --no-optional-locks status --short --branch`、`git log -1 --format='%H%n%s'` 及读取 AGENTS.md/PLAN.md/HANDOFF.md；命令成功。Git 输出、补丁和命令数组见 `/home/kingderman/.codex/visualizations/2026/10/30/01a18e26-94c1-7160-ba35-a119ee7cf0fb/group3-execution-20261031-001/commands.json` 及 git-*.txt / git-*.patch。

保全命令：`python3 /tmp/me5412-execution-20261031/preserve_baseline.py` 首次退出 1（统计阶段将检查点 envelope 错当 record，KeyError: status），归档及恢复已完成且保留。核对实际结构后使用 `python3 /tmp/me5412-execution-20261031/preserve_baseline.py --resume-preservation`，退出 0，未覆盖归档，恢复与源复核均无差异。最初两条 `python` 只读盘点退出 127（环境仅提供 python3），改为 python3 后成功。完整验证见 `/home/kingderman/.codex/visualizations/2026/10/30/01a18e26-94c1-7160-ba35-a119ee7cf0fb/group3-execution-20261031-001/preservation.json`、`/home/kingderman/.codex/visualizations/2026/10/30/01a18e26-94c1-7160-ba35-a119ee7cf0fb/group3-execution-20261031-001/frozen-input-check.json`，仓库证据副本见 `results/group3_execution_20261031_001/P0-1/`。

本轮实际核对 3,378 个运行文件、4 个冻结运行文件、22 个源码文件、142 个输入/模型文件、32 个摘要证据文件，大小及 SHA-256 全匹配。1,225 条唯一记录＝1,190 异词＋35 自对，899 个候选、1,225 个复核文件。326 BLOCKED_ENDPOINT、386 FAILED_SEARCH、513 FAILED_QUALITY、0 PASS_SIM。这里验证文件完整性，未重新执行几何复核或 pytest；589 passed 仍仅为历史日志。

## 偏差与回滚

目录差异已报告；未将当前 ME5412 检出误作目标。备份保存在允许写入的会话产物目录，目标写入使用明确的沙箱授权。用户全局 AGENTS 要求子代理核查，与摘要“不使用子代理”冲突；仅使用 audit_handoff 做独立只读路径与完成状态核查，未分派修改。

P0-1 范围验收通过；L2 目标未完成。按任务证据 changes.json 回滚本任务新增文件/索引，保留其他改动。恢复整个基线时先解压到新的空目录，校验 baseline-content.json；禁止覆盖原目录、reset --hard 或 clean。批准核心/窗口、质量阈值及碰撞覆盖仍待外部确认。
