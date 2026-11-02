# 九个医院句子，第四轮：衔接提速 + 回到初始姿态（2026-11-01）

**中文** · [English](README.en.md)

仅为开发证据：正式 PASS_SIM 为 0，`formal_acceptance_enabled=false`，不是已验证的 ASL，未经人工评审。
之前：第二轮 [`../hospital_sentences_20261101_002/README.md`](../hospital_sentences_20261101_002/README.md)，
第三轮（已取代，修正了收尾段搜索）[`../hospital_sentences_20261101_003/README.md`](../hospital_sentences_20261101_003/README.md)。

用户要求：(1) 句子结束后回到双手垂下的初始位置；(2) 衔接段明显比手势段慢。代码 `0b2528d` + `843cd45`；输入与
批次沿用第三轮（`../hospital_sentences_20261101_003/make_inputs.py`）；运行 `run.sh`，16 个词对 run 用 cpu0–15，
20:43–21:18。

## 结果：7/7 句子 NUMERICAL_PASS，且都回到初始姿态

| 句子 | 第二轮帧数 | 第四轮帧数（含回到初始姿态） | 回到初始姿态 |
|---|---|---|---|
| HELLO YOU APPOINTMENT HAVE | 417（13.9 s） | 271（9.0 s） | 15 帧 |
| YOU NEED INTERPRETER | 316（10.5 s） | 201（6.7 s） | 15 帧 |
| PLEASE WAIT DOCTOR COME SOON | 765（25.5 s） | 441（14.7 s） | 12 帧 |
| YOU HURT WHERE | 291（9.7 s） | 161（5.4 s） | 12 帧 |
| NOW NURSE BLOOD-DRAW | 405（13.5 s） | 334（11.1 s） | 19 帧 |
| MEDICINE MORNING NIGHT TAKE | 387（12.9 s） | 246（8.2 s） | 17 帧 |
| YOU UNDERSTAND | 198（6.6 s） | 107（3.6 s） | 15 帧 |
| BREATHE-DEEP、THANK-YOU | 单词：完整播放源片段，本身就从初始姿态开始、回到初始姿态 | | |

- 序列独立复核 7/7 一致，24/24 个受保护核心逐位不变（`verify_sequences.log`）；17 个选中衔接全新复核全部一致
  （`selected_recheck_*/summary.json`）。
- 每个回放都停在初始姿态：终点位置误差 ≤ 1e-14 rad，速度与加速度为零
  （`sequences/independent_recheck/<句子>.json` 中的 `rest_tail`）。
- 手臂平均速度（肩/肘/腕关节速度的范数）：衔接段 2.7–12 rad/s，回到初始姿态 2.2–7.0 rad/s，受保护的手势核心
  1.5–10.5 rad/s。第二轮衔接段为 0.8–6 rad/s。

| 词对 | run | 尝试 | 通过 | 选中 | 方法 | 切点 | 衔接帧 | 两核心间帧数 | 第二轮 |
|---|---|---|---|---|---|---|---|---|---|
| NURSE→BLOOD-DRAW | 01 | 58 | 1 | attempt_00050 | rrt_connect | 98→23 | 60 | 92 | 78 |
| MORNING→NIGHT | 02 | 37 | 4 | attempt_00027 | rrt_connect | 69→39 | 30 | 30 | 30 |
| PLEASE→WAIT | 03 | 67 | 5 | attempt_00059 | rrt_connect | 85→23 | 36 | 59 | 203 |
| NIGHT→TAKE | 04 | 46 | 5 | attempt_00011 | ik_via1 | 60→51 | 24 | 24 | 128 |
| WAIT→DOCTOR | 05 | 82 | 20 | attempt_00074 | rrt_connect | 100→23 | 30 | 57 | 206 |
| MEDICINE→MORNING | 06 | 97 | 16 | attempt_00095 | rrt_connect | 86→26 | 24 | 41 | 95 |
| YOU→HURT | 07 | 40 | 10 | attempt_00008 | ik_via1 | 72→27 | 43 | 43 | 161 |
| YOU→APPOINTMENT | 08 | 46 | 14 | attempt_00045 | rrt_connect | 73→59 | 24 | 35 | 162 |
| YOU→NEED | 09 | 44 | 21 | attempt_00022 | rrt_connect | 72→30 | 24 | 24 | 151 |
| HELLO→YOU | 10 | 59 | 33 | attempt_00002 | direct | 66→45 | 17 | 17 | 47 |
| NOW→NURSE | 11 | 45 | 18 | attempt_00002 | direct | 51→38 | 15 | 15 | 132 |
| NEED→INTERPRETER | 12 | 81 | 39 | attempt_00008 | direct | 93→15 | 19 | 34 | 44 |
| YOU→UNDERSTAND | 13 | 76 | 57 | attempt_00008 | direct | 73→27 | 12 | 13 | 119 |
| HURT→WHERE | 14 | 110 | 71 | attempt_00002 | direct | 58→51 | 17 | 18 | 42 |
| DOCTOR→COME | 15 | 130 | 96 | attempt_00002 | direct | 57→27 | 15 | 15 | 39 |
| APPOINTMENT→HAVE | 16 | 39 | 14 | attempt_00007 | ik_via1 | 143→24 | 30 | 41 | 48 |
| COME→SOON | 16 | 131 | 118 | attempt_00002 | direct | 132→27 | 12 | 12 | 32 |

