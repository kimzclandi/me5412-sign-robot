# TASK-27：35 词保护导入与全库衔接执行

[English](TASK-27.en.md) · [当前状态](STATE.md) · [交接](HANDOFF.md) · [上一轮 TASK-26](TASK-26.md)

状态：**阶段性报告（P1-5 中期）；P1-3 仍在运行。** 执行日期 2026-11-01（Asia/Shanghai），按 HANDOFF 顺序 P0-1 → P0-7 → P1-1 → P1-2 → P1-3。本文件在代码冻结前创建，以便先完成文档索引哈希维护；结果在冻结后填写，未改动任何冻结源码、测试或索引。

**35 个保护区间已严格导入并冻结。新保护范围下的回归通过：4/4 词对（76/76 候选）、12/12 序列，全新复核一致，44/44 保护实例不变。但预检显示，35 个保护核心中有 24 个在源动作本身就违反不可豁免的门槛。因此在当前输入与门槛下，1,225 对中有 1,104 对无论规划何种衔接都无法通过。全库扫描（P1-3）正按冻结批次运行，以记录实际结果；要再往前推进，需要工程以外的决定。** 测试 962 passed（836 + 新增 126）。正式 PASS_SIM 为 0。

这些是运动学工程检查，不是 ASL 句子或独立语义测试集；视频未经人工观看，未上实机，正式 PASS_SIM 为 0。

## 任务状态

| 任务 | 状态 | 证据 |
|---|---|---|
| P0-1 冻结现场、原表与来源 | 完成 | `baseline/`：分支/HEAD、`git status`（5,672 行）、已跟踪差异、31 个备份文件及 SHA-256；`results/`（11,546 个文件）、`motions/`、`config/`、`contracts/`、`assets/robot/` 的哈希清单；35 个选定动作的来源清单（9 mocap、26 视频） |
| P0-2 严格导入 35 词 | 完成 | `scripts/import_user_protections.py`；`config/` 中的 bundle、政策与出处；ODS 逐字节副本在 `data/user_protection/hospital35_20261101/` |
| P0-3 核心与端点预检 | 完成；**24 个词源动作阻塞** | `scripts/preflight_hospital35.py`；`preflight_dev_001/`（开发）与 `preflight_final/`（冻结代码），逐词结果相同 |
| P0-4 分批预算与单写者 | 完成 | `src/sign_robot/batch_control.py`、`scripts/run_hospital35_batches.py pairs/recheck-pairs` |
| P0-5 惰性组合 | 完成 | `sequence_assembly.combinations` |
| P0-6 逐用例阻塞与序列子批 | 完成 | `plan_sequences.py`、`verify_sequences.py`、`render_sequences.py`、`src/sign_robot/sequence_batches.py`、`run_hospital35_batches.py sequences/aggregate` |
| P0-7 冻结批次、111 例、测试与身份 | 完成 | `batches/`（79 个文件）、`config/sequence_policy_hospital35_v1.json`、`sequence_cases/case_manifest.json`、`freeze/freeze.json` |
| P1-1 新保护范围下的四对 | 完成：4/4 选中，76/76 候选通过，全新复核 4/4 一致 | `pair_runs/hospital35_protected_20261101_001/`、`P1-1/` |
| P1-2 原 12 条序列与视频 | 完成：12/12，复核 12/12，44/44 保护，32 组 connector，12 个视频 | `sequences_regression_001/`、`videos_regression_001/` |
| P1-3 按冻结批次覆盖 1,225 对 | **运行中，未完成**（10:47 快照：27/79 批、393/1,225 对已复核，见下）；在当前输入下 1,225/1,225 数值目标无法达到 | `P1-3.log`、`batch_control/`、`P1-3/` |
| P1-4 111 条序列 | 未运行：等待 P1-3 结束；所需 169 对已全部复核，上限 29/111 | `sequence_cases/case_manifest.json`（已冻结） |
| P1-5 审查与双语文档 | 阶段性：本报告、STATE、HANDOFF、哈希核对 | `P1-5/` |

未写前缀的路径均位于 `results/hospital35_protected_20261101_001/`。

## P0-2 导入 35 个保护区间

- **读取：** 只读取 ODS（SHA-256 `4fe5b3bb3f7d12cf4cd4418b8431325dec48fbed3c29a2a1e29447cdf89667e3`，导入器先核对哈希并拒绝实体声明）工作表 `保护区间填写` A1:C36 中存储的 `office:value`。拒绝公式、空或非数值单元格、非有限值、显示值与存储值不同、未知/重复/漏词、A1:C36 之外的任何内容，以及 `start ≥ end` 或 `end` 超过末帧时间。
- **来源：** 每个词绑定 `motions/hospital_v1_motions.json` 中实际的 `library`/`motion`（文件必须位于所声明的库中且以该词命名），并核对 SHA-256、帧数与 30 Hz 时间轴。
- **帧：** 零起始、两端包含的 `[floor(start×30), ceil(end×30)]`，用 Decimal 计算；加载器的浮点规则必须得到相同的帧，否则拒绝该行。35/35 行一致，每行取整审计见出处文件。
- **输出（从不覆盖；`--check` 在内存中重建并逐字节比较）：**
  - `config/user_protected_hospital35_v1.json`（35 条记录，`retiming_allowed=false`，不编造视频身份），SHA-256 `d19fec39dcc28dd54fa3d93260dbe0bcbec81062cd190669f74681c5172e3ae0`；
  - `config/transition_policy_user_protected_hospital35_v1.json`，为 v5 的副本，只改 `policy_id`、窗口版本与 bundle 路径/哈希，SHA-256 `d0bc6d9182a72bd1e13106c7732206083ae26acc377f8b60829ed431a5bc59c1`；
  - `config/user_protected_hospital35_v1.provenance.json`（工作表、单元格、取值、取整审计、来源绑定）。
