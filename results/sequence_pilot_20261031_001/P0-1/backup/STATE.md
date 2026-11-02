# 当前项目状态

[English](STATE.en.md) · [下一步执行交接](HANDOFF.md) · [v5 执行报告](TASK-25.md)

更新：2026-10-31（Asia/Shanghai）。本文件是当前状态摘要；历史运行保持原样，下一步计划不代表已完成。

## 1. 当前结论

**COME/NOW 的四个有序词对在 v5 开发政策下数值通过 4/4；正式 PASS_SIM=0，整体目标尚未完成。** 已保存 45 条候选，45 份保存文件独立验证均完成且数值通过；四条选中轨迹已再次独立复核。多词串联、其余词对和正式验收仍未完成。

| 词对 | 保存候选 / 数值通过 | 选中候选 | 保留原词帧（0 起始、两端包含） | 过渡时长 | 采样最小间隙 |
|---|---:|---|---|---:|---:|
| COME→NOW | 7 / 7 | attempt_00016 | COME [27,132]；NOW [2,76] | 0.733333 s | 7.616 mm |
| NOW→NOW | 8 / 8 | attempt_00015 | NOW [3,76]；NOW [3,76] | 1.000000 s | 4.418 mm |
| NOW→COME | 17 / 17 | attempt_00023 | NOW [3,77]；COME [27,132] | 0.800000 s | 8.085 mm |
| COME→COME | 13 / 13 | attempt_00003 | COME [27,132]；COME [27,132] | 0.733333 s | 4.711 mm |

全库分母为 **1,225 对（1,190 异词对 + 35 同词对）**；仅执行上述 4 对，**1,221 对 NOT_RUN**。`planning_complete=false`、`verification_complete=false`、`L2_complete=false` 是全库状态，不否定这 45 条候选的验证已完成。`formal_acceptance_enabled=false`、`playback_eligible=false`；现有摘要仍将这四对归为 `FAILED_QUALITY`，须同时查看 `numerical_checks_passed` 和正式门槛原因，不能据此写成数值 0/4。

## 2. 当前基线与证据

- 目标目录：`/home/kingderman/Documents/ME5412-github-latest`。聊天工作目录 `/home/kingderman/Documents/ME5412` 是另一检出。
- 分支：`codex/group3-all-pairs-v1`；HEAD：`2875e499d79b7264b3fe0414318b30ca8aab1f4d`。当前含大量未提交/未跟踪实现，不能只靠 HEAD 复现。
- 政策：[transition_policy_user_protected_v5.json](config/transition_policy_user_protected_v5.json)；生成器 `protected_cut_search_v3`。
- 当前运行：`lift_off_arrival_pilot_20261031_002`，位于 [runs 目录](results/user_protected_lift_off_arrival_20261031_001/runs/lift_off_arrival_pilot_20261031_002/summary.json)。以 run 002 为当前代码、输入及视频对应版本；run 001 留作历史。
- 代码集合 SHA-256：`5d0332c2ac5a87e49288302f1517cad90f897ce2bfd46b999e922c4a9dd864bc`。
- 政策文件 SHA-256：`4a08faee59d0b1dec77fb5106261a7b2f75d66147278d7646eb51061d198261f`；规范化政策哈希：`839cbf14ecf37baece107fde30e9cc190501f700943663c6345a5f852e22c850`，二者不是同一种哈希。
- 已核对 [library_manifest.json](results/user_protected_lift_off_arrival_20261031_001/runs/lift_off_arrival_pilot_20261031_002/library_manifest.json) 的 70 个代码文件、144 个输入文件及 [manifest.json](results/user_protected_lift_off_arrival_20261031_001/runs/lift_off_arrival_pilot_20261031_002/manifest.json) 的 607 个条目，均与当前文件匹配。

四个诊断视频均已存在：[COME→NOW](results/user_protected_lift_off_arrival_20261031_001/videos/COME__NOW/comparison.mp4)、[NOW→NOW](results/user_protected_lift_off_arrival_20261031_001/videos/NOW__NOW/comparison.mp4)、[NOW→COME](results/user_protected_lift_off_arrival_20261031_001/videos/NOW__COME/comparison.mp4)、[COME→COME](results/user_protected_lift_off_arrival_20261031_001/videos/COME__COME/comparison.mp4)。它们是数值通过、正式开关关闭的回放预览；`videos_interrupted_partial/` 不作为当前交付证据。

本次进度复核的外部证据保存在 `/home/kingderman/Documents/ME5412/execution_evidence/thread_acceptance_20261031/`：

- [current_v5_fresh_verification.json](/home/kingderman/Documents/ME5412/execution_evidence/thread_acceptance_20261031/current_v5_fresh_verification.json)：实际重新验证四条选中轨迹，数值、验证完整性、保护核心保持均为 true，复核前后身份未变。
- [current_v5_media_review.json](/home/kingderman/Documents/ME5412/execution_evidence/thread_acceptance_20261031/current_v5_media_review.json)：独立比较视频回放中的 8 个保护实例，姿态逐位相同，相对时序误差小于 `9e-16 s`。
- [CURRENT_PROGRESS_REVIEW.md](/home/kingderman/Documents/ME5412/execution_evidence/thread_acceptance_20261031/CURRENT_PROGRESS_REVIEW.md)：复核范围与限制。上述绝对路径是本机审查证据，交接到其他机器时须显式携带，不能假设仓库自带。

