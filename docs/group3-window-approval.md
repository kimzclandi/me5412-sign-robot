# P1-1 批准窗口读取与选择

[English](group3-window-approval.en.md) · [任务报告](../TASK-06.md)

新增 `pair_windows.py`。`load_window_approvals(root, policy, library)` 从实际 bundle、原动作文件和外部审核证据重新读入；校验 bundle SHA-256、动作 SHA-256/帧数、审核文档 SHA-256/内容、window_version、唯一 ID/词、真实填写的评审人字段，以及带时区的审核/到期时间。只更改 approved 字符串无法通过。证据完整性和一致性不证明评审人身份；正式人工导入仍属于 P1-8。

保护核心和入口/出口范围是经审阅记录提供的闭区间。入口窗口最晚帧不得超过核心首帧，出口窗口最早帧不得早于核心末帧；越界、次序错误、空侧边界、原词版本变化均拒绝。不会把 library 的几何 core_frames 提示自动认作语义批准。NURSE 等旧硬编码端点例外没有被继承。

`select_pair_windows(source, target, approvals, library)` 对每个角色枚举合法帧，按距原始 sign endpoint 最近、帧号的稳定顺序排序；选用时再次检查审批到期和动作版本。A→B 与 B→A 各自选择；A→A 返回两个独立实例。具体端点的限位/耦合/几何判定属于后续候选与复核任务。

v2 冻结清单现在同时登记真实 bundle 和它引用的审核文件，任何字节变化都会更改运行身份。合同增加可选 valid_until/exceptions 和审核证据的精确格式，并同步更新 policy 中合同哈希；没有改动 v1 政策或旧资产。

实际测试在恢复副本执行：`pytest -q -p no:cacheprovider tests/test_pair_windows_v2.py tests/test_pair_contract_v2.py tests/test_all_pairs_contract.py`，最终退出 0，72 passed。两轮中后一轮针对合同/策略哈希同步后的最终状态；不叠加计数。所有合成审批都仅存在于 pytest 临时目录，标明 synthetic test，不是第二组真实材料。

当前真实 `transition_policy_v2.json` 未配置 approval_file，实际读取明确为 MISSING_APPROVAL_BUNDLE；未生成真实批准，也没有解锁 PASS_SIM。日志、哈希和状态见 results/group3_execution_20261031_001/P1-1/。
