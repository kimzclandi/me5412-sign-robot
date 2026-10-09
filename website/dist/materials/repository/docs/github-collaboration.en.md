# GitHub collaboration: six task branches, checked PRs, then merge

[中文](github-collaboration.md) · **English** · [Documentation index](README.md)

Repository: <https://github.com/kimzclandi/me5412-sign-robot>. Default branch: **`master`**. All commands below use it.

Start each task from latest `master`, edit/commit/push to a task branch, then request integration review through a PR. `master` holds the integrated version. Prefer a small PR per acceptable milestone. Freeze final mainline before delivery; do not wait for all six people before the first integration.

## 1. Branches and ownership

Suggested names, not yet assigned to real GitHub accounts:

| Person | First branch | Scope |
|---|---|---|
| 1: intent/text data | `feat/semantic-data-v1` | Ten meanings, paraphrases, development examples, sources. |
| 2: selection | `feat/semantic-selector-v1` | `language.py`, embedding config, language checks. |
| 3: motion data/mapping | `feat/motion-data-v1` | Demonstration processing, shared retargeting, versioned trajectories/manifests. |
| 4: learning | `feat/motion-learning-v2` | Conditional model, training scripts, separate weights/reports. |
| 5: integration/evaluation | `feat/integration-v1` | Interfaces, registry, backend, independent tests/reproduction. |
| 6: presentation | `feat/demo-v1` | `web/`, exports, static display, presentation. |

After merging a first task, branch from updated `master` using a new version such as `feat/semantic-selector-v2`. Person 5 manages shared interfaces/catalog merges. Person 1 proposes catalog changes through a PR; others build against the merged catalog. Coordinate overlapping files and merge order.

Read [implementation guide](ten-intent-learning-guide.en.md) and [dependencies](code-dependencies.en.md): selection emits valid `action_id`, motion generates by ID, and presentation reads acceptance and trajectory/video versions.

## 2. Access, clone, environment

This is private. Each teammate signs into their own GitHub account, accepts the owner's invitation, and needs write access to push same-repository branches. A link alone grants no access. Invitations have not been sent here.

Beginners can use GitHub Desktop: `File → Clone repository → URL`. Follow [README](../README.en.md) for environment/assets; Python/MuJoCo is primarily tested on Mac.

```bash
git clone https://github.com/kimzclandi/me5412-sign-robot.git
cd me5412-sign-robot
git switch master
git pull --ff-only origin master
git switch -c feat/semantic-selector-v1
```

The final line is person 2's example. Use your own branch. Authenticate through Desktop or configured Git credentials; never put passwords/tokens in files, example commands, or PRs.

## 3. Edit, commit, push your branch

Check the current branch before editing. Inspect changes and stage only your files:

```bash
git branch --show-current
git status
git diff
git add src/sign_robot/language.py config/embedding.json tests/test_language.py
git commit -m "Improve semantic selection for ten intents"
git push -u origin feat/semantic-selector-v1
```

This is a language-team example; stage only files actually changed. Later commits followed by `git push` update the same PR. Desktop: update `master` → New Branch → edit → review selected Changes → Commit → Publish branch/Push origin.

Keep existing ignores for environments, large third-party weights/vendor meshes, machine config, and session logs. Versioned checkpoints/trajectories follow project agreements, sizes, and data licenses. New experiments use new directories and retain old weights/results.

## 4. Open a PR

Select the branch → Compare & pull request, or Pull requests → New pull request.

- Base **`master`**; compare your task branch.
- Use a Draft PR for incomplete work/interfaces needed by others; state what remains.
- When acceptable, mark ready and document behavior, commands, actual checks, and unverified scope.
- Request person 5/upstream/downstream review where permissions allow; use actual account assignments.

Use the bilingual template. Explain the concrete improvement, interface changes, execution, evidence, dependencies, and remaining issues. Example title: `Add ID-conditioned motion generation v2`; describe data, output format, engineering checks, and independent evaluation rather than “optimized.”

## 5. Synchronize latest master before merge

Use a clean worktree; first commit changes you need to preserve:

```bash
git fetch origin
git switch feat/semantic-selector-v1
git merge origin/master
```

This merges mainline into your task branch for compatibility checks. For conflicts, inspect both versions and agree with relevant owners, then stage every resolved file, commit, and push:

```bash
git add src/sign_robot/language.py
git commit
git push
```

Do not blindly choose all “ours” or “theirs.” If unresolved, `git merge --abort` returns to pre-merge state. Desktop: Fetch origin → Branch → Merge into current branch → `origin/master` or updated local `master` → resolve → commit/push. Merge synchronization is sufficient; no history rewriting/force-push is needed.

## 6. Review and merge

Person 5 coordinates; an authorized maintainer merges. At least one other teammate checks changes/run records; involve affected owners for interfaces/motion.

- Files changed should match scope.
- Check shared IDs, joint formats, and model versions.
- Run relevant checks: selection/rejection for language, generation/constraints for motion, end-to-end demonstration for integration.
- Wait for automated checks if configured. Otherwise record manual validation explicitly; do not claim CI passed.
- Missing resources/models mean a check was not run, not passed.

For repository-wide verification with prepared assets:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/verify_assets.py
```

New experiments also need their independent evaluation. Code checks do not validate ASL understanding. After review, conflict resolution, and current-version checks, select **Squash and merge**. Merge prerequisite interfaces first, synchronize/check downstream branches, then merge them.

Delete completed remote branches if desired. Start subsequent tasks from updated `master`, avoiding further commits on an already-squashed old branch.

## 7. Everyone updates; next tasks get new branches

```bash
git switch master
git pull --ff-only origin master
git switch -c feat/semantic-selector-v2
```

People with ongoing work stay on their branches and synchronize as in step 5. Suggested order: catalog/interfaces → independent selection/data modules → learning → complete integration → presentation. Independent PRs can merge earlier. Person 6 can submit the presentation framework early and connect new models later.

This is a team convention, not evidence that enforced branch protection or CI exists. The owner may configure those separately.

## Prompt for each teammate's agent

> Read AGENTS.md, docs/ten-intent-learning-guide.en.md, and docs/github-collaboration.en.md first. Check the current branch/worktree. Create my task branch from latest master and change only relevant files. Follow existing interfaces, record actual checks/failures, commit/push the branch, then create a PR targeting master. Do not merge the PR yourself; team integration coordinates review. Propose and coordinate shared-interface changes. Preserve existing models/historical experiments through separate new versions. Provide Chinese and English documentation together.

## Official references

- [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow).
- [Desktop branches](https://docs.github.com/en/desktop/making-changes-in-a-branch/managing-branches-in-github-desktop).
- [Desktop PR creation](https://docs.github.com/en/desktop/working-with-your-remote-repository-on-github-or-github-enterprise/creating-an-issue-or-pull-request-from-github-desktop).
- [Merge methods](https://docs.github.com/en/pull-requests/reference/pull-request-merges).
