# Migration package: hospital35 transition scan (2026-11-01)

[中文](MIGRATION.md) · **English**

For an AI agent (or a person) taking over after the unexpected crash and restart at 12:35 on 2026-11-01
(Asia/Shanghai). **Deadline: before midnight 2026-11-01.** Read this file, then `state_snapshot.json`, then the project
rules in `AGENTS.en.md`, `HANDOFF.en.md` and `TASK-27.en.md`.

> **Decision 12:49:** the user chose to hand the task to Windows (WSL2). The Ubuntu copy is retired and `resume.sh`
> refuses there; only the Windows copy continues. Start with [START_HERE.en.md](START_HERE.en.md).

## 1. Where things stand (snapshot 12:45, after the restart)

- **P1-3 (all 1,225 ordered pairs):** 46 of 79 frozen batches complete, 33 open (4 of them were mid-batch at the
  crash). Since 11:26 the open batches are split across 4 runs with one identity (`hospital35_protected_20261101_001`
  … `_004`), one writer each; remaining per run: 8 / 9 / 8 / 8 batches (`state_snapshot.json` → `remaining_by_run`).
- **Integrity after the crash:** all four run stores load and pass the store's own verification (507 / 73 / 78 / 79
  pair heads); no empty or temporary files. Locks are kernel `flock` locks and were released by the crash; the leftover
  `.lock` files are harmless.
- **Identity:** the frozen pair identity reproduces exactly on this machine after the restart (`identity.reproduces = true`).
- **Not started yet:** P1-3 final table and rechecks, P1-4 (111 sequences), the budget retry, final docs, commit/push/PR.
- Formal PASS_SIM is 0 and `formal_acceptance_enabled=false` everywhere. Nothing is committed (on purpose, see §5).

## 2. Recommended environment

**Continue on the same Ubuntu 24.04 machine. It is back up and verified, and resuming is one command (§6A).** Moving
costs time and puts the frozen identity at risk; it does not make the work faster.

| Factor | Ubuntu (this machine) | WSL2 Ubuntu 24.04 on Windows | Native Windows |
|---|---|---|---|
| Can resume the frozen runs? | **Yes** (verified) | Yes, if Python 3.12.3, identical package versions, LF line endings, same `.git` HEAD and the same path | **No.** `environment_id` hashes `platform.system()` ("Windows"), so the identity changes and the frozen runs refuse to resume; the code also imports `fcntl` (Linux-only) and fails to start |
| Recompute needed | none | none if `verify_target.sh` passes | everything: a new versioned run of all 1,225 pairs (~5–6 h on 4 fast cores) plus code changes and new tests |
| CPU speed (single-threaded MuJoCo + NumPy) | baseline | ~0–5% overhead on the same CPU | about the same per core |
| Parallel workers | 4 processes pinned to the performance cores with `taskset` | same scripts work | needs new launch scripts (no `taskset`/`pgrep`; use process affinity in PowerShell) |
| ~75,000 small JSON files | fast (ext4) | fast on the WSL ext4 disk; **very slow** under `/mnt/c` | slower: Defender scans every new file unless the folder is excluded |
| Video rendering | `MUJOCO_GL=egl` works | EGL depends on WSLg/Mesa; `osmesa` works but slowly | different GL backend (WGL) |
| Hard-coded paths | as written | create the same path `/home/kingderman/Documents/ME5412-github-latest` | `/home/kingderman/...` paths in helper scripts break |

Wall-clock planning budgets (30 s per pair) mean a slower CPU or slower cores yield fewer candidates. On a different
machine, keep one driver per **performance** core (check `cpuinfo_max_freq` in WSL) and record the CPU model in the report.

## 3. Completed (evidence under `results/hospital35_protected_20261101_001/`)

P0-1 baseline → P0-2 strict import of the 35 protected intervals → P0-3 preflight (24 of 35 cores fail non-waivable
gates in the source motion itself) → P0-4/P0-6 batch and sequence control → P0-7 freeze (962 tests passed) → P1-1 four
pairs 4/4 → P1-2 twelve sequences 12/12 with videos → P1-3 started 03:10, parallel from 11:26. Also prepared and
tested on their refusal paths: `commands/p1_3_final.sh`, `commands/p1_4.sh`, `commands/retry_budget.sh`,
`commands/after_p1_3.sh`, the retry policy `config/transition_policy_user_protected_hospital35_retry_budget_v1.json`
and its rule-based generator (dry run in `retry_budget_001/dryrun_20261101_1047/`). Full details: `TASK-27.en.md`.

## 4. Pending, in order (estimates on this machine)

| # | Task | Command | Time |
|---|---|---|---|
| 1 | Finish P1-3 (33 batches, 4 parallel runs) | `migration/windows_handoff_20261101/resume.sh` (starts 2 and 3 automatically) | ~2.5 h |
| 2 | P1-3 final: merged 1,225-row table, fresh recheck of every selection | `commands/p1_3_final.sh` (inside the chain) | ~30 min |
| 3 | P1-4: 111 sequences (≤29 can pass) on cpu0, and the budget retry on cpu1, side by side | `commands/p1_4.sh`, `commands/retry_budget.sh` (inside the chain) | ~2–4.5 h |
| 4 | Final bilingual docs: TASK-27, STATE, HANDOFF, docs index (re-pin hashes in `project_overview.py`), full pytest, comparability check (4.4 vs 4.8 GHz) | manual | ~1 h |
| 5 | Commit, merge latest `master`, push `group3/trajectory-planning` to `kimzclandi/me5412-sign-robot`, open PR | `commit_plan.md` | ~30 min |
| later | Faster scanner (new version, after the retry; approved), decision on the 24 source-blocked words, human video review, formal acceptance | — | after submission |

