# 九个医院句子，第八轮：不停顿的平滑衔接 + 手势级动力学门槛（2026-11-02）

**中文** · [English](README.en.md)

仅为开发证据：正式 PASS_SIM 为 0，`formal_acceptance_enabled=false`，不是已验证的 ASL，未经人工评审。
之前：第七轮 [`../hospital_sentences_20261102_007/README.md`](../hospital_sentences_20261102_007/README.md)。

用户对第七轮的反馈（对话，2026-11-02）：动作没问题，但衔接的段落感太强，一顿一顿的（走一段、停一下、再走）；速度仍比
手势慢；如果是加速度硬限制卡住，可以适当放宽。代码 `1d07d2d`；输入 `make_inputs.py`；运行 `run.sh`，16 个词对 run 用
cpu0–15，02:50–03:39。

## 诊断（第七轮）

- **一顿一顿**：路线的每个节点都按"从静止到静止"定时（速度、加速度为零），刹车变体还在两端加了停止段。17 个衔接里有 9 个
  在衔接内部完全停下 1–3 次（共 16 次全身停顿），例如 NURSE→BLOOD-DRAW 3 次（4 段 × 15 帧）、MORNING→NIGHT 3 次、
  YOU→HURT 3 次、PLEASE→WAIT 2 次。
- **速度**：17 个衔接在通过前的那次尝试全部超了加加速度积分门槛（1e6 rad²/s⁵）；峰值加加速度卡了 5 个，峰值加速度卡了
  2 个。与手势自身的保护区间相比（21 个句中词、验证器同样的 30 Hz 有限差分、所有关节），衔接段温和了 5–10 倍：

| | 手势保护区间（中位数 / 上四分位） | 第七轮衔接 |
|---|---|---|
| 峰值加速度 | 171 / 211 rad/s² | 23–99 |
| 峰值加加速度 | 4283 / 5447 rad/s³ | 607–2336 |
| 每秒加加速度积分 | 9.2e6 / 1.26e7 rad²/s⁵ | 3.2e5–2.4e6 |

## 改动（词对策略 `config/transition_policy_hospital_sentences_fast_v5.json`，序列策略 v7）

- **`planner.smooth_timing`（`smooth_route_timing_v1`）**，先于旧的"每个节点都停下"的五次曲线尝试：
  - *最小加加速度样条*（`min_jerk_spline_v1`）：每段一条五次曲线，穿过每个节点；内部节点的速度、加速度按总加加速度平方
    最小求解（一直连续到四阶导数），因此不会在节点处停下；
  - *拐角平滑过渡*（`corner_blend_v1`）：每段内匀速，相邻两段在 min(T_i, T_i+1) 的窗口内用 smoothstep 速度曲线衔接。
    在某段里不动的关节就真的不动（样条在关节限位附近的来回振荡正是它在 NURSE/MORNING 分阶段路线上失败的原因），下一阶段
    在上一阶段收尾时就开始；拐角被切掉一点，碰撞照常按实际曲线检查；
  - 两种曲线各按两种时长比例分配（各段关节在速度上限下所需时间，或同时考虑速度、峰值加速度、峰值加加速度三项限制所需
    时间）；每种都从速度下限总时长起步，所有段一起每次 ×1.12（整帧）延长，四种里取最短的通过者；
  - 旧的"先停后走"五次曲线和刹车仍作为后备（本轮没有用到）。手指离限到达在衔接还太短时放不下，现在只算一次失败尝试，不再
    中止整个定时；解析门槛通过后才做碰撞采样。
- **选优规则 `numerical_pass_then_fewest_stops_then_core_gap_v1`**：先比衔接内部的全身停顿次数（衔接内部某个段边界处所有
  关节都低于 0.05 rad/s），再比两个保护核心之间的帧数。收尾段用同样的规则。
