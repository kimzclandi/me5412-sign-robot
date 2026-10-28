# 第三组：衔接规划器，第七轮

**中文** · [English](transition-planner.en.md)

本轮从 `group3/transition-planner @ 2c3aea4` 增加通用的**源收回 / 目标接近**回退（在 direct / via1 / via2 / hub 之后），把 ≥9.5 mm 的间隙显示为 `>=9.5`，并保持运动对 2 mm 门槛与原厂结构缝分列。九个脚本句子加 THANK-YOU 已重新规划：**19 段 = 16 PASS、2 source_near、1 FAILED**。MEDICINE→MORNING 走到收回/接近后因切片内库动作碰撞失败，故未运行 RRT。BREATHE-DEEP 和 THANK-YOU 是单词句，零次过渡检查不代表单词本身无碰撞。

## 静态配对如何推导

`MujocoClearance` 首次构造时只读 `motions/hospital_v1_motions.json` 及其全部 35 个动作的所有帧（共 4485 帧），跨文件累计每个关节的最大 / 最小值。跨度严格大于 **1e-9 rad** 的关节视为运动关节；再并入规划器实际使用的 `retarget.ARM_SUFFIXES` 双臂 IK 关节。库中没有证据的未知模型关节保守视为运动，不会静默免检。当前模型得到 **38 个运动关节**；已确认恒定的 12 个腿部关节和 3 个腰部关节维持模型 qpos0。

对每个 body 沿 `body_parentid` 走到 world，收集沿途及自身的运动关节 ID。`derive_static_body_pairs(model, moving_joint_ids)` 比较两体的运动祖先集合：**集合相等，等价于两体之间的运动学路径上没有运动关节，才是静态对**。整个过程由模型拓扑与动作数据计算，没有手写体对名单。当前推导出 **136 个不同 body 的静态对**，不含手臂、手腕、手指或手部 body。`fixed_mount` 与左右 `hip_pitch_link` 属于静态对；腕部与基座仍是运动对，即使基座自身固定。

构造时在恒定姿态临时扩大 `mj_collision` 的 geom / 显式 pair 检测 margin 至覆盖场景，保留原生过滤和同手排除，再用 **`mj_geomDistance`** 对检测到的静态 geom 对逐一测量，按 geom 对去重。这样不依赖大 margin 下可能较粗的 mesh 接触距离。当前 **47 个原生有效 geom 对**记录为 `vendor_structural_gaps`（原厂结构缝），含 `bodies`、`geoms`、`geom_ids`、`distance_m`、`distance_mm`。其中：

| 原厂结构缝 | 距离 mm |
|---|---:|
| fixed_mount / left_hip_pitch_link | +0.701651 |
| fixed_mount / right_hip_pitch_link | +0.719230 |

136 是拓扑体对数，47 是通过原生碰撞过滤后实际测量的 geom 对数，二者不是同一计数。完整清单及推导来源在总报告和句子报告中，所选过渡与各次 clearance 结果也保留清单。几何、掩码和 MJCF 均未永久编辑；`prepare_robot.py` 未修改。

## 运动配对的距离与搜索规则

统一使用有符号距离：**正值分离，负值穿透**。`PENETRATION_TOLERANCE_M = 0.002`、`ENDPOINT_NEAR_M = 0.002`、手臂 **15 rad/s**、手指 **10 rad/s** 全部不变。

| 运动配对端点分类 | 全路径及 hub 各腿条件 | 通过状态 |
|---|---|---|
| 两端最小间隙均 ≥ 2 mm | 最小间隙 ≥ +2 mm | PASS |
| 任一端点最小间隙严格 < 2 mm | 最小间隙 ≥ 两端较小的间隙 | source_near |
| 全部候选未满足对应条件 | 保留最小间隙最大的已检查候选供诊断 | FAILED |

恰好 2 mm 不算 near。FAILED 也保留 `source_near=true` 端点标志；`source_near_count` 只计相对通过的段。`clearance.passed` 仍表示运动对的绝对 +2 mm 检查，near 段应同时读取 `status` 和 `relative_floor_passed`。`min_distance_m`、`closest_pair` / `worst_collision`、`endpoint_clearances_mm` 和 handoff 均不混入静态间隙。

运动配对继续使用 R4 的数值查询：从 2 mm、1 cm、5 cm、25 cm 逐级扩大检测 margin，必要时覆盖场景；只有检测到有效**运动对**才能停止扩展，静态接触不会让查询提前返回。读取 `contact.dist`，每次在 `finally` 恢复 geom / pair margin；原生 MuJoCo 配对过滤和既有同手指 / 腕排除不变。分离姿态也返回有限数值和最近体 / geom 对；空轨迹或没有有效运动对的模型报错。规划姿态若改变被分类为恒定的关节，会显式拒绝该失效分类。

