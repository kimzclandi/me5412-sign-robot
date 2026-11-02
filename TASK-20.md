# TASK-20 — R6

[English](TASK-20.en.md)

状态：四对执行和失败诊断交付完成，**数值验收未通过（0/4）**。未获得合格衔接，不把本任务标成算法目标完成。正式开关始终 false，未改变原始动作、保护段或阈值。

运行 user_protected_pilot_20261031_001：117 次尝试，64 个可选候选全部属于 COME→COME，64 份独立完整曲线复核全部因平方 jerk 积分超限失败；另三对规划 TIMEOUT、0 可选候选，保存输入诊断。四对均实际尝试 direct、neutral、ik_via1、ik_via2、retract_approach 和 rrt_connect。有限搜索失败不证明几何无解。

四个视频各另选一条已保存失败曲线，重新从文件完成完整动作独立复核（均 validation_complete=true、numerical_checks_passed=false）。这些是诊断曲线，不是可选解。下表为视频对应曲线的完整指标；它们与规划状态分列，避免把输入诊断误当完整验证。

| 词对 | 规划状态 | 可选候选 | 完整峰值加速度 rad/s² | 完整峰值 jerk rad/s³ | 完整平方 jerk 积分 rad²/s⁵ | 采样最小间隙 mm |
|---|---|---:|---:|---:|---:|---:|
| COME→NOW | TIMEOUT | 0 | 206.817407 | 4889.644865 | 42109091.946263 | 4.730808 |
| NOW→COME | TIMEOUT | 0 | 206.817407 | 4889.644865 | 40474415.433381 | 4.730808 |
| COME→COME | FAILED_QUALITY | 64 | 97.143139 | 2196.390448 | 5634160.454384 | 8.702362 |
| NOW→NOW | TIMEOUT | 0 | 206.817407 | 4889.644865 | 76503824.684449 | 4.730808 |

保护段根因：不含任何新增连接的原动作内部，COME f30～138 平方 jerk 积分 1,850,853.261494；NOW f6～99 为 38,239,278.289876；均超过冻结上限 1,000,000。NOW f31（1.033333 秒）右手腕 roll 加速度 206.817407 >120，f37（1.233333 秒）右小指近端 jerk 4,889.644865 >3000。只使用保护边界内至少 3 帧距离的原始差分模板，因此外部裁剪/连接不能移除该非负积分贡献。复现脚本 R6/audit_protected_sources.py，退出 0 表示计算完成；JSON 的 exceeds_frozen_limit=true 是失败判定。每个实例在对照视频的具体时间见 R6/run_analysis.json 的 failure_video_locations。

视频：results/user_protected_auto_20261031_001/videos_complete/{COME__NOW,NOW__COME,COME__COME,NOW__NOW}/comparison.mp4。每对同时有 trajectory.json、replay.npz、baseline.npz、trajectory_evidence.csv、独立验证 JSON、contact_sheet.png 和 report.json。原始两词上排、算法下排，左正面/右侧面；同一真实时间轴，较短一排结束保持。绿=保护、蓝=保留、红=裁剪、黄=新增。持续显示 FAILED DIAGNOSTIC/未选用、算法窗口、运动学回放。

命令与退出码：plan_four 0；verify_four 0；resume_four 0；renderer_probe 0；render_four 143（SIGTERM，原因未确认，完整首视频及部分第二视频、日志保留）；render_four_fast 0。快速重导出仅关闭阴影/反射和抗锯齿，原轨迹代码、模型几何、碰撞规则和身份不变；R6/fast_render.py 及 videos_complete/render_configuration.json 分别记录脚本和渲染配置，输出使用新目录。完整 argv、工作目录、耗时和日志在对应 *.command.json 与 FINAL/commands.json。

验证：全仓 .venv/bin/python -m pytest -q -p no:cacheprovider tests，退出 0，784 passed in 61.04s；已有本机 HTTP 测试使用临时 127.0.0.1 端口。恢复副本测试，不冒充新环境复现。续跑前后 790 个运行文件字节哈希不变。四对分母 4，完整词库仍 1,225（1,190 异词、35 自对），1,221 NOT_RUN、0 PASS_SIM、L2 未完成。正式质量/碰撞审核 pending 与工程数值按政策哈希冻结是独立事实。

修改/操作：新增真实对照视频导出、标注测试；自动模式代码冻结纳入两个新 CLI；预登记本轮报告索引并仅同步 project_overview.py 的两个下载 SHA。未修改其已有其他改动。偏差：R3 切向筛选回补见 TASK-18；导出中断后另建快速画面目录，不重写旧文件；动作验收失败保留并交回审查，不放宽上限。

