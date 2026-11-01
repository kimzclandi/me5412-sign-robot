# 九个医院句子，第六轮：不再保留重定向翻转的源动作边缘（2026-11-01）

**中文** · [English](README.en.md)

仅为开发证据：正式 PASS_SIM 为 0，`formal_acceptance_enabled=false`，不是已验证的 ASL，未经人工评审。
之前：第四轮 [`../hospital_sentences_20261101_004/README.md`](../hospital_sentences_20261101_004/README.md)
（衔接提速 + 回到初始姿态），第五轮（已取代）[`../hospital_sentences_20261101_005/README.md`](../hospital_sentences_20261101_005/README.md)。

用户反馈：第四轮 NOW NURSE BLOOD-DRAW 中左手异常扭曲（NURSE 第 81 帧）。代码 `27b6304` + `368fc4b`；输入
`make_inputs.py`；运行 `run.sh`，16 个词对 run 用 cpu0–15，22:55–23:32。

## 原因

不是新增的衔接段，而是**保留下来的 NURSE 源动作**。NURSE 的保护核心在第 79 帧结束；紧接着重定向后的片段把左臂翻转：
肩 yaw 约 5 帧内以 15 rad/s 的上限从 -0.15 甩到 -2.62 rad 的限位，腕 roll 停在 1.972 rad 的限位上，前臂缠绕
（`videos_gpu/source_edge_frames_round5_flags.png` 第一行）。第四轮的切点保留了第 80–98 帧，所以翻转被播放出来。
第 79 帧本身有自碰撞（-10.3 mm），衔接不能从那里开始。

## 修正

- `endpoints.retained_edge_screen` = `no_proximal_limit_excursion_v1`（词对策略
  `config/transition_policy_hospital_sentences_fast_v3.json`）：肩或肘关节离开其在保护核心中的活动范围、并碰到核心
  从未碰到的限位，这一整段的每一帧都被标记；这些帧（包括切点帧本身）不得作为核心外的保留部分。NURSE：第 82–116 帧
  被标记，唯一干净且无碰撞的出口是第 80 帧。规划器的切点筛选和两个独立验证器都执行这一检查（证据中的
  `retained_edge_screen`）。腕关节不计入：第五轮的 v1 筛选还标记了 MEDICINE 73–86 和 DOCTOR 28–33，那里只是腕关节停
  在限位上，渲染出来与相邻帧一样，结果卡住了两个句子。
- `endpoints.clamped_joint_stop` = `clamped_joint_stop_v1`：第 80 帧处重定向把左腕 roll 钳在限位上（1.972219 =
  限位 − 1e-6），而回放斜率仍以 0.49 rad/s 冲向限位，任何不越限的衔接都无法延续这个斜率。被钳在限位上、斜率（从衔接
  的角度看）指向限位外的关节，在切点处按停在限位上处理（边界速度为 0）。验证器只对这些关节接受速度跳变，并逐个列出：
  本轮为 NURSE→BLOOD-DRAW 出口的 `left_wrist_roll_joint` 和 HURT→WHERE 出口的 `R_thumb_proximal_yaw_joint`。
- 两条规则都是可选策略字段，旧策略行为不变。测试 `tests/test_retained_edge_screen_v1.py`（8 项）；全套
  **996 passed**（`tests/pytest_full.log`）。

## 结果：7/7 句子 NUMERICAL_PASS，且都回到初始姿态

- 17/17 个选中衔接、7/7 个句子全新复核一致；24/24 个受保护核心逐位不变；所有句子都没有被筛选标记的保留边缘。
- NOW NURSE BLOOD-DRAW：NURSE 现在在第 80 帧结束（第四轮为 98）；NURSE→BLOOD-DRAW 是 38 帧的 RRT 衔接，左臂从身体
  外侧绕到 BLOOD-DRAW 的起始姿态（两核心间 74 帧，第四轮 92）。
  `videos_gpu/NOW__NURSE__BLOOD-DRAW/round4_vs_round6_nurse_exit.png`：从 NURSE 核心结束起每 4 帧一格，正面与侧面；
  上为第四轮（保留了翻转），下为第六轮。
