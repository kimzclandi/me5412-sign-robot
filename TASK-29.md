# TASK-29：换用第二组的新片段（clips-v2），重新标定保护区间

> **公开交付（2026-11-03）：** 私仓第十轮结果提交为 `ec89a7f`。本次按用户要求，以公开第九轮提交 `83dffbfc` 为基线，同步其非原始快照及 clips-v2 依赖，并保留旧结果为历史。下文“第十轮未提交”的记录已被本次状态替代；原始运行身份及其测试限制保持原样。

[English](TASK-29.en.md) · [当前状态](STATE.md) · [交接](HANDOFF.md) · [上一阶段 TASK-28](TASK-28.md)

状态：**保护表 v5 已定；第十轮在新片段上求解了九个句子，7/7 NUMERICAL_PASS。** 执行日期 2026-11-02（Asia/Shanghai）。先按用户要求只做片段复核和保护表 v5、不求解；晚上用户说开始后做了第十轮（见下文"第十轮"）。

**第二组在 `group2/clips-v2`（`85bc230`）上发布了新的词片段，并请第三组从这个分支开新分支继续。新片段中 NURSE 是新动作，另有 23 个视频词做了碰撞修复，帧数都没变。用户看过渲染后，把 NURSE 的保护定为 f23–f79，INTERPRETER 改为 f19–f40，HAVE 和其余词沿用原区间，形成保护表 v5。第八、九轮在旧片段上的轨迹不能直接用于新片段，九个句子要在新片段上重新求解。**

仅为开发证据：不是已验证的 ASL；新片段的渲染未经第三方审阅。

## 分支

- 本分支 `group3/clips-v2` 从 `group2/clips-v2` 的 `85bc230` 创建。`85bc230` 已含第八轮的规划代码（上午发布到团队仓库、第二组合并的非原始快照）。
- 第九轮（YOU HURT WHERE，HURT 从第 37 帧开始）原来只在本地源分支 `group3/trajectory-planning` 上，已带到本分支：结果目录 `results/hospital_sentences_20261102_009/`（不含原始词对存储）、保护表 v3、策略 `fast_v6` 和序列策略 `v8`。项目记录（TASK-28、STATE、HANDOFF）把源分支的第九轮内容与发布时的改动三方合并。
- `assets/robot/vendor/` 的网格不入库，换机器时要另外复制或获取。
- `models/all-MiniLM-L6-v2/`（第一组的句向量权重，88 MB）同样不入库；缺了它 `test_learned_motion`、`test_learning_api` 会失败。

## 用户的决定（2026-11-02，按时间）

| 决定 | 落实 |
|---|---|
| 新片段只在 `group2/clips-v2` 上，从它开新分支（第二组转述） | 本分支 `group3/clips-v2` |
| 新 NURSE 保护 f23–f80，随后改为 f23–f79（f80 是最后一下点腕的第一帧，右手拇指已贴到左手腕，不要这一下） | 保护表 v4 |
| 其余碰撞修复的词：先复核旧保护区间的起止帧姿态是否一致 | 23 个词中 17 个起止帧完全相同；6 个有手指级的差别，其中句子词为 HAVE（结束帧 f54）和 INTERPRETER（起始帧 f30） |
| 渲染这两个词后重新标定：INTERPRETER f19–f40，HAVE 沿用 f24–f54 | 保护表 v5 |
| 先不做新的轨迹求解；把下一步求解要用的全部信息和文件上传到 `Kingderman/ME5412-Project` | 本分支推送到该仓库 |
| 晚上：在 `group3/clips-v2` 上用 12 个线程开始求解；不先修失败的测试；删掉 NURSE 的分阶段出口 | 第十轮（`results/hospital_sentences_20261102_010/`） |

## 保护表 v5（`config/user_protected_hospital35_v5.json`）

| 词 | v3（旧片段） | v5（clips-v2） |
|---|---|---|
| NURSE | f38–f75 | **f23–f79** |
| INTERPRETER | f30–f60 | **f19–f40** |
| HAVE | f24–f54 | f24–f54（沿用） |
| HURT | f37–f57 | f37–f57 |
| MORNING | f26–f37 | f26–f37 |
| 其余 30 个词 | 用户填写表的区间 | 不变 |

v4 由 v3 生成（替换 NURSE、24 个变化片段重新绑定哈希），v5 由 v4 生成（替换 INTERPRETER）；两者都用规划器自己的加载器在本分支的动作库上加载通过（35/35）。生成脚本、逐帧检查、对比图和说明在 [`results/clips_v2_review_20261102/`](results/clips_v2_review_20261102/README.md)。

## 下一步求解要用的内容（都在本分支）

