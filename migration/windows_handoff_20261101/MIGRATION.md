# 迁移包：hospital35 衔接扫描（2026-11-01）

**中文** · [English](MIGRATION.en.md)

供 2026-11-01 12:35（Asia/Shanghai）意外崩溃并重启后接手的 AI agent（或人员）使用。**截止时间：2026-11-01 午夜前。**
请先读本文件，再读 `state_snapshot.json`，然后是项目规则 `AGENTS.md`、`HANDOFF.md` 与 `TASK-27.md`。

> **12:49 决定：** 用户选择把任务移交给 Windows（WSL2）。Ubuntu 上的副本已停用，`resume.sh` 在那里会拒绝运行；只有 Windows 上的副本继续。
> 请从 [START_HERE.md](START_HERE.md) 开始。

## 1. 当前状态（重启后 12:45 快照）

- **P1-3（全部 1,225 个有序词对）：** 79 个冻结批次中 46 个完成，33 个未完成（其中 4 个在崩溃时处于批次中途）。自 11:26 起，
  未完成批次分给 4 个同身份 run（`hospital35_protected_20261101_001` … `_004`），每个 run 一个写入者；各 run 剩余 8 / 9 / 8 / 8 批
  （`state_snapshot.json` → `remaining_by_run`）。
- **崩溃后的完整性：** 4 个 run 存储均可加载并通过存储自身的校验（词对记录 507 / 73 / 78 / 79）；没有空文件或临时文件。锁是内核
  `flock`，崩溃时已释放，残留的 `.lock` 文件无害。
- **身份：** 重启后在本机冻结的词对身份完全复现（`identity.reproduces = true`）。
- **尚未开始：** P1-3 最终表与复核、P1-4（111 条序列）、预算重试、最终文档、提交/推送/PR。
- 正式 PASS_SIM 为 0，`formal_acceptance_enabled=false`。尚未提交任何内容（有意如此，见第 5 节）。

## 2. 推荐环境

**继续在同一台 Ubuntu 24.04 机器上运行。它已恢复且已核对，续跑只需一条命令（6A）。** 迁移耗时并会危及冻结身份，并不会更快。

| 因素 | Ubuntu（本机） | Windows 上的 WSL2 Ubuntu 24.04 | 原生 Windows |
|---|---|---|---|
| 能否续跑冻结的 run | **能**（已核对） | 能，前提是 Python 3.12.3、包版本完全相同、LF 换行、相同 `.git` HEAD 与相同路径 | **不能。** `environment_id` 包含 `platform.system()`（"Windows"），身份改变，冻结 run 拒绝续跑；代码还导入仅限 Linux 的 `fcntl`，无法启动 |
| 是否需要重算 | 不需要 | `verify_target.sh` 通过则不需要 | 全部：新版本 run 重跑 1,225 对（4 个快核约 5–6 小时），另需改代码与新增测试 |
| CPU 速度（单线程 MuJoCo + NumPy） | 基准 | 同一 CPU 上约 0–5% 开销 | 每核大致相同 |
| 并行 | 4 个进程用 `taskset` 绑定性能核 | 同一脚本可用 | 需新的启动脚本（无 `taskset`/`pgrep`，需在 PowerShell 设置亲和性） |
| 约 75,000 个小 JSON 文件 | 快（ext4） | 在 WSL 的 ext4 磁盘上快；在 `/mnt/c` 下**很慢** | 较慢：除非排除该目录，Defender 会扫描每个新文件 |
| 视频渲染 | `MUJOCO_GL=egl` 可用 | EGL 取决于 WSLg/Mesa；`osmesa` 可用但慢 | 不同的 GL 后端（WGL） |
| 写死的路径 | 原样可用 | 建立相同路径 `/home/kingderman/Documents/ME5412-github-latest` | 辅助脚本中的 `/home/kingderman/...` 路径失效 |

规划使用墙钟预算（每对 30 s），CPU 或核心越慢，候选越少。换机器时仍按每个**性能核**一个驱动（在 WSL 中查看
`cpuinfo_max_freq`），并在报告中记录 CPU 型号。

