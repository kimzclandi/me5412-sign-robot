# 九个医院句子，第七轮：缩短 MORNING/NURSE 保护区间 + 分阶段出口（2026-11-02）

**中文** · [English](README.en.md)

仅为开发证据：正式 PASS_SIM 为 0，`formal_acceptance_enabled=false`，不是已验证的 ASL，未经人工评审。
之前：第六轮 [`../hospital_sentences_20261101_006/README.md`](../hospital_sentences_20261101_006/README.md)。

用户要求（对话，2026-11-02）：删掉 MORNING 第 38 帧之后的用户保护；NURSE 的保护截到第 75 帧，之后先让右手快速移开，再
把左手手腕回正。代码 `129891a`；输入 `make_inputs.py`；运行 `run.sh`，16 个词对 run 用 cpu0–15，01:17–01:51。

## 改动

- **保护区间 v2**（`config/user_protected_hospital35_v2.json`）：只改了 v1 中的两条记录，并在记录中写明改动来源；v1 保留
  给之前的 run。
  - NURSE：[38, 79] → **[38, 75]**。
  - MORNING：[26, 69] → **[26, 37]**。原要求为 38：第 37→38 帧重定向后的右手中指、无名指以 10 rad/s 的上限速度突然
    合拢，离限位只剩 0.8 rad。仅把它们刹住就需要 5 帧刹车段，占掉衔接加加速度积分门槛的 95%（952,146 / 1e6 rad²/s⁵），
    因此在门槛不变的前提下，从第 38 帧出发接不出任何衔接（所有 NIGHT 入口都试过）。用户选择改为第 37 帧。
- **分阶段出口**（`planner.staged_exits`，`staged_exit_v1`，词对策略
  `config/transition_policy_hospital_sentences_fast_v4.json`）：对配置的词，衔接严格从保护核心末尾出发，经过若干
  "先停后走"的节点，每段只动一组关节，最后进入目标入口。阶段目标可以是初始姿态、目标入口姿态、归零，或逆运动学求得的
  手腕位移（`ik:<方向>:<步数>`，每步 6.5 cm，只取该组关节）。入口从最靠近目标核心的帧往前试；这些词不再使用通用路径族
  和 RRT。阶段选项事先沿节点折线做过离线碰撞筛查。
  - **NURSE**（选中 `right_arm:target + left_upper_arm:ik:out+up+forward:3 + left_wrist:zero`，4 段 × 15 帧）：
    1）右臂离开左手腕，直接移到 BLOOD-DRAW 需要的位置；2）左前臂离开大腿抬起（手腕处向外+上+前约 19.5 cm）；
    3）左腕回正到 0；4）进入 BLOOD-DRAW 入口（第 35 帧）。第 2 步不是用户要求的，但不抬起就原地回正，左手拇指会扎进
    躯干 52 mm。
  - **MORNING**（选中 `right_arm:ik:out+up:2`）：从第 37 帧直接走到 NIGHT 双手交叉会穿过左前臂，所以右手先向外上方
    移开（13 cm），再两臂交叉进入 NIGHT 的核心起点（第 39 帧）；两端各有 3 帧刹车、2 帧起步。
- 测试 `tests/test_staged_exit_v1.py`（11 项）；全套 **1007 passed**（`tests/pytest_full.log`）。

## 结果：7/7 句子 NUMERICAL_PASS，且都回到初始姿态

- 17/17 个选中衔接、7/7 个句子全新复核一致；24/24 个受保护核心逐位不变（NURSE [38, 75]，MORNING [26, 37]）；没有被
  筛选标记的保留边缘。
- NOW NURSE BLOOD-DRAW：回放 299 帧（第六轮 316）；NURSE→BLOOD-DRAW 衔接 60 帧，两核心间 61 帧（第六轮 74）。最小间隙
  2.0 mm，正好等于 2 mm 门槛。
- MEDICINE MORNING NIGHT TAKE：回放 230 帧（第六轮 249）；MORNING→NIGHT 衔接 43 帧（第六轮 30，但 MORNING 核心短了
  32 帧）。
