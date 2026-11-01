# 九个医院句子：仅衔接段范围（2026-11-01）

**中文** · [English](README.en.md)

仅为开发证据：正式 PASS_SIM 为 0，`formal_acceptance_enabled=false`，不是已验证的 ASL，未经人工评审。

## 用户决定

- 只做用户给出的九个句子，不再做全部 1,225 个词对的扫描（hospital35 的 P1-3 停在 46/79 批之后，见下文）。
- 第三组只负责两个词动作之间的衔接。源动作本身的问题（受保护核心内外的碰撞、超速、质量缺陷）属于第二组：
  记录，但不判失败。

## 新版本（不改旧版本）

| 项目 | 内容 |
|---|---|
| 复核范围 v4 | `CONNECTOR_ONLY_METHOD_V4`（`pair_contract.py`）。只对新增的衔接曲线设门槛：衔接段碰撞、关节限位、耦合、速度，衔接段内部的有限差分加速度/加加速度/加加速度积分（3 帧模板完全落在衔接段内的帧），解析衔接极值，与源动作的位置/速度/加速度边界连续性，受保护核心逐位不变。源片段的发现写入 `source_side_findings`（`informational_only`，归属第二组）。v2/v3 行为不变。 |
| 词对策略 | `config/transition_policy_hospital_sentences_connector_only_v1.json`：重试预算策略（每对 240 s、RRT 80 s）+ v4；所有门槛数值不变（测试核对）。 |
| 序列策略 | `config/sequence_policy_hospital_sentences_v1.json`：七个多词句；BREATHE-DEEP、THANK-YOU 为单词，无衔接。 |
| 代码 | `pair_verification_v2.py`、`sequence_verification.py`（v4 分支）；`plan_sequences.py` 可重复 `--pair-run-dir`（每个词对从规划它的唯一 run 读取，单 run 行为不变）。 |
| 测试 | 新增 `tests/test_connector_only_v4.py`（5 项）；全套 **967 passed**（`tests/pytest_full.log`）。 |

## 结果

四个同身份 run 并行（WSL2，cpu0–3，13:54–14:28）。词对：

| 词对 | run | 尝试 | 候选 | 通过 | 选中 |
|---|---|---|---|---|---|
| HELLO→YOU | 001 | 86 | 25 | 25 | attempt_00033 |
| YOU→APPOINTMENT | 002 | 72 | 3 | 3 | attempt_00063 |
| APPOINTMENT→HAVE | 002 | 73 | 8 | 8 | attempt_00060 |
| YOU→NEED | 002 | 63 | 20 | 20 | attempt_00051 |
| NEED→INTERPRETER | 004 | 121 | 75 | 75 | attempt_00002 |
| PLEASE→WAIT | 003 | 92 | 0 | 0 | — |
| WAIT→DOCTOR | 003 | 78 | 0 | 0 | — |
| DOCTOR→COME | 003 | 129 | 89 | 89 | attempt_00031 |
| COME→SOON | 001 | 112 | 91 | 91 | attempt_00026 |
| YOU→HURT | 001 | 72 | 0 | 0 | — |
| HURT→WHERE | 001 | 120 | 75 | 75 | attempt_00026 |
| NOW→NURSE | 004 | 74 | 16 | 16 | attempt_00009 |
| NURSE→BLOOD-DRAW | 004 | 68 | 0 | 0 | — |
| MEDICINE→MORNING | 001 | 59 | 0 | 0 | — |
| MORNING→NIGHT | 002 | 79 | 7 | 7 | attempt_00023 |
| NIGHT→TAKE | 003 | 82 | 2 | 2 | attempt_00025 |
| YOU→UNDERSTAND | 004 | 86 | 45 | 45 | attempt_00051 |

12 个选中候选的全新独立复核全部一致（`selected_recheck_00[1-4]/summary.json`）。

句子（`sequences/summary.json`，复核 `verify_sequences.log`，3/3 一致）：

| 句子 | 状态 |
|---|---|
| HELLO YOU APPOINTMENT HAVE | NUMERICAL_PASS |
| YOU NEED INTERPRETER | NUMERICAL_PASS |
| YOU UNDERSTAND | NUMERICAL_PASS |
| PLEASE WAIT DOCTOR COME SOON | BLOCKED_DEPENDENCY（PLEASE→WAIT、WAIT→DOCTOR） |
| YOU HURT WHERE | BLOCKED_DEPENDENCY（YOU→HURT） |
| NOW NURSE BLOOD-DRAW | BLOCKED_DEPENDENCY（NURSE→BLOOD-DRAW） |
| MEDICINE MORNING NIGHT TAKE | BLOCKED_DEPENDENCY（MEDICINE→MORNING） |
| BREATHE-DEEP、THANK-YOU | 单词，无衔接；直接播放源动作 |

## 五个无候选词对的原因

规划只检查衔接段。几乎所有尝试都以 `TIMING_MAXIMUM_DURATION_REACHED` 结束：每次时间参数化失败（主要是衔接第一段
`GEOMETRY_AFTER_TIMING_FAILED` 碰撞与 `TIMED_CURVE_JOINT_LIMIT_VIOLATION`）后延长时长，直到超过 6 s。衔接必须在起点
匹配源动作的切点速度；源动作仍在快速运动时，时长越长，五次曲线沿该速度越冲越远，因此更大的预算无效（240 s 下与 30 s
下同样失败，唯一被预算解决的是 YOU→APPOINTMENT）。建议的下一版本：先在加速度/加加速度限内把速度刹到 0 的短段，再规划
路径；进入目标同理。尚未实现。

## 复现

```bash
.venv/bin/python results/hospital_sentences_20261101_001/make_inputs.py   # 只在文件不存在时写入
bash results/hospital_sentences_20261101_001/run.sh
```

## 偏差与未验证限制

- **视频**：WSL 没有 `render_sequences.py` 写死的 Noto CJK 字体（无 sudo），因此用 `render_with_windows_font.py` 包装
  运行（只把标签字体换成 Windows 的微软雅黑，不改计入身份的脚本）。`videos_001/` 在 20 分钟超时处中断：前两句完成，
  `videos_001/YOU__UNDERSTAND` 不完整；`videos_002/` 中的重新渲染按用户要求在提交前被中止，也不完整。YOU UNDERSTAND
  目前没有完整视频；提交后须在新 run 上渲染。视频按用户决定不入库。未经人工观看。
- **身份**：run 的 `code_commit` 为 2875e49（未提交工作树）。本目录随后被提交，之后不能在新 HEAD 上续跑或复核这些
  run；需要新 run。
- **hospital35 主扫描**：迁移到 WSL 后 P1-3 停在 46/79 批（另 rest_018–020 补记 BATCH_COMPLETE）。run 001/003/004
  的崩溃中途词对重放不一致（带墙钟限制的第 3 次及以后尝试；前两次逐位一致）；我两次按错误顺序启动，留下若干
  `BACKLOG_NOT_CLEARED` 调用日志（只追加，结果未改）；run 002 于用户改变范围后平稳停止。原交接 `resume.sh` 在存在
  积压时会同样被拒绝。原始 `pair_runs` 留在本地。
- 采样碰撞检查不是连续碰撞证明；TIMEOUT/无候选不能证明不存在衔接。
