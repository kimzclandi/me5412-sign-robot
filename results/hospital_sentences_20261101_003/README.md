# 九个医院句子，第三轮：衔接提速 + 回到初始姿态（2026-11-01）

**中文** · [English](README.en.md)

仅为开发证据：正式 PASS_SIM 为 0，`formal_acceptance_enabled=false`，不是已验证的 ASL，未经人工评审。
**已被第四轮取代**（[`../hospital_sentences_20261101_004/README.md`](../hospital_sentences_20261101_004/README.md)），
第四轮在修正收尾段搜索后用相同输入重跑。本目录保留作为下述失败的证据。

代码 `0b2528d`：词对候选按"两个保护核心之间的帧数最少"选优（`numerical_pass_then_core_gap_then_smoothness_v1`），
并在最后一个词之后规划回到库中静止姿态的收尾段（`rest_tail_v1`）。输入：`make_inputs.py`；运行：`run.sh`
（16 个词对 run 用 cpu0–15，19:56–20:32）。

## 结果：6/7 句子 NUMERICAL_PASS

- 17/17 个选中的词对衔接全新复核一致（`selected_recheck_*/summary.json`）。
- 6 个句子通过序列独立复核，21/21 个受保护核心逐位不变（`verify_sequences.log`）。
- **YOU NEED INTERPRETER：BLOCKED_DEPENDENCY**。INTERPRETER 的收尾段（`sequences/rest_tails/INTERPRETER.json`）
  没有找到：紧接保护核心的出口帧 60–61 处，手指仍快速冲向关节限位。这两帧的 25 条路径全部超过 6 s 时长上限，
  并用光了 262144 次碰撞采样，没能轮到后面速度较慢的帧。
- 修正（第四轮）：先在每个出口帧只试两条直线路径（直接、经中立姿态），再只在仍可能胜出的帧上试绕行路径。
  相同输入下 INTERPRETER 得到第 67 帧出发、15 帧的直接收尾段。
