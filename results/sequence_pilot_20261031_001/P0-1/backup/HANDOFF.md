# 下一步执行交接：COME/NOW 多词串联试点

[English](HANDOFF.en.md) · [当前状态](STATE.md) · [当前 v5 报告](TASK-25.md)

========== HANDOFF BEGIN ==========

更新：2026-10-31（Asia/Shanghai）。**本文件是下一阶段指令，以下任务均未执行。** 本次整理仅修改 STATE/HANDOFF 中英四份文档。

## 项目与目标

项目：ME5412 第三组任意词对动作衔接。最终目标是在保留词义动作的前提下，为词库任意两个词提供合适衔接；本轮先用已有 COME/NOW 成果验证多词组合。

本轮目标：复用 v5 候选机制，生成可追溯的三词和五词序列；每个中间词只出现一次，每次词实例的保护姿态、顺序、相对时序不变；从保存文件独立验证整条序列并输出诊断回放。**本轮不扩跑其余 1,221 对，不开启正式验收，不上实机。**

## 当前状态

- 已完成：四个有序词对数值通过 4/4；45/45 保存候选完整独立验证；四条选中曲线重新复核通过；四个诊断视频及 8 个保护实例姿态/时序比较。
- 未完成：v5 多词合同、组装、独立验证及序列视频；其余 1,221 对；全库 L2、语义人工观看、工程交叉评审、新环境复现、实机。
- 已知问题：摘要仍将正式未批准的数值通过结果写为 `FAILED_QUALITY`；`acceptance_pending()` 仍有自动窗口人工评审旧措辞。必须单列数值与正式状态，不把旧措辞变成用户审批切点的前置条件。保护内原动作平滑度问题仍保留。
- 当前分支：`codex/group3-all-pairs-v1`；HEAD：`2875e499d79b7264b3fe0414318b30ca8aab1f4d`。未提交/未跟踪内容是基线的一部分。
- **执行目录：`/home/kingderman/Documents/ME5412-github-latest`**。`/home/kingderman/Documents/ME5412` 及其 `execution_evidence/thread_acceptance_20261031/repository` 不作为实现基线；后者是已被替代的旧 v2 副本，禁止安装。
- 代码哈希：`5d0332c2ac5a87e49288302f1517cad90f897ce2bfd46b999e922c4a9dd864bc`；政策 `config/transition_policy_user_protected_v5.json`；当前 run `lift_off_arrival_pilot_20261031_002`，位于 `results/user_protected_lift_off_arrival_20261031_001/runs/`。
- 测试口径：TASK-25 报告 812 passed；进度复核实际重验的是四条选中曲线和媒体保护实例，未重跑完整测试。旧 v2 的 831 passed 不适用。

## 不变约束与冻结用例

1. 保护输入为 `config/user_protected_come_now_v2.json`：COME **0.93–4.40 s / [27,132]**，源 `motions/studio_galt_v1/COME.npz`；NOW **0.13–2.53 s / [3,76]**，源 `motions/wlasl_video_v1/NOW.npz`。0 起始、两端包含、30 Hz、`time_scale=1`；源 SHA 见 STATE。不得替换成另一 COME 版本。
2. 算法负责保护区外裁剪、端点、过渡和工程指标。用户提供不可删语义部分；需要人工观看时只核对语义是否保留、新增动作是否误导，不让用户认证算法窗口。
3. 当前四条选中候选：COME→NOW `attempt_00016`；NOW→NOW `attempt_00015`；NOW→COME `attempt_00023`；COME→COME `attempt_00003`。通过 run manifest/checkpoint 解析真实候选路径，不猜文件名。
4. 冻结 8 个三词：COME–COME–COME、COME–COME–NOW、COME–NOW–COME、COME–NOW–NOW、NOW–COME–COME、NOW–COME–NOW、NOW–NOW–COME、NOW–NOW–NOW。压力集为 COME×5、NOW×5、COME–NOW–COME–NOW–COME、NOW–COME–NOW–COME–NOW。共 12 条工程用例，不宣称是 ASL 句子或独立语义测试集。
5. 本试点直接从首个保留源切片开始，到最后一个保留源切片结束；不隐式加入 neutral 起止动作。未来若需要 neutral，另列任务与验收。
6. `formal_acceptance_enabled=false`；使用全新运行目录和 run_id。旧输入、政策、模型、原动作、失败证据和历史结果保持原样。代码变化后不能继续给旧 run 写结果或复用旧身份。

