# Commit / PR plan / 提交与 PR 计划

Run only after P1-3, P1-4, the retry and the final docs are done. / 仅在 P1-3、P1-4、重试与最终文档全部完成后执行。

Why later / 为何延后: `run_identity` includes the git HEAD commit; committing while any run is active stops it with
`IDENTITY_CHANGED_DURING_RUN`, and resuming a run after a commit is refused. / 运行身份包含 git HEAD；运行期间提交会使其以
`IDENTITY_CHANGED_DURING_RUN` 停止，提交后也无法续跑。

## Target / 目标（user decisions, 2026-11-01 / 用户决定）

- Push to `kimzclandi/me5412-sign-robot`, new branch `group3/trajectory-planning`, PR into `master`. The repo is PUBLIC; the
  user confirmed the public push ("Yes, push to public"). Never push to `Kingderman/ME5412-Project`.
  推送到 `kimzclandi/me5412-sign-robot` 的新分支 `group3/trajectory-planning`，PR 指向 `master`。该仓库为公开仓库，用户已确认公开推送；不要推送到 `Kingderman/ME5412-Project`。
- Account `Kingderman` has push, not admin. Merge base with master `bcdefc4`; branch +20, master +14 commits (81 files).
  The committed HEAD merges cleanly. Files changed on both sides: `README.md`, `README.en.md`, `docs/README.md`,
  `docs/README.en.md`, `src/sign_robot/project_overview.py`.
- Do not merge the PR, change visibility or create a release. / 不合并 PR、不改可见性、不创建 Release。

## Steps / 步骤

1. `.gitignore`: add `results/**/pair_runs/` (raw stores, ~1.2 GB, stay local); check `find results -type f -size +20M`.
2. Commits (each ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`):
   1. `feat(group3): hospital35 protection import, preflight, batch control, lazy sequence combinations` (src, scripts, tests, config, data ODS)
   2. `results(group3): hospital35 run evidence` (baseline, preflight, freeze, P1-1..P1-4, retry, commands; no raw stores)
   3. `results(group3): earlier user-protected rounds and sequence pilot evidence` (no raw stores)
   4. `docs: TASK-01..27, STATE, HANDOFF, PLAN, migration package, README and docs index` (bilingual)
3. `git fetch https://github.com/kimzclandi/me5412-sign-robot.git master:refs/remotes/signrobot/master`
4. `git switch -c group3/trajectory-planning`; `git merge signrobot/master`; keep both sides' rows in the five files;
   re-pin the docs index hashes in `project_overview.py`; full `pytest`.
5. `git -c credential.helper= -c credential.helper='!gh auth git-credential' push -u https://github.com/kimzclandi/me5412-sign-robot.git group3/trajectory-planning`
6. `gh pr create --repo kimzclandi/me5412-sign-robot --base master --head group3/trajectory-planning` with summary,
   results, commands, tests, unverified limits and deviations (4 parallel runs; retry alongside P1-4; crash at 12:35 and
   resume); body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
