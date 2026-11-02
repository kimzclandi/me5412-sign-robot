# 当前项目状态

[English](STATE.en.md) · [下一步交接](HANDOFF.md) · [最新执行报告 TASK-26](TASK-26.md)

更新：2026-11-01（Asia/Shanghai）。范围：第三组词间衔接与多词回放。此次仅刷新状态与交接文档；没有导入配置、修改算法、重新规划、运行轨迹验证器或重跑测试。历史报告记录当时状态；与最新输入冲突时，以本文件的版本区分为准。

## 1. 当前结论

**旧 COME/NOW 配置下，4/4 词对和 12/12 多词工程序列数值通过；最新 35 词保护表已收齐并核对，但尚未导入，尚无新配置运行结果。** 用户无需继续补其余 33 词的时间。下一步由工程执行者导入、检查、回归，再扩展到全库；正式验收仍未完成。

| 状态层 | 当前事实 | 边界 |
|---|---|---|
| 用户输入 | 35/35 词、70 个数值时间，完整唯一；范围与选定源动作相符 | 已核对不等于已安装；未认证源动作语义 |
| 当前配置 | `user_protected_come_now_v2.json` 仍只有 COME/NOW，NOW 为旧 [3,76] | 新表 NOW [27,51] 未生效 |
| 最新保存词对结果 | 4/4 数值通过，46/46 候选独立验证完整且数值通过 | 全库 1,225 对中仍有 1,221 对 NOT_RUN |
| 最新保存序列结果 | 12/12 数值通过；保存的独立复核 12/12 一致；44/44 保护实例不变；32 组 connector | 仅 COME/NOW 的 8 三词和 4 五词工程用例 |
| 媒体 | 12 个序列诊断视频，44/44 视频回放保护实例逐位一致 | 未获人工语义或跨组工程验收 |
| 测试 | TASK-26 记载 24 项序列测试、836 项全套测试通过 | 本次未重跑；未在现有 results 的 `.log/.txt` 定位到对应完整 pytest 输出 |
| 正式状态 | 正式 PASS_SIM=0，`formal_acceptance_enabled=false`，`playback_eligible=false` | 数值通过不等于正式可用或实机安全 |

## 2. 当前基线与保存证据

- 目标目录：`/home/kingderman/Documents/ME5412-github-latest`；聊天工作目录 `/home/kingderman/Documents/ME5412` 是另一检出。
- 分支：`codex/group3-all-pairs-v1`；HEAD：`2875e499d79b7264b3fe0414318b30ca8aab1f4d`。存在未提交和未跟踪实现，HEAD 不能独立复现当前工作树。
- 最新报告：[TASK-26](TASK-26.md)；上一轮 [TASK-25](TASK-25.md) 与 run 002 留作历史。
- 最新 pair run：`sequence_pilot_pairs_20261031_001`，见 [summary.json](results/sequence_pilot_20261031_001/pair_runs/sequence_pilot_pairs_20261031_001/summary.json)。
- 最新序列：[sequences_001/summary.json](results/sequence_pilot_20261031_001/sequences_001/summary.json)；[独立复核汇总](results/sequence_pilot_20261031_001/sequences_001/independent_recheck/summary.json)；[媒体汇总](results/sequence_pilot_20261031_001/videos/summary.json)。
- 实际政策：[transition_policy_user_protected_v5.json](config/transition_policy_user_protected_v5.json)、[sequence_policy_user_protected_v1.json](config/sequence_policy_user_protected_v1.json)，绑定旧 [保护 bundle](config/user_protected_come_now_v2.json)。
- Pair 代码集合 SHA-256（74 文件）：`4080b98e73a121c866115882483ef5b7631532d9add4bed4ff5dfbe214ad9cef`。
- Sequence 代码集合 SHA-256（77 文件）：`1ecfcc9f95830071dfbffbb895cf4f664ca5aecd4b38398ceb91ececdea15bb0`。

本次只读核对：74 个 pair 代码文件、144 个输入文件与冻结清单匹配；pair manifest 的 615 条、46 份候选验证及身份绑定匹配；12 条序列 artifact/保存验证/独立复核的引用匹配；60 个媒体文件及 12 个源引用哈希匹配。没有重新执行物理/轨迹验证，保存证据的检查与重新计算验证是两种证据。