- **核对：** COME [27,132]、NOW [27,51]；真实加载器恰好返回 35 个词；旧 bundle、v5 政策和 COME/NOW 动作与基线逐字节相同。完整对照表见 [STATE](STATE.md)。

## P0-3 预检：35 个保护核心中有 24 个在源动作本身违反不可豁免的门槛

预检只读取每个用户保护核心内的原始源样本，不经过规划器。速度、关节限位和耦合按验证器同样的方法检查；几何按验证器对词切片的采样方式（1×/2×/4×，≤1/120 s，≤0.04 rad）检查；两个端点角色用真实端点选择器筛查。核心内加速度与 jerk 和 v5 一样仅作信息。未发现全局输入阻塞，每行都在预算内完成（无 TIMEOUT）。

**结果：11 个词通过，24 个词存在源缺陷，0 个词缺少可用端点。**

- **通过（11）：** COME、DEAF、HEADACHE、NO、NOT、NOW、SOON、STOMACH、WAIT、WHERE、YOU。
- **保护核心内采样间隙低于 2 mm（23）**，按接触类型：
  - **静止的左手插入左髋/大腿（8）：** LATER、NURSE、PLEASE、THANK-YOU、TOMORROW、UNDERSTAND、YES、YOUR。穿透最深 −52.0 mm（YES）。这些词的左臂并不打手语，看起来是闲置手臂的重定向伪影，而非手语本身。
  - **双手接触（9）：** APPOINTMENT、BLOOD-DRAW、BREATHE-DEEP、HAVE、INTERPRETER、MEDICINE、MORNING、SORRY、WRITE（最深 −49.1 mm，BLOOD-DRAW）。其中部分手语本就要触碰另一只手，但重定向后的双手互相插入。
  - **手触躯干（4）：** DOCTOR、HURT、ME、NIGHT（−2.1 至 −16.1 mm）。ME 本就是指向胸口。
  - **接近但仍低于 2 mm（2）：** HELLO 1.10 mm（右腕–右髋）、NEED 0.25 mm（左腕–左髋）。
- **核心内速度超上限（4）：** HELLO 1.304、PLEASE 1.667（腕滚转）、APPOINTMENT 1.345（腕滚转）、TAKE 1.669（右中指）。TAKE 仅速度不合格。

在冻结的 v5 门槛下，任何包含这 24 个词之一的词对，无论规划出什么衔接，预计都会因 `PROTECTED_SOURCE_QUALITY_VIOLATION` 或 `ORIGINAL_WORD_SLICE_COLLISION` 在独立验证中失败：**1,225 对中的 1,104 对**；只剩通过词之间的 11 × 11 = 121 对仍可能通过。这是基于源数据的预测，不是验证结果；P1-3 仍会规划并验证这些词对。每个缺陷核心在最差帧的静帧位于 `preflight_final/worst_frames/`（运动学渲染，仅由执行模型查看）。

逐词预检（按字母序；粗体表示不合格；端点数为出口与入口角色的有效/候选帧数）：

