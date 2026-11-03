# group2/clips-v2 片段复核与保护表 v4（2026-11-02）

**中文** · [English](README.en.md)

仅为开发证据，不是已验证的 ASL。**本目录没有做任何轨迹求解**（用户要求先不求解），只做了片段对比、渲染和保护表。

## 背景

第二组（2026-11-02）：新的词片段只在 `group2/clips-v2`（`85bc230`）上，请从这个分支开新分支来做；NURSE 的姿势变化较大，
之前针对 NURSE 的出场设置和保护窗口需要重新调整。本分支 `group3/clips-v2` 从 `85bc230` 创建，放在单独的工作目录
`/home/kingderman/Documents/ME5412-group3-clips-v2`（原检出不动）。`assets/robot/vendor/` 的网格不入库，从原检出复制
（62 个文件，逐字节相同）；`assets/robot` 的入库文件与原分支相同。

## clips-v2 改了什么

相对第八、九轮所用的片段（`e8e025d`），35 个词里有 24 个片段变了，帧数都没变；9 个动捕词以及 WAIT、NOW 没变。

- **NURSE**：基本是新动作。127 帧中 123 帧有关节变化超过 0.05 rad，左腕 roll 最多变了 3.9 rad。
- **其余 23 个视频词**：碰撞修复，只动了少数帧。各词最大关节变化（rad）/ 变化超过 0.05 rad 的帧数：THANK-YOU 1.48/21、
  WRITE 0.84/34、YES 0.83/32、MORNING 0.75/36、NOT 0.69/23、STOMACH 0.62/20、HAVE 0.38/26、TOMORROW 0.37/11、
  HEADACHE 0.34/11、LATER 0.29/12、YOUR 0.26/5、MEDICINE 0.24/11、NO 0.21/7、DOCTOR 0.21/3、NEED 0.18/8、NIGHT 0.17/36、
  HURT 0.15/18、SOON 0.14/5、SORRY 0.12/25、INTERPRETER 0.11/6、ME 0.06/3、UNDERSTAND 0.06/1、DEAF 0.06/1
  （`clips_v2_diff.py`）。

## 新 NURSE 的检查（`nurse_check.json`）

逐帧用规划器的 `MujocoClearance` 量自身间隙（采样，不是连续碰撞证明），速度取源动作审核同样的 30 Hz 相邻帧差分。

| | 旧版 NURSE | 新版 NURSE（clips-v2） |
|---|---|---|
| 最深穿透 | −91.7 mm（f112，左手腕插进躯干） | −0.3 mm（f33，右手拇指贴着左手腕） |
| 达到速度上限的帧 | 15 帧（f29–39、f80–84，含旧的翻转） | 0 帧 |
| 间隙小于 2 mm 的帧 | 23 帧 | 25 帧：f25–33、40–43、50–51、54–55、76、78、80–85 |

