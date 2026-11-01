# 中英说明目录 / Bilingual documentation index

当前开发目标：十个固定语意 → ID 条件学习动作；目前实现仍是三类原型。先读最新六人指南及 GitHub 协作。
Current target: ten fixed intents → ID-conditioned learned motions. The implementation remains the three-class prototype. Start with the current team guide and GitHub workflow.

| 内容 / Document | 中文 | English |
|---|---|---|
| 仓库入口 / Repository entry | [中文](../README.md) | [English](../README.en.md) |
| 最新六人实施指南 / Current team guide | [中文](ten-intent-learning-guide.md) | [English](ten-intent-learning-guide.en.md) |
| GitHub 分支协作 / GitHub workflow | [中文](github-collaboration.md) | [English](github-collaboration.en.md) |
| 代码依赖 / Dependencies | [中文](code-dependencies.md) | [English](code-dependencies.en.md) |
| 第三组衔接规划：R13c-f80x NURSE:80 命名例外，PASS/PASS / Group 3 transitions: R13c-f80x named NURSE:80 exception, PASS/PASS | [中文](transition-planner.md) | [English](transition-planner.en.md) |
| 第三组任意词对衔接任务规划 / Group 3 all-pairs transition task plan | [中文](group3-all-pairs-transition-plan.md) | [English](group3-all-pairs-transition-plan.en.md) |
| 执行模型简化交接 / Concise execution-model handoff | [中文](../HANDOFF.md) | [English](../HANDOFF.en.md) |
| 执行状态与原子任务报告 / Execution state and atomic task reports | [中文](../STATE.md) | [English](../STATE.en.md) |
| P0-1 基线保全 / Baseline preservation | [中文](../TASK-01.md) | [English](../TASK-01.en.md) |
| 第三组全词对开发扫描：运行、复核与执行记录 / Group 3 all-pairs development scan | [中文](group3-all-pairs-startup.md) | [English](group3-all-pairs-startup.en.md) |
| 历史任务卡 / Historical handoff | [中文](six-person-handoff.md) | [English](six-person-handoff.en.md) |
| 实施路线 / Roadmap | [中文](实施路线.md) | [English](实施路线.en.md) |
| 学习模型 / Learned model | [中文](学习型轨迹模型.md) | [English](学习型轨迹模型.en.md) |
| 语料规模 / Corpus scale | [中文](语料规模与模型升级.md) | [English](语料规模与模型升级.en.md) |
| 来源审查 / Source review | [中文](source-review.md) | [English](source-review.en.md) |
| 视频校准 / Video calibration | [中文](video-calibration.md) | [English](video-calibration.en.md) |
| 实验与答辩 / Evaluation and defense | [中文](实验解读与答辩.md) | [English](实验解读与答辩.en.md) |
| 机器人资源 / Robot assets | [中文](../assets/robot/README.md) | [English](../assets/robot/README.en.md) |
| 静态网站 / Static website | [中文](../website/README.md) | [English](../website/README.en.md) |
| 协作规则 / Agent instructions | [中文](../AGENTS.md) | [English](../AGENTS.en.md) |
| 第三方说明 / Attribution | [中文](../THIRD_PARTY_NOTICES.txt) | [English](../THIRD_PARTY_NOTICES.en.txt) |
| v4 讲稿 / v4 speaker notes | [中文](../deliverables/course-report-v4/speaker-notes.zh-CN.txt) | [English](../deliverables/course-report-v4/speaker-notes.en.txt) |
| v4 使用说明 / v4 usage | [中文](../deliverables/course-report-v4/使用说明.txt) | [English](../deliverables/course-report-v4/README.en.txt) |
| v3 讲稿 / v3 speaker notes | [中文](../deliverables/course-report-v1/speaker-notes.zh-CN.txt) | [English](../deliverables/course-report-v1/speaker-notes.en.txt) |
| v3 使用说明 / v3 usage | [中文](../deliverables/course-report-v1/使用说明.txt) | [English](../deliverables/course-report-v1/README.en.txt) |

R13c-f80x：保留 NURSE:80，仅裁离开端 **8/79 = 10.126582278481013%**，无起点裁剪。生产入口默认严格执行 `trim_frames / core_len <= 0.10`；唯一精确帧例外为 `TRIM_CAP_EXCEPTIONS = {"NURSE": 80}`，**10.13%，待 Thomas 确认**。MEDICINE/NIGHT/HURT 无例外；移除例外后 NURSE:80 抛错。新烟测 NOW→NURSE 为 **PASS / +9.365600 mm**，NURSE→BLOOD-DRAW 为 **PASS / +3.470359 mm**，后者实际使用逐边最小跃度 RRT，时长 1 秒。248 项聚焦测试通过；启动命令、保存轨迹复查与限制见上方成对说明。

R13c-f80x: NURSE:80 trims only the departure, **8/79 = 10.126582278481013%**, with no start trim. Production defaults to strict `trim_frames / core_len <= 0.10`; the sole exact-frame exception is `TRIM_CAP_EXCEPTIONS = {"NURSE": 80}`, **10.13%, pending Thomas's confirmation**. MEDICINE/NIGHT/HURT have no exceptions; NURSE:80 raises without its exception. The new smoke gives **PASS / +9.365600 mm** for NOW→NURSE and **PASS / +3.470359 mm** for NURSE→BLOOD-DRAW; the latter actually uses minimum-jerk RRT edges for 1 s. All 248 focused tests pass; startup commands, the saved-trajectory recheck, and limitations are in the paired documentation above.

PR 模板本身双语 / The [PR template](../.github/PULL_REQUEST_TEMPLATE.md) contains both languages.

原始实验日志、JSON/NPZ、冻结协议及失败原文保留；语言版说明不改变其数值或完成状态。英文幻灯片与原中文内嵌讲稿保留，并提供英文 TXT 讲稿；历史版本不覆盖。
Raw logs, JSON/NPZ, frozen protocols and failure text are preserved. Translations do not alter numbers or completion status. Original English slides/Chinese embedded notes remain, with English TXT companions; historical versions are retained.

How2Sign 文本索引不等于动作监督；同轨迹验证不等于独立动作泛化；工程通过不等于 ASL 理解评审。
Text indexes are not motion targets; within-trajectory validation is not independent motion generalization; engineering acceptance is not ASL-user review.