- 回放帧数：HELLO YOU APPOINTMENT HAVE 271、YOU NEED INTERPRETER 198、PLEASE WAIT DOCTOR COME SOON 448、
  YOU HURT WHERE 165、NOW NURSE BLOOD-DRAW 316、MEDICINE MORNING NIGHT TAKE 249、YOU UNDERSTAND 107。17 个词对两核心间
  帧数合计 563（第四轮 570，第二轮 1717）。衔接段手臂平均速度 2.7–12 rad/s；选中词对衔接峰值加加速度
  298–787 rad/s³，峰值加速度 ≤ 95 rad/s²；收尾段与第四轮相同。

| 词对 | run | 尝试 | 通过 | 选中 | 方法 | 切点 | 衔接帧 | 两核心间帧数 | 第四轮 |
|---|---|---|---|---|---|---|---|---|---|
| NURSE→BLOOD-DRAW | 01 | 65 | 2 | attempt_00058 | rrt_connect | 80→1 | 38 | 74 | 92 |
| MORNING→NIGHT | 02 | 67 | 4 | attempt_00051 | rrt_connect | 69→39 | 30 | 30 | 30 |
| PLEASE→WAIT | 03 | 63 | 8 | attempt_00055 | rrt_connect | 85→23 | 36 | 59 | 59 |
| NIGHT→TAKE | 04 | 76 | 28 | attempt_00016 | ik_via1 | 60→51 | 24 | 24 | 24 |
| WAIT→DOCTOR | 05 | 55 | 13 | attempt_00047 | rrt_connect | 107→23 | 30 | 64 | 57 |
| MEDICINE→MORNING | 06 | 77 | 13 | attempt_00060 | rrt_connect | 86→23 | 24 | 44 | 41 |
| YOU→HURT | 07 | 38 | 10 | attempt_00008 | ik_via1 | 72→27 | 43 | 43 | 43 |
| YOU→APPOINTMENT | 08 | 46 | 14 | attempt_00045 | rrt_connect | 73→59 | 24 | 35 | 35 |
| YOU→NEED | 09 | 42 | 20 | attempt_00021 | rrt_connect | 72→30 | 24 | 24 | 24 |
| HELLO→YOU | 10 | 57 | 30 | attempt_00002 | direct | 66→45 | 17 | 17 | 17 |
| NOW→NURSE | 11 | 43 | 19 | attempt_00002 | direct | 51→38 | 15 | 15 | 15 |
| NEED→INTERPRETER | 12 | 105 | 69 | attempt_00014 | direct | 93→14 | 15 | 31 | 34 |
| YOU→UNDERSTAND | 13 | 70 | 51 | attempt_00008 | direct | 73→27 | 12 | 13 | 13 |
| HURT→WHERE | 14 | 55 | 26 | attempt_00040 | rrt_connect | 57→51 | 22 | 22 | 18 |
| DOCTOR→COME | 15 | 130 | 91 | attempt_00002 | direct | 57→27 | 15 | 15 | 15 |
| APPOINTMENT→HAVE | 16 | 40 | 14 | attempt_00008 | ik_via1 | 143→24 | 30 | 41 | 41 |
| COME→SOON | 16 | 131 | 115 | attempt_00002 | direct | 132→27 | 12 | 12 | 12 |

搜索受墙钟时间限制，所以修正没有涉及的词对也可能和第四轮略有不同（WAIT→DOCTOR +7、HURT→WHERE +4、
MEDICINE→MORNING +3、NEED→INTERPRETER −3 帧）。

## 视频

`videos_gpu/<句子>/`：`comparison.mp4`（按用户决定不入库）、`report.json`、`contact_sheet.png`；与第四轮相同的 GPU
渲染（RTX 5060）。未经人工观看。

## 限制

- 只筛选近端（肩/肘）翻转。MEDICINE→MORNING 仍保留 MEDICINE 第 73–86 帧，那里左腕 yaw 停在限位上；渲染看起来正常，
  但需要人工确认。其他源动作问题（碰撞、核心内速度）仍归第二组，只报告不设门槛。
- NURSE 的保护核心本身在自碰撞（第 79 帧 -10.3 mm）和翻转起始处结束；这是源动作/保护区间数据，这里没有改动。
- 句子仍从第一个保护核心开始；采样碰撞检查不是连续碰撞证明；本目录提交后，这些 run 不能在新 HEAD 上续跑或复核。
