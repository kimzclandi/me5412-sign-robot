# 当前项目状态

[English](STATE.en.md) · [下一步交接](HANDOFF.md) · [最新执行报告 TASK-29](TASK-29.md) · [九句话各轮 TASK-28](TASK-28.md) · [TASK-27](TASK-27.md)

更新：2026-11-02（Asia/Shanghai），第十轮（在第二组新片段 `group2/clips-v2` 上的第一次求解）之后。范围：第三组词间衔接与多词回放。"最新"一节为当前状态；其后是旧片段上第八、九轮的状态，再往后第 0–5 节为 2026-11-01 的历史，标题保持原样；有冲突时以"最新"一节为准。

## 最新（2026-11-02）：新片段 clips-v2，第十轮 7/7 数值通过

**第二组发布了新的词片段（`group2/clips-v2`，`85bc230`）：NURSE 是新动作，另 23 个视频词做了碰撞修复，帧数都没变。工作改在分支 `group3/clips-v2` 上。用户看过渲染后重新标定了 NURSE（f23–f79）和 INTERPRETER（f19–f40），HAVE 与其余词沿用原区间，写成保护表 v5。第十轮按用户要求在新片段上求解九个句子：12 个 run、删掉 NURSE 的分阶段出口、没有先修失败的测试；七个多词句子全部 NUMERICAL_PASS。** 详见 [第十轮](results/hospital_sentences_20261102_010/README.md)、[TASK-29](TASK-29.md)。

| 层级 | 当前事实 | 边界 |
|---|---|---|
| 片段 | `group2/clips-v2`（`85bc230`）：35 个词中 24 个变了（NURSE 新动作，23 个碰撞修复） | 9 个动捕词及 WAIT、NOW 不变 |
| 保护表 | `config/user_protected_hospital35_v5.json`：NURSE [23,79]、INTERPRETER [19,40]、HURT [37,57]、MORNING [26,37]，其余同 v3；全部绑定新片段哈希，规划器加载通过 35/35 | v1–v4 保留 |
| 轨迹 | [第十轮](results/hospital_sentences_20261102_010/README.md)：词对策略 `fast_v7`（第八轮 `fast_v5` + 保护表 v5，删掉 NURSE 分阶段出口，搜索 1800 s），序列策略 `v9`。17/17 个衔接、7/7 个句子全新复核一致；24/24 个保护核心逐位不变；中途停顿 0 次；核心间 263 帧（第八轮 310）；NURSE→BLOOD-DRAW 为 10 帧直接衔接 | 视频未经人工观看；MEDICINE→MORNING 的间隙正好 2.0 mm |
| 测试 | 在 `00124363` 上：988 passed、16 failed、18 errors（旧片段哈希、旧 NURSE 帧、已不入库的原始存储等）。`a1eb6e53`（18:48 推送，第十轮已开始之后）修好：1021 passed、1 skipped | 第十轮在 `00124363` 上用旧测试运行（用户的选择）；测试文件计入代码哈希，第十轮只能在 `00124363` 上复核；要在修好的测试上运行需要新的一轮 |
| Git | 私仓源 `group3/clips-v2` / `ec89a7f`；以公开 `83dffbfc` 为基线同步第十轮非原始内容到 `group3/trajectory-planning` | 按用户2026-11-03要求发布；原始存储与新视频留本地 |

---

## 旧片段（2026-11-02 前）：九个医院句子，第八轮 7/7 数值通过，第九轮重做 YOU HURT WHERE

**2026-11-01 用户把范围改为九个医院句子，第三组只负责衔接；全库 1,225 对扫描停止（P1-3 停在 46/79 批），P1-4、预算重试和更快的扫描器没有运行。第八轮七个多词句子全部 NUMERICAL_PASS，结尾回到初始姿态，衔接中途不再停顿。第九轮按用户要求让 HURT 从第 37 帧开始，单独重做 YOU HURT WHERE，同样 NUMERICAL_PASS（120 → 109 帧）。** 各轮记录、配置、命令与待办见 [TASK-28](TASK-28.md)。