| 词 | 保护帧 | 预检 | 速度比 | 核心最小间隙 mm | 最差接触 | 出口有效/候选 | 入口有效/候选 |
|---|---|---|---:|---:|---|---:|---:|
| APPOINTMENT | [69,132] | **间隙+速度** | **1.345** | **-8.89** | 左腕–右腕 f74 | 39/55 | 49/70 |
| BLOOD-DRAW | [36,165] | **间隙** | 0.963 | **-49.09** | 左腕–右腕 f65 | 34/51 | 33/37 |
| BREATHE-DEEP | [42,84] | **间隙** | 0.456 | **-12.44** | 左手指–右腕 f77 | 43/55 | 40/43 |
| COME | [27,132] | 通过 | 0.974 | 9.36 | 右手指–右腕 f27 | 65/69 | 28/28 |
| DEAF | [33,57] | 通过 | 0.383 | 6.72 | 右手指–躯干 f44 | 54/57 | 32/34 |
| DOCTOR | [34,57] | **间隙** | 1.000 | **-2.44** | 左腕–躯干 f43 | 55/64 | 34/35 |
| HAVE | [24,54] | **间隙** | 1.000 | **-19.20** | 右手指–左腕 f41 | 33/50 | 24/25 |
| HEADACHE | [27,75] | 通过 | 1.000 | 2.69 | 右手指–躯干 f60 | 37/54 | 27/28 |
| HELLO | [27,66] | **间隙+速度** | **1.304** | **1.10** | 右髋–右腕 f29 | 42/48 | 28/28 |
| HURT | [27,57] | **间隙** | 1.000 | **-4.14** | 左腕–躯干 f33 | 20/59 | 26/28 |
| INTERPRETER | [30,60] | **间隙** | 1.000 | **-14.83** | 左手指–右手指 f31 | 41/42 | 17/31 |
| LATER | [27,51] | **间隙** | 1.000 | **-4.16** | 左髋–左腕 f33 | 15/31 | 27/28 |
| ME | [30,75] | **间隙** | 0.730 | **-2.09** | 右手指–躯干 f71 | 56/60 | 30/31 |
| MEDICINE | [27,69] | **间隙** | 1.000 | **-34.04** | 右手指–左腕 f32 | 36/49 | 15/28 |
| MORNING | [26,69] | **间隙** | 1.000 | **-25.77** | 左手指–右腕 f44 | 20/54 | 26/27 |
| NEED | [30,93] | **间隙** | 0.487 | **0.25** | 左髋–左腕 f40 | 19/49 | 29/31 |
| NIGHT | [39,60] | **间隙** | 1.000 | **-16.15** | 左腕–躯干 f42 | 8/43 | 12/40 |
| NO | [21,105] | 通过 | 1.000 | 3.63 | 左手指–左髋 f83 | 37/49 | 21/22 |
| NOT | [27,69] | 通过 | 1.000 | 2.48 | 左手指–左髋 f35 | 28/42 | 17/28 |
| NOW | [27,51] | 通过 | 1.000 | 9.25 | 右手指–躯干 f27 | 52/53 | 27/28 |
| NURSE | [38,79] | **间隙** | 1.000 | **-45.78** | 左手指–左髋 f78 | 28/48 | 35/39 |
| PLEASE | [27,66] | **间隙+速度** | **1.667** | **-23.52** | 左髋–左腕 f43 | 26/43 | 28/28 |
| SOON | [27,87] | 通过 | 1.000 | 3.57 | 左手指–左髋 f42 | 27/63 | 27/28 |
| SORRY | [21,168] | **间隙** | 0.916 | **-14.07** | 左手指–右腕 f166 | 10/20 | 21/22 |
| STOMACH | [33,75] | 通过 | 0.897 | 5.00 | 左手指–左髋 f42 | 19/37 | 25/34 |
| TAKE | [51,78] | **速度** | **1.669** | 9.50 | 右肘–右腕 f60 | 25/38 | 48/52 |
| THANK-YOU | [17,87] | **间隙** | 1.000 | **-30.06** | 左髋–左腕 f28 | 11/28 | 17/18 |
| TOMORROW | [24,66] | **间隙** | 0.665 | **-30.86** | 左髋–左腕 f24 | 43/47 | 14/25 |
| UNDERSTAND | [27,78] | **间隙** | 1.000 | **-10.77** | 左髋–左腕 f28 | 37/47 | 27/28 |
| WAIT | [27,84] | 通过 | 0.821 | 9.11 | 右手指–躯干 f52 | 46/47 | 27/28 |
| WHERE | [51,81] | 通过 | 0.539 | 8.81 | 左髋–左腕 f58 | 46/55 | 48/52 |
| WRITE | [27,69] | **间隙** | 1.000 | **-34.32** | 左手指–右腕 f32 | 36/63 | 12/28 |
| YES | [18,69] | **间隙** | 1.000 | **-52.00** | 左手指–左髋 f20 | 24/46 | 15/19 |
| YOU | [45,72] | 通过 | 0.261 | 9.50 | 右手指–左腕 f60 | 66/71 | 42/46 |
| YOUR | [33,73] | **间隙** | 1.000 | **-46.55** | 左手指–左髋 f36 | 54/60 | 32/34 |

## P0-4/P0-6 批次与序列控制

- **词对：** 一个 run、一个写者（位于 run 目录外的建议锁）。每个冻结批次最多 16 对，软墙钟 7,200 s，剩余磁盘不低于 5 GiB。预算只在开始新词对规划前和开始新候选复核前检查，因此停止是“软”的；已开始的步骤不会被中断，某对的全部候选复核完成前不会选中。只有之前没有“已规划但未复核”的词对时才开始新批次；已完成的失败在续跑时不重试。规划沿用 v5 的墙钟调度，候选池仍受机器负载影响。
- **停止与漂移：** 创建 `batch_control/<run-id>.stop` 或发送 SIGTERM，会在下一个断点停止。驱动在每个新步骤前还会重新计算代码/输入身份；运行中途修改代码会以 `IDENTITY_CHANGED_DURING_RUN` 停止，而不是保存 ERROR 复核（见“偏差”）。
- **序列：** 每个用例先检查其词对依赖：`PAIR_NOT_PLANNED`、`PAIR_PLANNING_INCOMPLETE`、`PAIR_VERIFICATION_INCOMPLETE`、`PAIR_NO_NUMERICAL_CANDIDATE`。被阻塞的用例记为 `BLOCKED_DEPENDENCY`，运行继续；损坏或过期的词对 run 仍会停止全部运行。
  - 子批最多 8 例，每例软预算 600 s（含规划与验证），软墙钟 7,200 s，64 个组合，磁盘下限 5 GiB。未开始的用例为 `NOT_RUN`，中断的尝试不会被选中。
  - 续跑写入 `<canonical>_resume_NN`，列出读取过的全部旧输出，保留旧的通过选择并跳过已完整验证的尝试；所有旧文件保留。
- **聚合：** 只读取预登记的 canonical 输出及其续跑链，分母固定为 111。已定论为通过或完整未通过的用例只能被原样重述，其他重复一律拒绝（不按最后写入，也不择优）。通过须有匹配的独立复核才计数；原 12 例与新 99 例分开统计；P1-2 回归输出单独保留，不计入。
- **组合：** 按秩和惰性生成，前 64 项与旧的整积排序逐项相同（在 300 种随机形状上测试，并在整积有 10³⁰ 项的五个池上测试且不构造整积）。

## P0-7 冻结

- **批次**（`batches/manifest.json`，SHA-256 `fb7c56187f6a1edded67b3c701fde6746a3c87d49eeff62af303ca19231ebf19`）：互斥，并集等于 1,225 对全集，每批 ≤16。依次为回归 4 对（1 批）、其余 33 个同词对（3 批）、132 个枢纽对（对每个其余词 w：COME→w、w→COME、NOW→w、w→NOW；9 批），以及按全集顺序排列的 1,056 个其他有序词对（66 批）。
- **序列政策** `config/sequence_policy_hospital35_v1.json`（SHA-256 `a37615d852d8db7fcdbdb1fb8c589cc7c21eec33bf9783bc5daa1f27fd4420a6`）：
  - 通过哈希绑定新词对政策，沿用旧的 2–5 词限制及旧的数值与验证预算。
  - 111 例：原 12 例，加上 33 个其余词各自的 `COME__w__NOW`、`NOW__w__COME`、`w__w__w`。
  - 全部通过时应为 341 个词实例、230 组 connector。
  - `sequence_cases/case_manifest.json`（SHA-256 `3e453cfdb89281a2258db7b3719c8d18b9f261bab8d88d4872837d2457bbe8ab`）把用例分成 14 个子批，并记录预期身份。