## 执行顺序与原子任务

### P0-1 — 冻结 v5 基线和试点清单

| 字段 | 指令 |
|---|---|
| ID / 优先级 / 名称 | P0-1 / P0 / 冻结 v5 基线和试点清单 |
| 目的 | 避免旧副本覆盖当前成果，使后续回归有可复核起点。 |
| 前置条件 | 读 AGENTS.md、STATE.md、TASK-25.md；确认实际执行目录。 |
| 具体操作 | 记录分支、HEAD、完整 git status；备份本轮将修改的文件及哈希；核对 run 002 的 70 代码、144 输入、607 清单条目；读取四条选中候选及保护输入；冻结上述 12 用例、候选排序/选择规则、随机种子和有界资源预算。 |
| 涉及文件/模块 | 现有 STATE/HANDOFF、run 002 的 library_manifest.json/manifest.json/checkpoints、v5 政策、保护 bundle；拟新增本轮 baseline/case/budget 清单。 |
| 输入 / 输出 | 输入：当前目标与已有证据；输出：新任务证据目录、基线哈希、用例与预算、差异记录。 |
| 完成定义 | 基线身份一致或差异已解释并重新冻结；12 用例唯一、四对来源可追溯，未改旧文件。 |
| 验证方法 | 逐文件 SHA-256 比较；核对 8 个三词恰好等于两词集合的长度 3 笛卡尔积；保存命令和退出码。 |
| 风险 / 回滚方法 | 并发更新或拿错检出；不覆盖现场，重新读取变化，废弃本轮未使用的清单后重做。 |
| 可并行 | 否，所有后续任务依赖它。 |

### P0-2 — 定义序列合同、评分范围与失败状态

| 字段 | 指令 |
|---|---|
| ID / 优先级 / 名称 | P0-2 / P0 / 定义序列合同、评分范围与失败状态 |
| 目的 | 将“两词通过”与“整条序列通过”分开，使组装器与验证器使用同一明确协议。 |
| 前置条件 | P0-1。 |
| 具体操作 | 设计新的序列 schema/政策，不放宽 pair v2；支持至少两词并明确拒绝空/单词输入；每词有唯一 occurrence ID，每过渡记录源 run/候选/文件哈希、两端实例、切点、手指相位和局部时间。候选来源身份与当前序列实现身份分别记录。序列身份须覆盖实际新增 CLI/验证/渲染入口、源码、测试、合同、政策和引用清单；现有 freeze_library 仅自动收集部分目录及固定脚本列表，不假定新脚本自动进入哈希，须做逐项覆盖及改动后身份变化测试。定义时间重排、30 Hz 网格、身份匹配、缺失/重复/损坏输入的拒绝行为。冻结评分掩码、有限差分边缘处理、积分归属及预算耗尽状态。 |
| 涉及文件/模块 | 参考 pair_contract.py、pair_verification_v2.py；拟新增版本化序列合同/政策及 schema 校验测试，路径在执行前登记。 |
| 输入 / 输出 | 输入：v5 政策、候选结构与保护定义；输出：版本化 schema/开发政策、接口说明、负例合同测试。 |
| 完成定义 | 所有 12 用例均能表达；重复词可区分；新接口不能把两词标签直接继承为序列通过；指标口径在看序列结果之前冻结。 |
| 验证方法 | 对错误哈希、重复实例 ID、缺核心、时间错序、源版本不一、非法段类型做拒绝测试；pair v2 仍拒绝三词。 |
| 风险 / 回滚方法 | 积分随长度增长而误判或通过平均掩盖局部峰值；保留 v5 不变，撤回未使用的新合同；有结果后变更必须新版本、新 run。 |
| 可并行 | 否；P1-1/P1-2 依赖本任务冻结接口。 |

**指标决策要求：** 沿用 v5 的保护核心外评分，覆盖所有词实例。建议每个过渡的评分区域包含“前词保护核心之后的保留边缘 + connector + 后词保护核心之前的保留边缘”，从整链重建数据计算，边界归属不得重计或漏计。每个过渡保留现有峰值、connector 时长上限 6 s（不是整句或整个评分区域的时长）与 `1,000,000 rad²/s⁵` 积分上限，解析 connector 也独立检查；全序列平方 jerk 总积分另报。此方案须在 P0-2 写成新序列开发政策，不伪称是已有 v5 多词口径。若选另一全局口径，先记录工程依据再运行；不得看结果后放宽阈值。受保护源内部异常仍报告，整个序列速度、限位、耦合、边界和采样几何不能豁免。

