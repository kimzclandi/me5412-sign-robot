# 第三组：衔接规划器交付

**中文** · [English](transition-planner.en.md)

基于 `group3/transition-planner` 的起点 `2656412`，本次新增关节空间最小 jerk 衔接与本地验收产物。10 个句子都已生成；19 个过渡中 13 个通过碰撞检查，6 个在一次中间点重试后仍为 **FAILED**。失败轨迹保留用于诊断，不可作为安全执行轨迹。单词句 `BREATHE-DEEP`、`THANK-YOU` 没有过渡，零次检查不代表整段动作通过碰撞验收。

## 运行

在仓库根目录运行，使用现有 `.venv` 和 `assets/robot/vendor` 软链接：

```bash
export PATH="$HOME/.local/bin:$PATH"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export LP_NUM_THREADS=1 MESA_GLTHREAD=false MUJOCO_GL=egl
.venv/bin/python scripts/plan_transitions.py YOU BUY BOOK
.venv/bin/python scripts/plan_transitions.py --all
.venv/bin/python scripts/evaluate_planned_transitions.py --render-comparison
.venv/bin/python scripts/plan_transitions.py YOU HURT WHERE --render --report results/planned_transitions/you_hurt_where_preview.json
.venv/bin/python -m pytest -q tests/test_plan_transitions.py
.venv/bin/python -m pytest -q
```

按顺序运行，单个渲染任务使用一个编码线程。macOS 可去掉 `MUJOCO_GL=egl`；本次没有在 macOS 验证。`--help` 有参数说明；`--out-dir` 可改变轨迹目录，`--report` 可改变报告路径。单句运行默认会更新 `report.json`，所以验收完整报告请用 `--all` 生成；单独渲染时使用示例的独立报告文件名。CLI 完成轨迹输出时返回 0，即使报告中有 FAILED；应读取报告状态，不能把进程退出码当成碰撞通过。

默认轨迹在 `results/mocap_previews/planned_sentence_<GLOSSES>.npz`，字段仍为 `timestamps_s`、`joint_names`、`positions`；`--render` 额外输出同名 MP4。原 `sentence_*.npz`、动作数据、`retarget.py`、`ACTION_IDS` 和 vendor 都保持原样。本次只做本地提交，不推送。

## 方法和边界

- 先读医院动作映射，再按动作捕捉、视频索引补全，采用与 `stitch_baseline.py` 相同的就绪/poor 过滤。输入 gloss 可用小写；未知词报错。
- 中间词保留包含两端的 `sign_frames`。首词从第 0 帧保留起手，末词一直保留回到中立姿态，和基线一致。过渡两端逐值等于前词 `sign_frames[1]` 和后词 `sign_frames[0]`；原单词切片不重采样、不改动。
- 插值为 `s(u)=10u³−15u⁴+6u⁵`。每段至少 3 个时间间隔（2 个内部采样帧），30 fps。连续速度峰值为 `1.875 × |Δq| / T`，据此取满足限速的最短整数间隔数。含 shoulder/elbow/wrist 的关节为 15 rad/s，L_/R_ 手指关节为 10 rad/s，包括被动耦合关节；没有把耦合关节当作独立驱动器。其他关节沿用原动作中的固定姿态。
- 用仓库 `load_model` / `apply_frame` 检查每一个输出过渡帧（包含端点），只用上游碰撞几何体；排除规则与 `summarize_library.py` 的同手手指/手腕网格邻接一致。按任务明确给出的判据，`contact.dist < -0.002 m` 失败，**这允许最多 2 mm 穿透，不等于正的 2 mm 空隙保证**。没有接触记录时最小接触距离记为 null，不伪造正距离。没有改碰撞掩码或放宽阈值；帧间连续碰撞未验证。
- 失败后只加一个确定的关节空间中间点：两端中点上，两侧肩俯仰减 0.35 rad、肘增加 0.15 rad，并按模型限位截断。两段都重新用最短限速五次曲线，交会处速度/加速度为零。若重试仍穿透，就输出失败中间点轨迹和原因，不继续搜索。
- 另检查腕部是否低于两端较低高度；有新增下沉时，也可以使用同一个中间点尝试消除。若原直连无碰撞而抬臂尝试没同时通过高度与碰撞检查，则保留原直连并写入 WARNING。尝试的 PASS/FAILED 和最终 PASS/FAILED 仅表示碰撞状态，高度结果单列；CLI 会打印警告。