## 3. 已完成（证据位于 `results/hospital35_protected_20261101_001/`）

P0-1 现场快照 → P0-2 严格导入 35 个保护区间 → P0-3 预检（35 个保护核心中有 24 个在源动作本身违反不可豁免门槛）→
P0-4/P0-6 批次与序列控制 → P0-7 冻结（962 项测试通过）→ P1-1 四对 4/4 → P1-2 十二条序列 12/12 及视频 → P1-3 于 03:10 开始，
11:26 起并行。另已准备并实测拒绝路径：`commands/p1_3_final.sh`、`commands/p1_4.sh`、`commands/retry_budget.sh`、
`commands/after_p1_3.sh`、重试政策 `config/transition_policy_user_protected_hospital35_retry_budget_v1.json` 及按规则生成定义的脚本
（试运行在 `retry_budget_001/dryrun_20261101_1047/`）。详情见 `TASK-27.md`。

## 4. 待办（按顺序；本机估时）

| # | 任务 | 命令 | 时间 |
|---|---|---|---|
| 1 | 完成 P1-3（33 批，4 个并行 run） | `migration/windows_handoff_20261101/resume.sh`（自动接续 2、3） | 约 2.5 小时 |
| 2 | P1-3 最终：合并的 1,225 行表、对全部选中候选的全新复核 | `commands/p1_3_final.sh`（在链中） | 约 30 分钟 |
| 3 | P1-4：111 条序列（最多 29 条可通过，cpu0）与预算重试（cpu1）并行 | `commands/p1_4.sh`、`commands/retry_budget.sh`（在链中） | 约 2–4.5 小时 |
| 4 | 最终双语文档：TASK-27、STATE、HANDOFF、文档索引（在 `project_overview.py` 中重新固定哈希）、全套 pytest、可比性检查（4.4 与 4.8 GHz） | 手动 | 约 1 小时 |
| 5 | 提交，合并最新 `master`，把 `group3/trajectory-planning` 推送到 `kimzclandi/me5412-sign-robot` 并创建 PR | `commit_plan.md` | 约 30 分钟 |
| 之后 | 更快的扫描器（新版本，重试之后；已批准）、24 个源动作受阻词的决定、人工观看视频、正式验收 | — | 提交之后 |

若时间不足：先提交 P1-3 与文档，把 P1-4／重试标为未完成，并附上已有部分证据。

## 5. 不可违反的规则

- 任何 run 或序列步骤运行期间，不得修改 `src/sign_robot/`、`tests/`、身份脚本、`docs/README*.md` 或 `project_overview.py`；
  第 4 步完成前不得 `git commit`（HEAD 属于身份）。
- 不覆盖或删除 run、失败与旧证据；不 reset/clean；新预算或新政策必须是新版本。
- 不裁剪保护核心、不改源动作、不放宽门槛。不把候选标为已验证 ASL；不编造人工评审。不使用付费 API，不提交数据申请或发送消息。
- 只推送到 `kimzclandi/me5412-sign-robot`（公开仓库，用户已确认）的 `group3/trajectory-planning`；绝不推送到
  `Kingderman/ME5412-Project`。不合并 PR、不改可见性、不创建 Release。
- 所有文档与网页保持中英双语同步。

## 6. 恢复步骤

### A. 同一台 Ubuntu 机器（推荐）

```bash
cd /home/kingderman/Documents/ME5412-github-latest
bash migration/windows_handoff_20261101/resume.sh
```

若已有驱动在运行则拒绝；它会清除 stop 文件、重启 4 个 run（已完成批次会跳过），再启动等待它们结束的后续链。进度：
`results/hospital35_protected_20261101_001/P1-3_parallel_*.log`、`after_p1_3.log`、`P1-4.log`、`retry_budget_001.log`。平稳停止扫描：
`for n in 1 2 3 4; do touch results/hospital35_protected_20261101_001/batch_control/hospital35_protected_20261101_00$n.stop; done`。

### B. 通过 WSL2 使用 Windows 机器（仅当本机无法使用时）

