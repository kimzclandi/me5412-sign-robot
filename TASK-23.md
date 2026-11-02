# TASK-23 — v3 质量范围：只评分过渡，保护段改为不变性检查

[English](TASK-23.en.md) · [当前状态](STATE.md) · [上一轮 v2 报告](TASK-22.md)

**v3 已实施并重跑四对：数值通过 1/4（NOW→COME），正式 PASS_SIM 仍为 0。** 804 项测试通过（原 799 + 新 5）。正式开关保持 false，阈值未改。

## 决策与原因

用户于 2026-10-31 选择“Score transitions only”。原因：TASK-22 证明受保护原词本身超过质量上限（NOW f6～73 平方 jerk 积分 38,213,419 > 1,000,000，f31 加速度 206.8 > 120，f37 jerk 4889.6 > 3000；COME f30～129 积分 1,479,273 > 1,000,000）。在不得修改原词的前提下，全片评分使任何过渡都不可能通过。

## v3 定义

- 新政策 `config/transition_policy_user_protected_v3.json`（SHA-256 `d0b0209e54a5d5c366285afd78a7bca9ce67f84f90c291c8f7a6eb9c181e9612`）。相对 v2 只改 `policy_id` 与 `quality.full_clip_method` = `finite_difference_30hz_outside_protected_cores_and_analytic_connector_v3`；全部阈值、约束、预算、端点与正式开关不变。
- 峰值加速度、峰值 jerk、平方 jerk 积分只在**保护核心之外**的回放帧上计算（过渡 + 算法保留的非保护原词边缘）。积分只累计两端都在评分范围内的区间。有限差分模板在边界处仍会读取最多 2～3 个保护帧，所以衔接处的不连续仍被计入。
- 保护核心内的加速度/jerk 缺陷继续写入 `protected_source_audit`，标为 `excluded_from_quality_gate`，不再判失败；保护段内的速度、关节限位、耦合缺陷仍判失败。
- 全片的速度、限位、耦合、碰撞（+2 mm）、边界连续性、手指相位，以及保护姿态 bitwise 相同、相对时序不变，仍对整段检查。全片未限定指标另存 `full_clip_unscoped_metrics`，只作参考。
- v3 只允许用于 `user_protected_auto_windows_v1`；人工窗口政策使用会被拒绝。v2 路径数值逐位不变。

代码：`src/sign_robot/pair_contract.py`、`src/sign_robot/pair_verification_v2.py`；测试 `tests/test_transition_scope_v3.py`。规划器未改动。

## 四对结果（run `transition_scope_pilot_20261031_001`）

| 词对 | 状态 | 候选 / 数值通过 | 说明 |
|---|---|---:|---|
| NOW→COME | 数值通过（正式待批） | 20 / 20 | 选中 attempt_00002：direct、同步手指，切点 NOW 77 / COME 23，过渡 0.5 s；限定加速度 44.78、jerk 786.5、积分 586,690，间隙 8.085 mm |
| COME→COME | FAILED_QUALITY | 58 / 0 | 全部仅因积分超限；最佳 1,908,672。拆分显示过渡本身约 0.07万～29万，约 184万～191万来自规划器保留的非保护 COME 尾段（帧 133→177/200） |
| COME→NOW | TIMEOUT | 0 / 0 | 规划超时（RRT/调时墙钟上限），与评分范围无关 |
| NOW→NOW | TIMEOUT | 0 / 0 | 同上 |

全词库分母仍为 1,225（1,190 异词 / 35 同词）：1 对数值通过但正式未批、1 FAILED_QUALITY、2 TIMEOUT、1,221 NOT_RUN、0 PASS_SIM。

## 发现的下一个阻塞

切点候选排序 `endpoint_pairs_v1`（`src/sign_robot/pair_routes.py`）先按边界速度、后按保留长度，因而偏向 COME 慢速的后段帧，保留了 jerk 较大的原词尾段。修改它属于规划器新版本，本轮未做。两个 TIMEOUT 需要单独排查规划预算或路线。

## 启动命令

```bash
.venv/bin/python scripts/plan_all_pairs.py --library hospital_v1 --include-self --policy config/transition_policy_user_protected_v3.json --run-id transition_scope_pilot_20261031_001 --results-root results/user_protected_transition_scope_20261031_001/runs --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW
```

```bash
.venv/bin/python scripts/verify_all_pairs.py --run-id transition_scope_pilot_20261031_001 --results-root results/user_protected_transition_scope_20261031_001/runs
```

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider tests
```

实际：规划 + 验证 11 分 32 秒，退出 0；日志 `results/user_protected_transition_scope_20261031_001/run.log`。pytest 804 passed in 77.53s。

## 未验证限制

- v3 是开发政策（`freeze_status: pending`），不是三组冻结的正式验收；评分范围改变需交叉评审确认。
- NOW→COME 评分帧只有 19 帧（排除 180 个保护帧），结论只覆盖过渡附近。
- 本轮未导出视频，未做人工观看、ASL 可理解性、多词组合、新环境复现或实机。
- 未提交 git，未修改 v2 结果、原动作或模型。
