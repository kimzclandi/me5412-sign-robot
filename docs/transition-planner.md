# 第三组：衔接规划器第三轮

**中文** · [English](transition-planner.en.md)

本轮在 `group3/transition-planner` 的 `98c0970`（原起点 `2656412`）上加入端点门控、双 via 和中立 hub 回退。九个脚本句子加 THANK-YOU 已本地重新生成：**19 段 = 16 PASS、3 source_collision、0 FAILED**。状态互斥；兼容字段 `accepted_count` 仍为 PASS 加 source_collision，不代表安全执行数量。source_collision 的直连输出只供诊断。BREATHE-DEEP 和 THANK-YOU 是单词句，过渡数为零，不获得单词自身碰撞认证。

## 启动与本地产物

从仓库根目录使用已有 `.venv`，顺序运行；不安装 `sentence_transformers`。每次重型任务前确认 `MemAvailable ≥ 2 GiB`，只运行一个 MuJoCo / 规划进程，总线程不超过三条：

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export LP_NUM_THREADS=1 MESA_GLTHREAD=false MUJOCO_GL=egl
.venv/bin/python -c 'from pathlib import Path; m = int(next(s.split()[1] for s in Path("/proc/meminfo").read_text().splitlines() if s.startswith("MemAvailable:"))); assert m >= 2 * 1024**2; print("MemAvailable GiB:", m / 1024**2)'
.venv/bin/python scripts/plan_transitions.py --all
.venv/bin/python scripts/evaluate_planned_transitions.py
.venv/bin/python -m pytest -q tests/test_plan_transitions.py
.venv/bin/python -m pytest -q
```

macOS 渲染时省略 `MUJOCO_GL=egl`；本轮没有 macOS 或宿主机环境验证。单句预览使用单独报告，避免覆盖十句结果：

```bash
MUJOCO_GL=egl .venv/bin/python scripts/plan_transitions.py YOU HURT WHERE --render --report results/planned_transitions/you_hurt_where_preview.json
```

生成的 NPZ 为 `results/mocap_previews/planned_sentence_<GLOSSES>.npz`，保持 `timestamps_s`、`joint_names`、`positions` 契约。以下产物均已 gitignore；全新检出须先重新生成：

- [report.json](../results/planned_transitions/report.json)、[中文表](../results/planned_transitions/report.md)、[英文表](../results/planned_transitions/report.en.md)：全部 19 段的 `method`、`via_direction` / `via_directions`、`min_clearance_mm`、`duration_s`，每句与基线的总时长对比，以及全部候选尝试和源帧交接表。
- [fixed_mount_finding.md](../results/planned_transitions/fixed_mount_finding.md)：定义位置、生成器、运行时 mesh / 掩码证据，中英双语。
- [规划日志](../results/planned_transitions/planner_round3_output.txt)、[保存产物复查日志](../results/planned_transitions/evaluate_round3_output.txt)、[测试前后比较](../results/planned_transitions/pytest_round3_summary.json)、[聚焦测试日志](../results/planned_transitions/pytest_round3_transitions_final.txt)、[全套测试日志](../results/planned_transitions/pytest_round3_after.txt)。
- `report_round2.json` / `.md` / `.en.md` 保留上一轮报告，`report_round3_initial.json` 保留加入单臂退让族之前仍有一个 FAILED 的结果；`serialized_neutral_probe.json` 和 `serialized_outward_probe.json` 保留通用候选探索中的失败及通过记录。

规划命令在成功写出产物后退出 0，即使报告存在 FAILED 也如此，使用者必须查看状态。句子时长按帧数 / 30；过渡及每腿时长按间隔数 / 30。

## 有序升级协议

1. **端点先行门控。** 每段先分别执行两个单帧 clearance 检查。显式常量 **`ENDPOINT_NEAR_M = 0.0 m`**：任一端点最小 `contact.dist` **严格 `< 0.0`**，立刻分类为 `source_collision`，记录词、零基源帧、体对和距离，停止 via1、via2、hub 搜索。这包含低于 −2 mm 的原始硬失败，也包含容差内的轻微负接触；恰好 0 不触发，null 表示未检测到接触。MEDICINE 第 119 帧为 **−0.806716 mm**，因此也须交接。此门控独立于路径的绝对硬失败线，不能用 detour 掩盖源姿态问题。
2. **直连。** 两端通过后，先检查 min-jerk 直连。绝对规则始终为 **`contact.dist < -PENETRATION_TOLERANCE_M`，`PENETRATION_TOLERANCE_M = 0.002 m`**。这是允许至多 2 mm 穿透的规则，并非正 2 mm 自由空间保证。每个输出采样都检查，包括端点；null 并非测得正间隙。
3. **via1 与 via2 共同择优。** 直连碰撞时，依次评估固定七种单 via 和十六种双 via；全部通过候选按**完整路径**的最小接触距离取最大，同分保持候选顺序。无接触候选排在有接触候选之前，报告仍为 null。`method="via1"` 配 `via_direction`；`method="via2"` 配两个 `via_directions`。每个 via 用原有有界 `G1Retargeter.solve_arms` 求解，未改 `retarget.py`，也不假定 IK 目标或中立姿态天然无碰撞。
4. **hub 回退。** 只有全部 via1/via2 碰撞失败，才尝试源 → hub → 目标；hub 取固定基座模型 **`qpos0` 中的同名关节值**。检查完整路径并单独检查两腿，均通过才记 PASS / `method="hub"`。仍失败则 `method="FAILED"`，保留检查过的最小穿透候选、最差体对和距离，仅供诊断。当前 19 段的通过候选均在 hub 前找到；真实 hub 路径可失败，回退选择通过模拟 clearance 的单元测试覆盖。

单 via 的机器人坐标方向仍为 `out`、`up`、`forward`、`out+up`、`out+forward`、`up+forward`、`out+up+forward`。机器人 +X 向前、+Y 向左、+Z 向上；左手向外为 +Y，右手为 −Y。向量归一化后每腕目标偏移 6.5 cm；单 via 从两端关节中点求 IK，非手臂坐标保持精确中点。关节限制可能使目标无法完全到达。

双 via 的十六个固定候选无需词名：七个把同方向偏移分别加到源 / 目标腕位姿；三个先用 qpos0 手臂作中立退让，再向外、外上或外前；另六个对左 / 右手臂对称尝试单臂退让。单臂族在两个 via 都把退让手臂保持在 qpos0 腕目标加外 / 外上 / 外前偏移，另一手臂在 via1 保持源姿态、via2 到达目标姿态，最后退让手臂接近目标。后两族的手指及其他非手臂坐标分别取源到目标的 1/3、2/3 插值。只求解手臂，保留上游耦合关系，不把耦合关节当独立驱动。

每腿使用 `s(u)=10u³−15u⁴+6u⁵`，连续峰值速度为 `1.875 × |Δq| / T`；按 30 fps 向上取整到满足限速且不少于 **0.3 s / 九个间隔**。via1 / hub 至少 0.6 s，via2 至少 0.9 s。手臂 **15 rad/s**、手指 **10 rad/s** 不变。

`endpoint_floor_m` 与 `relative_floor_passed` 保留原始低于 −2 mm 端点的相对下限诊断，但新的端点门控先停止搜索，不能把内部恶化标成碰撞通过。source_collision 仍保存并测量直连诊断路径。腕部低于两端的下垂检查继续独立报告；已碰撞通过的直连可尝试消除下垂，只有同时通过高度和碰撞的 via 才能替换它，纯外观搜索不升级到 hub。

源单词查找仍按 hospital map 优先，其次 mocap / video 的既有 ready / poor 规则。内部词保留含端点的 `sign_frames`，首词保留第 0 帧起势、末词保留回中立；源切片不编辑、不重采样，衔接端点逐位等于源文件。保持既有同手指 / 腕邻接体对规则，没有新增任何 geom 排除、修改碰撞掩码或过滤 `fixed_mount`。

## 本轮结果与第二组交接

| 原 FAILED 段 | 本轮状态 / 方法 | via 方向 | 时长 s | 完整路径最小距离 mm |
|---|---|---|---:|---:|
| MEDICINE → MORNING | source_collision | 无搜索 | 0.433 | −56.182782 |
| NURSE → BLOOD-DRAW | PASS / via2 | up → up | 1.000 | null |
| COME → SOON | PASS / via2 | neutral_retreat_right+out → hold_right+out | 0.900 | null |
| NEED → INTERPRETER | PASS / via2 | out → out | 0.900 | null |

**MEDICINE → MORNING 的 −56.183 mm 是保留下来的直连诊断路径测量，不是门控端点值，也不是通过轨迹。** 其触发端点为 MEDICINE 119 帧的左肩 yaw / torso（−0.807 mm）。NOW → NURSE 和 DOCTOR → COME 同样保留 source_collision：最差源端点分别为 **−32.892744 mm** 和 **−7.854003 mm**。交接表共 **10 条体对记录、3 个词帧**（MEDICINE 119、NURSE 24、DOCTOR 89），包含容差内接触，并在句子和总报告中去重列出。没有修改源动作。

保存后的十个 NPZ 已重新检查端点、采样限速、每腿下限、两端门控和碰撞分类。输出过渡的最大采样速度为手臂 **14.635394 rad/s**、手指 **8.868628 rad/s**。JSON 记录输入 SHA-256、规划器源码哈希和运行时版本。全部句子时长 / 基线对比见本地中英表。YOU HURT WHERE 仍为规划 **9.033 s**、基线 **9.400 s**，本轮未刷新 v2 对照视频；原视频保留。可选用 `MUJOCO_GL=egl .venv/bin/python scripts/evaluate_planned_transitions.py --render-comparison` 刷新到 `results/planned_transitions/you_hurt_where_baseline_vs_planned_v2.mp4`，默认另复制到 `/workspace/you_hurt_where_baseline_vs_planned_v2.mp4`，`--copy-to` 可更改位置。

YOU → BUY 仍选 up via，右腕相对较低端点的下垂从 **0.849769 mm** 降至零。YOU 源词内部的腕 / 肘峰值到末帧下降仍为 **234.348952 / 54.821335 mm**，不可通过保持源帧的衔接规划修复；详见 [you_buy_sag.json](../results/planned_transitions/you_buy_sag.json)。

### fixed_mount 证据

[scene.xml 第 65–68 行](../assets/robot/scene.xml) 定义 z=0.79 m 的包装体；[prepare_robot.py 第 27–31 行](../scripts/prepare_robot.py) 将导入机器人重新挂到该体下；[model_info.json](../assets/robot/model_info.json) 明记 `Fixed mount at z=0.79m`。其直接几何为视觉 pelvis、视觉 pelvis_contour_link（均 0/0）以及活动碰撞 pelvis_contour_link（运行时 `contype=1 conaffinity=1`）。证据表明它是虚拟挂载 / 固定基座占位，不是单独增加的真实机器人夹具；活动网格仍是骨盆轮廓几何，**必须保留碰撞检查**。本轮只报告证据，没有修改模型。完整运行时表见本地 [fixed_mount_finding.md](../results/planned_transitions/fixed_mount_finding.md)。

## 实际测试与限制

聚焦测试 **55 passed**，覆盖严格端点门控、不触发 via/hub、双 via 真实 IK、中立 qpos0、速率 / 0.3 s、全部候选最大距离选择、hub 双腿检查与选择、源碰撞相对 floor 诊断、固定挂载碰撞与源帧交接。全仓修改前 **299 passed、8 failed、23 errors**，修改后 **316 passed、8 failed、23 errors**；31 项失败 / 错误集合逐项一致，**新增为零**。其中 5 项是未安装 `sentence_transformers` 的既有 learned_motion / learning_api 失败，1 项是既有 overview 失败，另外 2 项失败和 23 项错误为沙箱 socket 限制。宿主机参考基线是 **324 passed / 6 failed**，本轮无法在宿主机执行，未将沙箱结果冒充宿主机结果，也未安装依赖、跳过测试或更改相关模块。

以上是开发回归检查，并非由未参与调参者执行的冻结独立评审。source_collision 和 FAILED 产物不可作为安全执行轨迹；单词自身限速 / 碰撞保留，整句峰值另报。采样点之间的连续碰撞、动力学、硬件执行、ASL 含义和真人可理解性仍未验证。

## Git 交接

生成产物继续保持 gitignored，不推送、不删除文件。仅交付以下六个代码 / 测试 / 文档文件，列表另存本地 `results/planned_transitions/FILE_LIST.txt`。本轮 `git add` 因无法创建只读工作树的 `index.lock` 而退出 128（[错误日志](../results/planned_transitions/git_handoff_round3.txt)）；六个变更保持未暂存，没有尝试提交或推送，由 foreman 在宿主机提交：

```bash
git add src/sign_robot/transitions.py scripts/plan_transitions.py scripts/evaluate_planned_transitions.py tests/test_plan_transitions.py docs/transition-planner.md docs/transition-planner.en.md
git commit -m "feat(group3): endpoint-near gate, dual-via and hub fallback"
```

`motions/`、`retarget.py`、`ACTION_IDS`、模型与碰撞掩码、基线片段、已有 `.venv` / vendor 软链接和 `_scratch/` 均未修改。
