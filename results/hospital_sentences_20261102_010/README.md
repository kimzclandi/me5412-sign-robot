# 九个医院句子，第十轮：在新片段 clips-v2 上第一次求解（2026-11-02）

**中文** · [English](README.en.md)

仅为开发证据：正式 PASS_SIM 为 0，`formal_acceptance_enabled=false`，不是已验证的 ASL，未经人工评审。
之前：第八轮 [`../hospital_sentences_20261102_008/README.md`](../hospital_sentences_20261102_008/README.md)、第九轮
[`../hospital_sentences_20261102_009/README.md`](../hospital_sentences_20261102_009/README.md)，都在旧片段上。阶段记录：
[TASK-29](../../TASK-29.md)。

用户指示（对话，2026-11-02）：在 `group3/clips-v2` 上用 12 个线程跑轨迹规划；不先修 34 个失败的测试，直接跑；去掉 NURSE
的分阶段出口。代码 `00124363`（没有改代码）；输入 `make_inputs.py`；运行 `run.sh`，12 个词对 run 用 cpu0–11，
18:31–20:18（词对到 19:58，句子 20:16，视频 20:18）。

## 输入（词对策略 `config/transition_policy_hospital_sentences_fast_v7.json`，序列策略 v9）

`fast_v7` 是第八轮的 `fast_v5` 改了三处，其余不变：

- **保护表 v5**（`config/user_protected_hospital35_v5.json`）：NURSE f23–f79、INTERPRETER f19–f40、HURT f37–f57、
  MORNING f26–f37，其余沿用；绑定 clips-v2 的片段哈希。
- **删掉 NURSE 的分阶段出口。** 它是按旧 NURSE 片段（左手垂在腿上）设计的；新 NURSE 结束时左前臂横在胸前、右手在左手腕旁。
  MORNING 的分阶段出口保留。
- **加长搜索**，同第九轮：每个词对 720 → 1800 s（RRT 240 → 600 s）。

序列策略 `config/sequence_policy_hospital_sentences_v9.json`：第八轮的七个多词句子（`v7` 的用例列表），指向 `fast_v7`。
17 个词对分成 12 个批次：涉及改动词或以前难解的 7 个词对各占一个 run，其余 10 个两两共用（见 `make_inputs.py`）。门槛、
速度上限、选优规则（`numerical_pass_then_fewest_stops_then_core_gap_v1`）和平滑定时都与第八轮相同。

身份：词对身份 `8c1a2007…`，代码哈希 `5a67cedd…`，策略哈希 `e0f204e4…`，代码提交 `00124363`。测试文件计入代码哈希，
所以这些 run 只能在本提交、测试不变的情况下续跑或复核。

## 结果：新片段上 7/7 句子 NUMERICAL_PASS

- 17/17 个词对都有数值通过的衔接；选中的 17 个衔接在全新复核中 17/17 一致（`selected_recheck_01`–`12`）。
- 7/7 句子 NUMERICAL_PASS，全新序列复核 7/7 一致（`verify_sequences.log`）；24/24 个保护核心逐位不变；17 个衔接组；
  每个句子都回到初始姿态结束（7 段收尾，8–10 帧，0 次停顿）。
- **衔接中途全停 0 次**，与第八轮相同。16 个衔接用最小加加速度样条，WAIT→DOCTOR 用拐角平滑。
- **NURSE→BLOOD-DRAW 不用分阶段出口**：从 NURSE f79 直接衔接，10 帧（第八轮在旧片段上用 42 帧的分阶段出口）。最小间隙 4.2 mm。
- 17 个衔接的保护核心之间总帧数：310（第八轮）→ **263**；衔接帧数 254 → 215。

| 句子 | 第八轮（旧片段） | 第十轮（clips-v2） |
|---|---|---|
| HELLO YOU APPOINTMENT HAVE | 235 帧（7.8 s） | 233 帧（7.7 s） |
| YOU NEED INTERPRETER | 168 帧（5.6 s） | 143 帧（4.7 s） |
| PLEASE WAIT DOCTOR COME SOON | 366 帧（12.2 s） | 366 帧（12.2 s） |
| YOU HURT WHERE | 120 帧（4.0 s）；第九轮 109 帧 | 109 帧（3.6 s） |
| NOW NURSE BLOOD-DRAW | 271 帧（9.0 s） | 254 帧（8.4 s） |
| MEDICINE MORNING NIGHT TAKE | 164 帧（5.5 s） | 167 帧（5.5 s） |
| YOU UNDERSTAND | 97 帧（3.2 s） | 97 帧（3.2 s） |

- 选中的词对衔接：峰值加加速度 819–1858 rad/s³（门槛 5000），峰值加速度 ≤ 130 rad/s²（门槛 200），最大加加速度积分
  4.89e6 rad²/s⁵（HELLO→YOU；门槛 5e6）。
- 交接里的端点问题：NEED→INTERPRETER 在 f14 进入 INTERPRETER（要求 f16 或更早，因此保留源动作 f14–18）；HAVE 的收尾段从
  f57 出发，即接触段 f41–56 之后的第一帧（也试过 f58，定时失败）。

