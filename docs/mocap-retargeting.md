# 动作捕捉到 G1 的重定向（第二组）

**中文** · [English](mocap-retargeting.en.md) · [说明目录](README.md)

第二组把第一组选定的 Studio Galt ASL 动作捕捉（FBX，CC0-1.0，固定提交 `eb9046596fffcc6e92ee91d021372961f3d4fcaa`）转换成仓库统一格式的机器人轨迹。当前已跑通 YOU 一个词，其余 26 个词尚未处理。

## 流程与每层输入输出

| 步骤 | 脚本 | 输入 | 输出 |
|---|---|---|---|
| 1. 读取 FBX | `scripts/mocap/extract_fbx_skeleton.py`（Blender 4.2 LTS 无界面运行） | `data/mocap/studio_galt_v1/raw/<词>/*.fbx` | `data/mocap/studio_galt_v1/skeleton/<词>.npz`：每帧胸、肩、肘、腕、五指 3 节骨骼的世界位置与朝向，源帧率 |
| 2. 重定向 | `scripts/mocap/retarget_to_g1.py --word <词>` | 第 1 步结果 | `motions/studio_galt_v1/<词>.npz`：`timestamps_s[T]`、`joint_names[53]`、`positions[T,53]`，弧度，30 fps；同名 JSON 记录来源、误差与限制 |
| 3. 对照检查 | 同上加 `--render` | 第 2 步结果 | `results/mocap_previews/<词>.mp4`：人体骨架与机器人的正面／右侧对照视频 |

```bash
~/tools/blender-4.2.3-linux-x64/blender -b --factory-startup --python scripts/mocap/extract_fbx_skeleton.py -- \
  --fbx "data/mocap/studio_galt_v1/raw/YOU/SG ASL You 2025-7-22 No Mesh Full.fbx" --word YOU \
  --out data/mocap/studio_galt_v1/skeleton/YOU.npz
MUJOCO_GL=egl PYTHONPATH=scripts/mocap .venv/bin/python scripts/mocap/retarget_to_g1.py --word YOU --render
```

macOS 上把 Blender 路径换成 `/Applications/Blender.app/Contents/MacOS/Blender`，并去掉 `MUJOCO_GL=egl`。原始 FBX 不入库（`.gitignore`），由第一组的压缩包或上游仓库按固定提交恢复。

## 映射方法

- **裁剪**：Studio Galt 文件第 0 帧是 T 字绑定姿势，跳过；再按手腕速度大于 0.03 m/s 截取动作段，前后各留 0.2／0.3 秒。YOU 原文件 10 秒，有效段约 3.2 秒。
- **手臂**：每帧以双肩和颈—骨盆方向建立人体胸部坐标系（前、左、上），把手腕和肘相对同侧肩的位置按手臂长度比例（约 0.82）缩放后放到机器人肩部；每侧 7 个关节用有界最小二乘逆运动学匹配手腕位置、手部朝向，并以较低权重匹配肘部位置，同时保持与躯干的间隙、与上一帧连续。
- **手部朝向**：人和机器人都用“手腕→中指根、小指根→食指根”两条方向建立手部坐标系，因此左右手的镜像关系自动一致。
- **手指**：每根手指取“手掌→第 1→2→3 节”三个关节相对绑定姿势的旋转角之和，15°～230° 线性映射到 Inspire 单个耦合关节 0～1.7 rad；拇指弯曲映射到 pitch（上限 0.5，避免耦合关节超限），拇指越过掌心的程度映射到 yaw。
- **衔接**：动作段重采样到 30 fps，前后各加 0.8 秒平滑过渡到共同中立姿势；JSON 中 `core_frames` 标出真正的手语段，供第三组拼接时裁掉过渡。

## YOU 的检查结果

- 手腕位置误差平均 0.5 mm、最大 2.9 mm；手部朝向误差最大 0.004 rad；无关节越界。
- 对照视频中，食指向前指出、其余三指握拳的手型与人体骨架一致。
- 已知差异：人体手肘弯曲更多，机器人手臂更直；手指闭合最快 13.7 rad/s，来自人体真实速度，真实 Inspire 手可能达不到，需第三组衔接时限速。

## 限制

- Inspire 手指不能张开或并拢，V、3 等手型无法再现（TWO、THREE 会走样）。
- 手指弯曲范围为固定常数，未按每个动作或演示者标定。
- 躯干、头部和面部动作未迁移；机器人基座固定。
- 按各自肩部缩放不保证双手接触、手碰身体等接触关系（BUY、CLEAN、COOK、BOOK 需另行处理）。
- 未经 ASL 使用者评审。
- ASK 使用旧骨骼命名，需要先补别名表。
