# 第三组：衔接规划器，第九轮

**中文** · [English](transition-planner.en.md)

第九轮增加**低于 2 mm 样本的端点连续附着与单调退出验收**，在原有较差端点相对下限之外实施。运动对 `ENDPOINT_NEAR_M = 0.002 m`、手臂 15 rad/s、手指 10 rad/s 不变；RRT-Connect 仍仅用于 MEDICINE→MORNING。重新生成目录为 `results/planned_transitions/round9/`，第八轮 Step 3 与更早原始产物保留。以下是开发者几何验收，不代表已验证 ASL；单词句零次过渡检查不证明词内动作通过。

## 第九轮新增验收规则

对每条候选轨迹逐帧计算**有效运动体对的最小有符号间隙**。通过搜索下限仍不足以接受；凡有样本严格低于 2 mm，还必须同时满足：

1. 全部低于 2 mm 的样本恰好组成一个连续区间，连到自身间隙也低于 2 mm 的源端点或目标端点。
2. 从所附着的端点向路径内部读取，间隙非递减，直至第一次达到至少 2 mm；目标端附着时逆序检查。
3. 第一次达到至少 2 mm 后，余下路径不再低于 2 mm。

相对下限仍用于搜索；新检查失败的尝试不能保留 `PASS` 或 `source_near`。JSON 每段及各尝试记录 `sub_2mm_frame_intervals`（**过渡路径内、从 0 开始、两端均含**）与 `sub_2mm_monotonic_ok`；没有低于 2 mm 样本时区间为 `[]`，该附加检查通过。`sub_2mm_attached_endpoint` 指明源端或目标端，`sub_2mm_first_clear_frame` 记录首次达到门槛的帧，失败原因放在 `sub_2mm_reason`。完整保存轨迹由 evaluator 再次计算，不能仅凭原报告通过。

若整条路径均低于 2 mm、没有清晰帧，则从符合条件的端点检查全路径是否非递减，`sub_2mm_first_clear_frame=null`；不额外要求必须达到 2 mm。本轮没有接受段使用这个边界情形。

## 第九轮实际结果

十句重新生成 **19 段 = 16 PASS、3 source_near、0 FAILED / needs_group2_fix**；全部 19 段附加检查为 `true`，状态与 `round8_step3` 相同。[轨迹一致性审计](../results/planned_transitions/round9/trajectory_identity.json) 验证全部 19 段及十个完整句子的数组逐位相同，十个 NPZ 的 SHA-256 也均与 `336ed69` 对应的 `round8_step3/` 文件完全一致。本轮增加报告与验收，没有改变轨迹。因此同一输入轨迹的新旧渲染等价，但第九轮尚未执行重渲染。

| 过渡 | 状态 | 低于 2 mm 帧区间（过渡内、含端点） | 端点附着单调检查 |
|---|---|---|---|
| HELLO → YOU | PASS | [] | true |
| YOU → APPOINTMENT | PASS | [] | true |
| APPOINTMENT → HAVE | PASS | [] | true |
| MEDICINE → MORNING | source_near | [[0, 0]] | true |
| MORNING → NIGHT | PASS | [] | true |
| NIGHT → TAKE | PASS | [] | true |
| NOW → NURSE | source_near | [[7, 9]] | true |
| NURSE → BLOOD-DRAW | PASS | [] | true |
| PLEASE → WAIT | PASS | [] | true |
| WAIT → DOCTOR | PASS | [] | true |
| DOCTOR → COME | source_near | [[0, 1]] | true |
| COME → SOON | PASS | [] | true |
| YOU → BUY | PASS | [] | true |
| BUY → BOOK | PASS | [] | true |
| YOU → HURT | PASS | [] | true |
| HURT → WHERE | PASS | [] | true |
| YOU → NEED | PASS | [] | true |
| NEED → INTERPRETER | PASS | [] | true |
| YOU → UNDERSTAND | PASS | [] | true |

三个接近端点的段均在一次连续区间后离开 2 mm 门槛，之后不再跌回：