- **门槛**（用户允许放宽）：峰值加速度 120 → **200** rad/s²，峰值加加速度 3000 → **5000** rad/s³，加加速度积分
  1e6 → **5e6** rad²/s⁵。每一项都在上表手势的上四分位以内（5e6 是上四分位水平乘以最短衔接的 0.4 s）；速度上限（手臂 15、
  手指 10 rad/s）不变。在相同路线节点上离线重定时第七轮的 17 条路线后，选了这一组而不是加加速度积分 1e7（后者只快一点点）。
- 每对搜索预算 480 → 720 s（RRT 160 → 240 s），因为每次定时现在要试四种方案。
- 测试 `tests/test_smooth_timing_v1.py`（7 项，含重新计算手势四分位数）；全套 **1014 passed**。

## 结果：7/7 句子 NUMERICAL_PASS，衔接不再停顿

- 17/17 个选中衔接、7/7 个句子全新复核一致；24/24 个受保护核心逐位不变；每句都回到初始姿态。
- **衔接内部全身停顿：16 → 0**（全部 17 个衔接和 7 个收尾段）。15 个衔接用样条，2 个用拐角平滑过渡
  （NURSE→BLOOD-DRAW、WAIT→DOCTOR）；"先停后走"的后备一次都没用到。
- **更快**：衔接总帧数 446 → 254；两个保护核心之间的总帧数 563 → 310（−45%）；收尾段 12–19 → 8–12 帧。手臂平均速度：
  衔接段 5.0–13.1 rad/s（第七轮 2.7–12.1），收尾段 4.6–8.2（第七轮 2.2–7.0），手势保护区间 1.5–10.5 rad/s。

| 句子 | 第七轮 | 第八轮 |
|---|---|---|
| HELLO YOU APPOINTMENT HAVE | 271 帧（9.0 s） | 235 帧（7.8 s） |
| YOU NEED INTERPRETER | 198 帧（6.6 s） | 168 帧（5.6 s） |
| PLEASE WAIT DOCTOR COME SOON | 448 帧（14.9 s） | 366 帧（12.2 s） |
| YOU HURT WHERE | 165 帧（5.5 s） | 120 帧（4.0 s） |
| NOW NURSE BLOOD-DRAW | 299 帧（10.0 s） | 271 帧（9.0 s） |
| MEDICINE MORNING NIGHT TAKE | 230 帧（7.7 s） | 164 帧（5.5 s） |
| YOU UNDERSTAND | 107 帧（3.6 s） | 97 帧（3.2 s） |

- 选中词对衔接：峰值加加速度 819–2058 rad/s³（门槛 5000），峰值加速度 ≤ 134 rad/s²（门槛 200），最大加加速度积分
  4.89e6 rad²/s⁵（门槛 5e6）。
- NURSE 的分阶段动作保留了先后次序，但不再停顿：右手先从左手腕上落下离开，左前臂抬起、手腕回正，然后进入 BLOOD-DRAW
  （42 帧，第七轮 60 帧且停 3 次）。
- `clamped_joint_stop_v1` 在 PLEASE→WAIT 出口（`left_wrist_roll_joint`）和 HURT→WHERE 出口（`R_thumb_proximal_yaw_joint`）
  起作用。

