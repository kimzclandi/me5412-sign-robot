# 从公开手语视频提取动作（第二组）

**中文** · [English](video-retargeting.en.md) · [动作捕捉方法](mocap-retargeting.md) · [交接说明](group2-handoff.md)

医院词表的 35 个词里，26 个在 Studio Galt 动作捕捉库中没有。原计划的 SignAvatars 需要本人填表申请，时间来不及，所以改为从公开的 ASL 词典视频中提取动作（2026-10-27）。

## 流程与每层输入输出

| 步骤 | 脚本 | 输入 | 输出 |
|---|---|---|---|
| 1. 下载视频 | `scripts/video/fetch_wlasl_videos.py` | WLASL v0.3 索引（C-UDA，学术用途） | `data/video/wlasl/raw/<词>/<video_id>.mp4`（**只存本地，不入库**）；`data/video/wlasl/manifest.json` 记录链接、来源、哈希 |
| 2. 提取关键点 | `scripts/video/extract_video_landmarks.py` | 视频 | 每帧身体 33 点、双手各 21 点的 3D 坐标（米），存于本地 `raw/landmarks/` |
| 3. 转成机器人动作 | `scripts/video/retarget_video.py <词> --render` | 关键点 | 每段视频一个候选 `motions/wlasl_video_v1/candidates/`；自动选出最佳的一段作为 `motions/wlasl_video_v1/<词>.npz/.json`；对照视频在 `results/video_previews/` |
| 4. 索引 | `scripts/video/build_video_index.py` | 选中的动作 | `motions/wlasl_video_v1/index.json`，字段与动作捕捉词库相同 |
| 5. 总览 | `scripts/video/render_video_overview.py` | 索引 | `results/video_previews/overview.png` |

之后运行 `scripts/mocap/build_hospital_motions.py` 更新医院词表对照：**同一个词优先用动作捕捉版本，没有才用视频版本**。

```bash
.venv/bin/python scripts/video/fetch_wlasl_videos.py            # 默认：缺的 26 词 + 6 个对照词
.venv/bin/python scripts/video/extract_video_landmarks.py
MUJOCO_GL=egl PYTHONPATH=scripts/mocap .venv/bin/python scripts/video/retarget_video.py HURT --render
.venv/bin/python scripts/video/build_video_index.py
.venv/bin/python scripts/mocap/build_hospital_motions.py
```

需要 `pip install mediapipe` 和 `models/mediapipe/` 下的两个官方模型（`pose_landmarker_heavy.task`、`hand_landmarker.task`，Google，Apache-2.0，从 `storage.googleapis.com/mediapipe-models` 下载）。

## 视频来源

- 只用 WLASL 收录的单人、正面拍摄的词典视频：StartASL、Spread The Sign、ASL Deafined、SignSchool、ASL Bricks。不用 YouTube；Signing Savvy、Handspeak 已无法下载。
- 每个词下载 2～4 段，共 32 个词（26 个缺的 + YOU、COME、TAKE、HELLO、PLEASE、WHERE 用于和动作捕捉对比）。
- **版权**：视频属于各网站，只在本地分析，不放进仓库；仓库里只有链接、哈希和最终的机器人关节轨迹。

## 方法

- **关键点**：MediaPipe PoseLandmarker（重型模型）给出肩、肘、腕的 3D 世界坐标；HandLandmarker 给出每只手 21 个点，平移到对应手腕上。左右手按图像中离哪个手腕近来分配（MediaPipe 自带的左右手标签假设是镜像自拍画面，不可靠）。
- **清洗**：去掉肘、腕置信度低于 0.5 的帧，以及上臂或前臂长度偏离中位数超过 40% 的帧，再线性插值补齐，最后用 Savitzky–Golay 滤波（约 0.2 秒窗口）平滑。手没识别到的帧同样插值。
- **手指**：视频里有真正的指尖位置，所以手指弯曲直接按“手腕→指根→各关节→指尖”的夹角之和计算。
- **转成机器人动作**：和动作捕捉词完全相同的映射、避碰和首尾中立姿势。**两只手臂用同一个缩放比例**：视频估计的左右臂长度常常不一样（朝向摄像头的手臂看起来更短，最多相差 1.9 倍），会让一只手的动作被放大，例如 MEDICINE 的左手一度飞到头顶。人的双臂是对称的，透视只会让手臂变短，所以取两侧中较长一侧逐帧长度的第 90 百分位数作为臂长。
- **关节滤波与限速**：从视频估计的拇指旋转和手部朝向会突然翻转（例如 HURT 的拇指一度达到 37.7 rad/s，左手腕在 4 帧内从 1.97 转到 −1.32）。视频词的关节角先做 5 帧中值滤波去掉短暂的跳变，再把手指关节限速 10 rad/s、手臂关节限速 15 rad/s。HURT 本身的手腕扭转动作保留。动作捕捉词不受影响。
- **选视频**：每个词的几段视频都转换一遍，在主手识别率不低于 50% 的视频里选打手语阶段误差最小的一段（之前按识别率优先，MEDICINE 选中了误差 22 cm 的视频，而另一段只有 3 cm）。所有候选都保留在 `candidates/` 里，选择过程记在 JSON 的 `selected_from`。

## 结果

- 32 个词全部转换成功，35 个医院用词全部有动作（9 个来自动作捕捉，26 个来自视频）。
- 视频词最高只评“近似”，不评“可用”：单个摄像头估计不出可靠的前后深度，手指细节也比动作捕捉粗。
- 和动作捕捉对比（YOU、COME 等）：动作方向和位置一致，但抖动更多；开头结尾双手放在腰前，而不是自然下垂。
- 误差数字偏大（部分词超过 10 cm），主要来自开头结尾手放在腰前、机器人的胯部挡住，以及视频估计的抖动。分级以看对照图为主。
- 抽查过的例子：THANK-YOU（手从下巴向前）、NO、SORRY、YES、WAIT、ME、NIGHT、MEDICINE（手在胸前的掌心里画圈）、HEADACHE（双手到额头高度，因为机器人脖子短，看起来比头还高）。

## 限制

- 前后深度来自单个摄像头的估计，是最不可靠的方向。
- 手指细节、手型比动作捕捉粗；手被挡住或移出画面时靠插值。
- 不同视频的打手语者、速度、取景不同，词与词之间风格不完全一致。
- 视频来源的 ASL 动作本身未经本组核实；机器人动作未经 ASL 使用者评审。