- **身份**（`freeze/freeze.json`）：词对身份 `c4624340015d9015ecc99231a969c1ab8b9f21aa0dc4844b4159747f59e21941`，代码哈希 `d5e179c27f447ad88208cabd9cd0e171535437fa43d03d42b7a6c77079250468`（85 个文件），序列身份 `a3f11715bfcd12417d1133d9a27bdb438b14494ef372497c80ad765e5389db6a`（88 个文件），环境 `599c49bedf2ffe0a5b933a1b518ec13510d906b7a14b0cd3c3a632851223d835`。最终预检与用例清单使用同一身份。
- **测试（保存日志与退出码）：** 聚焦 222 passed，exit 0（`freeze/pytest_focused_final.log`）；全套 **962 passed**，exit 0（`freeze/pytest_full_candidate_002.log`）；11 个 `--help` 检查 exit 0（`freeze/cli_help.log`）。新增 126 项测试：
  - `test_hospital35_protection_import.py`（29）：真实工作表逐字节相等、上述全部拒绝、过期/错误同名源。
  - `test_hospital35_preflight.py`（7）：注入的限位/耦合/速度/几何缺陷归因正确，加速度/jerk 仅作信息，预算耗尽为 INCOMPLETE，全局阻塞不缩小范围。
  - `test_hospital35_batches.py`（9）：词对之间与复核之间的软停止、磁盘下限、积压门槛、不重试已完成失败、拒绝第二个写者、冻结批次被篡改/重叠/缺漏/超限、停止文件与身份漂移。
  - `test_sequence_combinations.py`（57）与 `test_sequence_blockers.py`（17）：顺序一致、内存有界、依赖状态、预算、续跑检查点、聚合冲突/链/身份，以及复核从不把阻塞用例计为通过。
  - `test_hospital35_freeze.py`（7）：批次并集/互斥、111/341/230、新脚本纳入代码身份及篡改负例。
- **冻结前烟测**（`smoke_pre_freeze_002/`，仅开发）：真实驱动跑回归批次（4/4 选中，74/74 候选通过）、空操作续跑、全新复核（4/4 一致）、序列子批 s001（8/8 通过，复核 8/8）、一个被阻塞子批（8 个 `BLOCKED_DEPENDENCY`）、序列续跑（保留 8 个）、聚合（111 行）与一个视频；随后确认代码身份未变才冻结。

## P1-1 新保护范围下的四个词对（run `hospital35_protected_20261101_001`）

批次驱动规划 `regression_001`，并在选择前独立复核每个保存的候选（437 s，exit 0，日志 `batch_control/pair_batches/regression_001/invocation_001.json`）。对每个选中候选另做的全新 `verify_saved_pair_v2` 复核（`P1-1/selected_recheck/`）4/4 一致。保护核心逐位不变：COME [27,132]、NOW [27,51]。

| 词对 | 尝试 | 候选 / 数值通过 | 选中（方法、手指） | 保留源帧 | 过渡 s | 峰值加速度 | 峰值 jerk | 区内积分 | 间隙 mm |
|---|---:|---:|---|---|---|---:|---:|---:|---:|
| COME→NOW | 31 | 20 / 20 | attempt_00009（neutral，early） | COME [27,132] → NOW [27,51] | 3.500–5.367 | 25.70 | 233.5 | 237,120 | 3.993 |
| NOW→COME | 27 | 18 / 18 | attempt_00013（ik_via2，synchronous） | NOW [27,51] → COME [27,132] | 0.800–2.367 | 29.67 | 279.0 | 322,229 | 9.251 |
| COME→COME | 23 | 13 / 13 | attempt_00003（direct，early） | COME [27,132] → COME [27,132] | 3.500–4.233 | 40.65 | 442.6 | 254,410 | 4.711 |
| NOW→NOW | 36 | 25 / 25 | attempt_00010（neutral，early） | NOW [27,51] → NOW [27,51] | 0.800–2.667 | 25.69 | 246.8 | 294,056 | 3.993 |

**与旧试点 run 比较**（`sequence_pilot_pairs_20261031_001`，NOW [3,76]）：COME→COME 完全相同（选择与指标一致，因为 COME 的保护未变）。三个含 NOW 的词对候选更多（20/18/25，旧为 7/18/8），选择也不同；由于 NOW 核心变短，衔接恰好在 NOW 核心边界离开或进入。三者都是新保护下的新结果，未复用旧结果；全部满足冻结的 v5 上限，正式状态仍待定。

## P1-2 新保护范围下的原 12 条序列（`sequences_regression_001`）

从新的 111 例政策中显式选出原 12 例，只使用同一新词对 run 的候选（四条边均为 `READY`）。12 条全部在 attempt_0001（每条边取第 0 名）通过，另做的全新复核 12/12 一致。下表为各序列所有过渡区中的最坏值；间隙为采样值，不是连续证明。

