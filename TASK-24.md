# TASK-24 — v4 切点排序：优先保留 jerk 小的原词边缘

[English](TASK-24.en.md) · [当前状态](STATE.md) · [上一轮 v3 报告](TASK-23.md)

**v4 已实施并重跑四对：数值通过 2/4（NOW→COME、COME→COME），正式 PASS_SIM 仍为 0。** 808 项测试通过（v3 后 804 + 新 4）。阈值、评分范围与正式开关均未改变。

## 问题与改动

TASK-23 发现 COME→COME 58 候选全部失败，过渡本身积分很小，约 184万～191万来自规划器保留的非保护 COME 尾段。原因是切点候选排序 `endpoint_pairs_v1` 先按边界速度、后按保留长度，偏向 COME 慢速的后段帧 177/200。

用户选择“Fix cut ranking”。新版本：

- 新政策 `config/transition_policy_user_protected_v4.json`（SHA-256 `de13b9f4e07378bd0226b837d261738463228887e32cbbfc5c0ba8dff7fcc9a9`），相对 v3 只改 `policy_id` 与 `endpoints.generator_version` = `protected_cut_search_v2`。
- `retained_edge_jerk_v2`（`src/sign_robot/pair_routes.py`）用与验证器相同的 30 Hz 有限差分，估算保护核心到切点之间保留原词帧的平方 jerk 积分。
- 在 v2 切点生成器下，候选排序为：限位越界估计 → **保留边缘 jerk 估计** → 边界速度 → 位移 → 保留长度。旧 v1 生成器（v2/v3 政策）排序不变。
- `protected_cut_search_v2` 只能与 v3 评分范围同用，否则政策被拒绝。
- 这只是排序估计；保存的轨迹仍由独立验证器从文件重算全部指标。

短名单对比（v3 → v4 首选切点）：COME→COME (177,23) → (132,27)；COME→NOW (145,1) → (132,1)；NOW→COME (77,23) → (76,27)；NOW→NOW (82,2) → (76,3)。

## 四对结果（run `edge_aware_cuts_pilot_20261031_001`）

| 词对 | 状态 | 候选 / 数值通过 | 选中候选 |
|---|---|---:|---|
| NOW→COME | 数值通过（正式待批） | 17 / 17 | attempt_00023：rrt_connect、late 手指，切点 NOW 77 / COME 27，过渡 0.8 s；限定加速度 31.71、jerk 317.3、积分 216,253，间隙 8.085 mm |
| COME→COME | 数值通过（正式待批） | 13 / 13 | attempt_00003：direct、early 手指，切点 COME 132 / COME 27（两端正好在保护边界），过渡 0.733 s；加速度 40.65、jerk 442.6、积分 254,410，间隙 4.711 mm |
| COME→NOW | TIMEOUT | 0 / 0 | 规划墙钟上限，未产生候选 |
| NOW→NOW | TIMEOUT | 0 / 0 | 同上 |

全词库分母 1,225（1,190 异词 / 35 同词）：2 对数值通过但正式未批、2 TIMEOUT、1,221 NOT_RUN、0 PASS_SIM。

## 启动命令

```bash
.venv/bin/python scripts/plan_all_pairs.py --library hospital_v1 --include-self --policy config/transition_policy_user_protected_v4.json --run-id edge_aware_cuts_pilot_20261031_001 --results-root results/user_protected_edge_aware_cuts_20261031_001/runs --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW
```

```bash
.venv/bin/python scripts/verify_all_pairs.py --run-id edge_aware_cuts_pilot_20261031_001 --results-root results/user_protected_edge_aware_cuts_20261031_001/runs
```

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider tests
```

实际：规划 + 验证 5 分 9 秒，退出 0；日志 `results/user_protected_edge_aware_cuts_20261031_001/run.log`。pytest 808 passed。新测试 `tests/test_edge_aware_cuts_v4.py`。另：因 TASK-23 在 `docs/README*.md` 增行，同步更新了 `src/sign_robot/project_overview.py` 中钉住的两个目录哈希。

## 下一阻塞与未验证限制

- COME→NOW、NOW→NOW 两对规划超时，与评分和切点无关，需单独排查（RRT/调时墙钟、NOW 起始段几何）。
- v3/v4 是开发政策（`freeze_status: pending`），评分范围与切点规则需交叉评审确认。
- 评分帧很少（NOW→COME 24 帧、COME→COME 21 帧），结论只覆盖过渡附近。
- 本轮未导出视频，未做人工观看、ASL 可理解性、多词组合、新环境复现或实机。
- 未提交 git；v2/v3 结果、原动作和模型均未修改。
