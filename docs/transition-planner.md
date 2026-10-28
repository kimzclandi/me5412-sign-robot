# 第三组：衔接规划器，第四轮

**中文** · [English](transition-planner.en.md)

本轮在 `group3/transition-planner` 的 `3eccb06`（原起点 `2656412`）上实现 **`ENDPOINT_NEAR_M = 0.002`、near-source 完整搜索和数值间隙**。九个脚本句子加 THANK-YOU 已重新生成并复核：**19 段 = 0 PASS、18 source_near、1 FAILED**。三个状态互斥；`accepted_count` 为 PASS 加 source_near，仅表示满足相应规划条件的数量。BREATHE-DEEP 和 THANK-YOU 是单词句，过渡数为零，不获得单词自身的碰撞认证。

零个普通 PASS 的原因是数值测距发现所有边界姿态都包含保留的 `fixed_mount` / `left_hip_pitch_link` 约 **+0.701652 mm** 间隙，小于 2 mm。没有排除此体或任何其他 geom。18 段只满足相对端点条件，不能宣称具有绝对 +2 mm 间隙。

## 启动、再生成与本地产物

在仓库根目录使用已有 `.venv`，不安装 `sentence_transformers`。所有重任务顺序执行，每次先确认 `MemAvailable ≥ 2 GiB`；最多三个线程、同时只有一个重进程：

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export LP_NUM_THREADS=1 MESA_GLTHREAD=false MUJOCO_GL=egl
check_mem() {
  .venv/bin/python -c 'from pathlib import Path; m = int(next(s.split()[1] for s in Path("/proc/meminfo").read_text().splitlines() if s.startswith("MemAvailable:"))); assert m >= 2 * 1024**2; print("MemAvailable GiB:", m / 1024**2)'
}
check_mem && .venv/bin/python scripts/plan_transitions.py --all
check_mem && .venv/bin/python scripts/evaluate_planned_transitions.py
check_mem && .venv/bin/python scripts/evaluate_planned_transitions.py --render-comparison --comparison-glosses YOU HURT WHERE --artifact-name you_hurt_where_baseline_vs_planned_v3 --copy-to /workspace/you_hurt_where_baseline_vs_planned_v3.mp4
check_mem && .venv/bin/python scripts/evaluate_planned_transitions.py --render-comparison --comparison-glosses MEDICINE MORNING NIGHT TAKE --artifact-name medicine_morning_baseline_vs_planned_v3 --copy-to /workspace/medicine_morning_baseline_vs_planned_v3.mp4
check_mem && .venv/bin/python -m pytest -q tests/test_plan_transitions.py
check_mem && .venv/bin/python -m pytest -q
```

macOS 渲染应省略 `MUJOCO_GL=egl`；本轮未测试 macOS 或可开放 socket 的宿主环境。单句预览使用独立报告，保留十句总报告：

```bash
check_mem && .venv/bin/python scripts/plan_transitions.py YOU HURT WHERE --render --report results/planned_transitions/you_hurt_where_preview.json
```

规划器写出报告后退出 0，即使存在 FAILED，也必须读取状态。NPZ 为 `results/mocap_previews/planned_sentence_<GLOSSES>.npz`，基线为同目录 `sentence_<GLOSSES>.npz`；两者均使用 `timestamps_s`、`joint_names`、`positions`。句子时长按帧数 / 30，过渡和各腿时长按间隔数 / 30。

以下产物均 gitignored，需在新 checkout 后再生成：

- [report.json](../results/planned_transitions/report.json)、[中文表](../results/planned_transitions/report.md)、[英文表](../results/planned_transitions/report.en.md)：全部 19 段的 `status`、`method`、`source_near`、`endpoint_clearances_mm`、`min_clearance_mm`、`closest_pair` / `worst_collision`、`duration_s`、via 方向及完整候选记录。最近对包含体名、geom 名或 ID；间隙始终为有限数值。
- [YOU HURT WHERE v3](../results/planned_transitions/you_hurt_where_baseline_vs_planned_v3.mp4)，另复制到 `/workspace/you_hurt_where_baseline_vs_planned_v3.mp4`。
- [MEDICINE MORNING NIGHT TAKE v3](../results/planned_transitions/medicine_morning_baseline_vs_planned_v3.mp4)，另复制到 `/workspace/medicine_morning_baseline_vs_planned_v3.mp4`。其 FAILED 衔接仅供诊断回放。
- [规划日志](../results/planned_transitions/planner_round4_adaptive_output.txt)、[保存产物复核](../results/planned_transitions/evaluate_round4_output.txt)、[测试比较](../results/planned_transitions/pytest_round4_summary.json)、[聚焦测试](../results/planned_transitions/pytest_round4_transitions_final.txt)、[全量测试](../results/planned_transitions/pytest_round4_after.txt)。
- [R3 归档](../results/planned_transitions/round3_archive/report.json) 保留更新前的报告、十个规划 NPZ 和 sag 记录；原 v1/v2 视频及历史实验日志保留。首次统一 25 cm margin 的慢速尝试被中断，日志保留为 `planner_round4_output.txt`；最终使用逐级扩展检测。

视频统一为上排基线、下排规划，左列正面、右列右侧；30 fps 原速，较短一排结束后保持末帧。`render_comparison` 根据传入 glosses 找基线、根据报告找规划 NPZ，并使用独立 artifact name；CLI 的 `--comparison-glosses`、`--artifact-name`、`--copy-to` 对应这些参数。两个视频的元数据分别保存在总报告的 `comparison_videos` 中。

## 距离约定与通过条件

统一使用 MuJoCo 碰撞表面的有符号距离：**正值为分离，负值为穿透**。`PENETRATION_TOLERANCE_M = 0.002 m` 不变，普通路径的物理规则是 **`min_distance_m >= PENETRATION_TOLERANCE_M`**，即至少 +2 mm 间隙。

| 端点分类 | 完整路径与 hub 各腿的条件 | 通过后的状态 |
|---|---|---|
| 两端最小间隙均 ≥ `ENDPOINT_NEAR_M` | 全路径最小间隙 ≥ +0.002 m | `PASS` |
| 任一端点最小间隙严格 < `ENDPOINT_NEAR_M = 0.002 m` | 全路径最小间隙 ≥ 两端最小间隙中的较小值 | `source_near` |
| 全部候选均不满足对应条件 | 保留最小间隙最大的已检查候选，仅供诊断 | `FAILED` |

恰好 2 mm 不属于 near；小于 2 mm 的正间隙、−0.8 mm 轻微接触及更深原始穿透都属于 near。`source_near=true` 标志在 FAILED 段也保留，`method` 始终记录诊断或通过路线 `direct` / `via1` / `via2` / `hub`。`source_near_count` 只计状态为 source_near 的通过段，与 `failed_count` 分开；`endpoint_floor_m` 在 near 段为较差端点值，`relative_floor_passed` 报告所选路线是否达到该值。新报告不再使用 `source_collision` 名称。

原始 `clearance.passed` 始终表示绝对 +2 mm 检查；near 段是否相对通过，应读取 `status` 和 `relative_floor_passed`。因此 source_near 与 `clearance.passed=false` 可以同时出现。

### 无接触时仍测数值距离

`MujocoClearance` 对每个输出采样先做原模型运动学，再临时提高 geom 和显式 pair 的检测 margin，调用 `mj_collision`：从 2 mm 开始，必要时依次扩展到 1 cm、5 cm、25 cm，最后覆盖当前场景的 geom 中心跨度加 1 m。一旦测到非同手的有效配对，未检测到的更远配对不会降低最小值。读取的 `contact.dist` 是表面距离，不减去检测 margin，也不把 margin 当作通过阈值。

每次查询在 `finally` 中恢复原始 geom / pair margin；不永久编辑 MJCF，不改变 contype / conaffinity、原有 MuJoCo 配对过滤或既有同手指 / 腕规则，不排除 `fixed_mount`。无原始接触的分离姿态也返回有限 `min_distance_m` 和最近体 / geom 对，远至 1.2 m 的分离球体测试覆盖扩展范围。空轨迹或完全没有有效非同手配对的模型明确报错，不编造距离或返回 null。本轮数值取统一检测过程下的结果，不能混用 R3 旧测量值。

## 所有段的搜索顺序

1. 分别测量两个端点，仅决定绝对或相对下限，**不停止搜索**。先检查包含两端的 direct min-jerk 路径；满足对应条件即可通过。
2. direct 不满足时，检查原有七个 via1 候选，随后检查十六个 via2 候选（含 neutral-retreat 和左右对称串行退让族）。对所有通过的 via1/via2 按完整路径最小间隙取最大值，平局保持候选顺序。
3. 全部 via 失败后，检查 source → `qpos0` hub → target。hub 为固定基座模型同名关节的原始中立值，完整路径及两腿分别检查同一下限；不假设 hub 安全。
4. 仍不满足则 FAILED，报告最佳诊断路线的最差体 / geom 对、帧和间隙；不将恶化的 direct 当作 source_near 通过。

已满足间隙条件的 direct 若有腕部下垂，可额外搜索 via；只有同时通过间隙与高度的候选才能替换它，否则保留 direct 并警告。纯高度搜索不升级 hub。

via1 的机器人坐标方向仍为 `out`、`up`、`forward` 及组合；+X 前、+Y 左、+Z 上，组合归一化后请求 6.5 cm 腕位移。via2 保留两端同方向偏移、中立手臂退让及单臂先停靠再移动另一臂的通用候选，不使用词身份特例。复用既有有界 `G1Retargeter.solve_arms`，只解手臂，其他坐标保留中点或 1/3、2/3 凸插值；上游耦合关系不变，耦合关节不是独立驱动。

每腿使用 `s(u)=10u³−15u⁴+6u⁵`，连续峰值速度为 `1.875 × |Δq| / T`，按 30 fps 向上取整，且每腿至少 **0.3 s / 九个间隔**。手臂 **15 rad/s**、手指 **10 rad/s** 不变。源动作不编辑、不重采样；内部词保留含端点的 `sign_frames`，首词保留第 0 帧起势、末词保留回中立，规划端点与源值逐位相同。

## 本轮结果与第二组交接

| 段 | 状态 / 方法 | via 方向 | 时长 s | 两端间隙 mm | 全路径最小 mm |
|---|---|---|---:|---|---:|
| MEDICINE → MORNING | FAILED / via2 | neutral_retreat_left+out+forward → hold_left+out+forward | 1.100 | −0.809260 / +0.701652 | −42.047690 |
| NURSE → BLOOD-DRAW | source_near / via2 | up → up | 1.000 | +0.701652 / +0.701652 | +0.701652 |
| COME → SOON | source_near / via2 | neutral_retreat_right+out → hold_right+out | 0.900 | +0.701652 / +0.701652 | +0.701652 |
| NEED → INTERPRETER | source_near / via2 | out → out | 0.900 | +0.701652 / +0.701652 | +0.701652 |

MEDICINE → MORNING 完整检查 **25 条路线：1 direct、7 via1、16 via2、1 hub**。direct 为 **−56.182729 mm**，hub 为 **−54.852146 mm**，最佳 via2 仍只有 **−42.047690 mm**，低于 **−0.809260 mm** 相对下限；输出及视频明确为 FAILED 诊断。最佳路线最差对为 `fixed_mount` / `left_wrist_yaw_link`（geom 3 / 57），过渡内第 5 帧。

`source_near_handoff` 在句子与总报告中去重，含 **83 条体对记录、34 个词帧**，每条有 word、零基源帧、pair、`clearance_mm`，也包含 FAILED 的 near 端点。所有边界的固定基座 / 髋部小间隙保留；MEDICINE 119 帧约 −0.809260 mm、NURSE 24 帧约 −32.846892 mm、DOCTOR 89 帧约 −7.853912 mm 的源问题另列交接。源动作未修改。

十个保存 NPZ 的端点、限速、每腿时长、数值间隙及状态已实际复核；过渡最大采样速度为手臂 **14.635394 rad/s**、手指 **8.868628 rad/s**。JSON 包含输入 SHA-256、规划器源码哈希和运行时版本。YOU HURT WHERE 为规划 **9.033 s**、基线 **9.400 s**；MEDICINE MORNING NIGHT TAKE 为规划 **10.267 s**、基线 **10.067 s**。

YOU → BUY 仍选 up via，右腕相对较低端点的下垂从 **0.849769 mm** 降至零；源 YOU 内部腕 / 肘峰值到末帧下降 **234.348952 / 54.821335 mm** 保留，详见 [you_buy_sag.json](../results/planned_transitions/you_buy_sag.json)。

`fixed_mount` 仍为 z=0.79 m 的固定基座包装体，其活动 pelvis-contour 碰撞网格必须保留；源定义和运行时证据见 [fixed_mount_finding.md](../results/planned_transitions/fixed_mount_finding.md)。本轮只临时扩展查询 margin，模型文件和碰撞掩码均未修改。

## 实际测试与限制

最终聚焦测试 **88 passed**，覆盖数值分离距离、普通路径 +2 mm、严格 near 阈值、near-source 相对通过与失败后的完整搜索、via1/via2/hub 路线保留、失败段不计 accepted 且保留 handoff、速率、0.3 s 下限、真实 IK、同手排除和 fixed_mount 检查。

全量测试修改前 **316 passed、8 failed、23 errors**，修改后 **349 passed、8 failed、23 errors**；**31 项失败 / 错误 ID 集合完全相同，新增为零**。其中六项是任务给定宿主参考基线中的既有 learned_motion / learning_api / overview 失败，另两项失败及 23 项错误来自沙箱 socket 限制。没有可运行宿主环境，本轮未冒充宿主测试。完整集合见 [pytest_round4_summary.json](../results/planned_transitions/pytest_round4_summary.json)。未安装依赖、跳过测试或修改这些模块。

两份 v3 视频均实际解码核对为 **30 fps、960×1088**，分别为 **282 / 308 帧**，指定 `/workspace` 副本 SHA-256 均相同；MEDICINE 失败帧已目视确认带 `FAILED` 标签。递归检查的 **309 个 clearance 结果全部为有限数值且有最近体 / geom 对**；见 [round4_artifact_audit.json](../results/planned_transitions/round4_artifact_audit.json)。渲染进程实测三个线程，重任务前可用内存均超过 2 GiB。

这是开发回归检查，并非未参与调参者执行的冻结独立评审。source_near 仅表示没有比原端点更差，仍可能保留明显穿透；FAILED 仅供诊断。单词内部速度 / 碰撞保留，整句峰值另报；采样之间的连续碰撞、动力学、硬件执行、ASL 含义和真人可理解性仍未验证。

## Git 交接

仅交付 `src/sign_robot/transitions.py`、`scripts/plan_transitions.py`、`scripts/evaluate_planned_transitions.py`、`tests/test_plan_transitions.py`、本中文说明及对应英文版，另存 [FILE_LIST.txt](../results/planned_transitions/FILE_LIST.txt)。生成结果不暂存；不推送、不删除文件。若只读 `.git` 阻止暂存 / 提交，变更保持未暂存，由 foreman 在宿主机执行：

```bash
git add src/sign_robot/transitions.py scripts/plan_transitions.py scripts/evaluate_planned_transitions.py tests/test_plan_transitions.py docs/transition-planner.md docs/transition-planner.en.md
git commit -m "feat(group3): near-source search with numeric clearance"
```

`motions/`、`retarget.py`、`ACTION_IDS`、原模型 / 碰撞掩码、基线片段、已有 `.venv` / vendor 软链接和 `_scratch/` 均未修改。
