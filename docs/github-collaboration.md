# GitHub 分支协作：六人各自开发，PR 检查后合并

**中文** · [English](github-collaboration.en.md) · [说明目录](README.md)

仓库：<https://github.com/kimzclandi/me5412-sign-robot>。默认分支是 **`master`**，下面的命令均使用这个名字。

每个人从最新 `master` 建自己的任务分支，修改、提交并推送到该分支，通过 Pull Request（PR）交集成人员检查后合并。`master` 保存当前已集成的版本。

建议每完成一个可验收阶段就开一个小 PR，合并后再开始下一阶段。最终交付前冻结 `master`；不要等六个人全部完成才第一次集成。

**1. 六人分支与文件边界**

以下是建议分支名称，组员领取任务后自行创建，尚未绑定真实 GitHub 账号。

| 人员 | 建议首个分支 | 工作范围 |
|---|---|---|
| 1：关键词基线 | `feat/keyword-baseline-v1` | 关键词实现、文本开发样例、基线测试 |
| 2：语义理解 | `feat/semantic-selector-v1` | MiniLM、改写与拒绝、共同文字评估 |
| 3：示范处理 | `feat/motion-data-v1` | 手臂动作提取清洗、来源与时间坐标记录 |
| 4：机器人映射 | `feat/motion-retargeting-v1` | 关节映射、重定向、约束与含义保留检查 |
| 5：动作训练 | `feat/motion-learning-v2` | ID 条件模型、数据划分、训练与独立权重 |
| 6：推理与执行 | `feat/motion-execution-v1` | 推理接入、衔接平滑、直接回放对照，并参与训练调试 |

分支名里的版本用于区分后续任务，例如首个 PR 合并后从最新 `master` 建 `feat/semantic-selector-v2`。三组共同约定目录和接口，指定当次协调人组织公共文件审查。第 1、2 人共同提出目录变更；重叠文件先协调范围和合并顺序。UI、报告、PPT、集成与复现由全组共同承担。

先读 [六人实施指南](ten-intent-learning-guide.md) 和 [当前代码依赖图](code-dependencies.md)。语意组输出合法 `action_id`；动作组按 ID 生成轨迹；第三组接入推理与执行，全组共同展示接受状态和轨迹／视频版本。

**2. 第一次准备：账号权限、克隆和环境**

这是私有仓库。每位同学需要登录自己的 GitHub 账号、接受仓库所有者发出的协作邀请，并具备写入权限，才能在同一仓库推送分支。只转发链接不会授予权限。这里没有替大家发送邀请。

新手可以用 GitHub Desktop 登录自己的账号，使用 `File → Clone repository → URL` 克隆上述仓库。开发环境安装按 [README](../README.md) 的资源复现步骤进行；当前 Python/MuJoCo 流程主要在 Mac 上验证。

命令行方式：

```bash
git clone https://github.com/kimzclandi/me5412-sign-robot.git
cd me5412-sign-robot
git switch master
git pull --ff-only origin master
git switch -c feat/semantic-selector-v1
```

最后一行是第 2 人的示例，其他人换成自己的任务分支。私有仓库身份验证可以由 GitHub Desktop 或已配置的 Git 凭据完成；不要把密码或 token 写进文件、命令示例或 PR。

**3. 在自己的分支修改、提交和推送**

每次修改前检查当前分支。提交前查看变更，只加入自己负责的文件。

```bash
git branch --show-current
git status
git diff
git add src/sign_robot/language.py config/embedding.json tests/test_language.py
git commit -m "Improve semantic selection for ten intents"
git push -u origin feat/semantic-selector-v1
```

这是语言组示例；只对实际修改的文件执行 `git add`。完成第一次推送后，继续在同一分支提交，再执行 `git push`，同一个 PR 会自动包含新的提交。

GitHub Desktop 的对应流程是：切换到 `master` 并拉取最新版本 → `New Branch` 建任务分支 → 修改文件 → 在 Changes 中检查勾选的文件 → `Commit` → `Publish branch` / `Push origin`。

虚拟环境、第三方大权重/机器人 vendor 网格、本机配置和临时会话日志沿用项目忽略规则。训练检查点与轨迹是否入库，要按项目约定、文件大小和实际数据许可处理。实验使用新版本目录，旧模型和旧记录保留。

**4. 到 GitHub 开 PR**

打开仓库，选择自己的分支，点击 `Compare & pull request`，或者进入 Pull requests → New pull request。