- **MEDICINE→MORNING**：附着源端点，f0 **−0.809260 mm** → f1 **+2.757020 mm**；首次清晰帧 f1，仍为 `source_near / rrt_connect`。
- **NOW→NURSE**：附着目标端点，逆序从 f9 读起：**−32.846892 → −26.332107 → −17.368712 → +8.476263 mm**（f9→f8→f7→f6）；首次清晰帧 f6，仍为 `source_near / direct`。
- **DOCTOR→COME**：附着源端点，f0→f1→f2 为 **−7.853912 → +1.066278 → +5.074008 mm**；首次清晰帧 f2，仍为 `source_near / direct`。

`source_near` 保留上述端点穿透，只有相对下限与新增几何检查通过，不是绝对 +2 mm 认证。可复核 [JSON](../results/planned_transitions/round9/report.json)、[中文生成表](../results/planned_transitions/round9/report.md)、[英文生成表](../results/planned_transitions/round9/report.en.md) 与 [本轮交付说明](../_scratch/sol_r9_result.md)。

evaluator 已逐句重测十个保存轨迹的端点、速率、间隙、单调附着门槛及既有 RRT / 原库切片约束。全量 pytest 实际结果为 **418 passed、6 failed（17.79 秒）**；六个失败的测试 ID 与归档基线六项完全一致，没有新增失败。最终可运行本地测试服务器的完整结果见 [pytest_full_socket_enabled.txt](../results/planned_transitions/round9/pytest_full_socket_enabled.txt)。新增的批量渲染测试使用模拟渲染器和编码器，检查顺序、单词句、末帧保持、标签、元数据与单线程编码配置；本轮未实际渲染 MP4。

这些是开发者回归检查，不是冻结独立评测或真人评审。采样不证明连续无碰撞；词内速度 / 碰撞、动力学、硬件、ASL 含义和使用者理解仍未验证。

## 第九轮启动与再生成