### P1-1 — 组装每个词只出现一次的序列

| 字段 | 指令 |
|---|---|
| ID / 优先级 / 名称 | P1-1 / P1 / 组装每个词只出现一次的序列 |
| 目的 | 复用已验证 connector，同时消除完整词对拼接导致的中间词重复。 |
| 前置条件 | P0-2。 |
| 具体操作 | 开发时以 run 002 的四条选中候选为 fixture；正式试点使用 P1-3 新 run 复核的候选。只取候选 connector；首词用首边 source 切片，末词用末边 target 切片；中间词只取 incoming.entry 到 outgoing.exit 的一个原始切片。校验 entry≤core_start≤core_end≤exit、entry<exit、源/保护/关节顺序/身份一致，入口后一帧与出口前一帧必须在切片内。重编号 occurrence，平移每段时间但不改系数、时长或原词时序；允许 connector 内部非 30 Hz 子段边界，完整 connector 和源帧落在回放网格。失败时保留原因，再按冻结规则在该 run 实际验证通过的候选池内有界选择兼容组合（旧 run 002 为 45 个，不假定新 run 数量相同）。 |
| 涉及文件/模块 | 现有 pair_routes.py:assemble_pair_trajectory_v2、pair_timing.py:boundary_state_v2、pair_fingers.py；拟新增序列组装模块、保存接口和 CLI，不把三词交给现有 save_pair_trajectory。 |
| 输入 / 输出 | 输入：冻结候选与新合同；输出：序列 artifact、逐边来源、逐词源帧映射、失败日志。 |
| 完成定义 | 每词实例恰好一个源切片；相邻词间恰好一组 connector；保护帧只按该实例出现一次，时间连续；两词退化案例与原候选回放等价。 |
| 验证方法 | 单测覆盖中间 NOW 不同范围、重复/self 词、不同手指策略、时间偏移、重放相等和缺失导数采样；检查系数/源帧/时长无暗改。 |
| 风险 / 回滚方法 | 端点不兼容、重复边界采样、错误时间归一化；只回退本任务新模块/调用点，保留失败 artifact，不改源曲线。 |
| 可并行 | 是，P0-2 后可与 P1-2 分工；文件独占，公共合同变更串行协调。 |

边界导数沿用 `linear_replay_one_sided_v2`：出发端取源帧前一间隔斜率，到达端取后一间隔斜率，线性源片段边界加速度为 0；不宣称受保护原词全局 C2 或连续导数已获证明。

例：COME→NOW→COME 的选中候选给出中间 NOW **[2,77]**，其中保护 **[3,76]** 只出现一次。这是组装要求，尚不是已验证序列。

### P1-2 — 从保存文件独立验证全序列

| 字段 | 指令 |
|---|---|
| ID / 优先级 / 名称 | P1-2 / P1 / 从保存文件独立验证全序列 |
| 目的 | 发现 pair 验证无法覆盖的中间词和整链问题。 |
| 前置条件 | P0-2；可用冻结小 fixture 开发，集成依赖 P1-1。 |
| 具体操作 | 重新读 artifact 和源文件；按实例查 source_slice，不能只 zip 首尾两段。逐实例比对保护姿态与相对时序；逐 connector 两端重算位置/一侧速度/加速度及手指相位、解析极值；重建整链，检查所有评分区、全链速度/限位/耦合、预算内密采样几何。分别报告 numerical_checks_passed、validation_complete、formal 状态、每词/每边失败及原词异常。 |
| 涉及文件/模块 | 参考 pair_verification_v2.py 的 _full_replay、_protected_replay_mask、verify_saved_pair_v2；拟新增序列 verifier/CLI/测试。私有 helper 可审慎复用，旧两词顶层验证器不能充当序列验证器。 |
| 输入 / 输出 | 输入：保存序列、新政策、原动作/模型；输出：绑定 artifact 哈希的独立证据、全链指标与逐实例保护报告。 |
| 完成定义 | 中间词也验证；缺字段、身份不符、预算耗尽不能通过；修改中间核心/时序/connector 的篡改均被拒绝；两词回归保留原行为。 |
| 验证方法 | 负例注入：中间核心缺帧/变值/调时、重复或交换实例、遗漏 connector、改系数/相位、过期哈希、耗尽预算；独立重算指标，与 planner 自报无关。 |
| 风险 / 回滚方法 | 与组装器共享错误假设，或将采样检查描述为连续证明；不同测试构造独立预期，保留旧 pair 路径并撤回新调用点。 |
| 可并行 | 是，P0-2 后与 P1-1 并行；由另一执行者审查验证逻辑及测试，集成串行。 |