新版的接触全部是右手拇指碰左手腕，即手势本身的点腕动作；左腕在 f30–74 基本停在关节限位上。图：
`NURSE_clips_v2_frames.png`（每 4 帧一格，正面与侧面）、`NURSE_clips_v2_timeline.png`（间隙与速度，灰线为旧版）。
视频不入库，在本机 `C:\Users\23971\Documents\5412\_runtime\render-out\nurse_clips_v2_162019\`（原速、3 倍慢放、新旧对比）。

## 用户的决定（对话，2026-11-02）

- **新 NURSE 保护 f23–f79**（0.77–2.63 s）。用户先给 f23–f80；f80 是最后一下点腕的第一帧（右手拇指已贴到左手腕，间隙
  0.35 mm），衔接不能从接触中的帧出发，用户选择不要这一下，改为 f79（间隙 4.24 mm）。f23 的间隙为 5.9 mm，几乎静止。
- **其余词沿用 v3 的区间**，依据下面的起止帧复核（用户没有提出修改）。
- 先不做新的轨迹求解。

## 起止帧复核（`boundary_check.json`、`boundary_detail.json`）

在 v3 区间的起始帧和结束帧上比较旧片段与新片段：关节角最大变化，以及正向运动学下任一机器人刚体原点的最大位移。

- 23 个碰撞修复的词中，17 个词的起止帧姿态完全相同（0 mm）。
- 6 个词的起止帧有差别，都是碰撞修复把插进身体的手指或手挪了出来：

| 词 | 区间 | 有差别的帧 | 手指最大位移 | 手/手臂最大位移 | 自身间隙（旧 → 新） |
|---|---|---|---|---|---|
| HAVE（句子词） | f24–54 | 结束帧 f54 | 21 mm | 6 mm（手腕约 5°） | −15.8 → −0.2 mm |
| INTERPRETER（句子词） | f30–60 | 起始帧 f30 | 10 mm | 2.5 mm | −12.9 → −0.1 mm |
| TOMORROW | f24–66 | 起始帧 f24 | 66 mm | 27 mm | −30.9 → +8.9 mm |
| YES | f18–69 | 起始帧 f18 | 64 mm | 22 mm | −32.3 → +9.2 mm |
| WRITE | f27–69 | 起始帧 f27 / 结束帧 f69 | 2 / 9 mm | 2.5 / 9 mm | −3.4 → 0.0 / −9.6 → −0.1 mm |
| SORRY | f21–168 | 结束帧 f168 | 7 mm | 4 mm | −7.3 → 0.0 mm |

- 句子词在区间内部的变化（起止帧相同）：THANK-YOU 5 帧超过 10 mm，最大 52 mm（f28，左臂离身体远了一点）；NIGHT 6 帧，
  最大 33 mm（f42）；HAVE 14 帧，最大 32 mm（f43）；UNDERSTAND、MEDICINE、DOCTOR 各 1 帧（28.5、24、19 mm）；INTERPRETER
  2 帧（最大 12.5 mm）。NEED、HURT、SOON、MORNING 的区间内完全不变（改动都在区间外）。
- 其他词区间内部：YOUR f36 一处 79 mm，ME 13 mm，LATER 20 mm；NO、DEAF、STOMACH、HEADACHE、NOT 不变。
- 图：`words_in_sentences_old_vs_new.png`（句子词）和 `other_words_old_vs_new.png`（其他词），每行依次为旧-正面、新-正面、
  旧-侧面、新-侧面。

## 保护表 v4（`config/user_protected_hospital35_v4.json`）

- 由 `make_protection_v4.py` 从 v3 生成：NURSE 换成 [23, 79]；24 个变化片段的哈希重新绑定（`rebinding.json`）；其余区间
  与 v3 完全相同。用规划器自己的加载器在本分支的动作库上加载通过（35/35 条）。
- v3（第九轮：HURT 从第 37 帧开始）从 `group3/trajectory-planning` 原样带到本分支（逐字节相同）；v1、v2 保留。

## 保护表 v5（`config/user_protected_hospital35_v5.json`）

用户看过 HAVE 和 INTERPRETER 在 clips-v2 上的渲染后（对话，2026-11-02）：**INTERPRETER 改为 f19–f40**（0.64–1.33 s，原
f30–f60），**HAVE 沿用 f24–f54**。`make_protection_v5.py` 由 v4 生成 v5，只替换 INTERPRETER 一条，并用规划器的加载器验证
（35/35）。渲染用 `word_check.py`（逐帧检查，输出 `HAVE_check.json`、`INTERPRETER_check.json`）和
`render_word_review.py`；帧表为 `HAVE_clips_v2_frames.png`、`INTERPRETER_clips_v2_frames.png`，视频只在本机
`C:\Users\23971\Documents\5412\_runtime\render-out\have_interpreter_clips_v2\`。

- INTERPRETER 新起点 f19 落在两手接触段 f17–24 内，衔接要从 f16 或更早进入；f25–27、f32–35 达到速度上限（源动作）。
- HAVE 终点 f54 在接触段 f41–56 内，f59 有接触，f61–65 达到速度上限；离开 HAVE 的衔接要从 f57 之后的干净帧出发。

## 还没做

- **没有轨迹求解**（用户要求）。七个句子都要在新片段上重新规划；NURSE 的分阶段出口是按旧姿势（左手垂在腿上）设计的，求解前
  要重新设计。
- 第九轮（YOU HURT WHERE）的结果和项目记录里的第九轮内容还在 `group3/trajectory-planning` 上，没有带到本分支；本分支的
  TASK-28、STATE、HANDOFF 是上午发布到团队仓库时的版本。
- 本目录的分析与渲染脚本（`nurse_check.py`、`boundary_check.py`、`boundary_detail.py`、`clips_v2_diff.py`、
  `render_nurse_review.py`、`render_boundary_compare.py`）是在临时目录里运行的，路径写死为本机，保存在这里作方法记录；
  旧片段取自原分支 `group3/trajectory-planning`。

## 复现

```bash
cd /home/kingderman/Documents/ME5412-group3-clips-v2
/home/kingderman/Documents/ME5412-github-latest/.venv/bin/python results/clips_v2_review_20261102/make_protection_v4.py   # 只在文件不存在时写入
```
