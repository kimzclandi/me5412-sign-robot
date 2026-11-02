# 九个医院句子，第二轮：仅衔接段 + 边界刹车（2026-11-01）

**中文** · [English](README.en.md)

仅为开发证据：正式 PASS_SIM 为 0，`formal_acceptance_enabled=false`，不是已验证的 ASL，未经人工评审。第一轮见
[`../hospital_sentences_20261101_001/README.md`](../hospital_sentences_20261101_001/README.md)。

## 结果：7/7 句子 NUMERICAL_PASS

| 句子 | 状态 |
|---|---|
| HELLO YOU APPOINTMENT HAVE | NUMERICAL_PASS |
| YOU NEED INTERPRETER | NUMERICAL_PASS |
| PLEASE WAIT DOCTOR COME SOON | NUMERICAL_PASS |
| YOU HURT WHERE | NUMERICAL_PASS |
| NOW NURSE BLOOD-DRAW | NUMERICAL_PASS |
| MEDICINE MORNING NIGHT TAKE | NUMERICAL_PASS |
| YOU UNDERSTAND | NUMERICAL_PASS |
| BREATHE-DEEP、THANK-YOU | 单词，无衔接；直接播放源动作 |

序列独立复核 7/7 一致，24 个词出现的受保护核心全部逐位不变（`verify_sequences.log`）。17 个选中衔接的全新复核全部
一致（`selected_recheck_0[1-9]/summary.json`）。

| 词对 | run | 尝试 | 候选=通过 | 选中 | 方法 | 切点（源→目标） |
|---|---|---|---|---|---|---|
| NURSE→BLOOD-DRAW | 01 | 94 | 2 | attempt_00087 | rrt_connect | 98→22 |
| MEDICINE→MORNING | 02 | 109 | 20 | attempt_00005 | direct | 86→23 |
| YOU→UNDERSTAND | 02 | 113 | 86 | attempt_00075 | retract_approach | 115→23 |
| COME→SOON | 03 | 131 | 118 | attempt_00050 | neutral | 132→27 |
| PLEASE→WAIT | 03 | 64 | 5 | attempt_00059 | rrt_connect | 85→23 |
| NIGHT→TAKE | 04 | 49 | 5 | attempt_00025 | retract_approach | 97→23 |
| WAIT→DOCTOR | 04 | 82 | 19 | attempt_00006 | direct | 107→23 |
| MORNING→NIGHT | 05 | 50 | 4 | attempt_00034 | rrt_connect | 69→39 |
| YOU→HURT | 05 | 61 | 22 | attempt_00031 | retract_approach | 115→23 |
| HELLO→YOU | 06 | 81 | 47 | attempt_00035 | ik_via2 | 66→45 |
| YOU→APPOINTMENT | 06 | 71 | 25 | attempt_00039 | retract_approach | 116→23 |
| APPOINTMENT→HAVE | 07 | 61 | 24 | attempt_00005 | direct | 163→24 |
| YOU→NEED | 07 | 62 | 33 | attempt_00040 | rrt_connect | 115→30 |
| DOCTOR→COME | 08 | 131 | 109 | attempt_00040 | neutral | 57→26 |
| NEED→INTERPRETER | 08 | 104 | 52 | attempt_00002 | direct | 93→16 |
| HURT→WHERE | 09 | 131 | 96 | attempt_00030 | neutral | 58→51 |
| NOW→NURSE | 09 | 63 | 24 | attempt_00029 | retract_approach | 78→23 |

## 修正了什么（提交 d1bd7dc）

第一轮的五个失败词对：入选的切点处，源动作的手指关节仍以 8–10 rad/s 冲向关节限位（剩余 0.36–0.63 rad）。衔接必须
匹配该速度，因此越延长越冲过限位/撞到身体；用五次曲线在加加速度门槛 3000 rad/s³ 内也停不下。逐帧检查发现，同一
用户保护窗口里的大多数其他切点只需 1–3 帧即可停下，但原排序（偏好靠近保护核心）只取了最差的那几个。

- `planner.boundary_braking`（`stop_and_go_v1`，可选）：路径无法定时（非超时）时，先用固定长度的五次段停下
  （p0 + v0 T (u − u³ + u⁴/2)，单调、行程 v0T/2；遇限位夹紧，0.4 v0T ≤ 行程时不过冲），入口对称；重定时只延长中间段。
- 启用刹车时，切点名单在原 8 个之后交替加入最多 8 个两端都能刹住的切点组合（所需刹车帧最少者优先）。
- **实际起作用的是第二项**：17 个选中衔接都是“携带边界速度”的普通曲线，落在新加入的切点上；刹车段作为兜底存在，
  本轮未被选中。
- 所有衔接门槛不变；每对预算 480 s（RRT 160 s）；九个 run 用 cpu0–8（含 E 核）并行，15:54–16:22。
- 无 `boundary_braking` 的策略行为与之前逐字节相同（测试覆盖）。新增 `tests/test_boundary_braking_v1.py`（6 项），
  全套 **973 passed**（`tests/pytest_full.log`）。

## 复现

```bash
.venv/bin/python results/hospital_sentences_20261101_002/make_inputs.py   # 只在文件不存在时写入
bash results/hospital_sentences_20261101_002/run.sh
```

## 限制

- 新切点离保护核心更远，保留的源动作边缘更长（源动作归第二组；核心不变）。
- 视频：GPU 渲染，`videos_gpu/<句子>/`（`comparison.mp4` 按用户决定不入库；`report.json`、`contact_sheet.png`
  入库）。两步：WSL 中 `export_render_inputs.py` 复用已保存的独立复核（核对序列文件哈希），导出回放、原始片段与逐帧
  阶段标签；Windows 原生 Python（`_runtime/render-venv`，mujoco 3.15.0）中 `render_gpu_windows.py` 以与
  `render_sequences.py` 相同的布局、相机、配色和编码绘制。GL 渲染器为 NVIDIA GeForce RTX 5060，七句并行共 18 s
  （WSL 软件渲染为每句数分钟）。模型为 `assets/robot` 的副本（MuJoCo 不能打开 `\\wsl.localhost` 路径），渲染前逐文件
  哈希核对一致。标签字体为微软雅黑。`videos/` 是被中止的 WSL 软件渲染，不完整。未经人工观看。
- 采样碰撞检查不是连续碰撞证明。本目录提交后，这些 run 不能在新 HEAD 上续跑或复核。