### P1-3 — 运行冻结用例并导出可核对回放

| 字段 | 指令 |
|---|---|
| ID / 优先级 / 名称 | P1-3 / P1 / 运行冻结用例并导出可核对回放 |
| 目的 | 用真实保存文件、整链几何和保护证据验证试点。 |
| 前置条件 | P1-1/P1-2 对应测试通过。 |
| 具体操作 | 冻结最终源码/测试/索引身份后，先用新 run_id 重跑并独立验证 v5 四对，记录实际候选数量/选择，再冻结本次候选清单并组装全部 8 三词和 4 个五词压力用例；保存所有尝试及失败，逐条独立复核。预算不足明确未完成，修复后新版本重跑，不替换难例。通过项导出带词实例/保护/裁剪/新增段标签的双视角视频；失败项若导出必须显著标诊断失败。比较每个视频 replay 的全部保护实例；任何后续代码变更均使本轮身份过期，必须保留已有证据并新建 run。 |
| 涉及文件/模块 | 新序列 CLI/verifier/render 输出；参考 scripts/render_user_protected_pairs.py（现有脚本仅两词）；tests/test_*_v2.py、tests/test_*_v5.py、拟新增序列测试。 |
| 输入 / 输出 | 输入：冻结 12 用例与预算；输出：新 run、逐条 JSON/日志/轨迹/视频/保护比较、四对回归与测试日志。 |
| 完成定义 | 成功交付要求 8/8 三词与 4/4 压力用例数值通过、验证完整、44 个词实例保护不变；四对基线回归通过；对应测试及完整测试通过。若未达，保留精确分母并标未完成。 |
| 验证方法 | 保存实际 CLI/参数/环境/退出码；从输出文件重算 12 条状态、44 实例和 32 个 connector 组计数；重放检查姿态逐位相同、相对时序误差≤1e-12 s；记录采样覆盖与预算；执行聚焦测试后运行完整 suite。 |
| 风险 / 回滚方法 | 长序列超预算、渲染与轨迹身份不符、视觉误当语义证明；冻结资源上限并记录耗尽，不覆盖旧结果，隔离失败 run。 |
| 可并行 | 否，先完成集成与合同测试；之后互不写同一 run 的复核/媒体检查可并行。 |

### P1-4 — 审查交付并更新状态

| 字段 | 指令 |
|---|---|
| ID / 优先级 / 名称 | P1-4 / P1 / 审查交付并更新状态 |
| 目的 | 给下一执行者留下事实清楚、可复现的结果。 |
| 前置条件 | P1-3 结束，包括失败或未完成状态。 |
| 具体操作 | 审查代码差异、保存验证和日志；核对原始资产/历史结果哈希未变；写实际使用命令、未验证限制、各任务状态与偏差；更新 STATE/HANDOFF 中英版，新增下一个未占用 TASK 编号的双语报告及索引。提出剩余 33 词的来源/保护输入清单，不在本轮扩跑。 |
| 涉及文件/模块 | STATE.md/.en.md、HANDOFF.md/.en.md、拟新增 TASK 报告、docs/README.md/.en.md；需要时单独记录 project_overview.py 文档索引哈希的维护及其代码身份影响。 |
| 输入 / 输出 | 输入：差异、运行证据、测试/媒体报告；输出：验收矩阵、可复现交付、下阶段缺口。 |
| 完成定义 | 事实与计划分开；没有伪造语义/正式/实机通过；中英文数值一致，所有链接可用；未完成项有最小复现。 |
| 验证方法 | 最终文件范围与哈希审计、文档链接核对、从 JSON 重新汇总结果；若维护索引触及代码，先冻结最终代码再新建 run/渲染，禁止给旧 run 换身份。 |
| 风险 / 回滚方法 | 文档索引维护改变代码身份，或把失败写成完成；恢复本任务有备份的文档差异，保留结果与审计记录。 |
| 可并行 | 否，最终整合串行；可请独立审查者只读复核。 |

## 关键文件与真实接口