| 词对 | 候选 / 数值通过 | 当前选中 |
|---|---:|---|
| COME→NOW | 7 / 7 | attempt_00016 |
| NOW→NOW | 8 / 8 | attempt_00015 |
| NOW→COME | 18 / 18 | attempt_00013 |
| COME→COME | 13 / 13 | attempt_00003 |

全库分母为 **1,225=1,190 异词对+35 同词对**。`planning_complete=false`、`verification_complete=false`、`L2_complete=false` 是全库状态。四对的正式分类仍为 `FAILED_QUALITY`，必须同时看 `numerical_checks_passed` 与正式门槛原因，不可据此写成数值 0/4。

保存的序列复核最大相对时序误差为 `3.1086244689504383e-15 s`（≤3.11e-15 s），低于 `1e-12 s` 门槛。全部 12 条在首个候选组合通过。它们是运动学工程用例，不是 ASL 句子。

与旧 run 002 相比，NOW→COME 从 17 候选、attempt_00023 变为 18 候选、attempt_00013；其余三对选中相同。原因是墙钟预算导致上次中止的候选本次完成。**机器负载可影响候选池，重跑不保证逐位重现规划选择。** 保存 artifact 的身份核对与数值复核仍可独立进行。

## 3. 最新用户保护输入：已核对，未导入

原表：[手势保护区间填写表.ods](/home/kingderman/Documents/ME5412/outputs/01a18d89-c53d-7340-b2b8-0f8ddfd306f2/手势保护区间填写表.ods)；工作表 `保护区间填写`，A1:C1 为词语/开始秒数/结束秒数，A2:C36 为 35 条记录。SHA-256：`4fe5b3bb3f7d12cf4cd4418b8431325dec48fbed3c29a2a1e29447cdf89667e3`。这是本机外部文件，交接到另一机器时必须携带原文件并核对哈希，不能假设已包含在 Git 中。

已核对：35 词完整唯一、顺序与 hospital 映射一致；70 值均为数值、无公式、无空白；所有 `0≤start<end≤实际末帧时间`。选定 NPZ 时间轴均为 `np.arange(n)/30`。按当前合同外向取整 `[floor(start×30),ceil(end×30)]`，零起始、两端包含，35/35 与 Decimal 计算一致。此核对覆盖选定 NPZ，未独立认证所有预览容器时长或历史视频字节身份。

| 词 | 旧运行保护输入 | 最新表输入 | 下一轮动作 |
|---|---|---|---|
| COME | 0.93–4.40 s → [27,132]，106 帧 | 0.93–4.40 s → [27,132]，106 帧 | 保持区间，纳入新 bundle |
| NOW | 0.13–2.53 s → [3,76]，74 帧 | **0.90–1.70 s → [27,51]，25 帧** | 创建新政策和新 run，重跑 4 对与 12 序列 |
| 其余 33 词 | 未配置用户保护输入 | 全部已填并核对 | 导入和全库预检 |

COME 源 SHA-256：`75d6455408ce6584043baedbd0e049cbeabcad534eda65ef561d2c7293b477a4`；NOW 源 SHA-256：`2d494c13fdf1b44bb11e97004e7b212ea5c45b7b0f8d0b972bd3589ae63e15e3`。**旧 4/4 与 12/12 不能计为新保护范围下通过；即使 COME 不变，新 bundle/政策身份也需重新绑定。**

同名视频选择以 [hospital_v1_motions.json](motions/hospital_v1_motions.json) 的实际 `library`、`motion` 为准，不以 `planned_source` 或目录中先找到的同名视频为准。9 个 mocap 词：HELLO、PLEASE、YOU、APPOINTMENT、COME、BREATHE-DEEP、BLOOD-DRAW、TAKE、WHERE；其余 26 个选用 `motions/wlasl_video_v1/`。例如 HELLO 选用 `motions/studio_galt_v1/HELLO.npz`。

下表是原表的核对摘要，不是已安装配置；原 ODS 与下一轮自动导入结果必须逐行比较。