If time runs short: submit P1-3 + docs, mark P1-4 / retry as unfinished with their partial evidence.

## 5. Rules that must not be broken

- Do not edit `src/sign_robot/`, `tests/`, the identity scripts, `docs/README*.md` or `project_overview.py` while any
  run or sequence step is active; do not `git commit` before step 4 is done (HEAD is part of the identity).
- Never overwrite or delete runs, failures or old evidence; never reset/clean; new budgets or policies are new versions.
- Do not trim protected cores, edit source motions or relax gates. Do not label candidates as verified ASL; do not invent
  human reviews. No paid APIs, no data requests or messages.
- Push only to `kimzclandi/me5412-sign-robot` (public; confirmed by the user) on `group3/trajectory-planning`; never to
  `Kingderman/ME5412-Project`. Do not merge PRs, change visibility or create releases.
- All docs and pages in Chinese and English, kept in sync.

## 6. Recovery instructions

### A. Same Ubuntu machine (recommended)

```bash
cd /home/kingderman/Documents/ME5412-github-latest
bash migration/windows_handoff_20261101/resume.sh
```

It refuses if a driver already runs, clears the stop files, restarts the 4 runs (completed batches are skipped), then
starts the chain that waits for them. Progress: `results/hospital35_protected_20261101_001/P1-3_parallel_*.log`,
`after_p1_3.log`, `P1-4.log`, `retry_budget_001.log`. Graceful stop of the scan:
`for n in 1 2 3 4; do touch results/hospital35_protected_20261101_001/batch_control/hospital35_protected_20261101_00$n.stop; done`.

### B. Windows machine via WSL2 (only if this machine cannot be used)

1. Source machine: `bash migration/windows_handoff_20261101/pack.sh` → `~/ME5412_migration_20261101.tar.zst` + `.sha256`
   (whole tree incl. `.git` and raw `pair_runs`; excludes `.venv`). Copy both files to Windows.
2. Windows: `wsl --install -d Ubuntu-24.04`; create the user `kingderman`; in WSL:
   `sudo apt install -y python3-venv zstd libegl1 libosmesa6`.
3. In WSL (not under `/mnt/c`): `mkdir -p /home/kingderman/Documents/ME5412-github-latest`, check the archive with
   `sha256sum -c`, then `tar -I zstd -xpf ME5412_migration_20261101.tar.zst -C /home/kingderman/Documents/ME5412-github-latest`.
   Do not use Git for Windows on this tree (CRLF conversion changes the code hash).
4. `python3 -m venv .venv && .venv/bin/pip install -r migration/windows_handoff_20261101/requirements-lock.txt`
   (`python3 --version` must be 3.12.3).
5. `bash migration/windows_handoff_20261101/verify_target.sh` must print `TARGET READY`. If it does not, do **not**
   resume the frozen runs; report the failing check.
6. Check which CPUs are the fast cores (`cat /sys/devices/system/cpu/cpu*/cpufreq/cpuinfo_max_freq`); if not 0–3, edit
   only the `taskset -c $w` mapping in `commands/p1_3_parallel.sh` (a results-side script, not part of the identity).
7. `bash migration/windows_handoff_20261101/resume.sh`. Rendering: if `MUJOCO_GL=egl` fails in WSL, set
   `MUJOCO_GL=osmesa` for `render_sequences.py` only.

### C. Native Windows (not recommended)

Breaks the frozen identity (system name, line endings) and needs code changes (`fcntl`, paths, launch scripts). It would
be a new code version and a new run from scratch, with tests and a new freeze; not feasible before midnight.

### Failure handling

- A run stops with a replay mismatch after the hard kill: keep that run, continue the affected batch in a new run_id
  (HANDOFF rule); record it.
- `IDENTITY_CHANGED_DURING_RUN`: something identity-covered changed; revert that change (never edit frozen code) and resume.
- A step refuses with exit 4: read its log; the guards check that P1-3 finished and the final table exists.

## 7. Execution history (2026-11-01)

| Time | Event |
|---|---|
| ~03:10 | P1-3 started in run 001 (single process) |
| 10:47 | snapshot: 27/79 batches, 393 pairs reviewed; P1-4 bound 29/111 |
| 11:24–11:26 | graceful stop; split into 4 parallel runs pinned to cpu0–3 |
| 11:40 | chain `after_p1_3.sh` started, waiting |
| ~12:35 | **crash and restart**; all processes lost |
| 12:45 | integrity checked, identity reproduces, this package written |

## 8. Package contents

| File | Purpose |
|---|---|
| `MIGRATION.md`, `MIGRATION.en.md` | this guide |
| `state_snapshot.json` | exact batch state, runs, identities, environment, chain progress |
| `SHA256SUMS.txt` | hashes of code, config, data, docs and all evidence except raw `pair_runs` |
| `requirements-lock.txt` | exact package versions of the frozen environment |
| `snapshot_state.py` | regenerates the snapshot (new output names) |
| `pack.sh`, `verify_target.sh`, `resume.sh` | transfer, target check, resume |
| `commit_plan.md` | commit, merge, push and PR steps with the user's decisions |

## 9. Unverified limits

The WSL2 path has not been tried; `verify_target.sh` and `resume.sh` were syntax-checked, not run on a target. Time
estimates assume this CPU. Results of runs 002–004 were produced at ~4.4 GHz instead of ~4.8 GHz; comparability is
checked in step 4. TIMEOUT is not a proof that no connector exists.
