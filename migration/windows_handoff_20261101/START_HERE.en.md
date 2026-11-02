# Start here (Windows takeover)

[中文](START_HERE.md) · **English**

On 2026-11-01 at 12:49 the user handed this task from the Ubuntu machine to a Windows machine. The Ubuntu copy is
retired (`resume.sh` refuses there). **Only the Windows/WSL2 copy may continue.** Deadline: before midnight 2026-11-01
(Asia/Shanghai).

## For the person

1. Copy `ME5412_migration_20261101.tar.zst` and `ME5412_migration_20261101.tar.zst.sha256` from the Ubuntu home folder
   (`/home/kingderman/`) to the Windows machine (USB drive or network copy, about 1.1 GB).
2. In PowerShell as administrator: `wsl --install -d Ubuntu-24.04`, restart if asked, and create the Linux user
   **`kingderman`** (the same name matters: scripts use `/home/kingderman/...`).
3. Open the Claude Code agent inside WSL (Ubuntu terminal, not PowerShell) and paste the prompt below.

## Prompt for the Windows agent (paste as is)

> You are taking over the ME5412 group-3 transition scan. Work inside WSL2 Ubuntu 24.04, never under `/mnt/c` and never
> with Git for Windows. The migration archive is `ME5412_migration_20261101.tar.zst` (copy it from `/mnt/c/...` into
> the WSL home first and check it with `sha256sum -c`). Extract it to `/home/kingderman/Documents/ME5412-github-latest`
> (`tar -I zstd -xpf ... -C ...`), install `python3-venv zstd libegl1 libosmesa6`, create `.venv` with Python 3.12.3 and
> `pip install -r migration/windows_handoff_20261101/requirements-lock.txt`. Then read
> `migration/windows_handoff_20261101/MIGRATION.en.md` completely and follow section 6B. Run `verify_target.sh`; continue
> only if it prints `TARGET READY`. Map the four fastest CPUs in `commands/p1_3_parallel.sh` if they are not 0–3, then run
> `resume.sh`. Follow AGENTS.en.md and the rules in MIGRATION section 5, finish the pending steps in section 4 before
> midnight, and do the commit, merge and push to `kimzclandi/me5412-sign-robot` branch `group3/trajectory-planning` only
> as described in `commit_plan.md` (run `gh auth login` in WSL first). Report actual test results and unverified limits.

## Timing

Transfer and setup take about 1–2 h; the remaining compute is about 2.5 h (scan) + 0.5 h (final table) + 2–4.5 h (P1-4
and retry in parallel) + 1 h (docs) + 0.5 h (push). If the Windows CPU has fewer fast cores, the scan takes longer; if
midnight comes close, submit P1-3 and the docs first and mark P1-4/retry unfinished (MIGRATION section 4).
