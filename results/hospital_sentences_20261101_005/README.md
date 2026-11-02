# 九个医院句子，第五轮：保留边缘筛选 v1（2026-11-01）

**中文** · [English](README.en.md)

仅为开发证据：正式 PASS_SIM 为 0，`formal_acceptance_enabled=false`，不是已验证的 ASL，未经人工评审。
**已被第六轮取代**（[`../hospital_sentences_20261101_006/README.md`](../hospital_sentences_20261101_006/README.md)）。
本目录保留作为下述"筛选过宽"的证据。

用户在第四轮 NOW NURSE BLOOD-DRAW 中看到左臂异常扭曲（NURSE 第 81 帧）。NURSE 的切点保留了源动作第 80–98 帧，
重定向后的片段在这里把左肩 yaw 以 15 rad/s 的上限甩到 -2.62 rad 的限位。代码 `27b6304` 新增
`endpoints.retained_edge_screen` = `no_new_arm_limit_contact_v1`（保护核心与切点之间保留的帧，不得让任何手臂关节
贴上核心从未碰到的限位）和 `endpoints.clamped_joint_stop` = `clamped_joint_stop_v1`（切点处被钳在限位上、斜率指向
限位外的关节按停在限位上处理）。输入：`make_inputs.py`；运行 `run.sh`，22:14–22:48。

## 结果：5/7 句子 NUMERICAL_PASS

- NOW NURSE BLOOD-DRAW 通过，NURSE 在第 80 帧出口：翻转不再播放。
- **MEDICINE MORNING NIGHT TAKE** 与 **PLEASE WAIT DOCTOR COME SOON**：BLOCKED_DEPENDENCY。筛选同时标记了 MEDICINE
  第 73–86 帧和 DOCTOR 第 28–33 帧，那里只是腕关节停在限位上；渲染出来与相邻未标记帧看起来一样。于是
  MEDICINE→MORNING（出口 69–73）和 WAIT→DOCTOR（入口 33–34）在词对预算内没找到衔接（碰撞与关节限位）。
- 15/15 个选中衔接、5/5 个句子全新复核一致；15/15 个受保护核心不变。
- 修正（第六轮）：筛选 v2 只标记近端翻转（肩/肘关节离开核心活动范围并碰到新限位的整段），不计腕关节。
