# P1-6 通用有界 RRT

[English](group3-bounded-search-v2.en.md) · [任务报告](../TASK-11.md)

`pair_search.py` 不按词名白名单限制 RRT。有限空间包括模型有限限位的手臂和独立 L_/R_ 手指；耦合 child 不采样，其限位反向收紧 parent 区间，完整姿态从 parent 逐层恢复。固定非驱动坐标不能改变，所有端点先检查全坐标限位与耦合。

搜索为固定 seed 的双向 RRT-Connect，受节点数、碰撞 pose 数、候选数和协作式墙钟约束；边按最大 0.04 rad 全坐标步长检查。手臂相同、手指不同仍有真实控制维度，不使用旧 arm-progress 退化规则。失败明确记录有限预算内未找到，不声称数学无解。

原始路径、捷径路径、控制关节/区间、hash、预算和 seed 全部保留。捷径边逐条重查，时间/手指处理后的最终曲线再查；捷径失败时保留已查 raw 路径并尝试 raw 时间化。raw 线性边通过不代表最终曲线或正式 PASS；独立复核仍为最后门槛。

实际恢复副本测试：`tests/test_pair_search_v2.py tests/test_rrt_connect.py tests/test_pair_timing_v2.py tests/test_pair_routes_v2.py`，最终退出 0，**56 passed in 13.34s**。覆盖固定种子可达障碍、纯手指变化、child 限位反推、极小节点/pose预算、墙钟、非驱动坐标拒绝、无旧白名单、故障捷径后重新检查并保留 raw fallback。一次新增测试夹具的时钟序列不足和“固定坐标”误用了手臂关节已修正，原失败日志保留。真实矩阵未运行、质量/核心/碰撞仍待批准，不能报告正式通过。