- `src/sign_robot/pair_contract.py`：`load_policy`、`freeze_library`、`run_identity`；`validate_trajectory_v2`、`save_pair_trajectory`、`read_pair_trajectory` 严格用于两词。
- `src/sign_robot/pair_routes.py`：`assemble_pair_trajectory_v2`；`src/sign_robot/pair_timing.py`：`boundary_state_v2`（一侧线性回放导数）。
- `src/sign_robot/pair_fingers.py`：v5 `finger_arrival_plan_v1` / `apply_finger_arrival_v1`。
- `src/sign_robot/pair_verification_v2.py`：`verify_saved_pair_v2` 只验证两词，保护掩码及边界位置有首尾假设。
- `src/sign_robot/transitions.py:plan_sentence` 与 `scripts/plan_transitions.py` 是旧多词流程，不是 v5 序列完成证据。
- **拟新增、当前不存在的接口**：序列 schema、组装/保存、独立验证、CLI、渲染与序列测试。执行者先登记真实路径和接口，不猜已有 API，也不要只把 pair 长度检查删掉。

## 关键命令

以下现有命令已核对入口；检查/测试在正确目标执行。新的序列 CLI 尚不存在，其命令必须在实现后用 `--help` 验证并写入交付报告。

```bash
cd /home/kingderman/Documents/ME5412-github-latest
git status --short
git branch --show-current
git rev-parse HEAD
sha256sum config/transition_policy_user_protected_v5.json config/user_protected_come_now_v2.json motions/studio_galt_v1/COME.npz motions/wlasl_video_v1/NOW.npz
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/plan_all_pairs.py --help
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/verify_all_pairs.py --help
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_pair_contract_v2.py tests/test_user_protected_routes.py tests/test_user_protected_verification.py tests/test_lift_off_arrival_v5.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests
```

上面聚焦命令仅覆盖已存在的 pair 测试；执行者还须加入实际新增的序列测试。源码和测试会进入代码哈希；不能改写旧 candidate.identity 或在代码改变后把旧 run 002 冒充当前验证。原四对回归的规划/验证/渲染参数参考 TASK-25，**改用新的唯一 run_id 和输出目录**；不要对 run 002 执行写入型重跑。

## 执行规则、风险与回滚

- 每任务先验证再进入依赖它的任务；实际结构与计划不符时报告具体差异，继续不受影响的工作。
- 使用真实 `gpt-6.1-sol`、`max` 子代理做有边界的实现/独立审查，主代理协调与最终审核；不递归扩散，不并发编辑同一文件。
- 不扩大修改范围，不重构无关模块，不 reset/clean/push，不删除历史记录或原资产。保留用户未提交内容；目标目录需授权写入时使用工具正常权限流程。
- 高风险点：中间实例被重复/遗漏、保护掩码只看首尾、connector 时间与归一化混淆、累积积分口径变动、过期代码身份、长链预算耗尽。负例测试和独立保存文件复核必须覆盖。
- 人工确认：源动作语义与新增动作是否影响理解可单列观看；三组工程交叉评审独立记录。它们不阻止正式关闭的本地开发试点，不得伪造其完成。
- 不可逆操作：本轮无必要操作。实机、发布、覆盖旧结果等均不在此交接范围。
- 回滚：仅撤回本轮实际新增/修改文件；恢复前逐一核对当前文件仍等于本轮安装后哈希，确认未被他人更新。恢复备份并保留本轮失败与命令记录；不要用 Git 全目录回退丢失未跟踪成果。
- 阻塞时保留新 run、输入、错误、最后成功步骤与最小复现命令；TIMEOUT/预算耗尽不等于无解证明。

## 最小路径与后续完整路径

最小路径：P0-1 → P0-2 → P1-1/P1-2 → P1-3 的 8 三词验证及回放 → P1-4，明确压力测试未完成。本轮完整交付再包含 4 个五词压力用例与全部回归。后续才收集其余 33 词保护信息、扩大词对覆盖、做语义与工程交叉评审、新环境复现；全库及实机另有验收，不能从 12 条试点推出。

## 执行完成后必须报告

1. 修改文件、基线与最终身份、原资产及历史结果是否保持；
2. P0-1～P1-4 各任务完成/失败/未完成状态；
3. 实际命令、环境、耗时、预算与退出码；
4. 8 三词、4 压力用例、四对回归和测试的分别统计，逐实例保护及视频证据；
5. 与计划的偏差、任何政策或合同变更及其理由；
6. 未完成、失败复现、残余风险及下一步要求。

========== HANDOFF END ==========