- 其余句子：HELLO YOU APPOINTMENT HAVE 271、YOU NEED INTERPRETER 198、PLEASE WAIT DOCTOR COME SOON 448、
  YOU HURT WHERE 165、YOU UNDERSTAND 107（与第六轮相同）。词对衔接峰值加加速度 298–787 rad/s³，峰值加速度
  ≤ 95 rad/s²；收尾段与第四轮相同。
- `clamped_joint_stop_v1` 只在 HURT→WHERE 出口（`R_thumb_proximal_yaw_joint`）起作用；NURSE 不再需要它。

| 词对 | run | 尝试 | 通过 | 选中 | 方法 | 切点 | 衔接帧 | 两核心间帧数 | 第六轮 |
|---|---|---|---|---|---|---|---|---|---|
| NURSE→BLOOD-DRAW | 01 | 47 | 15 | attempt_00023 | staged_exit | 75→35 | 60 | 61 | 74 |
| MORNING→NIGHT | 02 | 53 | 31 | attempt_00004 | staged_exit | 37→39 | 43 | 43 | 30 |
| PLEASE→WAIT | 03 | 68 | 8 | attempt_00058 | rrt_connect | 85→23 | 36 | 59 | 59 |
| NIGHT→TAKE | 04 | 81 | 28 | attempt_00018 | ik_via1 | 60→51 | 24 | 24 | 24 |
| WAIT→DOCTOR | 05 | 58 | 13 | attempt_00049 | rrt_connect | 107→23 | 30 | 64 | 64 |
| MEDICINE→MORNING | 06 | 80 | 13 | attempt_00062 | rrt_connect | 86→23 | 24 | 44 | 44 |
| YOU→HURT | 07 | 43 | 13 | attempt_00008 | ik_via1 | 72→27 | 43 | 43 | 43 |
| YOU→APPOINTMENT | 08 | 50 | 15 | attempt_00047 | rrt_connect | 73→59 | 24 | 35 | 35 |
| YOU→NEED | 09 | 47 | 24 | attempt_00022 | rrt_connect | 72→30 | 24 | 24 | 24 |
| HELLO→YOU | 10 | 65 | 34 | attempt_00002 | direct | 66→45 | 17 | 17 | 17 |
| NOW→NURSE | 11 | 48 | 19 | attempt_00002 | direct | 51→38 | 15 | 15 | 15 |
| NEED→INTERPRETER | 12 | 117 | 79 | attempt_00014 | direct | 93→14 | 15 | 31 | 31 |
| YOU→UNDERSTAND | 13 | 78 | 59 | attempt_00008 | direct | 73→27 | 12 | 13 | 13 |
| HURT→WHERE | 14 | 60 | 30 | attempt_00004 | direct | 57→51 | 22 | 22 | 22 |
| DOCTOR→COME | 15 | 130 | 94 | attempt_00002 | direct | 57→27 | 15 | 15 | 15 |
| APPOINTMENT→HAVE | 16 | 42 | 15 | attempt_00008 | ik_via1 | 143→24 | 30 | 41 | 41 |
| COME→SOON | 16 | 131 | 116 | attempt_00002 | direct | 132→27 | 12 | 12 | 12 |

## 视频

`videos_gpu/<句子>/`：`comparison.mp4`（按用户决定不入库）、`report.json`、`contact_sheet.png`。
`NOW__NURSE__BLOOD-DRAW/round6_vs_round7_nurse_exit.png` 和 `MEDICINE__MORNING__NIGHT__TAKE/round6_vs_round7_morning_exit.png`：
从核心结束起每 4 帧一格，正面与侧面，上为第六轮、下为第七轮。`source_frames_morning_night_nurse.png`：新切点附近的源动作帧。
本轮渲染跑在 Intel Arc B390 核显上（这次 Windows 没有把 GL 上下文交给 RTX 5060），每句 97–230 s，之前约 12 s；脚本和
输出格式相同。未经人工观看。

## 限制

- NURSE 的分阶段出口共 2 s（4 段各 0.5 s 的先停后走）；每段都定时到通过全部门槛的最短时长，所以"快速"是门槛允许的最快，
  没有单独调速。
- NOW NURSE BLOOD-DRAW 的最小间隙正好是 2.0 mm。
- 句子仍从第一个保护核心开始；采样碰撞检查不是连续碰撞证明；本目录提交后，这些 run 不能在新 HEAD 上续跑或复核。