搜索按 **direct → via1/via2 → qpos0 hub → 源收回/目标接近** 升级，near 端点不截断。全部 via 失败后检查 hub；hub 仍失败则拼接源词 `sign_frames[1]` 之后的收回与目标词 `sign_frames[0]` 之前的接近（中性点不一致时用最小 jerk 桥接），整段按时限伸缩并保留 0.3 s 下限。通过条件为全路径最小间隙 ≥ 较差端点；切片内碰撞则报告库帧与配对并停止，不进 RRT。本轮 MEDICINE 为切片内失败，故未实现/运行 RRT。≥9.5 mm 显示为 `>=9.5`（`clearance_capped`）。通过的 direct 如有腕部下垂可额外搜索 via，只有高度与距离均通过才替换；纯高度搜索不升级 hub。全部失败仍保留最佳诊断路线。

via1 / via2 保留通用的双臂偏移、中立手臂退让和左右串行退让候选，不按词身份做特例。IK 只解手臂，手指和其他坐标保留端点凸插值；耦合关节不是独立驱动。每腿采用 `s(u)=10u³−15u⁴+6u⁵`，按连续峰值 `1.875 × |Δq| / T` 向上取整到 30 fps，至少 **0.3 s / 九个间隔**。源词不修改或重采样，内部词使用含端点的 sign_frames；首词保留第 0 帧起势、末词保留回中立，过渡端点逐位相同。

## 本轮结果与交接

| 段 | 状态 / 方法 | 运动对端点间隙 mm | 运动对全路径最小 mm | 时长 s |
|---|---|---|---:|---:|
| MEDICINE → MORNING | FAILED / retract_approach | −0.809260 / +9.434433 | −67.599238 | 2.500 |
| NOW → NURSE | source_near / direct | +8.813409 / −32.846892 | −32.846892 | 0.300 |
| DOCTOR → COME | source_near / direct | −7.853912 / >=9.5 | −7.853912 | 0.300 |
| NURSE → BLOOD-DRAW | PASS / via2 | +5.952892 / >=9.5 | +5.952892 | 1.000 |
| COME → SOON | PASS / via2 | >=9.5 / +5.476825 | +5.476825 | 0.900 |

**MEDICINE → MORNING 依次检查了 direct、via1/via2、hub，以及收回/接近 (c)。** 相对下限仍为 −0.809260 mm。(c) 使用 MEDICINE 收回帧 **119–159** 与 MORNING 接近帧 **0–35**，在中性点拼接并按时限伸缩（2.500 s）。两段切片均低于下限：收回库帧 **145**（fixed_mount / left_wrist_yaw_link，−67.599 mm）与接近库帧 **28**（R_thumb_proximal / left_wrist_yaw_link，−44.832 mm）。因切片内碰撞，**未运行 RRT**。

去重后的 `source_near_handoff` 为 **15 条运动体对记录、3 个词帧**，包含 MEDICINE 119、NURSE 24、DOCTOR 89；源动作问题继续交第二组。静态基座 / 髋部间隙不再成为 source_near 交接。十个保存 NPZ 的端点、速率、每腿时长、运动对数值间隙、状态和结构缝一致性均由 evaluate 复核。过渡最大采样速度为手臂 **14.635394 rad/s**、手指 **8.868628 rad/s**。

YOU → BUY 本轮选 `out+up` via1，右腕相对较低端点的新增下垂仍为零；源 YOU 内部腕 / 肘峰值到末帧下降 **234.348952 / 54.821335 mm** 保留。YOU HURT WHERE 规划 **9.033 s**、基线 **9.400 s**；MEDICINE MORNING NIGHT TAKE 规划 **10.267 s**、基线 **10.067 s**。句子时长是帧数 / 30，过渡和各腿时长是间隔数 / 30。

## 启动、再生成与 v4 视频

