# TASK-25 — v5 手指抬起式到达：消除进入 NOW 的规划超时

[English](TASK-25.en.md) · [当前状态](STATE.md) · [上一轮 v4 报告](TASK-24.md)

**v5 已实施并重跑四对：数值通过 4/4，正式 PASS_SIM 仍为 0。** 812 项测试通过（v4 后 808 + 新 4）。阈值、评分范围与正式开关均未改变。

## 根因

COME→NOW、NOW→NOW 的 TIMEOUT 与碰撞或预算无关。NOW 保护核心从第 3 帧开始，入口只能是第 1～3 帧（第 0 帧在限位上，已被筛除）。这些帧里 16 个手指关节刚离开 0 rad 下限：仅高出 1.5～13 mrad，且以 0.13～0.75 rad/s 向上运动。单段五次多项式要以该速度到达限位附近，必须先下探越过限位：

| 词对 | 过渡时长与越限 |
|---|---|
| COME 132 → NOW 3 | 0.1 s 在限内；0.3 s 越限 0.033 rad；1.0 s 越限 0.21 rad |
| NOW 76 → NOW 3 | ≤0.3 s 在限内；0.5 s 越限 0.019 rad；1.0 s 越限 0.15 rad |

短时长超出加速度/jerk 上限，长时长越过关节限位；调时器失败后只会加长，越限反而增大，直到 30 s 预算耗尽。所有尝试几何均通过。

## v5 改动

- 新政策 `config/transition_policy_user_protected_v5.json`（SHA-256 `4a08faee59d0b1dec77fb5106261a7b2f75d66147278d7646eb51061d198261f`），相对 v4 只改 `policy_id` 与 `endpoints.generator_version` = `protected_cut_search_v3`（保留 v4 边缘排序，增加抬起式到达）。
- `finger_arrival_plan_v1`（`src/sign_robot/pair_fingers.py`）：仅当某独立手指在入口处离限位的余量 < 0.4·|v|·最短时长时启用。依次尝试同一目标词更早的帧作为停靠姿态（最早优先），要求最后一段在关节限位、速度、加速度、jerk 上限内；不可行则标 `feasible: false`。
- `apply_finger_arrival_v1`：手指先平滑到停靠姿态并静止，再用一段短五次多项式重现原词的抬起，到达入口状态。手臂曲线逐系数不变，端点位置/速度/加速度不变，耦合关节从主动关节重算。仅与 synchronous、late 手指策略组合（late 的相位契约保持）；early 不变。
- 切点短名单（v3 生成器）：需要但不可行的入口排最后；可行入口的越限估计不计手指。
- 验证器未改动；保存的轨迹仍由独立验证器从文件重算全部指标。

实际计划：NOW 入口 3 → 从第 0 帧停靠，抬起 0.1 s（加速度 24.7、jerk 1328）；入口 2 → 第 0 帧，0.067 s（加速度 30.0、jerk 2849）；入口 1 不可行；COME 入口无需。

## 四对结果（run `lift_off_arrival_pilot_20261031_001`）

| 词对 | 候选 / 数值通过 | 选中候选 |
|---|---:|---|
| COME→NOW | 7 / 7 | attempt_00016：rrt_connect、同步手指，切点 COME 132 / NOW 2，抬起 0.067 s（8 个主动手指）；过渡 0.733 s；加速度 21.34、jerk 214.0、积分 61,674，间隙 7.616 mm |
| NOW→NOW | 8 / 8 | attempt_00015：rrt_connect、late 手指，切点 NOW 76 / NOW 3，抬起 0.1 s；过渡 1.0 s；加速度 28.60、jerk 269.4、积分 162,443，间隙 4.418 mm |
| NOW→COME | 17 / 17 | 与 v4 相同（attempt_00023，无需抬起） |
| COME→COME | 13 / 13 | 与 v4 相同（attempt_00003，无需抬起） |

全词库分母 1,225（1,190 异词 / 35 同词）：4 对数值通过但正式未批、1,221 NOT_RUN、0 PASS_SIM。

## 启动命令

```bash
.venv/bin/python scripts/plan_all_pairs.py --library hospital_v1 --include-self --policy config/transition_policy_user_protected_v5.json --run-id lift_off_arrival_pilot_20261031_001 --results-root results/user_protected_lift_off_arrival_20261031_001/runs --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW
```

