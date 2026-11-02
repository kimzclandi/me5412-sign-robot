# P1-3 边界导数匹配与时间参数化

[English](group3-pair-timing-v2.en.md) · [任务报告](../TASK-08.md)

`pair_timing.py` 的 `boundary_state_v2` 读取未改动原词的真实单侧割线速度和区间内零加速度。`quintic_coefficients_v2` 用固定 p/v/a 求归一化五次曲线；`time_route_v2` 在每次增加时长后重新求系数，重新计算解析位置范围、速度/加速度/jerk、平方 jerk 积分、耦合和时长上限。中间路由 knot 采用零速度/加速度，保持 C2 段衔接。

时长按 30 Hz 量化；每轮都保留时长、指标、失败原因和几何回调证据。给定几何回调时，对每个新曲线重新调用；没有回调时显式标记 `geometry_checked=false`，结果只能叫 TIMED_CANDIDATE，必须交独立完整轨迹复核。不会复用旧碰撞或旧导数结果，不改原词数组/时序。

超速边界、越界 knot、无效输入、有限尝试用尽、最大时长或墙钟预算分别报明确原因；有限搜索失败不等同数学无解。相同位置但不同导数可以生成非零连接，完全零距离也保留有限时长。

实际恢复副本测试：`tests/test_pair_timing_v2.py tests/test_pair_verification_v2.py tests/test_pair_contract_v2.py`，目标 `.venv/bin/python -m pytest -q -p no:cacheprovider`，最终退出 0，**61 passed in 0.38s**。覆盖非零 p/v/a、独立保存文件再读验证、同位置不同导数、零距离、过短/超限时长、原曲线重定时后的新超调、几何重新调用与墙钟中止。一次测试端矩阵求值方向写错导致 1 failed/52 passed，已修复测试并保留日志；没有修改工程阈值。
