# 从这里开始（Windows 接手）

**中文** · [English](START_HERE.en.md)

2026-11-01 12:49，用户把本任务从 Ubuntu 机器移交给 Windows 机器。Ubuntu 上的副本已停用（`resume.sh` 在那里会拒绝运行）。
**只有 Windows/WSL2 上的副本可以继续。** 截止时间：2026-11-01 午夜前（Asia/Shanghai）。

## 给操作人员

1. 把 Ubuntu 主目录（`/home/kingderman/`）中的 `ME5412_migration_20261101.tar.zst` 和 `ME5412_migration_20261101.tar.zst.sha256`
   复制到 Windows 机器（U 盘或网络复制，约 1.1 GB）。
2. 以管理员身份打开 PowerShell：`wsl --install -d Ubuntu-24.04`，按提示重启，并创建 Linux 用户 **`kingderman`**（用户名必须相同：
   脚本使用 `/home/kingderman/...`）。
3. 在 WSL 中（Ubuntu 终端，不是 PowerShell）打开 Claude Code agent，粘贴下面的提示。

## 给 Windows agent 的提示（原样粘贴）

> 你将接手 ME5412 第三组的衔接扫描。在 WSL2 Ubuntu 24.04 中工作，不要在 `/mnt/c` 下工作，也不要用 Git for Windows。迁移压缩包为
> `ME5412_migration_20261101.tar.zst`（先从 `/mnt/c/...` 复制到 WSL 主目录，并用 `sha256sum -c` 核对）。解压到
> `/home/kingderman/Documents/ME5412-github-latest`（`tar -I zstd -xpf ... -C ...`），安装 `python3-venv zstd libegl1 libosmesa6`，
> 用 Python 3.12.3 创建 `.venv` 并执行 `pip install -r migration/windows_handoff_20261101/requirements-lock.txt`。然后完整阅读
> `migration/windows_handoff_20261101/MIGRATION.md` 并按 6B 节操作。运行 `verify_target.sh`，只有输出 `TARGET READY` 才能继续。
> 若最快的四个 CPU 不是 0–3，修改 `commands/p1_3_parallel.sh` 中的映射，再运行 `resume.sh`。遵守 AGENTS.md 与 MIGRATION 第 5 节的
> 规则，在午夜前完成第 4 节的待办；提交、合并并推送到 `kimzclandi/me5412-sign-robot` 的 `group3/trajectory-planning` 时，严格按
> `commit_plan.md` 执行（先在 WSL 中运行 `gh auth login`）。报告实际测试结果与未验证限制。

## 时间

传输与配置约 1–2 小时；剩余计算约 2.5 小时（扫描）+ 0.5 小时（最终表）+ 2–4.5 小时（P1-4 与重试并行）+ 1 小时（文档）+ 0.5 小时
（推送）。若 Windows CPU 的快核较少，扫描会更久；临近午夜时先提交 P1-3 与文档，把 P1-4／重试标为未完成（MIGRATION 第 4 节）。