| 序列 | 时长 s | 峰值加速度 | 峰值 jerk | 区内积分 | 解析 connector 积分 | 间隙 mm |
|---|---:|---:|---:|---:|---:|---:|
| COME–COME–COME | 11.967 | 40.65 | 442.6 | 254,410 | 469,770 | 4.711 |
| COME–COME–NOW | 10.400 | 40.65 | 442.6 | 254,410 | 469,770 | 3.993 |
| COME–NOW–COME | 11.233 | 29.67 | 279.0 | 322,229 | 485,712 | 3.993 |
| COME–NOW–NOW | 8.833 | 25.70 | 246.8 | 294,056 | 504,454 | 3.993 |
| NOW–COME–COME | 10.100 | 40.65 | 442.6 | 322,229 | 485,712 | 4.711 |
| NOW–COME–NOW | 8.533 | 29.67 | 279.0 | 322,229 | 485,712 | 3.993 |
| NOW–NOW–COME | 8.533 | 29.67 | 279.0 | 322,229 | 504,454 | 3.993 |
| NOW–NOW–NOW | 6.133 | 25.69 | 246.8 | 294,056 | 504,454 | 3.993 |
| COME×5 | 20.433 | 40.65 | 442.6 | 254,410 | 469,770 | 4.711 |
| NOW×5 | 11.467 | 25.69 | 246.8 | 294,056 | 504,454 | 3.993 |
| COME–NOW–COME–NOW–COME | 18.967 | 29.67 | 279.0 | 322,229 | 485,712 | 3.993 |
| NOW–COME–NOW–COME–NOW | 16.267 | 29.67 | 279.0 | 322,229 | 485,712 | 3.993 |

- **复核**（`independent_recheck/summary.json`）：12 用例，复核 12，数值通过 12，与规划一致 12。44 个词实例，44 个保护实例全部不变，32 组 connector。最大相对时序误差 3.2e-15 s（门槛 1e-12 s）。
- **NOW 变短：** NOW 现在只保留 [27,51]（25 帧，原为 74 帧），因此含 NOW 的序列比 TASK-26 短（例如 NOW×5 由 16.167 s 变为 11.467 s）。
- **视频**（`videos_regression_001/<序列>/comparison.mp4`）：已渲染 12 个；媒体分母为 12 例中的 12 例。上排为原始片段，下排为序列，正面与侧面。渲染器先重新运行独立验证器，再按绘制视频所用的回放比较保护实例：44/44 逐位一致。执行模型查看了 NOW–COME–NOW–COME–NOW 的联系表，标签显示新的核心终点（NOW f51、COME f132）。这不是人工、第二组或 ASL 可理解性评审。

## P1-3 全库分批（运行中）

驱动在同一 run 中按顺序处理 79 个冻结批次（`P1-3.log`；每次批次调用的只追加日志位于 `batch_control/pair_batches/<批次>/`）。每对先规划、再逐个独立复核全部候选，最后才选择；遇到第一个未完成的批次即停止。实测速度（批次用时 ÷ 词对数，单线程）：同词组每对约 63 s，枢纽组约 80 s，其余组约 64 s；交接时按“每对约 30 s 规划，加每个候选约 4.5 s 复核”估计的 40–50 小时偏保守。按其余组速度，剩余 52 批（832 对）约需 15 小时，约在 2026-11-02 02:00 完成；单批用时 600–1,770 s 不等，实际可能早或晚数小时。**尚未完成。** 下面的快照取自运行期间；尚未处理的词对为 `NOT_RUN`。

**11:26 起并行（不改代码）：** 应用户提速要求，11:24 在断点平稳停止 run 001（rest_017 中途，exit 3），把剩余 50 个冻结批次按清单顺序轮转分给 4 个 run：001 继续自己的切片（含 rest_017），新建 002–004；代码、政策、环境与身份完全相同，每个 run 仍只有一个写入者，各自绑定一个性能核（cpu0–3；规划有墙钟预算，效率核 3.3–3.7 GHz 会减少候选）。词对种子只取决于冻结批次中的位置，与 run 无关。切片写在 `P1-3/parallel_partition.json`（13/13/12/12 批），命令为 `commands/p1_3_parallel.sh`。预计约 15:30 完成（原约 02:00）。
- **与交接的偏差：** HANDOFF 要求“同一新 run”；现在 1,225 对分布在 4 个同身份 run 中。最终表由 `P1-3/scan_progress_multi.py` 合并（每对最多出现在一个 run，身份必须一致），复核按 run 分别执行。P1-4 不受影响：111 例所需的 169 对全部在 run 001。
- **可比性：** 4 个性能核同时满载时频率约 4.4 GHz，单核运行时约 4.8 GHz，30 s 规划预算内的计算量少约 8%；完成后按组比较候选数与 TIMEOUT 比例。停止前快照：`P1-3/progress_20261101_presplit.json`（441 对有记录）。

**快照 2026-11-01 10:47**（只读，`P1-3/progress_20261101_104756.json`，由 `P1-3/scan_progress.py` 生成；03:32 的首个快照保留在 `P1-3/progress_20261101_033213.json`）：

| 组 | 词对 | 数值通过 | 数值失败 | 无曲线（TIMEOUT，仅诊断） | 已规划、待复核 | 规划中 | 未运行 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 回归 | 4 | 4 | 0 | 0 | 0 | 0 | 0 |
| 同词 | 33 | 6 | 15 | 12 | 0 | 0 | 0 |
| 枢纽 | 132 | 27 | 78 | 27 | 0 | 0 | 0 |
| 其余 | 1,056 | 13 | 149 | 62 | 14 | 1 | 817 |
| **全部** | **1,225** | **50** | **242** | **101** | **14** | **1** | **817** |

