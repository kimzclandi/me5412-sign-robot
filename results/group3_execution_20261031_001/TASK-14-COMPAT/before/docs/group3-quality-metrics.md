# P0-4 质量指标与阈值审批表

[English](group3-quality-metrics.en.md) · [执行报告](../TASK-04.md)

正式冻结状态：**pending**。本文件把“平滑”拆成可复算的量、单位和判定方向；提案未获批准前，不改变 `config/transition_policy.json`，也不能产生正式 `PASS_SIM`。

## 指标合同

| 指标 | 算法与范围 | 单位 | 判定方向/限制 |
|---|---|---|---|
| `velocity_jump_*` | 原词边界一侧 5 帧二次最小二乘拟合速度，与连接曲线声明的零端速度比较；手臂/手指分别取最大绝对值 | rad/s | 越小越好；原词线性回放的内部折点不被零端模型掩盖 |
| `acceleration_jump_*` | 同一边界拟合加速度与连接曲线零端加速度比较；手臂/手指分别取最大绝对值 | rad/s² | 越小越好；不是连续原词的证明 |
| `peak_acceleration` | 保存完整轨迹在真实时间戳上 `gradient(gradient(q,t),t)`，`edge_order=2` | rad/s² | 越小越好；含原词离散边界影响 |
| `peak_jerk` | 对上述加速度再按真实时间戳 `gradient` | rad/s³ | 越小越好；线性回放内部折点的真实连续 jerk 未定义 |
| `jerk_integral` | `trapezoid(sum(jerk²), t)`，全保存轨迹 | rad²/s⁵ | 越小越好；为有限差分能量，不是动力学成本 |
| `analytic_connector_*` | 对每段五次曲线用解析导数极值和解析平方 jerk 积分；重新定时后重算 | 对应 SI 角速度单位 | 越小越好；不得只复用旧值 |
| `maximum_transition_duration_s` | 连接段最后时刻减第一时刻 | s | 不超过冻结上限；预算耗尽另报 TIMEOUT |
| 位置/关节限位/耦合误差 | 从保存数组重算；限位和耦合误差为最大绝对/越界量 | rad | 必须满足独立合同；不能只看候选元数据 |

边界拟合使用源侧 `[frame-window+1, frame]`、目标侧 `[frame, frame+window-1]` 的实际时间；窗口不足直接失败。所有差分都记录时间基准、窗口和方法；不会把离散 jerk 写成连续物理保证。

## 开发数据重算

899 条保存候选逐条按上述函数重建；结果与既有 `quality_development_metrics.json` 的 p50/p95/p99/max 全部一致。关键统计：

| 指标 | p50 | p95 | p99 | max |
|---|---:|---:|---:|---:|
| peak arm speed | 15.000000 | 24.999940 | 24.999940 | 24.999940 |
| peak finger speed | 10.000000 | 21.169373 | 25.349300 | 25.349300 |
| peak acceleration | 225.000000 | 374.377234 | 400.741645 | 407.951790 |
| peak jerk | 5853.456528 | 10576.667495 | 11626.783186 | 11734.935362 |
| velocity jump | 8.068215 | 17.886287 | 33.276591 | 33.276591 |
| acceleration jump | 104.735395 | 190.816472 | 317.586360 | 317.586360 |
| jerk integral | 45,779,096.58 | 94,242,015.80 | 115,008,347.67 | 136,104,424.42 |
| transition duration (s) | 0.300000 | 0.400000 | 0.433333 | 0.566667 |

这些是开发扫描观察值，不是独立测试集，也不是阈值审批。连接曲线解析统计另存 JSON。

## 待批阈值提案

提案文件 `quality_threshold_proposal.json` 仍为 `freeze_status=pending`。其中边界跳变容差为 `1e-5` rad/s、`1e-4` rad/s²，峰值/积分/时长给出有限工程上限；这些数值按 1 rad、0.3 s 五次参考曲线的解析量、数值误差裕量和安全上界组织，明确不是从观察样本倒推通过率。以当前原词线性回放直接套用会拒绝候选，这是预期的输入/表示缺口，不是放宽理由。

审批前必须决定：原词是否允许连续化或重新定时；核心/窗口是否允许；是否接受有限差分而非连续导数；手指耦合、动力学和硬件限制如何定义；以及碰撞覆盖提案。改变任何决定后使用新策略版本和新 run_id。

## 验证

`audit_p0_4.py` 对 899 条保存候选、35 个原词和三类解析正例做断言，退出 0。检查 1 rad/1 s 五次曲线的峰值速度 1.875 rad/s、峰值加速度 `10/√3` rad/s²、峰值 jerk 60 rad/s³、jerk 积分 720 rad²/s⁵，并用独立 100001 点积分复核。未运行全仓 pytest；P0-4 的验证目标是度量算法和单位一致性。


v2 提案改用原词线性回放的真实单侧区间速度（相邻样本割线）及区间内零加速度定义边界，当前 v1 五帧二次拟合只保留为旧诊断；不会将拟合值冒充原词的真实连续导数。该差异必须在合同/测量版本中记录。

| 指标 / Metric | 提案上限 / Proposed cap | 单位 / Unit |
|---|---:|---|
| `velocity_jump_arm_rad_s` | 1e-05 | rad/s |
| `velocity_jump_finger_rad_s` | 1e-05 | rad/s |
| `acceleration_jump_arm_rad_s2` | 0.0001 | rad/s² |
| `acceleration_jump_finger_rad_s2` | 0.0001 | rad/s² |
| `peak_acceleration_rad_s2` | 120 | rad/s² |
| `peak_jerk_rad_s3` | 3000 | rad/s³ |
| `jerk_integral_rad2_s5` | 1e+06 | rad²/s⁵ |
| `maximum_transition_duration_s` | 6 | s |
