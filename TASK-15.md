# TASK-15 — R1 保全与状态核对

[English](TASK-15.en.md)

状态：完成。只读核对目标仓库存在、分支与 HEAD、实际文件、原词库、已有 v2 实现和历史报告。聊天 cwd 与目标不同；按本轮单代理约束未创建子代理。

修改：HANDOFF.md、HANDOFF.en.md；新增本报告及 R1 证据。更新了过时的直接连接/审批阻塞描述，PLAN.md 和历史 TASK 保留。正式状态仍 false/pending。

归档：`/home/kingderman/Documents/ME5412/execution_evidence/auto_cuts_20261031_001/baseline.tar`，863,150,080 字节，SHA-256 `501e2e75d05bad81f93a70e24b76b121370c345f45ee4973dd33ec6ea733d22f`。7,585 条目源/恢复完整匹配，源在保全过程未变。恢复目录 `/tmp/me5412_auto_cuts_20261031_001/repository`。包括 .git、未提交/未跟踪/被忽略结果、原始资产和外部 .venv 符号链接（不解引用）。恢复到新空目录后按 baseline_inventory.json 比对；不能只恢复 HEAD。

命令：`python3 /tmp/me5412_preserve_auto.py` 退出 0；`.venv/bin/python -m pytest -q -p no:cacheprovider tests` 首次受沙箱 socket 限制，退出 1，724 passed、2 failed、23 errors；同一未修改基线经允许临时本机 127.0.0.1 端口后退出 0，749 passed in 43.11s。两份日志均保留在 results/user_protected_auto_20261031_001/R1/。

关键决策：先归档、在恢复副本修改，最终按逐文件安装前哈希校验。COME 使用当前 hospital_v1 的 201 帧 Studio Galt 文件；89 帧 WLASL 文件与保护范围不相容。完整版本绑定及无法重新确认先前视频身份的限制见 HANDOFF.md。

偏差：目标目录不在沙箱可写根，需要最终安装自动审批；基线测试需要本机临时 HTTP 端口。未放宽测试或数值阈值。
