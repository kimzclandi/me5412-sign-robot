# TASK-19 — R5

[English](TASK-19.en.md)

状态：工程验证器适配完成。保存文件重新读取动作/保护记录/机器人模型、重建全部分段曲线；检查新模式与政策一致、用户保护引用、两次实例、外侧裁剪规则、位姿逐帧完整性、相对时序、p/v/a、完整质量、解析过渡限位/耦合/速率和 1×/2×/4× 几何。原始结点时间仅消除 1e-12 秒内的浮点舍入，保留姿态 bitwise equal；测试验证两次 COME 各 115 帧。人工审批检查在自动模式明确 false，独立输入检查另记 true。

新增保护段内原始运动缺陷和完整曲线极值定位（源帧/源秒/视频时间/关节），几何最坏点标注是否落入保护段。无候选时只诊断输入，不能当完整数值验证。

命令：.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_user_protected_verification.py tests/test_pair_verification_v2.py tests/test_pair_runner_v2.py tests/test_user_protected_windows.py。首次退出 1，73 passed/2 failed，新增几何标注包含 np.bool 导致 JSON 序列化失败；强制转为标准 bool 后最终退出 0，75 passed in 16.14s。两份日志均保留。最小复现：tests/test_pair_runner_v2.py::test_real_independent_verifier_reconstructs_saved_runner_outputs。

覆盖：丢失重复实例、保护误删、保护版本引用变化、伪造人工审批、改写 time_scale、优先平滑再时长。修改 pair_verification_v2.py 和新增测试，见 changes.json。

偏差：修复新增证据的标准 JSON 类型；未调整阈值、删失败或改原始动作。真实四对独立结果留待 R6，不将本任务测试当试点通过。