| 层级 | 当前事实 | 边界 |
|---|---|---|
| 范围 | 七个多词句子、17 个词对：HELLO YOU APPOINTMENT HAVE、YOU NEED INTERPRETER、PLEASE WAIT DOCTOR COME SOON、YOU HURT WHERE、NOW NURSE BLOOD-DRAW、MEDICINE MORNING NIGHT TAKE、YOU UNDERSTAND；单词 BREATHE-DEEP、THANK-YOU 直接播放源动作 | 只负责衔接（复核范围 v4）；源动作缺陷记录给第二组，不判失败 |
| 结果 | [第八轮](results/hospital_sentences_20261102_008/README.md)：17/17 衔接、7/7 句子全新复核一致；24/24 保护核心逐位不变；衔接内部停顿 0；17 个衔接两核心间共 310 帧（第二轮 1,717）。[第九轮](results/hospital_sentences_20261102_009/README.md)：YOU HURT WHERE 2/2 衔接、1/1 句子全新复核一致，YOU→HURT 在 HURT 第 37 帧进入，整句 120 → 109 帧 | 视频未经人工观看 |
| 配置 | 词对 `config/transition_policy_hospital_sentences_fast_v5.json`，序列 `config/sequence_policy_hospital_sentences_v7.json`，保护表 `config/user_protected_hospital35_v2.json`（NURSE [38,75]、MORNING [26,37]）；YOU HURT WHERE 为 `fast_v6`、序列 `v8`、保护表 `v3`（HURT [37,57]） | 加速度类门槛按用户允许放宽到 200 rad/s²、5000 rad/s³、5e6 rad²/s⁵；速度上限不变 |
| 代码与测试 | 代码 `1d07d2d`；第九轮 `dfe4bac`（规划代码相同，没有改代码）；全套测试 1014 passed | — |
| Git | 团队仓库 `group3/trajectory-planning`：以清理提交 `86428693` 为基线发布了第八轮非原始快照；第九轮在本地源分支，随后带到 `group3/clips-v2` | 原始存储只保留本地 |
| 正式 | PASS_SIM 0；`formal_acceptance_enabled=false` | 数值通过不等于正式、语义或实机验收 |

**待确认：** 人工观看第八、九轮视频；句子开头仍从第一个保护核心直接开始；HURT 保护区间内第 39–41、47–49 帧仍有源动作的快速摆动（按规则不改）。第 0 节中 24 个源动作受阻词的决定仍未作出，但不阻塞当前范围。

---

> 以下第 0–5 节为 2026-11-01 的历史状态。

## 0. 最新（执行后）：35 词已导入并冻结，预检发现 24 个词受源动作阻塞

**35 词保护表已严格导入并冻结；新保护范围下的回归通过（4/4 词对、12/12 序列）；全库扫描正在分批运行，但无法达到 1,225/1,225，因为 35 个保护核心中有 24 个在源动作本身就违反不可豁免的门槛。** 详见 [TASK-27](TASK-27.md)。

| 层级 | 当前事实 | 边界 |
|---|---|---|
| 输入 | 已从 ODS 严格导入 35/35 条（`config/user_protected_hospital35_v1.json`）；COME [27,132]、NOW [27,51]；导入可逐字节复现 | 未认证语义；旧 COME/NOW bundle 保留给旧 run |
| 预检 | 11 个词通过；24 个词在保护核心内有源缺陷（23 个采样穿透，最深 −52.0 mm；4 个超速）；0 个词缺少端点 | 预计 1,104/1,225 对无论规划何种衔接都会失败，只剩 121 对可能通过；这是预测，不是验证结果 |
| 冻结 | 词对身份 `c4624340…`，代码 `d5e179c2…`（85 个文件），序列身份 `a3f11715…`；全套测试 962 passed，exit 0 | 扫描运行期间任何代码修改都会使身份过期，驱动随即停止 |
| P1-1 四对 | 4/4 选中，76/76 候选数值通过，全新复核 4/4 一致；保护核心逐位不变 | 墙钟预算使候选池随负载变化 |
| P1-2 原 12 条序列 | 12/12 数值通过，全新复核 12/12 一致；44/44 保护实例不变，32 组 connector；12 个视频 | 仅 COME/NOW 工程用例，非 ASL 句子 |
| P1-3 1,225 对 | 在后台按冻结批次运行。10:47 快照：27/79 批完成；已复核 393 对（50 通过、242 失败、101 对 TIMEOUT 无曲线），15 对进行中，817 对未运行；预测受阻的 328 对全部失败，预测可通过的 65 对中 15 对 TIMEOUT（WAIT、HEADACHE、SOON、STOMACH） | 未完成；11:26 起拆为 4 个同身份并行 run（各绑定一个性能核），预计约 15:30 结束；在当前输入下 1,225/1,225 无法达到 |
| P1-4 111 条序列 | 未运行：等待 P1-3 结束。所需 169 对已全部复核；29/111 例的词对全部数值通过（上限），82 例将因依赖受阻 | 仅有冻结的用例清单 |
| 预算重试 | 用户已批准，P1-4 之后运行：新政策只提高规划搜索预算（墙钟 30→240 s 等），新 run 重试通过词之间的 TIMEOUT 词对及受影响用例（10:47 试运行：20 对、10 例） | 已准备并实测拒绝路径，未运行；可能仍失败 |
| 更快的扫描器 | 用户已批准，在预算重试之后作为新版本开发：验证网格去重、端点/源片段缓存、单写者多工作进程 | 未开始；不含跳过源动作受阻词对 |
| 正式 | PASS_SIM 0；`formal_acceptance_enabled=false`；`playback_eligible=false` | 数值通过不等于正式、语义或实机验收 |

**需要决定：** 24 个词需要修订源动作（第二组）、版本化接触规则（政策负责人）或缩窄保护区间（用户）之一；工程不得裁剪核心、修改源动作或放宽门槛。逐词帧、接触部位与深度见 TASK-27 及 `results/hospital35_protected_20261101_001/preflight_final/`。2026-11-01 用户选择先继续扫描，未起草修订请求；该决定仍未作出。


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