```bash
.venv/bin/python scripts/verify_all_pairs.py --run-id lift_off_arrival_pilot_20261031_001 --results-root results/user_protected_lift_off_arrival_20261031_001/runs
```

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider tests
```

实际：规划 + 验证 6 分 29 秒，退出 0；日志 `results/user_protected_lift_off_arrival_20261031_001/run.log`。pytest 812 passed。新测试 `tests/test_lift_off_arrival_v5.py`。

## 视频

`render_user_protected_pairs.py` 拒绝渲染代码哈希已变化的 run。运行后仅 `src/sign_robot/project_overview.py`（文档目录哈希重钉）变化，因此用同一 v5 政策以 `lift_off_arrival_pilot_20261031_002` 重跑四对：全部 45 条保存的候选曲线的分段与词实例与 run 001 完全一致，仅 `identity` 字段不同，选中候选相同。run 001 未修改。首次渲染尝试因会话中断留下部分输出 `videos_interrupted_partial/`，已保留但不使用。

| 词对 | 保留的原词帧 | 新增过渡 | 视频 |
|---|---|---|---|
| COME→NOW | COME [27,132]；NOW [2,76] | 3.500～4.233 s | [MP4](results/user_protected_lift_off_arrival_20261031_001/videos/COME__NOW/comparison.mp4) |
| NOW→NOW | NOW [3,76]；NOW [3,76] | 2.433～3.433 s | [MP4](results/user_protected_lift_off_arrival_20261031_001/videos/NOW__NOW/comparison.mp4) |
| NOW→COME | NOW [3,77]；COME [27,132] | 2.467～3.267 s | [MP4](results/user_protected_lift_off_arrival_20261031_001/videos/NOW__COME/comparison.mp4) |
| COME→COME | COME [27,132]；COME [27,132] | 3.500～4.233 s | [MP4](results/user_protected_lift_off_arrival_20261031_001/videos/COME__COME/comparison.mp4) |

布局同 TASK-22：上排原始、下排算法；左正面、右侧面；绿=保护、蓝=保留、红=裁剪、黄=新增、灰=保持。每个文件夹另含 trajectory.json、replay.npz、baseline.npz、trajectory_evidence.csv、independent_verification.json、contact_sheet.png 和 report.json。渲染前对每条选中曲线重新运行独立验证器，四对均数值通过（`summary.json`：数值 4，PASS_SIM 0）。与 TASK-22 不同，本次未用快速光栅包装器，使用 MuJoCo 默认渲染设置（阴影、反射开启）；几何与轨迹不受影响。

执行模型查看了 COME→NOW、NOW→NOW 抬起前后的抽帧：此分辨率下手臂在过渡中平滑、无可见跳变；数 mrad 的手指抬起不可见。这不是人工或第二组评审，也不是 ASL 可理解性检查。

```bash
PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 .venv/bin/python scripts/plan_all_pairs.py --library hospital_v1 --include-self --policy config/transition_policy_user_protected_v5.json --run-id lift_off_arrival_pilot_20261031_002 --results-root results/user_protected_lift_off_arrival_20261031_001/runs --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW
```

```bash
PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 .venv/bin/python scripts/verify_all_pairs.py --run-id lift_off_arrival_pilot_20261031_002 --results-root results/user_protected_lift_off_arrival_20261031_001/runs
```

```bash
PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 .venv/bin/python scripts/render_user_protected_pairs.py --run-dir results/user_protected_lift_off_arrival_20261031_001/runs/lift_off_arrival_pilot_20261031_002 --output results/user_protected_lift_off_arrival_20261031_001/videos --pair COME__NOW --pair NOW__NOW --pair NOW__COME --pair COME__COME
```

实际：渲染 38 秒，退出 0；日志 `run_002_and_render.log`、`render_002.log`。之后任何代码修改（包括文档目录哈希重钉）都会让基于 run 002 的渲染再次被拒绝，届时需用新 run_id。

## 未验证限制

- 抬起式到达在原词之前加入一段“手先摆到 NOW 起始手形再抬起”的动作；其观感与 ASL 可理解性未经人工确认。
- v3～v5 是开发政策（`freeze_status: pending`），评分范围、切点与到达规则需三组交叉评审。
- 评分帧很少（21～29 帧），结论只覆盖过渡附近；碰撞为采样检查，非连续碰撞证明。
- 只覆盖 COME/NOW 四对；其余 1,221 对未运行，其他词是否有同类限位问题未知。
- 视频仅为运动学回放，只由执行模型查看了抽帧，不是人工观看；未做人工观看、多词组合、新环境复现或实机。未提交 git；旧结果、原动作和模型未修改。
