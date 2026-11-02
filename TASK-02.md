# TASK-02：P0-2 逐词问题与确认清单

[English](TASK-02.en.md) · [项目状态](STATE.md) · [问题清单](docs/group3-all-pairs-word-issues.md)

日期：2026-10-31（Asia/Shanghai）。任务 P0-2：完成。读取 `/home/kingderman/Documents/ME5412-github-latest/word_audit.json`、`/home/kingderman/Documents/ME5412-github-latest/results/group3_all_pairs_startup/endpoint_blockers.json` 和开发运行 `all_pairs_dev_20261031_v2`，生成 35 词结构化清单与双语审阅模板。

## 修改与关键决策

- 新增 `docs/group3-all-pairs-word-issues.md`、`.en.md`，以及 `results/group3_execution_20261031_001/P0-2/word_issue_manifest.json`。
- 明确记录 10 条端点角色问题（10 个词）、30 个词的词内碰撞、8 个词的速率超限；端点问题关联 326 个唯一词对，保留 35 个自对。
- 记录每个词的动作哈希、保护核心提示、原始入口/出口帧、问题帧、最近碰撞对、研究端点和待确认材料。没有改变任何动作、窗口或时序。
- NURSE f80/f81、HURT f66、MEDICINE f73、INTERPRETER f25 等研究端点仍为 pending；审批输入必须绑定动作哈希，不能只改 `approved` 字符串。

## 执行命令与验证

工作目录：`/home/kingderman/Documents/ME5412-github-latest`。执行 `/home/kingderman/Documents/ME5412-github-latest/.venv/bin/python /tmp/me5412-execution-20261031/generate_p0_2.py`（生成器只写入 `/tmp` 恢复副本）并对 JSON 结构、35 词计数、端点数量、问题词数量、动作哈希和影响词对做断言；退出码 0。然后用任务级 hash-guarded installer 写入目标仓库，退出码 0，备份和清单在 `results/group3_execution_20261031_001/TASK-02/`。

P0-2 证据：[`word_issue_manifest.json`](results/group3_execution_20261031_001/P0-2/word_issue_manifest.json)。未运行 pytest；本任务是冻结证据的只读派生，并从原动作重算速率区间。正式质量阈值、保护核心/窗口和修复动作仍待第二组确认。几何证据包含每帧间隙、词级最坏碰撞对；没有逐帧枚举所有碰撞对，不将此任务当作新几何审计。

## 偏差与状态

计划要求逐词列出端点、原词缺陷、帧号、动作哈希、影响词对和第二组确认内容，已全部覆盖。计划中的“问题单”没有规定文件名，因此采用双语 docs 文件和结构化 JSON；不扩大代码范围。P0-2 完成，P0-3 为下一个原子任务；L2 仍未完成。