| 词对 | run | 尝试 | 通过 | 选中 | 方法 | 曲线 | 切点 | 衔接帧 | 停顿 | 两核心间帧数 | 第七轮（帧 / 停顿 / 两核心间） |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NURSE→BLOOD-DRAW | 01 | 20 | 4 | attempt_00016 | staged_exit | corner_blend_v1 | 75→35 | 42 | 0 | 43 | 60 / 3 / 61 |
| MORNING→NIGHT | 02 | 53 | 40 | attempt_00002 | staged_exit | min_jerk_spline_v1 | 37→39 | 13 | 0 | 13 | 43 / 3 / 43 |
| PLEASE→WAIT | 03 | 35 | 4 | attempt_00010 | ik_via1 | min_jerk_spline_v1 | 66→27 | 22 | 0 | 22 | 36 / 2 / 59 |
| NIGHT→TAKE | 04 | 82 | 58 | attempt_00002 | direct | min_jerk_spline_v1 | 60→51 | 10 | 0 | 10 | 24 / 1 / 24 |
| WAIT→DOCTOR | 05 | 34 | 7 | attempt_00006 | neutral | corner_blend_v1 | 84→34 | 32 | 0 | 32 | 30 / 1 / 64 |
| MEDICINE→MORNING | 06 | 41 | 7 | attempt_00038 | rrt_connect | min_jerk_spline_v1 | 86→25 | 11 | 0 | 29 | 24 / 1 / 44 |
| YOU→HURT | 07 | 40 | 15 | attempt_00015 | ik_via1 | min_jerk_spline_v1 | 72→27 | 12 | 0 | 12 | 43 / 3 / 43 |
| YOU→APPOINTMENT | 08 | 41 | 21 | attempt_00026 | ik_via2 | min_jerk_spline_v1 | 72→59 | 19 | 0 | 29 | 24 / 0 / 35 |
| YOU→NEED | 09 | 37 | 20 | attempt_00027 | rrt_connect | min_jerk_spline_v1 | 72→30 | 8 | 0 | 8 | 24 / 1 / 24 |
| HELLO→YOU | 10 | 83 | 68 | attempt_00002 | direct | min_jerk_spline_v1 | 66→45 | 10 | 0 | 10 | 17 / 0 / 17 |
| NOW→NURSE | 11 | 32 | 15 | attempt_00004 | direct | min_jerk_spline_v1 | 51→38 | 14 | 0 | 14 | 15 / 0 / 15 |
| NEED→INTERPRETER | 12 | 53 | 43 | attempt_00014 | direct | min_jerk_spline_v1 | 93→14 | 10 | 0 | 26 | 15 / 0 / 31 |
| YOU→UNDERSTAND | 13 | 73 | 63 | attempt_00002 | direct | min_jerk_spline_v1 | 72→27 | 9 | 0 | 9 | 12 / 0 / 13 |
| HURT→WHERE | 14 | 66 | 43 | attempt_00028 | ik_via1 | min_jerk_spline_v1 | 57→51 | 11 | 0 | 11 | 22 / 0 / 22 |
| DOCTOR→COME | 15 | 86 | 69 | attempt_00002 | direct | min_jerk_spline_v1 | 57→27 | 10 | 0 | 10 | 15 / 0 / 15 |
| APPOINTMENT→HAVE | 16 | 32 | 19 | attempt_00013 | ik_via1 | min_jerk_spline_v1 | 143→24 | 12 | 0 | 23 | 30 / 1 / 41 |
| COME→SOON | 16 | 95 | 84 | attempt_00002 | direct | min_jerk_spline_v1 | 132→27 | 9 | 0 | 9 | 12 / 0 / 12 |

## 视频与图

`videos_gpu/<句子>/`：`comparison.mp4`（按用户决定不入库）、`report.json`、`contact_sheet.png`。
`MEDICINE__MORNING__NIGHT__TAKE/arm_speed_round7_vs_round8.png` 和 `NOW__NURSE__BLOOD-DRAW/arm_speed_round7_vs_round8.png`：
手臂速度随时间变化，上为第七轮、下为第八轮，灰色底带为新增衔接，圆点为衔接内部的全身停顿。
`NOW__NURSE__BLOOD-DRAW/round7_vs_round8_nurse_exit.png`：NURSE 出口每 5 帧一格。本轮仍在 Intel Arc B390 核显上渲染（给渲染
进程设置 `SHIM_MCCOMPAT` 没能切到 RTX 5060），每句 94–231 s；脚本和输出格式相同。未经人工观看。

## 限制

- 更快、更平滑，但仍在手势自身上四分位的动力学范围以内，没有超出；动作是否自然需要人看视频确认。最大的衔接加加速度积分
  （4.89e6）接近新门槛。
- MEDICINE MORNING NIGHT TAKE 的最小间隙正好是 2.0 mm（门槛）。
- 拐角平滑过渡会切角，所以两个用它的衔接不会精确经过各阶段节点；碰撞按实际曲线检查。
- 句子仍从第一个保护核心开始；采样碰撞检查不是连续碰撞证明；本目录提交后，这些 run 不能在新 HEAD 上续跑或复核。