| 词对 | Run | 尝试 | 通过 | 选中 | 方法 | 曲线 | 切点 | 衔接帧 | 停顿 | 核心间 | 第八轮核心间 | 最小间隙 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NURSE→BLOOD-DRAW | 01 | 50 | 20 | attempt_00008 | direct | min_jerk_spline_v1 | 79→35 | 10 | 0 | 11 | 43 | 4.2 mm |
| NOW→NURSE | 02 | 73 | 62 | attempt_00002 | direct | min_jerk_spline_v1 | 51→23 | 10 | 0 | 10 | 14 | 5.9 mm |
| NEED→INTERPRETER | 03 | 92 | 72 | attempt_00014 | direct | min_jerk_spline_v1 | 93→14 | 10 | 0 | 15 | 26 | 6.2 mm |
| YOU→HURT | 04 | 77 | 58 | attempt_00048 | ik_via1 | min_jerk_spline_v1 | 72→37 | 11 | 0 | 11 | 12 | 9.5 mm |
| HURT→WHERE | 05 | 124 | 89 | attempt_00065 | ik_via1 | min_jerk_spline_v1 | 57→51 | 11 | 0 | 11 | 11 | 8.9 mm |
| MEDICINE→MORNING | 06 | 75 | 12 | attempt_00064 | rrt_connect | min_jerk_spline_v1 | 86→25 | 11 | 0 | 29 | 29 | 2.0 mm |
| PLEASE→WAIT | 07 | 57 | 20 | attempt_00028 | ik_via1 | min_jerk_spline_v1 | 66→27 | 22 | 0 | 22 | 22 | 7.7 mm |
| WAIT→DOCTOR | 08 | 72 | 18 | attempt_00012 | neutral | corner_blend_v1 | 84→34 | 32 | 0 | 32 | 32 | 3.4 mm |
| YOU→UNDERSTAND | 08 | 131 | 117 | attempt_00002 | direct | min_jerk_spline_v1 | 72→27 | 9 | 0 | 9 | 9 | 9.0 mm |
| HELLO→YOU | 09 | 115 | 102 | attempt_00002 | direct | min_jerk_spline_v1 | 66→45 | 10 | 0 | 10 | 10 | 9.5 mm |
| MORNING→NIGHT | 09 | 53 | 32 | attempt_00008 | staged_exit | min_jerk_spline_v1 | 37→37 | 14 | 0 | 16 | 13 | 4.0 mm |
| NIGHT→TAKE | 10 | 126 | 90 | attempt_00002 | direct | min_jerk_spline_v1 | 60→51 | 10 | 0 | 10 | 10 | 3.1 mm |
| YOU→NEED | 10 | 55 | 29 | attempt_00042 | rrt_connect | min_jerk_spline_v1 | 72→30 | 8 | 0 | 8 | 8 | 9.1 mm |
| APPOINTMENT→HAVE | 11 | 74 | 42 | attempt_00030 | ik_via1 | min_jerk_spline_v1 | 143→24 | 12 | 0 | 23 | 23 | 9.2 mm |
| DOCTOR→COME | 11 | 116 | 96 | attempt_00002 | direct | min_jerk_spline_v1 | 57→27 | 10 | 0 | 10 | 10 | 8.3 mm |
| COME→SOON | 12 | 131 | 115 | attempt_00002 | direct | min_jerk_spline_v1 | 132→27 | 9 | 0 | 9 | 9 | 8.9 mm |
| YOU→APPOINTMENT | 12 | 63 | 33 | attempt_00032 | neutral | min_jerk_spline_v1 | 72→58 | 16 | 0 | 27 | 29 | 2.8 mm |

`summarize.py` 从运行记录重新生成此表和 `summary.json`。

## 视频

`videos_<句子>/<句子>/`：`comparison.mp4`（上排原始片段、下排序列；正面与侧面；不入库）、`contact_sheet.png`、
`replay.npz`、`baseline.npz`、`report.json`、`independent_verification.json`。用 `scripts/render_sequences.py`（CPU、EGL）
渲染，每个句子一个进程，总共约 1 分钟。未经人工观看。交互回放：
`.venv/bin/python play_sentence.py results/hospital_sentences_20261102_010/videos_*/*/replay.npz --loop`
（`play_sentence.py` 是本地查看脚本，不入库）。

## 复现

```bash
.venv/bin/python results/hospital_sentences_20261102_010/make_inputs.py   # 只写不存在的文件
bash results/hospital_sentences_20261102_010/run.sh                       # 可续跑；已有步骤会跳过
.venv/bin/python results/hospital_sentences_20261102_010/summarize.py
```

## 偏离与未验证限制

- **没有先修测试。** 交接要求求解前先让全套测试在新片段上通过；按用户要求，本次直接用当时的 `00124363` 运行（988 passed、
  16 failed、18 errors）。测试修复 `a1eb6e53`（1021 passed、1 skipped）于 18:48 推送，正值本次运行期间。测试文件计入代码
  哈希，所以这些 run 只能在 `00124363` 上续跑或复核；要在修好的测试上运行需要新的一轮。
- **12 个 run 而不是 16 个**，按用户要求（12 个线程）；词对到 run 的分配与第八轮不同。
- **NURSE 的分阶段出口是删掉而不是重新设计。** 直接衔接已经通过，本轮不需要重新设计。
- MEDICINE→MORNING 的最小间隙正好 2.0 mm（门槛），与第八轮相同；YOU→APPOINTMENT 2.8 mm。
- 源动作一侧的发现（审查范围 v4 下仅作记录，归第二组）：保护核心之外保留的源帧在五个句子里有采样穿透，最深 −49.1 mm
  （NOW NURSE BLOOD-DRAW）；YOU HURT WHERE 和 YOU UNDERSTAND 没有。
- 句子仍从第一个保护核心直接开始；碰撞为逐帧采样，不是连续碰撞证明。
- 原始词对存储（`pair_runs/`）只留本地，不入库。
