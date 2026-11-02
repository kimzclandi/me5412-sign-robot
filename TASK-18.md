# TASK-18 — R4

[English](TASK-18.en.md)

状态：工程实现完成，真实四对最终通过情况待 R5/R6。算法按保守保护裁剪外侧区间，筛选后有限排序 8 组端点；先 direct，再 neutral、IK、回撤/接近和有界 RRT。保留每次调时曲线、p/v/a 边界、解析质量/限位/耦合和几何结果；只解新增过渡。独立通过候选按 jerk、加速度、过渡 jerk 积分、完整时长排序，旧审批模式保留原排序。

测试：routes_timing_pytest 首次退出 1，97 passed/3 failed；原因是测试错误假设四对必有直接通过候选。真实诊断揭示限位外向速度端点和五次连接越界；失败不应自动提升为可选。修复端点切向可行性检查；测试逐一验证失败的已保存曲线仍准确匹配 p/v/a，同时保留失败理由。最终 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_user_protected_routes.py tests/test_user_protected_cuts.py tests/test_pair_routes_v2.py tests/test_pair_search_v2.py tests/test_pair_timing_v2.py tests/test_pair_fingers_v2.py tests/test_pair_runner_v2.py，退出 0，104 passed in 29.19s。

诊断复现：R4/diagnose_direct.py，命令与退出 0 日志 direct_limit_diagnosis；原测试失败日志原样保留。R3 补充重筛退出 0，最终有效出口/入口 COME→NOW 56/3、NOW→COME 1/28、COME→COME 56/28、NOW→NOW 1/3，见 cut_screen_with_tangents.json。原 R3 证据不覆盖。

关键决策：不保证 direct 能过；边界处限位外向速度在新模式拒绝，各路线在 30 秒总预算中分配时间、预留搜索；8 组是有限搜索短名单，不是无解证明。

偏差：回补 R3 切向检查并记录；测试修正错误成功假设，未放宽生产检查、阈值或改变保护段。修改文件见 changes.json。
