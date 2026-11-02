# TASK-17 — R3

[English](TASK-17.en.md)

状态：完成。筛选 source 出口≥保护终点、target 入口≤保护起点；逐点保存姿态、原时间、单边线性回放速度/零加速度、限位/耦合误差、原生几何最小间隙/最坏接触、速度比例和有效性。算法按边界速度再按保护边界距离排序；外侧裁剪采用保护边界，未改变保护帧。

实际筛选命令：scripts/screen_user_protected_cuts.py --policy config/transition_policy_user_protected_v1.json --output results/user_protected_auto_20261031_001/R3/cut_screen.json，四次 --pair 选择。修复后退出 0。COME→NOW 有效出口/入口 60/4；NOW→COME 2/28；COME 自对 60/28；NOW 自对 2/4。证据为真实动作和机器人几何，不是人工审批。

对应测试首次 60 passed in 13.12s，退出 0；修正边界速度容差后再次回归，结果见 cuts_final_pytest.command.json。脚本初次 SyntaxError 括号错误，退出 1，最小复现即初次命令，日志保留；修正后重跑成功。

修改：pair_routes.py、新增 scripts/screen_user_protected_cuts.py 与 tests/test_user_protected_cuts.py。偏差：新增专用只读筛选 CLI 以持久化所有裁剪点证据；没有调整阈值或自动批准窗口。

R4 真实调时暴露的限位外向切向问题已补充筛选；最终有效出口/入口为 56/3、1/28、56/28、1/3，详见 TASK-18.md 和 cut_screen_with_tangents.json。原筛选证据保留。