| 词语 | 开始秒数 | 结束秒数 | 保护帧（两端包含） |
|---|---:|---:|---|
| HELLO | 0.9 | 2.2 | [27,66] |
| PLEASE | 0.9 | 2.17 | [27,66] |
| THANK-YOU | 0.57 | 2.9 | [17,87] |
| SORRY | 0.7 | 5.57 | [21,168] |
| YES | 0.63 | 2.3 | [18,69] |
| NO | 0.7 | 3.5 | [21,105] |
| YOU | 1.53 | 2.37 | [45,72] |
| YOUR | 1.1 | 2.43 | [33,73] |
| ME | 1 | 2.5 | [30,75] |
| DEAF | 1.1 | 1.9 | [33,57] |
| DOCTOR | 1.15 | 1.87 | [34,57] |
| NURSE | 1.27 | 2.63 | [38,79] |
| INTERPRETER | 1 | 2 | [30,60] |
| APPOINTMENT | 2.3 | 4.4 | [69,132] |
| MEDICINE | 0.9 | 2.3 | [27,69] |
| STOMACH | 1.1 | 2.5 | [33,75] |
| HEADACHE | 0.9 | 2.47 | [27,75] |
| HAVE | 0.83 | 1.8 | [24,54] |
| NEED | 1 | 3.1 | [30,93] |
| WAIT | 0.9 | 2.8 | [27,84] |
| COME | 0.93 | 4.4 | [27,132] |
| HURT | 0.9 | 1.9 | [27,57] |
| BREATHE-DEEP | 1.4 | 2.8 | [42,84] |
| BLOOD-DRAW | 1.2 | 5.5 | [36,165] |
| TAKE | 1.7 | 2.6 | [51,78] |
| UNDERSTAND | 0.9 | 2.6 | [27,78] |
| WRITE | 0.9 | 2.3 | [27,69] |
| NOT | 0.9 | 2.27 | [27,69] |
| NOW | 0.9 | 1.7 | [27,51] |
| SOON | 0.9 | 2.9 | [27,87] |
| LATER | 0.9 | 1.7 | [27,51] |
| TOMORROW | 0.83 | 2.2 | [24,66] |
| MORNING | 0.87 | 2.27 | [26,69] |
| NIGHT | 1.3 | 2 | [39,60] |
| WHERE | 1.7 | 2.67 | [51,81] |

## 4. 已实现能力与扩展前缺口

- 已有通用保护读取：`src/sign_robot/pair_windows.py:load_user_protections`。它校验每条绑定，但不保证恰好覆盖 35 词；导入层须额外核对精确集合。
- 已有两词规划、独立验证、增量扫描和真实几何端点筛选；已有 `sequence_contract.py`、`sequence_assembly.py`、`sequence_verification.py` 与三个序列 CLI。无需重新实现多词基础能力。
- `sequence_assembly.combinations()` 先物化整个笛卡尔积再截取 64 项；当前上限没有限制组合构造内存。扩大候选池前需要保序的有界枚举及等价测试。
- 序列规划目前会因任一用例缺少可用 pair 池而整体报错；扩库前需逐用例记录缺失/未完成/无数值候选，并保留固定分母。身份损坏仍应拒绝运行。
- 全库保护核心的限位、速度、耦合和采样几何尚未检查。秒数合法不代表原动作通过工程门槛；不得通过裁剪保护段或改时序掩盖源缺陷。
- `--max-pairs` 只限新增处理的词对数，不限每对全部候选验证费用；规划与验证需要分批、预算和断点清单。已有 COMPLETE 验证会被跳过，重复调用批量 verifier 不等于全新独立复核。

现有数值政策在保护核心外检查保留边缘和新增过渡的加速度/jerk/积分，并检查解析 connector；逐过渡上限 120 rad/s²、3000 rad/s³、1,000,000 rad²/s⁵、connector≤6 s。保护内部加速度/jerk 仅报告；全链限位、速度、耦合、边界和采样几何仍须检查。不能将结果解释为全动作导数连续或连续碰撞证明。

## 5. 下一阶段及责任边界

执行顺序见 [HANDOFF](HANDOFF.md)：冻结现场 → 严格导入 35 词 → 全词预检 → 有界组合和阻塞报告 → 冻结所有代码/政策/用例 → 新 4 对及 12 序列回归 → 分批覆盖 1,225 对 → 固定 111 条序列覆盖与交付审查。当前这些新阶段均未执行。

用户负责说明必须保留的语义片段；工程负责其余裁剪、出入口、时长、衔接与技术验证，`window_provenance=algorithm`。不再要求用户认证技术窗口。若源动作与语义保护要求存在真实冲突，应提交具体词/帧/证据请求源修订，不能擅改用户输入。

尚未完成：新表导入与新版本结果、剩余全库覆盖、人工语义观看、跨组工程评审、neutral 起止、新环境复现、实机和正式验收。这些独立验收与能力不得被开发数值通过替代。正式开关继续关闭；本轮无提交、发布或硬件操作。