在仓库根目录使用已有 `.venv`；不安装 `sentence_transformers`。重任务顺序执行，最多三个线程、同时一个重进程，每次先确认 `MemAvailable ≥ 2 GiB`：

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export LP_NUM_THREADS=1 MESA_GLTHREAD=false MUJOCO_GL=egl
check_mem() {
  .venv/bin/python -c 'from pathlib import Path; m = int(next(s.split()[1] for s in Path("/proc/meminfo").read_text().splitlines() if s.startswith("MemAvailable:"))); assert m >= 2 * 1024**2; print("MemAvailable GiB:", m / 1024**2)'
}
check_mem && .venv/bin/python scripts/plan_transitions.py --all
check_mem && .venv/bin/python scripts/evaluate_planned_transitions.py
check_mem && .venv/bin/python scripts/evaluate_planned_transitions.py --render-comparison --comparison-glosses YOU HURT WHERE --artifact-name you_hurt_where_baseline_vs_planned_v4 --copy-to /workspace/you_hurt_where_baseline_vs_planned_v4.mp4
check_mem && .venv/bin/python scripts/evaluate_planned_transitions.py --render-comparison --comparison-glosses MEDICINE MORNING NIGHT TAKE --artifact-name medicine_morning_baseline_vs_planned_v5 --copy-to /workspace/medicine_morning_baseline_vs_planned_v5.mp4
check_mem && .venv/bin/python -m pytest -q tests/test_plan_transitions.py
```

macOS 省略 `MUJOCO_GL=egl`；本轮未测试 macOS。`plan_transitions.py` 写报告后即使有 FAILED 也退出 0，必须读状态；evaluate 若外部复制失败会保留本地视频和报告、记录 `copy_requested` / `copy_error` 并退出 1。单句预览应指定独立 `--report`，避免覆盖十句总报告。无参数 artifact name 默认使用 v4；本任务两个名称由 `--artifact-name` 显式指定。

- [report.json](../results/planned_transitions/report.json)、[中文表](../results/planned_transitions/report.md)、[英文表](../results/planned_transitions/report.en.md)：19 段的 method、source_near、运动对端点及全路径间隙、最近体对、duration_s、status、hub 记录，以及独立原厂结构缝清单。JSON 另含全部 35 个派生输入动作的 SHA-256 和运行时版本。
- [YOU HURT WHERE v4](../results/planned_transitions/you_hurt_where_baseline_vs_planned_v4.mp4)；目标副本 `/workspace/you_hurt_where_baseline_vs_planned_v4.mp4`。
- [MEDICINE MORNING NIGHT TAKE v5](../results/planned_transitions/medicine_morning_baseline_vs_planned_v5.mp4)；目标副本 `/workspace/medicine_morning_baseline_vs_planned_v5.mp4`。FAILED 衔接保持诊断标签。
- 规划 NPZ 为 `results/mocap_previews/planned_sentence_<GLOSSES>.npz`，基线为同目录 `sentence_<GLOSSES>.npz`，契约为 timestamps_s / joint_names / positions。
- [round6 规划日志](../results/planned_transitions/planner_round7_output.txt)、[YOU HURT WHERE 复核 / 渲染日志](../results/planned_transitions/evaluate_round6_you_hurt_where.txt)、[MEDICINE 复核 / 渲染日志](../results/planned_transitions/evaluate_round7_medicine_morning.txt)。
- [round4 更新前归档](../results/planned_transitions/round4_before_round6_archive/report.json) 保留旧报告及十个规划 NPZ；此前 v1/v2/v3 视频、原始实验和失败记录均保留。

两个视频均为 `render_comparison` 输出：上排基线、下排规划，左侧正面、右侧右视图；30 fps 原速，较短一排结束后保持末帧，不做时间拉伸。输出文件、复制状态和视频元数据记录于总报告 `comparison_videos`。上述结果与视频均 gitignored，需要新 checkout 后重新生成。

## 实际测试与未验证限制

最终聚焦测试 **94 passed（2.98 s）**，见 [测试日志](../results/planned_transitions/pytest_round6_transitions_final.txt)。覆盖原有 R4 约束，以及跨文件 1e-9 运动范围、IK 运动关节并集、任意名称的拓扑推导、双侧基座 / 髋部结构缝、静态接触不主导门槛或提前结束测距、强制左腕 / 基座 1 mm 和 −3 mm 违规仍失败并尝试 hub。全量 pytest 由 foreman 在宿主机运行；本轮不宣称宿主全量通过，也未安装缺失的语意模型依赖。

两份 v4 视频已完整解码核对为 **30 fps、960×1088、282 / 308 帧**，MEDICINE 过渡第 124 个视频帧已目视确认显示 FAILED。全部 **309 个 clearance** 结果为有限数值且最近对来自运动集合；见 [产物审计](../results/planned_transitions/round6_artifact_audit.json)。第二份渲染采样记录主进程峰值 **3 线程**，重任务前可用内存均高于 2 GiB；见 [资源记录](../results/planned_transitions/medicine_morning_round6_resources.json)。

本受管沙箱的 `/workspace` 为只读，两次指定外部复制均实际被拒绝；本地视频完整，报告已记录 `copy_requested` / `copy_error`，渲染命令因复制失败退出 1。宿主机还需执行：

```bash
cp results/planned_transitions/you_hurt_where_baseline_vs_planned_v4.mp4 /workspace/you_hurt_where_baseline_vs_planned_v4.mp4
cp results/planned_transitions/medicine_morning_baseline_vs_planned_v5.mp4 /workspace/medicine_morning_baseline_vs_planned_v5.mp4
```

这是开发回归检查，不是未参与调参者执行的冻结独立评审。PASS 仅指输出采样中的运动配对达到 +2 mm；source_near 仅相对端点通过，仍可能保留明显穿透；FAILED 仅供诊断。原厂结构缝只是给定恒定关节条件下的几何报告，不能据此认证硬件结构安全。单词内部速度 / 碰撞、采样间连续碰撞、动力学、硬件执行、ASL 含义及真人可理解性均未验证。

## Git 交接

仅交付代码、脚本、测试及中英说明，不暂存生成产物；不 push，不删除文件。若只读 `.git` 阻止暂存 / 提交，变更保持未暂存，由 foreman 按 [FILE_LIST](../results/planned_transitions/FILE_LIST.txt) 在宿主机执行：

```bash
git add src/sign_robot/transitions.py scripts/plan_transitions.py scripts/evaluate_planned_transitions.py tests/test_plan_transitions.py docs/transition-planner.md docs/transition-planner.en.md
git commit -m "feat(group3): retract/approach fallback and capped clearance reporting"
```

`motions/`、`retarget.py`、`ACTION_IDS`、`scripts/prepare_robot.py`、原模型和碰撞掩码均未修改。
