# P1-5 确定性 v2 候选适配

[English](group3-deterministic-routes-v2.en.md) · [任务报告](../TASK-10.md)

`pair_routes.py` 统一 direct、neutral、ik_via1、ik_via2、retract_approach 的输出。每次尝试保存角色帧、审批引用、路径节点/hash、方法参数、原片段预检、手指策略、每次调时的实际曲线与 hash、质量/几何结果和共享候选/pose/node/墙钟预算。

端点只从经 hash 绑定审批的窗口枚举，再按绝对 +2 mm、关节限位和耦合过滤；没有继承旧 hard-coded trim、两词偏好或 source-relative clearance。两个角色与自对分别处理。生成候选仍只返回 FAILED_QUALITY/待独立复核，不能自行生成 PASS_SIM。

neutral/IK 的原语被复用，但整条最终多项式都重新采样检查；某个 factory 失败会保存 ERROR 后继续其他独立方法。回撤/接近先对完整原始几何引导片段加密检查，再最多各取四个几何节点并查最终曲线；这些节点不是原词保护片段，不改变原词核心或时序。引导片段碰撞时该方法明确失败，不能用节点简化掩盖它。

墙钟在原语调用和碰撞批次边界检查；单次底层 IK 调用依赖它自身的有限迭代，当前没有硬实时中断保证。实际 1,225 对的成本与成功率仍待批准输入后的正式运行。

实际恢复副本命令覆盖 route/timing/verifier/contract：最终退出 0，**73 passed in 12.88s**。包括可直连、必须绕行、无效端点、回撤片段碰撞、factory 异常继续、候选预算耗尽、自对及排除运行耗时的稳定 hash。当前真实策略仍因缺批准 bundle 阻塞。
