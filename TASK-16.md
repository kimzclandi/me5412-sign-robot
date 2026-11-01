# TASK-16 — R2

[English](TASK-16.en.md)

状态：完成。新增独立用户保护记录/数据类型和算法来源字段；自动窗口不具有人工 approval 字段。保留旧人工审批模式。用户时间文本、保守帧、动作路径/哈希/帧数/时序和视频绑定限制均可追溯。新政策固定原有 constraints、quality、validation、planner 等数值，正式开关 false；工程冻结证据见 R2/engineering_freeze.json。

修改文件见本任务 changes.json（绝对路径/哈希）；合同/窗口/上下文入口以及新增 config、contract、测试。测试时钟通过独立 _utc_now 注入固定测试时间，生产仍检查真实 UTC 和审批过期，未删日期负例。

命令：.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pair_contract_v2.py tests/test_pair_windows_v2.py tests/test_user_protected_windows.py tests/test_pair_routes_v2.py tests/test_pair_verification_v2.py tests/test_pair_runner_v2.py。退出 0，129 passed in 19.48s，日志 R2/contract_windows_pytest.log。覆盖版本/保守保护范围错误、伪造审批字段、丢词、保护误删、旧模式兼容。

关键决策：v2 表示内显式新增 endpoint_mode，用户 protection 与 legacy approval 使用互斥字段。算法窗口来源只允许 algorithm，审核状态仍 pending。

偏差：无功能范围扩大；新增 tests/conftest.py 修复所有相关测试的墙钟日期依赖。R3～R5 生成与独立验证适配尚未执行，不能提前声明试点通过。