"两核心间帧数" = 前一个核心之后保留的源动作 + 衔接 + 后一个核心之前保留的源动作。合计 570 帧（19.0 s），第二轮为
1717 帧（57.2 s）。NURSE→BLOOD-DRAW 比第二轮长：搜索受墙钟时间限制，本轮只找到一个通过的候选。

## 改了什么

- **选优规则** `numerical_pass_then_core_gap_then_smoothness_v1`（词对策略
  `config/transition_policy_hospital_sentences_fast_v1.json`，其余与 `braking_v1` 相同）：在通过独立复核的候选中，
  取两个保护核心之间帧数最少的；峰值加加速度、峰值加速度和加加速度积分只用来打破平局。原规则先比峰值加加速度，
  总是偏向又长又慢的衔接（第二轮在有 36 帧可通过的情况下选了 180 帧）。所有衔接门槛不变；选中衔接仍低于峰值
  加加速度 3000 rad/s³ 和峰值加速度 120 rad/s²。
- **回到初始姿态** `rest_tail_v1`（序列策略 `config/sequence_policy_hospital_sentences_v3.json` 的
  `assembly.rest_tail`）：静止姿态取 35 个库片段逐位相同的首帧（重定向得到的双手垂下姿态：肘 0.25 rad、拇指略内收；
  不是 MuJoCo 的 qpos0）。最后一个词之后，按顺序尝试其出口窗口内的出口帧；路径族与五次曲线定时沿用词对规划器，
  终点速度、加速度为零；从核心结束到静止所需帧数最少者胜出。搜索先在每个出口帧试直线路径（直接、经中立姿态），
  再只在帧数界限仍允许胜出的帧上试绕行路径。七个收尾段都选了直接路径。
- 独立验证器把收尾段当作衔接段检查（哈希绑定的规划记录 `sequences/rest_tails/<词>.json`、由全部库片段重新计算的
  静止姿态、边界、解析极值、内部有限差分质量、密集碰撞），结果记在 `rest_tail`。
- 新增测试 `tests/test_rest_tail_v1.py`（15 项）；全套 **988 passed**（`tests/pytest_full.log`）。

## 视频

`videos_gpu/<句子>/`：`comparison.mp4`（按用户决定不入库）、`report.json`、`contact_sheet.png`。与第二轮相同的两步
GPU 渲染（WSL 中 `export_render_inputs.py`，Windows 中 `render_gpu_windows.py`，RTX 5060，七句共 16 s）；收尾段标为
"ADDED return to rest / 新增回到初始姿态"。未经人工观看。

## 限制

- 提速后的动作更接近门槛：选中词对衔接的峰值加加速度 171–787 rad/s³（第二轮 1–500），峰值加速度 ≤ 95 rad/s²
  （第二轮 ≤ 63）；收尾段解析峰值加加速度 561–1986 rad/s³（NOW NURSE BLOOD-DRAW 最高），加速度 ≤ 66 rad/s²。
  全部低于 3000 rad/s³ 和 120 rad/s²；动作是否自然需要人工看视频。
- 句子仍从第一个词的保护核心开始，而不是从初始姿态开始（本次未要求；同样的机制可以镜像出"从初始姿态出发"的开头段）。
- 采样碰撞检查不是连续碰撞证明。本目录提交后，这些 run 不能在新 HEAD 上续跑或复核。