1. 源机器：`bash migration/windows_handoff_20261101/pack.sh` → `~/ME5412_migration_20261101.tar.zst` 与 `.sha256`（整个目录，
   含 `.git` 与原始 `pair_runs`；不含 `.venv`）。把两个文件复制到 Windows。
2. Windows：`wsl --install -d Ubuntu-24.04`；创建用户 `kingderman`；在 WSL 中：`sudo apt install -y python3-venv zstd libegl1 libosmesa6`。
3. 在 WSL 中（不要在 `/mnt/c` 下）：`mkdir -p /home/kingderman/Documents/ME5412-github-latest`，用 `sha256sum -c` 核对压缩包，再
   `tar -I zstd -xpf ME5412_migration_20261101.tar.zst -C /home/kingderman/Documents/ME5412-github-latest`。不要用 Git for Windows
   处理此目录（CRLF 转换会改变代码哈希）。
4. `python3 -m venv .venv && .venv/bin/pip install -r migration/windows_handoff_20261101/requirements-lock.txt`（`python3 --version`
   必须为 3.12.3）。
5. `bash migration/windows_handoff_20261101/verify_target.sh` 必须输出 `TARGET READY`；否则**不要**续跑冻结的 run，报告失败的检查项。
6. 查看哪些 CPU 是快核（`cat /sys/devices/system/cpu/cpu*/cpufreq/cpuinfo_max_freq`）；若不是 0–3，只修改
   `commands/p1_3_parallel.sh` 中的 `taskset -c $w` 映射（结果侧脚本，不属于身份）。
7. `bash migration/windows_handoff_20261101/resume.sh`。渲染：若 WSL 中 `MUJOCO_GL=egl` 失败，仅对 `render_sequences.py` 设置
   `MUJOCO_GL=osmesa`。

### C. 原生 Windows（不推荐）

会破坏冻结身份（系统名、换行符），并需要改代码（`fcntl`、路径、启动脚本）。这将是新代码版本与从头开始的新 run，需要测试与重新冻结；
午夜前不可行。

### 故障处理

- 强制中断后某 run 因重放不一致而停止：保留该 run，把受影响批次放到新 run_id 中继续（HANDOFF 规则），并记录。
- `IDENTITY_CHANGED_DURING_RUN`：有身份覆盖的文件被改动；撤回该改动（绝不修改冻结代码）后续跑。
- 某步骤以 exit 4 拒绝：查看其日志；守卫会检查 P1-3 是否完成、最终表是否存在。

## 7. 执行历史（2026-11-01）

| 时间 | 事件 |
|---|---|
| 约 03:10 | P1-3 在 run 001 中开始（单进程） |
| 10:47 | 快照：27/79 批，已复核 393 对；P1-4 上限 29/111 |
| 11:24–11:26 | 平稳停止；拆为 4 个并行 run，绑定 cpu0–3 |
| 11:40 | 后续链 `after_p1_3.sh` 启动并等待 |
| 约 12:35 | **崩溃并重启**；所有进程丢失 |
| 12:45 | 核对完整性，身份复现，编写本迁移包 |

## 8. 迁移包内容

| 文件 | 用途 |
|---|---|
| `MIGRATION.md`、`MIGRATION.en.md` | 本指南 |
| `state_snapshot.json` | 准确的批次状态、run、身份、环境与后续链进度 |
| `SHA256SUMS.txt` | 代码、配置、数据、文档及除原始 `pair_runs` 外全部证据的哈希 |
| `requirements-lock.txt` | 冻结环境的精确包版本 |
| `snapshot_state.py` | 重新生成快照（使用新的输出文件名） |
| `pack.sh`、`verify_target.sh`、`resume.sh` | 打包传输、目标核对、续跑 |
| `commit_plan.md` | 提交、合并、推送与 PR 步骤及用户决定 |

## 9. 未验证限制

WSL2 路径尚未实际尝试；`verify_target.sh` 与 `resume.sh` 只做了语法检查，未在目标机器上运行。估时以本机 CPU 为准。run 002–004 的结果
在约 4.4 GHz 而非约 4.8 GHz 下产生，可比性在第 4 步检查。TIMEOUT 不能证明不存在衔接。
