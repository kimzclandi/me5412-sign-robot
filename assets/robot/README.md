# 固定底座机器人候选

官方来源：Unitree `unitree_ros`，提交 `5994d4faef0a9cadd3287f8de0199a67eeb2a259`，模型 `g1_29dof_rev_1_0_with_inspire_hand_DFQ.urdf`。

`vendor/` 为未修改原始 URDF、59 个引用网格及官方 README/许可证，共 62 个文件（27,189,102 字节）。逐文件 URL 和 SHA-256 记录在 `upstream_manifest.json`。首次下载仅访问该固定版本的官方公开文件，没有安装 ROS、下载学习模型或申请付费资源。

`scripts/prepare_robot.py` 修复原模型的重复 `meshes/meshes` 路径，导出派生 MJCF，并添加固定支座、场景与掌部参考点。原始文件不修改。`scene.xml` 在 MuJoCo 3.15.0 实际加载：53 个标量关节、12 个 mimic 等式、0 个执行器。轨迹中腿和腰保持固定，所有 12 条手指耦合逐帧显式满足；没有把耦合关节当成独立驱动。

这是运动学回放：写 `qpos` 后调用 `mj_forward`。没有运行基于执行器的 `mj_step` 控制，不声称动力学可执行、真实机器人可跟踪或临床可用。头部与脸部不动，五指不能独立横向展开。选择合适表达仍需实际 ASL 使用者审查。

从项目根目录运行：

```sh
.venv/bin/python scripts/fetch_robot.py
.venv/bin/python scripts/prepare_robot.py
.venv/bin/python scripts/build_motions.py
.venv/bin/python scripts/render_motions.py --allow-candidate-preview
.venv/bin/python scripts/check_motion_calibration.py
.venv/bin/python -m pytest tests/test_motion.py -q
.venv/bin/mjpython scripts/play_motion.py --action HELLO --allow-candidate-preview
```

macOS 受限命令沙盒中渲染可能报 `invalid CoreGraphics connection`；本次在获得本地渲染权限后，原生 MuJoCo Renderer 成功生成了 PNG/MP4。无需把界面录屏冒充渲染结果。

动作由代理编写少量腕部目标和时间，数值 IK 求双臂姿势，平滑插值，手指按原始耦合式变化；并非从真人提取的三维数据。`motions/*.json` 记录来源、制作方法和验证范围。`PLEASE_WAIT` 当前仅 WAIT 词例近似，没有把 PLEASE 与 WAIT 随意拼接。

开发中首版 THANK_YOU 的肩关节穿入躯干，最大 4.12 cm。后续逐帧检查还发现起点太高、修正起点引入碰撞、关节插值导致中段向上绕行和起手距头部过远，五个开发版本原样保存在 `motions/development_failures/`。最后采用更窄的肩部作者约束、腕肘到躯干距离惩罚及 12 个中间腕部位姿，重新检查完整轨迹。它们是公开记录的开发修正，不是独立确认实验。最终接触扫描只覆盖原模型提供的碰撞几何，不能作为完整无碰撞或安全保证。

视频参照到机器人的阶段对照、起末掌面法向、指尖代理路径及头部间距下界记录在 `results/previews/THANK_YOU_calibration.json`。源视频由 A1 实际播放并逐帧查看，机器人坐标由正运动学计算。报告明确不将人工目标 IK 误差当作真人三维跟踪误差。当前指尖代理距头部包围盒仍有约 2.6 cm 间距下界；没有嘴部接触、微笑或真人可理解性验证。

`play_motion.py` 已在本机用 `mjpython` 实际打开原生可旋转视角的 MuJoCo viewer，完整回放 HELLO 后正常退出。加 `--loop` 可循环；这是实时 3D 轨迹回放，不是播放 MP4。