- **批次：** 27/79 个批次以 BATCH_COMPLETE 结束（regression_001、self_001–003、hub_001–009、rest_001–014），尚无预算停止；rest_015 正在运行。驱动已运行 7 h 37 min，RSS 1.8 GB；词对 run 占 926 MB，磁盘剩余 100 GB。
- **预测核对（393 对已完成独立复核）：** 预测受阻的 328 对全部失败，没有意外通过。预测可通过的 65 对中，50 对通过，15 对在规划预算内没有候选（TIMEOUT）。预检只检查保护核心与端点，不规划衔接，所以“预测可通过”只是必要条件。
- **15 个 TIMEOUT 集中在 4 个通过预检的词：** WAIT 已复核的 12 对全部没有曲线，其中与通过词之间的 7 对为 WAIT–WAIT、COME→WAIT、WAIT→COME、NOW→WAIT、WAIT→NOW、NO→WAIT、YOU→WAIT。HEADACHE 与 SOON 可以进入（COME/NOW/NO→HEADACHE、COME/NOW/NO/YOU→SOON 均通过），但无法离开（HEADACHE→COME、HEADACHE→NOW、HEADACHE–HEADACHE、SOON→COME、SOON→NOW、SOON–SOON），另有 YOU→HEADACHE。STOMACH 只有 STOMACH→COME。TIMEOUT 不能证明不存在衔接。
- **失败原因**（按词对计，一对可有多项）：`ORIGINAL_WORD_SLICE_COLLISION` 220、`FULL_CLIP_SPEED_VIOLATION` 79、`PROTECTED_SOURCE_QUALITY_VIOLATION` 78、峰值加速度 28、jerk 积分 28、峰值 jerk 20。

执行覆盖（每对都已规划并独立复核，允许失败）与数值目标（1,225/1,225 都有可用衔接）是两回事。在当前输入与门槛下，数值目标无法达到（见 P0-3）；扫描记录的是实际失败，而不是直接假定失败。

## P1-4 111 条序列（未运行）

111 例及其 14 个子批已冻结（`sequence_cases/case_manifest.json`）。它们尚未运行：P1-3 仍在写入词对 run，而读取候选池前要先校验整个 run，所以等 P1-3 结束后再运行（HANDOFF 对 P1-4 的前置条件也是 P1-3 完成或停在明确的预算断点）。这 111 例只用到 169 个词对，全部属于回归、同词和枢纽组，截至 10:47 已全部完成独立复核，因此依赖状态已经确定：

- **29/111 例的所有词对都数值通过：** 原 12 例；NO、YOU、DEAF、NOT、WHERE 各自的 `COME__w__NOW`、`NOW__w__COME`、`w__w__w`（15 例）；以及 `COME__STOMACH__NOW`、`STOMACH__STOMACH__STOMACH`。这是上限，序列层面的组合与验证仍可能失败。
- **10 例只因通过预检的词的 TIMEOUT 词对受阻：** HEADACHE、WAIT、SOON 各 3 例，以及 `NOW__STOMACH__COME`（STOMACH→COME）。恢复这些用例属于工程事项（规划预算或端点），需要新版本政策和新 run；当前 run 不变。
- **72 例含源动作受阻的词。**

预检给出的上限 39/111 因此降为 29/111；其余 82 例预计以 `BLOCKED_DEPENDENCY`（`PAIR_NO_NUMERICAL_CANDIDATE`）结束。在当前输入下无法全部通过（341 个词实例、230 组 connector）。

### 已批准的预算重试（P1-4 之后）

用户于 2026-11-01 批准：P1-4 结束后，以更大的版本化预算重试通过词之间的 TIMEOUT 词对。准备情况：

- **新政策** `config/transition_policy_user_protected_hospital35_retry_budget_v1.json`（SHA-256 `bcef2e84…`），由 `retry_budget_001/generate_retry_policy.py` 从冻结政策复制，只提高规划搜索预算：`wall_time_s` 30→240、`rrt.wall_time_s` 10→80、`max_collision_samples` 32,768→262,144、`max_nodes` 4,096→16,384、`max_time_attempts` 12→48。`max_candidates`（128）、验证预算、端点、保护与所有门槛不变；旧政策与旧 run 不变。用冻结代码核对：代码哈希与环境和冻结记录相同，只有政策哈希不同；冻结身份仍可复现。
- **范围规则（在 P1-3 最终表上一次性冻结）：** A = 两个通过词之间以 TIMEOUT 无曲线结束的词对；用例 = 111 例中未全部通过、且失败词对都属于 A 的用例；B = 这些用例用到的全部词对（为让同一 pair run 供给整条序列而重新规划）。新 run `hospital35_retry_budget_001` 规划 A ∪ B；批次清单仍覆盖全集，未列入的词对放在永不执行的 `unrun` 批次。按 10:47 快照试运行：15 个 TIMEOUT 词对 + 5 个额外词对 = 20 对（3 批），10 个用例；冻结的加载器接受生成的清单（`retry_budget_001/dryrun_20261101_1047/`，仅为试运行）。
- **为何可能仍失败：** WAIT–WAIT 的诊断显示，除墙钟限制外，RRT 找到的几何路径还因“手指到位时间放不进衔接段”而定时失败。更大的预算是公平的再试，但不保证成功；结果无论成败都会保留。

## 命令

所有命令都在仓库根目录、以下环境中运行（线程变量属于 run 身份的一部分）：

```bash
cd /home/kingderman/Documents/ME5412-github-latest
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
```

导入（exit 0）与逐字节核对（exit 0，`MATCH`）：

```bash
.venv/bin/python scripts/import_user_protections.py --ods data/user_protection/hospital35_20261101/protection_intervals.ods --expected-sha256 4fe5b3bb3f7d12cf4cd4418b8431325dec48fbed3c29a2a1e29447cdf89667e3
```

