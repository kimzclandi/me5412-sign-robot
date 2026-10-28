# 第三组：衔接规划器第二轮

**中文** · [English](transition-planner.en.md)

本轮在 `group3/transition-planner` 的 `bded331`（原起点 `2656412`）上修改现有规划器。九个脚本句子和 THANK-YOU 已在本地重新生成。19 个过渡中 **13 个 PASS、2 个 source_collision、4 个 FAILED**；三种状态互斥，`accepted_count` 为 PASS 加 source_collision。source_collision 仍含源姿态穿透，FAILED 轨迹只保留诊断用途。BREATHE-DEEP 和 THANK-YOU 是无过渡的单词句，零次检查不代表单词动作完成碰撞验收。

## 启动与本地产物

在仓库根目录使用现有 `.venv` 和 vendor 软链接顺序运行。以下设置保持一个重进程、最多三条线程，运行前需确认 MemAvailable 至少 2 GiB：

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export LP_NUM_THREADS=1 MESA_GLTHREAD=false
.venv/bin/python scripts/plan_transitions.py --all
MUJOCO_GL=egl .venv/bin/python scripts/evaluate_planned_transitions.py --render-comparison
.venv/bin/python -m pytest -q tests/test_plan_transitions.py
.venv/bin/python -m pytest -q
```

评估器默认写入 `results/planned_transitions/you_hurt_where_baseline_vs_planned_v2.mp4`，并复制到 `/workspace/you_hurt_where_baseline_vs_planned_v2.mp4`；可用 `--copy-to` 改变复制路径。macOS 去掉 `MUJOCO_GL=egl`，本轮未在 macOS 验证。`--help` 列出参数。单句预览使用独立报告名，以免覆盖十句总报告：

```bash
MUJOCO_GL=egl .venv/bin/python scripts/plan_transitions.py YOU HURT WHERE --render --report results/planned_transitions/you_hurt_where_preview.json
```

轨迹仍写入 `results/mocap_previews/planned_sentence_<GLOSSES>.npz`，字段仍是 `timestamps_s`、`joint_names`、`positions`。本地报告、日志、下沉数据和视频位于 `results/planned_transitions/`：[JSON](../results/planned_transitions/report.json)、[中文表格](../results/planned_transitions/report.md)、[英文表格](../results/planned_transitions/report.en.md)、[规划日志](../results/planned_transitions/planner_round2_output.txt)、[v2 视频](../results/planned_transitions/you_hurt_where_baseline_vs_planned_v2.mp4)。这些生成文件已加入忽略规则；新检出工作区需先重新生成，之后本地链接才有效。即使某些过渡 FAILED，规划器仍会在写出诊断轨迹后返回 0，应读取报告状态。

## 协议

- 先读医院动作映射，再按基线的 ready/poor 规则读 mocap/video 索引。中间词保留包含两端的 `sign_frames`；首词保留第 0 帧起手，末词保留回到中立姿态。过渡端点逐值等于前词 `sign_frames[1]` 和后词 `sign_frames[0]`，源单词不重采样、不修改。
- 每条直连和每条 via 腿使用 `s(u)=10u³−15u⁴+6u⁵`。时长为 `max(限速所需最短时长, 0.3 s)`，按 30 fps 向上取整数间隔：每腿至少 9 个间隔，双腿 via 至少 0.6 s。连续速度峰值为 `1.875 × |Δq| / T`。手臂限速仍为 15 rad/s，手指为 10 rad/s，包括耦合手指；耦合关节不是独立驱动器。
- `load_model` / `apply_frame` 检查每个输出过渡采样（含端点），使用上游碰撞几何体和既有同手邻接排除规则。绝对失败阈值仍是 **`contact.dist < -0.002 m`**；允许 2 mm 穿透，不保证正的 2 mm 间隙。null 表示没有接触记录，不是测得正间距。没有修改碰撞掩码、限速或阈值；帧间连续碰撞未验证。
- 若端点低于 -2 mm，只有当整条过渡的最小接触距离不小于两个端点距离的较小值时，才标为 **source_collision**。无接触记录的端点不会降低下限。内部更差的碰撞必须由同一相对规则下的 via 修复，否则 FAILED。`clearance.passed` 仍表示绝对阈值检查，过渡 `status` 表示相对分类。
- 碰撞失败时固定尝试 `out`、`up`、`forward`、`out+up`、`out+forward`、`up+forward`、`out+up+forward` 七个方向。每个方向从端点关节姿态中点的腕部目标移动 6.5 cm，组合向量归一化。由已有肩部偏移和脚部几何确认机器人 +Y 向左、+X 向前、+Z 向上；向外对左手是 +Y，对右手是 -Y。调用现有 `G1Retargeter.solve_arms` 有界 IK，每个候选从同一中点开始，软约束掌向和肘部。只有手臂变化；手指和其他坐标保持端点凸组合中点。关节限位可能使腕部未完全到达目标。
- 每个候选的两条完整最小 jerk 腿都检查碰撞。在通过候选中选择最小接触距离最大的一个，固定方向顺序用于平局；无接触记录优先，但报告仍保留 null。记录 `via_direction`、全部尝试、端点距离、选中轨迹的最差碰撞体对及 `distance_m`。没有候选通过时输出穿透最小的 FAILED via。
- 腕部低于较低端点的检查仍是独立外观检查。直连已通过碰撞时，可用同一搜索消除下沉；若没有 via 同时通过高度和碰撞，则保留直连并写 WARNING。碰撞要求使用 via 时，以碰撞分类和间隙排序优先，残余下沉单列报告。

交给第二组的列表包含每个碰撞端点的单词、`sign_frames` 的零基源帧、碰撞体对和带符号 `distance_m`，也包含 FAILED 过渡的坏端点。每句及去重后的总报告均保留。本轮共有 NURSE 帧 24、DOCTOR 帧 89 的 8 条碰撞体对记录；源动作未改动。

## 结果与验证

两个 source_collision 是 NOW→NURSE（端点下限 **-0.032892744 m**）和 DOCTOR→COME（**-0.007854003 m**），各自整条路径等于端点下限。七个方向全部尝试后仍失败的四段为：

| 过渡 | 选中方向 | 最差碰撞体对 | distance_m |
|---|---|---|---:|
| MEDICINE→MORNING | out+up | left_wrist_yaw_link / torso_link | -0.047320147 |
| NURSE→BLOOD-DRAW | up | R_thumb_proximal / fixed_mount | -0.040771353 |
| COME→SOON | out | R_index_proximal / left_wrist_yaw_link | -0.025966885 |
| NEED→INTERPRETER | out+up | L_thumb_distal / left_hip_roll_link | -0.034908732 |

这些候选仍有明显穿透，不能作为执行轨迹；固定搜索没有解决所有过渡。

保存的 NPZ 会再次检查端点逐值一致、采样限速、每腿最短时长和碰撞分类。JSON 还记录输入 SHA-256 与运行时版本。句子时长按帧数 / 30；过渡和每腿时长按间隔数 / 30。对照视频上排基线、下排规划，左列正面、右列右侧，按原始 30 fps 播放；较短的一行保持最后一帧，不做时间拉伸。YOU HURT WHERE 基线 **9.400 s**，规划 **9.033 s**，两个规划过渡均 PASS。

YOU→BUY 选择 up via；右腕相对较低端点的下沉由 **0.849769 mm 降为零**，肘部两者均为零，端点固定高度差造成的 8.059297 mm 下降保留。YOU 源动作内部腕部和肘部峰值到结束帧的下降仍分别为 **234.348952 mm**、**54.821335 mm**。完整数值见本地 [you_buy_sag.json](../results/planned_transitions/you_buy_sag.json)。历史基线端点与当前源文件约有 1e-8 rad 差异；新规划端点逐值一致。

衔接测试 **38 项通过**，比第一轮增加 13 项。本沙箱未修改的全仓基线为 **286 passed、8 failed、23 errors**：5 项缺少 `sentence_transformers`，1 项是已有项目概览失败，另 2 项失败和 23 项错误源于禁止创建 socket。修改后全仓为 **299 passed、8 failed、23 errors**，**新增失败和错误均为零**。修改前后日志及[失败集合比较](../results/planned_transitions/pytest_round2_summary.json)保留在本地；没有可调用的宿主机测试环境，没有使用绕过参数、跳过失败或修补缺失依赖。这些开发检查不代表冻结独立评审。动力学、硬件执行、ASL 含义、真人可理解性仍未验证；源单词本身的限速/碰撞保留，整句峰值另行记录。

## Git 交接

`.gitignore` 已排除 planned NPZ/MP4、`results/planned_transitions/` 和对照视频。由于工作树 Git index 位于只读文件系统，本轮 `git rm --cached` 失败。忽略规则不会自动取消既有追踪；foreman 应在宿主机运行以下命令，`--cached` 保留所有磁盘文件：

```bash
git rm -r --cached -- 'results/mocap_previews/planned_sentence_*.npz' results/planned_transitions/ results/you_hurt_where_baseline_vs_planned.mp4
git add .gitignore src/sign_robot/transitions.py scripts/plan_transitions.py scripts/evaluate_planned_transitions.py tests/test_plan_transitions.py docs/transition-planner.md docs/transition-planner.en.md
git commit -m "feat(group3): add IK via search and source collision handoff"
```

当前所有变更保持未暂存；没有提交或推送，没有删除文件。`motions/`、`retarget.py`、`ACTION_IDS`、原基线片段、vendor 软链接、`.venv` 和 `_scratch/` 不属于本次修改。