从仓库根目录使用已有 `.venv` 顺序执行；不安装 `sentence_transformers`。每个重任务先运行同一内存检查，至少 2 GiB 可用，并且同一时刻仅一个重进程：

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export LP_NUM_THREADS=1 MESA_GLTHREAD=false MUJOCO_GL=egl
check_mem() {
  awk '/MemAvailable/{ok=$2>=2097152; printf "MemAvailable_KiB=%d ok=%s\n",$2,(ok?"yes":"no"); exit !ok}' /proc/meminfo
}
check_mem && .venv/bin/python scripts/plan_transitions.py --all --out-dir results/planned_transitions/round9 --report results/planned_transitions/round9/report.json
check_mem && .venv/bin/python scripts/evaluate_planned_transitions.py --report results/planned_transitions/round9/report.json --out-dir results/planned_transitions/round9
check_mem && .venv/bin/python -m pytest -q
```

`--report` 显式指定输入 JSON，单独 `--out-dir` 不会选择新报告。规划器即使有失败段也退出 0，必须读取状态。定向测试使用模拟间隙序列，覆盖正常单调退出、中途再次跌破 2 mm 与端点区间内反向下降，不在单元测试中运行完整 MuJoCo RRT。

## 全部句子的同一对照视频

`--render-all-comparison` 复用原渲染器，将报告中的**全部十句（八个多词句、两个单词句）**按原次序连续写入一个 MP4；每句显示序号与 gloss。上排基线、下排规划，左正面、右右视图，30 fps 原速；每句中较短一排保持末帧，下一句双方从第 0 帧开始。编码固定 `ffmpeg_params=["-threads", "1"]`。视频的逐句帧区间为**视频内、从 0 开始、两端均含**，和上述过渡局部区间不同。

| 次序 | 句子 | 类型 |
|---|---|---|
| 1 | HELLO YOU APPOINTMENT HAVE | 多词 |
| 2 | MEDICINE MORNING NIGHT TAKE | 多词 |
| 3 | NOW NURSE BLOOD-DRAW | 多词 |
| 4 | PLEASE WAIT DOCTOR COME SOON | 多词 |
| 5 | YOU BUY BOOK | 多词 |
| 6 | YOU HURT WHERE | 多词 |
| 7 | YOU NEED INTERPRETER | 多词 |
| 8 | YOU UNDERSTAND | 多词 |
| 9 | BREATHE-DEEP | 单词 |
| 10 | THANK-YOU | 单词 |

在上述线程环境和 `check_mem` 函数设置后，宿主可运行：

```bash
check_mem && .venv/bin/python scripts/evaluate_planned_transitions.py --report results/planned_transitions/round9/report.json --out-dir results/planned_transitions/round9 --render-all-comparison --artifact-name all9_sentences_baseline_vs_planned_r9 --copy-to /workspace/all9_sentences_baseline_vs_planned_r9.mp4
```

文件名按需求保留 `all9`，实际范围为上述十句。若外部复制因只读文件系统失败，完整本地视频保留在 `results/planned_transitions/round9/all9_sentences_baseline_vs_planned_r9.mp4`，复制错误写入 JSON，程序退出 1；宿主可从该处复制。单句 `--render-comparison --comparison-glosses ...` 继续可用。macOS 省略 `MUJOCO_GL=egl`，本轮未测试 macOS。

## 第八轮 Step 3 历史基线

第八轮 Step 3 **仅为 MEDICINE→MORNING 增加一次仅手臂的 RRT-Connect**，在全部既有路线失败后运行，包括切片内碰撞。该轮 `results/planned_transitions/round8_step3/` 十句复核为 **19 段 = 16 PASS、3 source_near、0 失败**，当时尚无第九轮单调退出门槛。MEDICINE→MORNING 达到端点相对下限，不表示满足绝对 +2 mm 或已验证 ASL。以下保留其距离、搜索协议与历史结果。

### 静态配对如何推导

`MujocoClearance` 首次构造时只读 `motions/hospital_v1_motions.json` 及其全部 35 个动作的所有帧（共 4485 帧），跨文件累计每个关节的最大 / 最小值。跨度严格大于 **1e-9 rad** 的关节视为运动关节；再并入规划器实际使用的 `retarget.ARM_SUFFIXES` 双臂 IK 关节。库中没有证据的未知模型关节保守视为运动，不会静默免检。当前模型得到 **38 个运动关节**；已确认恒定的 12 个腿部关节和 3 个腰部关节维持模型 qpos0。

对每个 body 沿 `body_parentid` 走到 world，收集沿途及自身的运动关节 ID。`derive_static_body_pairs(model, moving_joint_ids)` 比较两体的运动祖先集合：**集合相等，等价于两体之间的运动学路径上没有运动关节，才是静态对**。整个过程由模型拓扑与动作数据计算，没有手写体对名单。当前推导出 **136 个不同 body 的静态对**，不含手臂、手腕、手指或手部 body。`fixed_mount` 与左右 `hip_pitch_link` 属于静态对；腕部与基座仍是运动对，即使基座自身固定。

构造时在恒定姿态临时扩大 `mj_collision` 的 geom / 显式 pair 检测 margin 至覆盖场景，保留原生过滤和同手排除，再用 **`mj_geomDistance`** 对检测到的静态 geom 对逐一测量，按 geom 对去重。这样不依赖大 margin 下可能较粗的 mesh 接触距离。当前 **47 个原生有效 geom 对**记录为 `vendor_structural_gaps`（原厂结构缝），含 `bodies`、`geoms`、`geom_ids`、`distance_m`、`distance_mm`。其中：

| 原厂结构缝 | 距离 mm |
|---|---:|
| fixed_mount / left_hip_pitch_link | +0.701651 |
| fixed_mount / right_hip_pitch_link | +0.719230 |

136 是拓扑体对数，47 是通过原生碰撞过滤后实际测量的 geom 对数，二者不是同一计数。完整清单及推导来源在总报告和句子报告中，所选过渡与各次 clearance 结果也保留清单。几何、掩码和 MJCF 均未永久编辑；`prepare_robot.py` 未修改。

### 运动配对的距离与搜索规则

统一使用有符号距离：**正值分离，负值穿透**。`PENETRATION_TOLERANCE_M = 0.002`、`ENDPOINT_NEAR_M = 0.002`、手臂 **15 rad/s**、手指 **10 rad/s** 全部不变。

| 运动配对端点分类 | 全路径及 hub 各腿条件 | 通过状态 |
|---|---|---|
| 两端最小间隙均 ≥ 2 mm | 最小间隙 ≥ +2 mm | PASS |
| 任一端点最小间隙严格 < 2 mm | 最小间隙 ≥ 两端较小的间隙 | source_near |
| 全部候选未满足对应条件 | 保留最小间隙最大的候选，切片失败例外见下文；专用 RRT 失败仅供诊断 | FAILED / needs_group2_fix |

恰好 2 mm 不算 near。`failed_count` 包含 `needs_group2_fix`，`needs_group2_fix_count` 是其子集，二者均不计接受。失败段也保留 `source_near=true` 端点标志；`source_near_count` 只计相对通过的段。`clearance.passed` 仍表示运动对的绝对 +2 mm 检查，near 段应同时读取 `status` 和 `relative_floor_passed`。`min_distance_m`、`closest_pair` / `worst_collision`、`endpoint_clearances_mm` 和 handoff 均不混入静态间隙。

运动配对继续使用 R4 的数值查询：从 2 mm、1 cm、5 cm、25 cm 逐级扩大检测 margin，必要时覆盖场景；只有检测到有效**运动对**才能停止扩展，静态接触不会让查询提前返回。读取 `contact.dist`，每次在 `finally` 恢复 geom / pair margin；原生 MuJoCo 配对过滤和既有同手指 / 腕排除不变。分离姿态也返回有限数值和最近体 / geom 对；空轨迹或没有有效运动对的模型报错。规划姿态若改变被分类为恒定的关节，会显式拒绝该失效分类。

搜索按 **direct → via1/via2 → qpos0 hub → 源收回/目标接近 (c)** 升级，near 端点不截断。(c) 使用含端点的源词 `positions[sign_frames[1]:]` 和目标词 `positions[:sign_frames[0]+1]`；中性点不一致时插入最小 jerk 桥。逐边增加整数帧间隔，保留全部原始节点（含中性点与桥接节点），不跨转折抄近路；整段至少 0.3 s，桥的每腿也至少 0.3 s。

上表的绝对 2 mm 规则用于 direct / via / hub；**(c) 的整条路线和两个原始库切片始终要求最小间隙 ≥ 较差端点，即使两端都 ≥2 mm**。例如端点为 8 / 12 mm、途中为 3 mm 的 (c) 必须 FAILED。每次尝试及所选过渡的 `required_clearance_m` 报告实际下限，`clearance.passed` 仍仅表示绝对 2 mm 检查。evaluate 独立复查引用的原始库切片；即使保存采样通过，也不能覆盖切片内 FAILED。

`failed_trajectory_policy` 的例外：若 (c) 原始切片低于下限，报告库帧与配对，并选择 retract_approach 供诊断，即使先前失败候选最小间隙更大。其他过渡到此停止；**仅 MEDICINE→MORNING 继续以下单次 RRT**。其他全部失败的搜索保留最小间隙最大的候选。FAILED 与 needs_group2_fix 输出均仅供诊断。达到或超过 9.5 mm 的运动间隙在控制台和双语表格统一显示 `>=9.5`（`clearance_capped=true`），JSON 保留原始测量值；约 9.50015 mm 来自 elbow/wrist_pitch 网格间隙，`mj_geomDistance(distmax=1.0)` 复测并非查询截断。通过的 direct 如有腕部下垂可额外搜索 via，只有高度与距离均通过才替换；纯高度搜索不升级 hub。

via1 / via2 保留通用的双臂偏移、中立手臂退让和左右串行退让候选，不按词身份做特例。IK 只解手臂，手指和其他坐标保留端点凸插值；耦合关节不是独立驱动。每腿采用 `s(u)=10u³−15u⁴+6u⁵`，按连续峰值 `1.875 × |Δq| / T` 向上取整到 30 fps，至少 **0.3 s / 九个间隔**。源词不修改或重采样，内部词使用含端点的 sign_frames；首词保留第 0 帧起势、末词保留回中立，过渡端点逐位相同。

### 单次 RRT-Connect 协议

`RRT_GLOSSES = ("MEDICINE", "MORNING")` 是唯一例外。direct、全部 via1/via2、hub、retract/approach 均失败后才搜索，从 MEDICINE 结束姿态（f119）到 MORNING 起始姿态（f35），不重放有缺陷的源收回或目标接近片段。(c) 的失败尝试及原库缺陷继续保存在 `attempts` 与 `source_near_handoff`。

- 搜索精确双臂 `ARM_SUFFIXES`：实际 **14 个手臂关节**，在有限 MuJoCo 限位内采样。欧氏最近邻与步进，步长 **0.35 rad**，目标偏置 **0.15**；随机源固定为 `numpy.random.default_rng(RRT_SEED=5412)`。
- 手指及全部非手臂坐标采用确定策略：将节点投影到手臂起终向量，截断投影进度至 [0, 1]，按该权重插值源 / 目标坐标；节点间所有坐标线性插值。不搜索任何非手臂维度，不宣称耦合手指可独立驱动。
- 复用 `MujocoClearance` 及同样的运动对 / 静态缝排除。每边各坐标按 **≤0.04 rad** 检查。该 source_near 段整条路线必须 **≥−0.0008092600523539207 m**，即较差端点；不放宽任何门槛或速度。
- **一次尝试，总上限 120 秒**：树搜索最多 96 秒，余量用于平滑与验证；查询间检查单调时钟，原生同步查询不能中途抢占。不更换种子重试。
- 首先完整复查重建路线并按速率伸缩，再以确定性的优先长跨度捷径严格缩短关节空间路长（最多 128 次检查，不宣称全局最优）。复查平滑后全部边和实际速率缩放输出；平滑复查失败或耗尽余量，回退至已验证的未平滑路线。
- 使用现有 `timescale_to_rate_limits`，保留节点、**15 / 10 rad/s**、全段至少 **0.3 秒**与 30 fps。尝试与过渡记录 `min_clearance_m`、mm 显示、`duration_s`、`rrt_nodes`、`rrt_runtime_s`、`rrt_seed`、`smoothed`、结果及接受节点。
- 若没有可接受路径，状态 / 方法为 **`needs_group2_fix` / `rrt_connect`**，不再搜索。保存已检查的失败 (c) 路线供诊断（`diagnostic_method=retract_approach`），不作为可执行输出、不计接受；验证器仍检查其原始库切片。

实现选项于集成前记录在中英并列的 [_scratch/sol_r8_rrt_notes.md](../_scratch/sol_r8_rrt_notes.md)。

### Step 3 结果与交接

| MEDICINE→MORNING 字段 | Step 3 实际结果 |
|---|---:|
| 状态 / 方法 | source_near / rrt_connect |
| 端点间隙 mm | −0.809260 / +9.434433 |
| 所需下限及保存路线最小值 m | −0.0008092600523539207 |
| 最小间隙显示 mm | −0.809260 |
| 过渡时长 s | 0.466666667（14 间隔） |
| 树节点数 / 种子 | 56 / 5412 |
| RRT 运行秒数 | 4.093947754 |
| 已平滑 / 原始→接受节点 | true / 39→6 |
| 手臂 / 手指峰值 rad/s | 13.578870 / 2.993295 |

MEDICINE MORNING NIGHT TAKE 现在为 **9.633333 秒**，基线 **10.066667 秒**，差值 **−0.433333 秒**；Step 1 诊断为 11.666667 秒、差值 **+1.600000 秒**。句子时长为帧数 / 30，过渡时长为间隔数 / 30。RRT 路线仍有腕部下垂警告；source_near 仅达到相对下限，保留源端点穿透。

[范围审计](../results/planned_transitions/round8_step3/scope_audit.json) 验证其余 **18 段轨迹**与 Step 1 逐位相同，方法、状态、时长、间隙与峰值速率也相同；其他九个完整句子逐位相同。十个保存 NPZ 的端点、速度、下限、接受的 RRT 节点 / 非手臂策略 / 密集边和结构缝一致性均经复核，词内动作不变。

第二组清单与 Step 1 **完全一致：17 条运动对记录、5 个词帧**：**MEDICINE f119、MEDICINE f145、MORNING f28、NURSE f24、DOCTOR f89**。RRT 不修复这些库缺陷。失败的 (c) 尝试仍记录 MEDICINE 收回 f119–159、MORNING 接近 f0–35；f145 `left_wrist_yaw_link / fixed_mount` 为 −67.599238 mm，f28 `R_thumb_proximal / left_wrist_yaw_link` 为 −44.832 mm。静态基座 / 髋部结构缝仍分列。

### Step 3 历史产物

当前再生成使用上文的独立 `round9/` 命令，不覆盖以下历史目录。

- Step 3 [JSON](../results/planned_transitions/round8_step3/report.json)、[中文表](../results/planned_transitions/round8_step3/report.md)、[英文表](../results/planned_transitions/round8_step3/report.en.md)、[范围审计](../results/planned_transitions/round8_step3/scope_audit.json)、[聚焦 pytest](../results/planned_transitions/round8_step3/pytest.txt)。
- [MEDICINE v6 对照](../results/planned_transitions/round8_step3/medicine_morning_baseline_vs_planned_v6.mp4)，元数据和复制状态在 JSON。上排基线、下排规划，左正面、右右视图；30 fps 原速，较短一排保持末帧，不拉伸时间。实际视频检查见 [artifact_audit.json](../results/planned_transitions/round8_step3/artifact_audit.json)。
- Step 3 NPZ 为 `results/planned_transitions/round8_step3/planned_sentence_<GLOSSES>.npz`，契约为 `timestamps_s / joint_names / positions`。日志与中英结果简报见 [_scratch/sol_r8_rrt_result.md](../_scratch/sol_r8_rrt_result.md)。
- 历史 [Step 1 JSON](../results/planned_transitions/round8_step1/report.json) 保留 16 PASS / 2 source_near / 1 FAILED 和切片停止诊断。[MEDICINE v5](../results/planned_transitions/medicine_morning_baseline_vs_planned_v5.mp4)、[YOU HURT WHERE v4](../results/planned_transitions/you_hurt_where_baseline_vs_planned_v4.mp4)、根目录 Round 7 报告、[round4 归档](../results/planned_transitions/round4_before_round6_archive/report.json)、旧视频与原始记录均保留。生成产物与视频被 gitignore，新 checkout 后需再生成。

### Step 3 实际检查与未验证限制

定向 pytest **120 passed（4.29 秒）**，覆盖固定种子稳定性、精确手臂索引与非手臂确定行为、相对下限通过、超时转 needs_group2_fix 且无重试、仅授权方向触发、先前路线通过不进 RRT，以及平滑复查失败的安全回退，并运行原有过渡回归。全量 pytest 和提交留给宿主，不推送。

这是开发者回归，不是冻结独立测试或 ASL / 使用者评审。PASS 仅证明采样的运动对达到 +2 mm；source_near 仅相对端点通过，仍可能穿透；FAILED / needs_group2_fix 只供诊断。采样不证明连续无碰撞，捷径平滑不保证加速度连续。词内速率 / 碰撞、动力学、硬件、ASL 含义、真实使用者理解和 macOS 均未验证；原厂结构缝也不是硬件安全认证。

v6 已完整解码验证为 **302 帧、30 fps、960×1088**，第 124 帧目视确认显示 `source_near`。外部复制实际因 `[Errno 30] Read-only file system` 被拒绝；渲染仅因此退出 1，本地视频和复核完整。宿主复制：

```bash
cp results/planned_transitions/round8_step3/medicine_morning_baseline_vs_planned_v6.mp4 /workspace/medicine_morning_baseline_vs_planned_v6.mp4
```

未暂存、提交或推送。`motions/`、`retarget.py`、`ACTION_IDS`、`scripts/prepare_robot.py`、原模型和碰撞掩码未修改。宿主按 [FILE_LIST](../results/planned_transitions/round8_step3/FILE_LIST.txt) 复核，运行全量 pytest 并提交。