- 代码：`src/`、`scripts/`（第八轮的规划与验证代码，本阶段没有改）；`tests/` 按新片段修过（见"测试"）。
- 片段与动作库：`motions/`（clips-v2）、`motions/hospital_v1_motions.json`。
- 保护表 v5，以及作为起点的策略 `config/transition_policy_hospital_sentences_fast_v5.json`、`config/sequence_policy_hospital_sentences_v7.json`。
- 第八轮的输入与运行脚本（[`results/hospital_sentences_20261102_008/`](results/hospital_sentences_20261102_008/README.md)：`make_inputs.py`、`run.sh`、`export_render_inputs.py`、`render_gpu_windows.py`），第九轮的单句做法（[`…_009/`](results/hospital_sentences_20261102_009/README.md)）。
- 交接步骤、NURSE 出场的重新设计要求和已知端点问题：[HANDOFF](HANDOFF.md) 顶部一节。

## 第十轮：新片段上的九个句子

[第十轮](results/hospital_sentences_20261102_010/README.md)于 18:31–20:18 运行，cpu0–11 上 12 个词对 run，代码 `00124363` 未改。词对策略 `fast_v7` 是 `fast_v5` 换用保护表 v5、从 `staged_exits` 删掉 NURSE、并采用第九轮的加长搜索（每个词对 1800 s）；序列策略 `v9` 含七个多词句子。

- 17/17 个词对数值通过，全新复核一致；7/7 句子 NUMERICAL_PASS，全新序列复核一致；24/24 个保护核心逐位不变；中途停顿 0 次；每个句子都回到初始姿态结束。
- NURSE→BLOOD-DRAW 从 f79 直接衔接 10 帧即通过，分阶段出口不需要重新设计。NEED→INTERPRETER 在 f14 进入，HAVE 的收尾段从 f57 出发，符合端点检查的要求。
- 17 个衔接的保护核心之间总帧数：263（第八轮在旧片段上为 310）。MEDICINE→MORNING 的最小间隙正好 2.0 mm，与第八轮相同。
- 未经人工观看。按用户要求在 `00124363` 上用旧的、有失败的测试运行；测试修复 `a1eb6e53` 于 18:48 推送，正值第十轮运行期间。本次运行只能在 `00124363` 上续跑或复核。

## 还没做

- 人工观看第八、九、十轮的视频。
- 在修好的测试（`a1eb6e53` 或之后）上运行，需要用第十轮的输入再跑新的一轮。
- 提交第十轮（输入、记录和文档）；只在用户要求时进行。

## 测试

本阶段开始时全套测试为 988 passed、16 failed、18 errors，与未改动的 `85bc230`（`group2/clips-v2` 原样）逐项相同。2026-11-02 按新片段修好后：**1021 passed、1 skipped**（exit 0）。`src/`、`scripts/` 和 `config/` 都没有改。

| 原因 | 数量 | 处理 |
|---|---|---|
| 测试用的旧策略指向保护表 v1–v3，它们绑定旧片段的哈希，加载器判定作废（`STALE_USER_PROTECTION_MOTION`），之后连锁出错 | 21 | 新增 `tests/clips_v2.py`：在内存里把旧策略改绑到保护表 v5，其余字段不变，不改任何策略文件。`test_hospital35_preflight`、`test_connector_only_v4`、`test_rest_tail_v1`、`test_staged_exit_v1` 改用它；NURSE 分阶段出口的起点按 v5 改为 f79 |
| 写死了旧 NURSE 的帧号和关节 | 4 | 检查"出核心后手腕翻转"的三个测试改用旧 NURSE 片段的副本 `tests/data/NURSE_hospital_v1.npz`（23 KB，取自 git 历史，哈希 `f75945f0…`，与旧策略里记录的一致）。出口窗口测试改用新 NURSE：新片段在 f90–94 碰到关节限位，v2 规则只保留 f79、f86–90（f80–85 是右手拇指贴左手腕，间隙不够）。`test_all_pairs_pipeline`：旧研究端点在新片段上判为过期（`STALE_INPUT_HASH`）；改绑到当前片段后仍然只提议、不扫描 |
| 用原始表格重建 v1，字节对不上 | 3 | 改为检查：重建结果与已装的 v1 只差 24 个被替换片段的 `motion_sha256`（等于 v4 的绑定）以及随之变化的哈希；`--check` 报告这三份 v1 文件不同（exit 1），不改写它们 |
| 读不入库的原始运行存储 | 1 | 文件不存在时跳过（即那 1 个 skipped） |
| 第一组的学习模块 | 5 | 不是代码问题：本机新检出缺 MiniLM 句向量权重 `models/all-MiniLM-L6-v2/`（不入库，88 MB）。从原检出复制后通过，测试没改 |

第十轮在 `00124363` 上运行，早于此次修复（18:48 推送，正值第十轮运行期间），所以它的代码哈希包含旧测试；要在修好的测试上运行需要新的一轮。

## 未验证限制

- 自身间隙为逐帧采样，不是连续碰撞证明；接触判断用规划器的碰撞范围与 2 mm 门槛。
- 新片段的手势含义未经认证；保护区间是用户按渲染标定的。