```bash
.venv/bin/python scripts/import_user_protections.py --ods data/user_protection/hospital35_20261101/protection_intervals.ods --expected-sha256 4fe5b3bb3f7d12cf4cd4418b8431325dec48fbed3c29a2a1e29447cdf89667e3 --check
```

冻结代码下的预检（exit 0，43 s）：

```bash
.venv/bin/python scripts/preflight_hospital35.py --output results/hospital35_protected_20261101_001/preflight_final
```

测试（全套 962 passed，exit 0，118 s）：

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider tests
```

P1-1 回归批次（exit 0，437 s），随后对选中候选做全新复核（exit 0）：

```bash
.venv/bin/python scripts/run_hospital35_batches.py pairs --batch-manifest results/hospital35_protected_20261101_001/batches/manifest.json --batch-manifest-sha256 fb7c56187f6a1edded67b3c701fde6746a3c87d49eeff62af303ca19231ebf19 --batch regression_001 --run-id hospital35_protected_20261101_001 --results-root results/hospital35_protected_20261101_001/pair_runs --control-dir results/hospital35_protected_20261101_001/batch_control
```

```bash
.venv/bin/python scripts/run_hospital35_batches.py recheck-pairs --run-dir results/hospital35_protected_20261101_001/pair_runs/hospital35_protected_20261101_001 --output results/hospital35_protected_20261101_001/P1-1/selected_recheck
```

P1-2（均 exit 0）；规划命令用 `--case` 列出原 12 例（见 `commands/p1_2.sh`）：

```bash
.venv/bin/python scripts/plan_sequences.py --sequence-policy config/sequence_policy_hospital35_v1.json --pair-run-dir results/hospital35_protected_20261101_001/pair_runs/hospital35_protected_20261101_001 --output results/hospital35_protected_20261101_001/sequences_regression_001 --case COME__COME__COME --case COME__COME__NOW --case COME__NOW__COME --case COME__NOW__NOW --case NOW__COME__COME --case NOW__COME__NOW --case NOW__NOW__COME --case NOW__NOW__NOW --case COME__COME__COME__COME__COME --case NOW__NOW__NOW__NOW__NOW --case COME__NOW__COME__NOW__COME --case NOW__COME__NOW__COME__NOW
```

```bash
.venv/bin/python scripts/verify_sequences.py --run-dir results/hospital35_protected_20261101_001/sequences_regression_001
```

```bash
.venv/bin/python scripts/render_sequences.py --run-dir results/hospital35_protected_20261101_001/sequences_regression_001 --output results/hospital35_protected_20261101_001/videos_regression_001
```

P1-3，按顺序运行全部冻结批次。同一命令即可续跑；仅在冻结身份不变时有效：

```bash
.venv/bin/python scripts/run_hospital35_batches.py pairs --batch-manifest results/hospital35_protected_20261101_001/batches/manifest.json --batch-manifest-sha256 fb7c56187f6a1edded67b3c701fde6746a3c87d49eeff62af303ca19231ebf19 --run-id hospital35_protected_20261101_001 --results-root results/hospital35_protected_20261101_001/pair_runs --control-dir results/hospital35_protected_20261101_001/batch_control
```

在下一个断点平稳停止（续跑前删除该文件）：

```bash
touch results/hospital35_protected_20261101_001/batch_control/hospital35_protected_20261101_001.stop
```

并行续跑（4 个 run，各绑定一个性能核；同一命令可续跑）：

```bash
bash results/hospital35_protected_20261101_001/commands/p1_3_parallel.sh
```

平稳停止全部并行 run：

```bash
for n in 1 2 3 4; do touch results/hospital35_protected_20261101_001/batch_control/hospital35_protected_20261101_00$n.stop; done
```

运行期间的只读进度快照（输出文件须为新文件）：

```bash
.venv/bin/python results/hospital35_protected_20261101_001/P1-3/scan_progress.py results/hospital35_protected_20261101_001/pair_runs/hospital35_protected_20261101_001 results/hospital35_protected_20261101_001/batches/manifest.json results/hospital35_protected_20261101_001/preflight_final/preflight.json results/hospital35_protected_20261101_001/P1-3/progress_$(date +%Y%m%d_%H%M%S).json
```

P1-3 之后的 P1-4（每个子批 `s001`…`s014` 各运行一次，再聚合）：

```bash
.venv/bin/python scripts/run_hospital35_batches.py sequences --sequence-policy config/sequence_policy_hospital35_v1.json --case-manifest results/hospital35_protected_20261101_001/sequence_cases/case_manifest.json --case-manifest-sha256 3e453cfdb89281a2258db7b3719c8d18b9f261bab8d88d4872837d2457bbe8ab --subbatch s001 --control-dir results/hospital35_protected_20261101_001/batch_control
```

```bash
.venv/bin/python scripts/run_hospital35_batches.py aggregate --sequence-policy config/sequence_policy_hospital35_v1.json --case-manifest results/hospital35_protected_20261101_001/sequence_cases/case_manifest.json --case-manifest-sha256 3e453cfdb89281a2258db7b3719c8d18b9f261bab8d88d4872837d2457bbe8ab
```

也可依次运行包装脚本 `commands/p1_3_final.sh`（最终快照，以及对全部已选候选的全新复核）和 `commands/p1_4.sh`（14 个子批、聚合，再为通过的用例渲染视频；重跑时跳过已完成的子批）。P1-3 未结束时两者都以 exit 4 拒绝运行；拒绝路径已实测。

P1-4 之后的预算重试（一次性生成定义，再运行重试词对、复核、受影响用例、聚合与视频；P1-3 或 P1-4 未完成时以 exit 4 拒绝，拒绝路径已实测）：

```bash
bash results/hospital35_protected_20261101_001/commands/retry_budget.sh
```

证据脚本（基线、冻结定义、用例清单与冻结记录生成器、对照、最差帧静帧）与其输出保存在一起；shell 包装脚本位于 `commands/`。

## 文件

新输入与政策（已冻结）：`data/user_protection/hospital35_20261101/protection_intervals.ods`、`config/user_protected_hospital35_v1.json`、`config/user_protected_hospital35_v1.provenance.json`、`config/transition_policy_user_protected_hospital35_v1.json`、`config/sequence_policy_hospital35_v1.json`。

新代码：`scripts/import_user_protections.py`、`scripts/preflight_hospital35.py`、`scripts/run_hospital35_batches.py`、`src/sign_robot/batch_control.py`、`src/sign_robot/sequence_batches.py`。修改：`src/sign_robot/pair_contract.py`、`pair_runner_v2.py`、`sequence_assembly.py`、`scripts/plan_sequences.py`、`verify_sequences.py`、`render_sequences.py`、`src/sign_robot/project_overview.py`（仅文档索引哈希）、`docs/README.md`/`.en.md`（新增一行）。新增 6 个测试文件。

证据位于 `results/hospital35_protected_20261101_001/`：

| 目录 | 内容 |
|---|---|
| `baseline/` | P0-1 基线、备份、哈希清单、来源清单 |
| `import/` | 导入器帮助、写入与 `--check` 日志、导入测试日志 |
| `preflight_dev_001/` | 冻结前的开发预检（仅诊断） |
| `preflight_final/` | 冻结代码的预检；`worst_frames/` 静帧 |
| `batches/` | 79 个冻结批次文件与 `manifest.json` |
| `sequence_cases/` | 冻结的 111 例清单（14 个子批） |
| `freeze/` | 测试日志、CLI 帮助日志、生成脚本、`freeze.json` |
| `smoke_pre_freeze/` | 已作废的开发烟测（见其 INVALIDATED.md） |
| `smoke_pre_freeze_002/` | 冻结前的干净开发烟测 |
| `pair_runs/hospital35_protected_20261101_001/` | 唯一的新词对 run（P1-1 与 P1-3） |
| `batch_control/` | 上限、锁、各批调用日志 |
| `P1-1/` | 四个选中候选的全新复核及与旧 run 的对照 |
| `sequences_regression_001/`、`videos_regression_001/` | P1-2 序列、复核与视频 |

## 需要决定（工程以外）

**2026-11-01 用户选择：继续扫描。** 未起草源动作修订请求；这 24 个词如何处理仍待决定，以下选项保持不变。

在冻结输入与 v5 门槛下，“任意两词衔接”无法达到 1,225/1,225，因为 24 个保护核心在规划任何衔接前就已不合格。工程不得裁剪核心、修改源动作或放宽门槛，以下选项需要由负责人决定。每个词的证据（帧、接触部位、深度、超速关节）见 `preflight_final/preflight.json`、`words.csv` 与 `worst_frames/`。

1. **修订源动作（第二组）：** 重新导出这 24 个动作，使保护核心保持含义但不穿透、不超速。例如把静止的左臂移离髋部（8 个词）；双手和躯干接触保持 ≥2 mm 而不是插入体内；限制 HELLO、PLEASE、APPOINTMENT、TAKE 的腕/指速度尖峰。新文件会改变源哈希，之后需在新文件上确认保护区间。
2. **版本化接触规则（政策负责人）：** 在新政策版本中定义保护核心内哪些接触属于手语本身（例如指定的手–手、手–躯干部位对）以及如何把关。这会改变碰撞范围，需要明确批准；本轮未做。
3. **缩窄保护区间（用户）：** 仅当缺陷位于语义片段之外时可行。闲置手臂的接触覆盖了大部分核心，因此很少有效。
4. **暂时接受缺口：** 以 11 个通过词作为数值上可用的子集，扫描继续记录失败。

## 与交接的偏差

- **未使用子代理：** 交接建议使用 `gpt-6.1-sol` 子代理。本会话除非用户要求不启动代理，因此未启动；实现、测试和审查均由主执行者完成。
- **首次全套测试被停止：** 为把软墙钟改为按批次而非按调用计算，我停止了第一次全套测试，其部分日志已被替换。两次完整的候选运行均保留（先 960 passed，后 962 passed）。
- **第一次烟测作废：** 我在其复核步骤中修改了 `batch_control.py`。此后每次复核都按设计以身份不匹配失败（ERROR），后续步骤拒绝了过期 run。这些文件保留，并以 `smoke_pre_freeze/INVALIDATED.md` 标注。这促成了漂移保护；干净的重做见 `smoke_pre_freeze_002/`。
- **P1-1 命令：** P1-1 使用冻结的批次驱动（`pairs --batch regression_001`），而非 `plan_all_pairs.py` + `verify_all_pairs.py`。两者运行器和种子相同，前者另有锁、预算与日志。
- **已知限制：** 若 `--resume-from` 指向被篡改的旧输出，`plan_sequences.py` 会在创建空输出目录后停止；之后聚合会因缺少 manifest 明确报错，而不是静默。

## 未验证限制

- 视频和静帧未经人工观看；过渡是否误导、用例是否仍可理解均未检查；它们不是 ASL 句子。
- 正式 PASS_SIM 为 0；政策均为开发政策，待跨组评审。
- 碰撞为采样检查，非连续证明；保护核心内的导数连续性未认证。
- P1-3 全库扫描未完成（见上文）。P1-4 的 111 例依赖 P1-3，尚未运行。
- 墙钟规划预算使候选池受机器负载影响，重跑不会逐位相同。
- 无 neutral 起止姿态、无实机、未在新环境复现；未提交 git。
