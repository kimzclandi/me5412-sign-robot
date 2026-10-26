# 第二组交接说明：示范动作 → 机器人关节轨迹

**中文** · [English](group2-handoff.en.md) · [方法细节](mocap-retargeting.md)

状态（2026-10-27）：第一组医院词表的 35 个词全部有 G1 机器人关节轨迹（见第〇节）；最初的 27 个词也已全部转换。代码、数据、视频和测试都在 PR [#5](https://github.com/kimzclandi/me5412-sign-robot/pull/5)（分支 `group2/fbx-retarget-you`），尚未合并到 `master`。

## 〇、2026-10-27 更新：第一组的 35 词医院词表

第一组改用医院场景的 35 词词表（`data/vocab/hospital_v1.json`，快照见 `data/mocap/hospital_v1_vocab_snapshot.json`），输出的是 gloss 名称而不是序号。对接文件是 **`motions/hospital_v1_motions.json`**：35 个词各自的 `motion_ready`、轨迹路径、`core_frames`、`sign_frames`、分级和说明，由 `scripts/mocap/build_hospital_motions.py` 生成。

**35 个词全部有动作（`motion_ready=true`）**：

| 来源 | 数量 | 词 |
|---|---|---|
| Studio Galt 动作捕捉 | 9 | YOU、COME、TAKE（原 27 词）；HELLO、PLEASE、APPOINTMENT、BREATHE-DEEP、BLOOD-DRAW、WHERE（从 Studio Galt 新增） |
| 公开 ASL 词典视频 + MediaPipe | 26 | THANK-YOU、SORRY、YES、NO、YOUR、ME、DEAF、DOCTOR、NURSE、INTERPRETER、MEDICINE、STOMACH、HEADACHE、HAVE、NEED、WAIT、HURT、UNDERSTAND、WRITE、NOT、NOW、SOON、LATER、TOMORROW、MORNING、NIGHT |

视频来源的 26 个词全部评为“近似”（单摄像头估计，深度和手指不如动作捕捉），方法和限制见 [video-retargeting.md](video-retargeting.md)。`hospital_v1_motions.json` 的 `library` 字段标明每个词来自哪个库。

- 新增 6 个词的分级：PLEASE、WHERE 可用；HELLO（肘关节最多弯约 120°，只能在头旁举手）、APPOINTMENT、BREATHE-DEEP、BLOOD-DRAW 近似。详见 `motions/studio_galt_v1/index.json` 的 `robot_note`。
- 原计划的 SignAvatars 需要本人申请，来不及，因此改用 WLASL 收录的公开词典视频；SignAvatars 以后拿到也可以替换质量更好的版本。
- 9 句脚本对话的词全部就绪，例如 `scripts/mocap/stitch_baseline.py YOU HURT WHERE --render` 可直接拼出 s4。
- 第一组更新 `hospital_v1.json` 的 `motion_ready` 时，以 `hospital_v1_motions.json` 为准。
- 下载这 6 个词的原始 FBX：`.venv/bin/python scripts/mocap/fetch_studio_galt.py`（固定提交、核对哈希）。

## 一、在整条流程中的位置

```
老师的句子 →【第一组】大模型 → gloss 序列，如 ["YOU", "HURT", "WHERE"]
          →【第二组，本交付】gloss → 每个词一段机器人关节轨迹（离线已做好）
          →【第三组】把几段轨迹衔接成一句 → MuJoCo 播放
```

第二组的产出是**离线做好的数据**，与操作系统无关：Linux 上生成的 `.npz` 在 Mac 上可直接使用。

## 二、交给第三组的东西

| 文件 | 内容 |
|---|---|
| `motions/hospital_v1_motions.json` | **医院演示的入口文件**。按第一组词表顺序列出 35 个 gloss，每个词：`motion_ready`、轨迹路径、`core_frames`、`sign_frames`、分级、说明、来源库 `library` |
| `motions/studio_galt_v1/index.json` | 动作捕捉词库：最初的 27 个词（`id` 1–27）加医院词表新增的 6 个（`id` 28–33） |
| `motions/wlasl_video_v1/index.json` | 视频词库：32 个词，字段相同，详见 [video-retargeting.md](video-retargeting.md) |
| `motions/studio_galt_v1/<词>.npz`、`motions/wlasl_video_v1/<词>.npz` | `timestamps_s[T]`、`joint_names[53]`、`positions[T,53]`，弧度，30 fps，与仓库原有动作同一格式，可直接用 `sign_robot.motion.apply_frame` 回放 |
| `motions/studio_galt_v1/<词>.json` | 来源 FBX 及哈希、逆运动学误差、最大关节速度、限制 |
| `scripts/mocap/stitch_baseline.py` | **最简单的拼句基线**：每个词裁到 `sign_frames`，词与词之间用固定 0.5 秒平滑过渡。可作为第三组要求的“直接播放对照” |
| `results/mocap_previews/sentence_*.mp4` | 基线拼出的整句示例视频，包括 9 句医院脚本对话 |

### 三组帧范围（每个词）

```
0 ────── core_frames[0] ── sign_frames[0] ════ 手语 ════ sign_frames[1] ── core_frames[1] ────── T-1
  中立姿势→                 手从下垂抬起                    手放回下垂                →中立姿势
  0.8 s 过渡                                                                         0.8 s 过渡
```

- 每段轨迹首尾都是**同一个中立姿势**，直接首尾相接播放不会跳变，但每个词之间机器人都会放下手。
- 拼句时建议在上一个词的 `sign_frames[1]` 和下一个词的 `sign_frames[0]` 之间做衔接；`stitch_baseline.py` 就是这样做的。
- `sign_frames` 定义：任一只手比它在该词中的最低位置高出 10 cm 以上的区间。

### 拼句示例

```bash
MUJOCO_GL=egl .venv/bin/python scripts/mocap/stitch_baseline.py YOU HURT WHERE --render   # macOS 去掉 MUJOCO_GL=egl
```

输出 `results/mocap_previews/sentence_YOU_HURT_WHERE.npz`（同一轨迹格式）和 `.mp4`。按 gloss 名称查找：先查 `hospital_v1_motions.json`（动作捕捉优先，没有再用视频），再查两个词库；都没有的词会直接报错。

### 第三组需要注意

- **关节速度**：动作捕捉词的手指和手臂最快约 25 rad/s（人体真实速度），真实 Inspire 手和 G1 手臂可能达不到；视频词已限速（手指 10、手臂 15 rad/s）。需要接近真实硬件时请统一限速。
- **基线的已知问题**：YOU 的 `sign_frames` 结尾时手已开始下落，所以 YOU→BUY 之间右臂会短暂下沉。这正是第三组衔接方法可以改进、并拿来和基线对比的地方。
- **接口未变**：`ACTION_IDS`、`data/catalog.json` 和原有三条动作没有改动；新词库独立放在 `motions/studio_galt_v1/`。接入演示时需要三组一起决定是否扩展 `ACTION_IDS`。

## 三、交给第一组的东西

- **医院词表**：大模型输出的 gloss 名称直接对应 `hospital_v1_motions.json` 里的 `gloss`。35 个词全部 `motion_ready=true`，请同步到第一组的 `data/vocab/hospital_v1.json`，否则 `demo_only` 模式只能用 YOU、COME、TAKE。
- 以下是最初 27 词版本的说明（历史，词表已换成医院用词）：
- `index.json` 的 `id` 是当时大模型应输出的序号（顺序与第一组 `recommended_vocabulary.csv` 一致）。
- 分级（只看机器人有没有还原人体动作，**不是 ASL 评审**）：
  - 可用 14 个：ASK、BAG、BIG、BOX、BRING、BUSY、CHILD、COME、COMPUTER、EQUAL、FUTURE、ONE、TAKE、YOU
  - 近似 13 个：BABY、BALL、BEFORE、BOOK、BUY、CALM、CLEAN、CLOSE、COOK、CUSTOMER、EVERYONE、THREE、TWO
  - 做不好 0 个
- 演示用的预设句子优先选“可用”的词，例如 `YOU COME`、`CHILD TAKE BOX`、`EVERYONE EQUAL`。
- 如果要加词：把同一来源（Studio Galt）的 FBX 发给第二组，按 [方法细节](mocap-retargeting.md) 的命令大约几分钟一个词。

## 四、给第二组队友看的东西（做了什么、怎么验证）

1. **先看图**：`results/mocap_previews/overview.png`，27 个词，每对左边是人体骨架、右边是机器人。
2. **再看视频**：`results/mocap_previews/<词>.mp4`，上排正面、下排右侧，左边人体、右边机器人。
3. **数据汇总**：`results/mocap_previews/summary.md`，每个词的误差、速度、穿模、双手距离。
4. **方法**：[mocap-retargeting.md](mocap-retargeting.md)，每一步的输入输出、映射方法、限制。
5. **代码**：`src/sign_robot/retarget.py`（映射算法），`scripts/mocap/`（提取、重定向、渲染、汇总、索引、拼句基线）。
6. **测试**：`tests/test_retarget.py`，全部 27 个词的格式、限位、耦合、首尾姿势、误差检查。

在自己电脑上复现（不需要 Blender，骨架数据已入库）：

```bash
git fetch origin && git switch group2/fbx-retarget-you
.venv/bin/python -m pytest -q tests/test_retarget.py
MUJOCO_GL=egl PYTHONPATH=scripts/mocap .venv/bin/python scripts/mocap/retarget_to_g1.py --word YOU --render
```

### 关键数字

- 医院词表：35/35 个词有动作（9 个动作捕捉，26 个视频提取，后者全部为“近似”）；9 句脚本对话都能拼出整句。
- 动作捕捉词库 33 个词：可用 16，近似 17，做不好 0；可用的词打手语阶段手腕误差全部 < 2 cm；穿模 ≤ 19 mm（APPOINTMENT 的手指—手腕重叠，其余 ≤ 16 mm，只统计上游模型自带的碰撞体）。
- 视频词库 32 个词：全部转换成功；关节速度 ≤ 15 rad/s。
- 全仓测试 291 项通过；唯一失败项 `test_project_overview` 在 `master` 上同样失败（文档改动后未更新网站白名单哈希），与第二组无关。

## 五、没做的、可以分给队友的

- **ASL 评审**：分级只是工程判断，没有懂 ASL 的人看过。
- **手指标定**：弯曲范围是固定常数（15°～230°），没有按词调整。
- **macOS 验证**：整套流程只在 Linux 上跑过；最终演示若在 Mac 上，需要在 Mac 上跑一遍测试和渲染。
- **`master` 上已有的测试失败**：更新网站白名单里 6 个文档的哈希，顺便把本文档和方法文档加进 `docs/README.md` 目录。
- **原始 FBX**：不入库，需要时从第一组的压缩包或 Studio Galt 仓库固定提交恢复。