- `base` 选 **`master`**，`compare` 选自己的任务分支。
- 未完成但需要上下游看接口时，开 Draft PR，并写明哪些部分未完成。
- 可验收后转为正式 PR，填写变更、运行方式、实际检查结果和未验证部分。
- 有权限时指定当次协调人或上下游同学审查。人员账号以实际名单为准。

仓库提供了 PR 模板。至少说明：本 PR 改善什么；输入输出是否变化；如何运行；实际验证了什么；依赖哪个 PR；剩余问题是什么。

本项目 PR 示例：`Add ID-conditioned motion generation v2`。描述中应说明使用了哪些数据、模型输出格式、工程检查和独立评价，不用一句“已优化”代替证据。

**5. 合并前把最新 master 同步到自己的分支**

在工作区没有未提交变更时执行；先提交需要保留的修改。

```bash
git fetch origin
git switch feat/semantic-selector-v1
git merge origin/master
```

这里是把最新主线合进你的任务分支，方便你在分支上检查兼容性。

若发生冲突，Git 会指出文件。在编辑器里逐段检查两个版本，与相关负责人确认最终内容，然后：

```bash
git add src/sign_robot/language.py
git commit
git push
```

上面只示范一个冲突文件，所有冲突文件都要完成处理。不要直接选择全部“自己的版本”或全部“别人的版本”。暂时无法处理时，可以执行 `git merge --abort` 返回合并前状态，再和负责人协调。

GitHub Desktop 可先 Fetch origin，在自己的分支中用 `Branch → Merge into current branch` 选择 `origin/master` 或已更新的本地 `master`，检查冲突并提交、推送。新手优先采用合并同步，无需为了本项目改写分支历史或强制推送。

**6. 集成人员检查并合并 PR**

建议由当次协调人组织审查，并由具备权限的负责人合并。至少一个其他同学检查改动和运行记录；接口或动作涉及上下游时请相应负责人参与。

- 检查 Files changed 中是否只有本任务需要的变更。
- 检查共同编号、关节格式和模型版本是否一致。
- 根据修改内容运行相关检查。语言模块查语意识别与拒绝，动作模块查生成与约束，集成模块查完整演示。
- 有自动检查时等待通过；未配置自动检查时，以明确的手动验证记录为依据，不能写成 CI 已通过。
- 模型/资源缺失导致未运行的项目，要写清楚，不能算测试通过。

需要全仓验证且环境与资源已准备时，现有命令是：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/verify_assets.py
```

新实验还需运行相应独立评价。代码检查通过不等于手语理解已获评审。

审查意见处理完、冲突解决、当前版本检查完成后，在 GitHub PR 页面选择 **Squash and merge** 并确认，把一个阶段整理成一次主线提交。若 PR 依赖尚未合入的共同接口，先合接口 PR，再同步、检查和合入下游 PR。

合并后可以在 GitHub 点击 Delete branch 删除远端已完成任务分支。新的工作从更新后的 `master` 再开分支，避免继续在已 squash 的旧分支上提交。

**7. 合并后所有人更新，下一阶段再建分支**

```bash
git switch master
git pull --ff-only origin master
git switch -c feat/semantic-selector-v2
```

尚在开发其他任务的人继续留在自己的分支，用第 5 步同步最新主线。

推荐合并次序：公共目录和接口 → 语意识别/动作数据的独立模块 → 动作学习 → 完整接口集成 → 展示。无依赖的 PR 可以先合，不需要等六人全部结束。第三组可先用示例动作搭建训练和推理框架；全组共同及早接入演示，后续持续同步新模型。

以上审查和合并方式是团队协作约定，不代表已经启用 GitHub 的强制分支保护或自动 CI。仓库所有者可以另行配置相应规则。

**给各自 agent 的开工说明**

> 请先读取 AGENTS.md、docs/ten-intent-learning-guide.md 和 docs/github-collaboration.md，确认当前分支与工作区状态。从最新 master 建立我负责的任务分支，仅修改本任务相关文件。按现有接口开发，记录实际检查与失败，提交并推送该分支，然后创建 base 为 master 的 PR。不要自行合并 PR；由组内集成人员组织检查。公共接口变化先提出具体修改并协调。已存在的模型和历史实验另存新版本。

**官方操作参考**

- [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow)：分支、PR、审查与合并流程。
- [GitHub Desktop 分支管理](https://docs.github.com/en/desktop/making-changes-in-a-branch/managing-branches-in-github-desktop)。
- [从 GitHub Desktop 创建 PR](https://docs.github.com/en/desktop/working-with-your-remote-repository-on-github-or-github-enterprise/creating-an-issue-or-pull-request-from-github-desktop)。
- [合并方法说明](https://docs.github.com/en/pull-requests/reference/pull-request-merges)。