这里只约束插入的过渡，不修复原单词内部的限速或穿模问题；完整句子的最大速度另列为 `sentence_peak_rates`。这是离线运动学候选演示，未验证动力学、硬件执行、ASL 含义或真人可理解性。软件测试不冒充独立使用者评审。

## 结果和复核

逐句计数、时长和全部失败原因见 [中文表格](../results/planned_transitions/report.md)、[原始 JSON](../results/planned_transitions/report.json)，日志见 [planner_output.txt](../results/planned_transitions/planner_output.txt)。时长统一按帧数 / 30 计算；最后时间戳则为 `(帧数−1)/30`。报告包含输入动作、模型和索引的 SHA-256，以及从已保存 NPZ 重新验证的端点和速度结果。

失败段为 `MEDICINE→MORNING`、`NOW→NURSE`、`NURSE→BLOOD-DRAW`、`DOCTOR→COME`、`COME→SOON`、`NEED→INTERPRETER`。例如 `DOCTOR→COME` 在固定起点已穿透 7.854 mm，换中间点无法改变起点；`NURSE→BLOOD-DRAW` 重试仍有 2.006 mm 穿透，因此仍失败。

`YOU→BUY` 的右腕过渡下沉（相对两端较低高度）由基线的 **0.849769 mm 降为 0**；右肘该指标两者均为 0。右肘起点到终点仍下降 8.059297 mm，属于固定两端的高度差。YOU 原单词内部峰值到结束帧的右腕下降 **234.348952 mm**、右肘下降 **54.821335 mm**，两种方案都保留；若要消除这段可见下降，需要另行允许提前截断或修改指定边界，不能声称已完成。完整高度曲线和数值见 [you_buy_sag.json](../results/planned_transitions/you_buy_sag.json)。历史基线 BUY 边界与现词库仅有约 1e-8 rad 数值差异，统计使用历史文件本身；新规划边界保持逐值一致。

对照视频见 [you_hurt_where_baseline_vs_planned.mp4](../results/planned_transitions/you_hurt_where_baseline_vs_planned.mp4)，另复制到 `/workspace/you_hurt_where_baseline_vs_planned.mp4`。上排基线、下排规划；左列正面、右列右侧。两者按原速 30 fps 播放，较短的规划在结束后保持最后一帧，不做时间拉伸。该句基线 9.400 s、规划 8.967 s，两个过渡均通过本次碰撞检查。

测试结果和修改前后失败集合比较见 [pytest_summary.json](../results/planned_transitions/pytest_summary.json)。本环境完整基线为 261 passed、8 failed、23 errors：5 项缺少 `sentence_transformers`、1 项已有 `test_project_overview` 失败，另 2 个失败与 23 个错误均因沙箱禁止创建 socket。原用户报告的 286 passed、6 failed 是另一个环境的结果。保留修改前、修改后的实际日志，以相同环境的失败集合比较判定有无新增失败。

本次新增 **25 项测试全部通过**（0.23 s）；全仓修改后为 **286 passed、8 failed、23 errors**（3.88 s），与本地修改前相比新增失败/错误均为 **0**。失败项没有跳过、修补或用绕过参数隐藏。

本地 `git add` 因 `.git/worktrees/wt-transitions/index.lock` 所在文件系统只读而失败，未创建提交；全部交付文件保持未暂存，供 foreman 在宿主机提交。没有推送。原 `.venv`、`assets/robot/vendor`、`_scratch/` 都保持原样，不属于本次交付。