**测试证据分层：** [TASK-25](TASK-25.md) 记载 812 项测试通过；本次进度复核与文档整理没有重跑完整 812 项测试。本聊天旧 v2 隔离副本的 831 项测试与 0/4 结果不代表当前 v5，且该副本未安装到当前目标，禁止用它覆盖当前代码。

## 3. 用户保护输入与责任边界

以最新更正的 [user_protected_come_now_v2.json](config/user_protected_come_now_v2.json) 为准，早期区间仅是历史：

| 词 | 用户要求保留 | 30 Hz 保守保护帧 | 实际源动作 | 总帧数 / SHA-256 |
|---|---|---|---|---|
| COME | 0.93–4.40 s | [27,132]，106 帧 | [studio_galt_v1/COME.npz](motions/studio_galt_v1/COME.npz) | 201 / `75d6455408ce6584043baedbd0e049cbeabcad534eda65ef561d2c7293b477a4` |
| NOW | 0.13–2.53 s | [3,76]，74 帧 | [wlasl_video_v1/NOW.npz](motions/wlasl_video_v1/NOW.npz) | 104 / `2d494c13fdf1b44bb11e97004e7b212ea5c45b7b0f8d0b972bd3589ae63e15e3` |

保护段的姿态、顺序、相对时序不得改动；重复词必须作为独立实例完整保留。保护段之外的裁剪、切点、时长和过渡由工程实现负责，`window_provenance=algorithm`，不要求用户认证技术窗口。用户只需在需要时补充语义保留内容、判断新增动作是否影响词义。此前展示原视频的字节身份仍不可得；当前源动作绑定已验证，但不得虚构原视频与动作的完整溯源。

## 4. 数值通过的范围

v3～v5 使用 `finite_difference_30hz_outside_protected_cores_and_analytic_connector_v3`：加速度、jerk、平方 jerk 积分只在保护核心之外评分，包括新增过渡和保留的非保护原词边缘，同时检查解析过渡。全动作速度、关节限位、耦合、边界与采样碰撞仍检查；保护核心检查姿态与时序不变。

v4 通过切点排序避开噪声较大的可删原词边缘；v5 使用 [pair_fingers.py](src/sign_robot/pair_fingers.py) 的 `finger_arrival_plan_v1` / `apply_finger_arrival_v1`，让手指先到较早手形，再短时抬起进入 NOW，解决此前的入口限位问题。它没有修改保护动作。

这次 4/4 不表示原 v2 全片平滑度通过。原 NOW 保护内部的加速度/jerk 超限仍是已报告的源动作问题；现有政策将其作为信息项。评分帧仅 21–29 帧；碰撞检查是有限采样、范围为 `native_moving_non_same_hand_v2`，不构成连续碰撞或所有接触对的证明。ASL 可理解性、三组工程交叉评审、新环境复现和实机均未完成。

`acceptance_pending()` 仍含自动窗口待人工评审的旧语义。这是后续工程状态表达要澄清的事项，不是要求用户审批算法切点，也不能伪造审批或开启正式通过。

## 5. 下一阶段：多词串联试点（未执行）

先冻结 COME/NOW 的全部 **8 个有序三词序列**，验证一进一出的中间词，再扩展词库。两两可衔接不自动证明连续多个词可衔接。

现有 `pair_contract.validate_trajectory_v2` 只允许两个词实例；`pair_routes.assemble_pair_trajectory_v2` 与 `pair_verification_v2.verify_saved_pair_v2` 都有首尾两词假设。旧 `transitions.plan_sentence` 属于另一条流程，不能作为 v5 多词能力的证据。下一步必须增加明确版本的序列合同、组装和独立验证，不能直接拼接完整词对视频或复用两词验证标签。

下一步任务和完成标准见 [HANDOFF.md](HANDOFF.md)：冻结当前基线与序列指标；中间词只组装一个原始切片；逐实例验证保护、逐过渡验证边界、重新检查全链；覆盖 8 个三词组合与重复词压力用例；输出新 run、视频和双语报告。上述工作、其余 1,221 对和全库 L2 均未完成。其余 33 个词的语义保护输入可随后收集，不阻塞当前两词的工程试点。

## 6. 历史版本（不作为当前状态）

| 版本 | 历史结果 | 主要变化 | 报告 |
|---|---|---|---|
| v2 更正区间 | 0/4 数值通过 | 采用最新保护区间，原全片评分失败 | [TASK-22](TASK-22.md) |
| v3 | 1/4 数值通过 | 保护核心外评分 | [TASK-23](TASK-23.md) |
| v4 | 2/4 数值通过 | 切点按保留边缘 jerk 排序 | [TASK-24](TASK-24.md) |
| v5 当前 | 4/4 数值通过，正式 0 | 增加手指抬起式到达 | [TASK-25](TASK-25.md) |

TASK-15～21 是更早区间的历史。历史 FINAL 清单只证明对应运行的检查范围，不能替代当前 v5 或未来多词序列的验收。
