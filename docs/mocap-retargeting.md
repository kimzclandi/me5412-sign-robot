# 动作捕捉到 G1 的重定向（第二组）

**中文** · [English](mocap-retargeting.en.md) · [说明目录](README.md)

第二组把第一组选定的 Studio Galt ASL 动作捕捉（FBX，CC0-1.0，固定提交 `eb9046596fffcc6e92ee91d021372961f3d4fcaa`）转换成仓库统一格式的机器人轨迹。第一组词库的 27 个词已全部转换，分级结果见下文。

## 流程与每层输入输出

| 步骤 | 脚本 | 输入 | 输出 |
|---|---|---|---|
| 1. 读取 FBX | `scripts/mocap/extract_fbx_skeleton.py`（Blender 4.2 LTS 无界面运行） | `data/mocap/studio_galt_v1/raw/<词>/*.fbx` | `data/mocap/studio_galt_v1/skeleton/<词>.npz`：每帧胸、肩、肘、腕、五指 3 节骨骼的世界位置与朝向，源帧率 |
| 2. 重定向 | `scripts/mocap/retarget_to_g1.py --word <词>` | 第 1 步结果 | `motions/studio_galt_v1/<词>.npz`：`timestamps_s[T]`、`joint_names[53]`、`positions[T,53]`，弧度，30 fps；同名 JSON 记录来源、误差与限制 |
| 3. 对照检查 | 同上加 `--render` | 第 2 步结果 | `results/mocap_previews/<词>.mp4`：人体骨架与机器人的正面／右侧对照视频 |
| 4. 汇总 | `scripts/mocap/summarize_library.py` | 全部轨迹 | `results/mocap_previews/summary.md`：误差、速度、穿模、双手距离 |
| 5. 词库索引 | `scripts/mocap/build_library_index.py` | 全部轨迹与第一组词表 | `motions/studio_galt_v1/index.json`：序号、词、轨迹文件、`core_frames`、机器人分级 |

```bash
# 单个词
~/tools/blender-4.2.3-linux-x64/blender -b --factory-startup --python scripts/mocap/extract_fbx_skeleton.py -- \
  --fbx "data/mocap/studio_galt_v1/raw/YOU/SG ASL You 2025-7-22 No Mesh Full.fbx" --word YOU \
  --out data/mocap/studio_galt_v1/skeleton/YOU.npz
MUJOCO_GL=egl PYTHONPATH=scripts/mocap .venv/bin/python scripts/mocap/retarget_to_g1.py --word YOU --render
# 全部词完成后
MUJOCO_GL=egl .venv/bin/python scripts/mocap/summarize_library.py
.venv/bin/python scripts/mocap/build_library_index.py
```

macOS 上把 Blender 路径换成 `/Applications/Blender.app/Contents/MacOS/Blender`，并去掉 `MUJOCO_GL=egl`。骨架提取结果已入库，只重定向时不需要 Blender。原始 FBX 不入库（`.gitignore`），由第一组的压缩包或上游仓库按固定提交恢复。

## 给第一组、第三组的接口

`motions/studio_galt_v1/index.json` 是词库表的基础：序号 1–27 按第一组 `recommended_vocabulary.csv` 的顺序。每条记录含轨迹路径、时长、`core_frames` 和 `robot_status`。

- 每段轨迹首尾都是同一个中立姿势，可以直接首尾相接播放。
- `core_frames` 标出真正的手语段；拼接时可以裁掉前后 0.8 秒过渡，在相邻两个词的手语段之间自己做衔接。
- 大模型输出的序号直接对应 `id`；`robot_status` 为 `poor` 的词建议演示前换掉或人工修正。

## 映射方法

- **裁剪**：Studio Galt 每个文件第 0 帧都是 T 字绑定姿势（已检查 27 个文件），跳过；再按手腕速度大于 0.03 m/s 截取动作段，前后各留 0.2／0.3 秒。
- **骨骼命名**：2023 年的文件（ASK、APPOINTMENT）使用旧版骨骼（Bicep/Forearm/Index1 等），提取脚本按骨骼名自动识别并映射到新命名。
- **手臂**：每帧以双肩和颈—骨盆方向建立人体胸部坐标系（前、左、上），把手腕和肘相对同侧肩的位置按手臂长度比例（约 0.82）缩放后放到机器人肩部；每侧 7 个关节用有界最小二乘逆运动学匹配手腕位置、手部朝向，并以较低权重匹配肘部位置。
- **避碰**：手臂、手和手指与躯干、髋部、机器人背后的固定支架保持 1 cm 间隙；两侧前臂和手（含全部手指）之间允许接触但不允许穿入（BLOOD-DRAW 需要手碰另一侧肘窝）。每帧先求左手（避开右手上一帧的位置），再求右手（避开左手）；若两只手距离小于 2 cm，再从这个没有穿插的起点同时求解两条手臂，让双手各让一点，而不是只扭右手腕去躲。之所以必须从没有穿插的状态开始，是因为避碰惩罚只有在两只手分开时才给出有效的梯度。
- **连续性**：每个手臂关节每帧变化不超过 25 rad/s 对应的角度，防止逆运动学在关节限位附近换解，导致关节在一帧内翻转。
- **手部朝向**：人和机器人都用“手腕→中指根、小指根→食指根”两条方向建立手部坐标系，因此左右手的镜像关系自动一致。
- **手指**：每根手指取“手掌→第 1→2→3 节”三个关节相对绑定姿势的旋转角之和，15°～230° 线性映射到 Inspire 单个耦合关节 0～1.7 rad；拇指弯曲映射到 pitch（上限 0.5，避免耦合关节超限），拇指越过掌心的程度映射到 yaw。之所以用相对旋转，是因为这批 FBX 的骨骼末端不沿手指方向，按位置算会多出约 90°。
- **衔接**：动作段重采样到 30 fps，前后各加 0.8 秒平滑过渡到共同中立姿势。

## 医院词表新增的 6 个词（2026-10-27）

由 `scripts/mocap/fetch_studio_galt.py` 从固定提交下载：HELLO、PLEASE、APPOINTMENT、BREATHE-DEEP、BLOOD-DRAW、WHERE。PLEASE、WHERE 可用；其余 4 个近似（原因见 `index.json` 的 `robot_note`）。加入前臂和手指避碰后重跑全部 33 个词，原 27 个词无变差（CUSTOMER 穿模 15.6→11.5 mm）；新增词中 APPOINTMENT 还有 19 mm 的手指—手腕重叠（手指角度直接来自人体数据，不参与优化）。

## 27 个词的结果

分级依据：总览图 `results/mocap_previews/overview.png`、每个词的对照图和视频，以及 `summary.md` 中的数值。这只是机器人动作是否还原了人体动作的工程判断，**不是 ASL 使用者评审**。

| 分级 | 数量 | 词 |
|---|---|---|
| 可用：动作、位置和手型与人体一致 | 14 | ASK、BAG、BIG、BOX、BRING、BUSY、CHILD、COME、COMPUTER、EQUAL、FUTURE、ONE、TAKE、YOU |
| 近似：能认出来，但有已知的机器人限制 | 13 | 双手接触只能做到“碰到”：BALL、BOOK、BUY、CALM、CLEAN、CLOSE、COOK、EVERYONE；双手交叠时手太大、朝向偏差约 0.7–0.8 rad：BABY、BEFORE；手靠近胸口时显得靠近脸：CUSTOMER；手指不能张开：TWO、THREE |
| 做不好：演示前需要修正或换词 | 0 | — |

- 打手语阶段（手抬到最低点以上 10 cm 的帧）的手腕误差：可用的词全部低于 2 cm，其中 12 个低于 3 mm。
- 穿模：所有词最深不超过 16 mm（CUSTOMER）（只统计上游模型自带的碰撞体，不含同一只手相邻零件的网格重叠）。
- 手臂下垂的开头和结尾，手腕与人体目标差 2～3 cm：人的手垂得比机器人胯部还低，机器人够过去会碰到腿。

## 限制

- Inspire 手指不能张开或并拢，V、3 等手型无法再现。
- 手指弯曲范围为固定常数，未按每个动作或演示者标定。
- 躯干、头部和面部动作未迁移；机器人基座固定。机器人脖子短，人体靠近脸的位置在机器人上会更靠近头。
- 机器人的手比人手大得多；双手接触的词只能做到碰到，不能完全贴合。
- 手指闭合最快约 25 rad/s（人体真实速度），真实 Inspire 手可能达不到，需第三组衔接时限速。
- 未经 ASL 使用者评审。
