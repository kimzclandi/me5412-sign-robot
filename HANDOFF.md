# 35 词保护输入与全库衔接执行交接

[English](HANDOFF.en.md) · [当前状态](STATE.md) · [最新执行报告 TASK-28](TASK-28.md) · [执行报告 TASK-27](TASK-27.md) · [历史报告 TASK-26](TASK-26.md)

## 最新交接（2026-11-02）：九个医院句子

> **本文件下方 2026-11-01 的 35 词全库计划与"下一步"已被用户的范围决定取代，不要照做。** 2026-11-01 用户改为只做九个医院句子，第三组只负责衔接。P1-3 停在 46/79 批；P1-4、预算重试和更快的扫描器没有运行；`resume.sh`、`after_p1_3.sh`、`p1_3_final.sh`、`p1_4.sh`、`retry_budget.sh` 不再使用（代码已变，那些 run 的冻结身份也已失效）。若以后恢复全库目标，需要新政策版本和新 run。

当前：第八轮 7/7 数值通过，结尾回到初始姿态，衔接中途不停顿。各轮、配置、命令、本机环境与待办见 [TASK-28](TASK-28.md)。

接手步骤：

1. 先读 [TASK-28](TASK-28.md) 和[第八轮 README](results/hospital_sentences_20261102_008/README.md)。
2. 等用户对第八轮视频的反馈。视频只在本机：`C:\Users\23971\Documents\5412\_runtime\render-out\round8_034002\`。
3. 用户已于 2026-11-02 明确要求本次更新 GitHub，替代此前暂停。以干净公开提交 `86428693` 为基线发布非原始快照，不直接推送包含原始存储提交的源历史。见根目录 README 与 PUBLICATION_MANIFEST.json。
4. 新一轮用新目录、新版本：复制上一轮的 `make_inputs.py`、`run.sh`、`export_render_inputs.py`、`render_gpu_windows.py`，改目录名、run_id 和策略版本；保护表与旧策略只新增版本，不覆盖；被取代的结果保留并标注。
5. run 运行期间不要修改 `src/`、`tests/`、`scripts/`（冻结身份）。
6. 修改 `docs/README*.md` 时，同步更新 `src/sign_robot/project_overview.py` 中登记的 sha256，否则 `tests/test_project_overview.py` 失败。
7. 每轮结束后更新双语 README、STATE、HANDOFF 与 TASK 记录。公开交付排除原始词对存储、保留整理后的摘要；原始存储只留本地。

---

更新：2026-11-01（Asia/Shanghai）。本交接替代已完成的 COME/NOW 序列试点交接。下方 P0/P1 计划写于执行前，保持不变；紧随其后的状态块记录实际执行情况。P0/P1 编号属于本阶段，不沿用 TASK-26 的完成标记。

> **执行状态（2026-11-01，见 [TASK-27](TASK-27.md)）：** P0-1 → P0-7 已完成并冻结；P1-1、P1-2 已完成；P1-3 正在分批运行，尚未完成（10:47：27/79 批，预计 2026-11-02 约 02:00 结束）；P1-4 等待 P1-3 结束；P1-5 为阶段性报告。
> 预检发现 35 个保护核心中有 24 个本身违反不可豁免的门槛（23 个采样穿透，4 个超速），因此预计 1,225 对中有 1,104 对无论规划何种衔接都会失败。这需要工程以外的决定（修订源动作、版本化接触规则或缩窄保护区间）；工程不得裁剪核心、修改源动作或放宽门槛。2026-11-01 用户选择先继续扫描，未起草修订请求；该决定仍未作出。
> P1-3 run 继续期间冻结代码身份不得改变：不要修改 `src/sign_robot/`、`tests/`、身份脚本、`docs/README*.md` 或 `project_overview.py`。续跑命令见 TASK-27；创建 `results/hospital35_protected_20261101_001/batch_control/hospital35_protected_20261101_001.stop` 可请求在下一个断点平稳停止。

**崩溃恢复（2026-11-01 12:35）：** 机器意外崩溃重启；4 个 run 存储均通过完整性校验，冻结身份在本机复现。接手请先读 [迁移包](migration/windows_handoff_20261101/MIGRATION.md)；同机续跑：`bash migration/windows_handoff_20261101/resume.sh`。

**下一步（按顺序）：**

**今晚的交付安排（用户要求 2026-11-01 午夜前完成）：** `commands/after_p1_3.sh` 已在后台等待并行 P1-3 结束（约 15:30），随后依次运行 `p1_3_final.sh`，再把 `p1_4.sh`（cpu0）与 `retry_budget.sh`（cpu1）并行运行（两者使用不同 run 与政策，互不依赖；顺序由“P1-4 之后”改为并行，不改变结果），预计约 20:00 前结束，然后完成最终双语文档。更快的扫描器移到提交之后。

1. **就 24 个受源动作阻塞的词作出决定（阻塞数值目标；仍待决定）。** 2026-11-01 用户选择先继续扫描，未起草修订请求。选项与逐词证据见 TASK-27“需要决定”。只有这样 1,225/1,225 才可能达到；工程不得裁剪核心、修改源动作或放宽门槛。
2. **P1-3 自 11:26 起在 4 个同身份 run 中并行**（`commands/p1_3_parallel.sh`，切片见 `P1-3/parallel_partition.json`，预计约 15:30 完成；停止需为 001–004 各建一个 stop 文件，详见 TASK-27）。原说明：P1-3 在当前 run 中继续，直到 79 个批次全部有记录或遇到预算停止。只在相同身份下续跑，命令见 TASK-27；平稳停止用 `touch results/hospital35_protected_20261101_001/batch_control/hospital35_protected_20261101_001.stop`（续跑前删除该文件）。若规划中被强行终止导致重放不一致，保留该 run，从该批次起换新 run_id 继续。
3. **P1-3 之后进行 P1-4：** 用 `run_hospital35_batches.py sequences` 运行 14 个冻结子批，再 `aggregate`。P1-3 仍在写入词对 run 时不要对它运行 P1-4。所需 169 对已全部复核，按其状态上限为 29/111（见 TASK-27）。包装脚本 `results/hospital35_protected_20261101_001/commands/p1_3_final.sh` 与 `results/hospital35_protected_20261101_001/commands/p1_4.sh` 会先确认 P1-3 已结束，否则以 exit 4 拒绝。
4. **源动作或政策决定之后：** 新动作、新 bundle 或新规则都是新版本：用新文件名重新导入、预检、冻结，并使用新 run。当前 run 保留为当前输入的记录。
5. **通过预检的词中的 TIMEOUT（用户 2026-11-01 已批准，在 P1-4 之后运行）：** 15 对在规划预算内没有候选：WAIT 进出两个方向、离开 HEADACHE 和 SOON，以及 STOMACH→COME；它们使 10 个序列用例受阻。规划预算与端点属于工程参数；已准备新版本政策 `config/transition_policy_user_protected_hospital35_retry_budget_v1.json`（只提高规划搜索预算）与 `results/hospital35_protected_20261101_001/commands/retry_budget.sh`（新 run `hospital35_retry_budget_001`，范围规则与试运行见 TASK-27），不改当前 run。
6. **更快的扫描器（用户 2026-11-01 已批准，在预算重试结束后开始）：** 作为新版本、新 run 开发：独立验证器内对完全相同的采样网格去重（dense factor 1/2/4 在 1/120 s 上限下几乎相同）；按源文件、模型、政策哈希与端点角色缓存端点与源片段检查；单写者内多工作进程规划与复核。完成后先用固定词对与旧版本对照（结果、耗时），全套测试通过后再冻结。不包括跳过源动作受阻词对：那会改变覆盖口径，需要用户另行决定。开发须在 P1-3、P1-4 与重试全部结束后进行，否则代码变化会使它们的冻结身份失效。
   原说明：**速度（可选工程改进）：** 实测每对约 63–80 s，单线程运行，全库约 22–23 小时。在单写者内并行复核候选可把耗时降低数倍；这属于代码修改，需要新版本。
7. 其余不变：人工语义观看、跨组评审、neutral 起止、新环境复现、实机与正式验收。

**最新快照（2026-11-01 10:47，`P1-3/progress_20261101_104756.json`）：** P1-3 run 仍在后台写入（单写者，持有锁），27/79 批为 BATCH_COMPLETE。1,225 对中：数值通过 50、数值失败 242、TIMEOUT 无曲线 101、进行中 15、未运行 817。预测受阻的 328 对全部失败；预测可通过的 65 对中 50 对通过、15 对 TIMEOUT。后续进度见 `results/hospital35_protected_20261101_001/P1-3.log` 与 `batch_control/pair_batches/`，或用 `P1-3/scan_progress.py` 生成新快照（命令见 TASK-27）；若会话已结束，该进程可能已不在。

以下原计划保持不变，作为当时要求的记录。

========== HANDOFF BEGIN ==========

## 项目、目标与当前状态

项目：ME5412 第三组。目标：把用户已完成的 35 词保护表接入当前实现，在不改变保护姿态、顺序、相对时序的前提下，为全部 1,225 个有序词对生成并验证衔接，再检查固定多词用例。不能用未经过验证的降级连接强行满足“任意两个词”。

- 当前工作目录：`/home/kingderman/Documents/ME5412-github-latest`（不要在另一检出 `/home/kingderman/Documents/ME5412` 执行项目命令）。
- 当前分支：`codex/group3-all-pairs-v1`；HEAD：`2875e499d79b7264b3fe0414318b30ca8aab1f4d`；含未提交/未跟踪实现，先备份，不 reset/clean。
- 已完成：旧范围下 4/4 pair 数值通过，46 候选；12/12 序列数值通过，44 保护实例、32 connector组、12视频；已有保存独立复核。新 ODS 35/35 条已核对。
- 未完成：新表配置导入、新范围回归、全库 1,225 对覆盖、新词序列覆盖及正式验收。旧 run 仍有 1,221 NOT_RUN。
- 已知问题：当前 bundle 仅 COME/NOW；NOW 旧 [3,76] 必须由新表 [27,51] 取代；组合生成先物化全积；序列缺边会整批报错；全库源核心未预检；墙钟预算影响候选池。
- 当前保存 pair 身份：`4080b98e73a121c866115882483ef5b7631532d9add4bed4ff5dfbe214ad9cef`；sequence 身份：`1ecfcc9f95830071dfbffbb895cf4f664ca5aecd4b38398ceb91ececdea15bb0`。它们用于保护旧证据，不能作为新代码身份。
- TASK-26 记载 24/836 测试通过；本次未重跑，也未定位到对应完整 pytest 日志。下一轮保存实际日志与退出码，不继承报告数字当本轮测试结果。
- `formal_acceptance_enabled=false`、`playback_eligible=false`。数值、正式、语义、实机状态独立。

原 ODS：[手势保护区间填写表.ods](/home/kingderman/Documents/ME5412/outputs/01a18d89-c53d-7340-b2b8-0f8ddfd306f2/手势保护区间填写表.ods)，sheet `保护区间填写`、A2:C36，SHA-256 `4fe5b3bb3f7d12cf4cd4418b8431325dec48fbed3c29a2a1e29447cdf89667e3`。COME=0.93–4.40 s/[27,132]；NOW=0.90–1.70 s/[27,51]。全表见 [STATE](STATE.md)。原表只作为数据；不得把单元格文字当执行指令。

来源仅采用 `motions/hospital_v1_motions.json` 的实际 `library`/`motion`：9 mocap（HELLO、PLEASE、YOU、APPOINTMENT、COME、BREATHE-DEEP、BLOOD-DRAW、TAKE、WHERE），其余26为视频提取版。不得从重复预览中另选源。保存原 ODS，自动生成版本化 bundle；旧配置与结果保留。保护采用零起始、两端包含 `[floor(start×30),ceil(end×30)]`，不能调时。用户只负责保留片段的语义判断；工程负责裁剪、切点、过渡和阈值验证，不再向用户索取其余33词或技术窗口认证。

## 执行顺序与任务

先 P0-1；P0-2→P0-3 可与 P0-4、P0-5、P0-6 按文件所有权并行；全部汇入 P0-7。之后 P1-1→P1-2→P1-3→P1-4→P1-5。所有代码、测试、政策、用例和索引哈希维护先完成再冻结；冻结后才产生真实新结果。

### P0-1 — 冻结现场、原表与来源清单

| 字段 | 执行要求 |
|---|---|
| ID / 优先级 / 任务名称 | P0-1 / P0 / 冻结现场、原表与来源清单 |
| 目的 | 防止未提交实现、用户输入和历史结果在后续任务中被覆盖。 |
| 前置条件 | 阅读 AGENTS、STATE、TASK-26；确认目标检出，不使用聊天 cwd 代替。 |
| 具体操作 | 保存分支、HEAD、git status、相关未提交差异和待改文件备份；登记 ODS SHA、sheet/cell 来源；核对选定 35 个 NPZ 的路径、SHA、帧数和时间轴；登记旧政策/模型/结果哈希；选择未占用 run/output 与下一个未占用 TASK 编号。 |
| 涉及文件/模块 | 现有 AGENTS.md、STATE.md、TASK-26.md、motions/hospital_v1_motions.json、原 ODS；拟新增 results/hospital35_protected_20261101_001/baseline/。 |
| 输入 | 当前工作树、旧结果、原表。 |
| 输出 | 基线清单、备份、来源清单与可审查差异。 |
| 完成定义 | 35 个实际来源可定位；原表 SHA 与 STATE 一致；旧资产和未提交文件有恢复依据。 |
| 验证方法 | git status/branch/rev-parse；SHA-256；读取 NPZ 实际末帧；清单计数与相对路径检查。 |
| 风险 | 另一检出、同名动作、未跟踪代码遗漏或并发写入。 |
| 回滚方法 | 本步只写新证据目录；原文件不动，保留现场。 |
| 可并行 | 否；后续实现的共同前置。 |

### P0-2 — 严格导入 35 词并绑定新保护政策

| 字段 | 执行要求 |
|---|---|
| ID / 优先级 / 任务名称 | P0-2 / P0 / 严格导入 35 词并绑定新保护政策 |
| 目的 | 把最新用户表变为可加载、可追溯的工程约束。 |
| 前置条件 | P0-1。 |
| 具体操作 | 拟新增导入入口，读取原表数值及出处，拒绝公式、空值、非有限值、重复/未知/漏词、非法边界；要求集合等于 policy["scope"]["expected_glosses"] 且为 35 条。按实际 hospital 映射绑定路径/SHA/帧数/30 Hz；外向取整并与 Decimal 比较。创建新 bundle、新 pair policy/window_version，沿用 v5 技术阈值、生成器与正式关闭状态；用现有 loader 验证。原表出处另存 provenance，不给严格 schema 随意加字段，不编造旧视频身份。 |
| 涉及文件/模块 | 复用 src/sign_robot/pair_windows.py:load_user_protections；拟新增 scripts/import_user_protections.py、config/user_protected_hospital35_v1.json、config/transition_policy_user_protected_hospital35_v1.json、tests/test_hospital35_protection_import.py。 |
| 输入 | 原 ODS、35 源文件、v5 policy 与旧 bundle 作为 schema 参考。 |
| 输出 | 新 35 记录 bundle/policy、逐行取整审计、provenance、导入测试日志。 |
| 完成定义 | 35/35 精确覆盖；COME [27,132]、NOW [27,51]；retiming_allowed=false；新旧身份不同；旧 bundle/policy/动作未改。 |
| 验证方法 | 正例与上述拒绝测试；过期 SHA/帧数/时间轴/错误同名源均拒绝；新记录与原表逐行相等；load_user_protections 返回恰好 35 词。 |
| 风险 | 只让 loader 无报错却漏词；新增字段被严格 schema 拒绝；取整或来源误配。 |
| 回滚方法 | 撤回本任务新增入口/配置和调用差异；保留原表与审计，恢复前检查文件未被他人更新。 |
| 可并行 | 是；P0-1 后可与 P0-4/P0-5/P0-6 分模块进行；共享身份收集修改留到 P0-7。 |

### P0-3 — 检查 35 词保护核心与双向端点

| 字段 | 执行要求 |
|---|---|
| ID / 优先级 / 任务名称 | P0-3 / P0 / 检查 35 词保护核心与双向端点 |
| 目的 | 区分时间合法、源动作缺陷和无可用端点，避免全库运行后才发现基础阻塞。 |
| 前置条件 | P0-2。 |
| 具体操作 | 用 v2 context 加载全 35 词并检查全局 input_blockers；新增逐词保护核心审计，报告限位、耦合、速度、采样几何、内段加速度/jerk及预算。按 35 个 self-pair 调用真实端点筛查，分别覆盖 source/target；每词保存可用帧、失败理由和输入身份。核心内加速度/jerk依 v5仅信息，其余门槛不豁免。全局加载失败时先保留根因，不缩小库冒充全库成功。 |
| 涉及文件/模块 | pair_routes.py:build_pair_context_v2/valid_endpoint_choices_v2；scripts/screen_user_protected_cuts.py；拟新增 scripts/preflight_hospital35.py 及聚焦测试、preflight/ 证据。 |
| 输入 | 新 bundle/policy、全部源动作和模型。 |
| 输出 | 35 行核心与端点报告、阻塞词及受影响词对清单。 |
| 完成定义 | 35 词均有明确检查结果及预算完成性；无缺行，无把 TIMEOUT 当通过；源问题与 connector 问题分开。 |
| 验证方法 | 计数/集合检查，注入核心限位/耦合/速度/几何缺陷验证归因；两种端点角色均有结果；核对原源哈希未变。 |
| 风险 | 端点检查被误当完整核心检查；核心缺陷使某些词无法在不改保护的情况下通过。 |
| 回滚方法 | 保留诊断失败；撤回新增检查调用即可，不修剪保护段、不改源、不放宽阈值。 |
| 可并行 | 是；P0-2 后与 P0-4/P0-5/P0-6 分文件并行。 |

### P0-4 — 添加分批预算和安全断点控制

| 字段 | 执行要求 |
|---|---|
| ID / 优先级 / 任务名称 | P0-4 / P0 / 添加分批预算和安全断点控制 |
| 目的 | 限制全库扫描资源，避免验证半个候选池就选择或多进程同时写 run。 |
| 前置条件 | P0-1；新 policy 集成依赖 P0-2。 |
| 具体操作 | 拟新增批次控制入口；每批最多 16 对、默认软墙钟 7,200 s、剩余磁盘至少 5 GiB，执行前按本机资源记录最终上限。到期在下一个不可变 attempt/verification 断点停止并保留未完成状态；不宣称硬实时中止。候选验证不完整时禁止选中。运行同一 run 的单写者；检查上一批验证积压为零才开下一批；保存起止、资源、命令、退出码。保持当前规划方法及墙钟调度，明确其候选池不保证确定性；不在此任务重写规划算法。 |
| 涉及文件/模块 | src/sign_robot/pair_runner_v2.py:V2RunStore.run_pair/verify_pair/run_scan_v2/verify_run_v2；拟新增 scripts/run_hospital35_batches.py、批次控制测试。 |
| 输入 | 冻结批次格式、现有不可变保存机制、工作/时间/磁盘预算。 |
| 输出 | 可暂停的单写者驱动、资源日志与检查点测试。 |
| 完成定义 | 预算中断无部分选中、无丢失/覆盖；重入处理已有验证文件；COMPLETED 失败不被误当可 resume 重试。 |
| 验证方法 | 注入小预算、中断、磁盘不足、未清验证积压和双写者；确认保存 artifact 可读，摘要未完成且不授权回放；相同身份恢复测试。 |
| 风险 | 未完成规划的重放受墙钟变化影响，可能触发 fingerprint 不一致；--max-pairs 本身不约束每对全部候选费用。 |
| 回滚方法 | 保留中断目录；重放不一致时报告并新建版本/run，绝不改旧指纹；可撤回新驱动，旧结果仍只读。 |
| 可并行 | 是；P0-1 后与导入/序列模块并行，独占 pair_runner_v2.py；最终集成串行。 |

### P0-5 — 按原排序惰性生成序列组合

| 字段 | 执行要求 |
|---|---|
| ID / 优先级 / 任务名称 | P0-5 / P0 / 按原排序惰性生成序列组合 |
| 目的 | 使 64 组合上限真正限制生成开销。 |
| 前置条件 | P0-1；不依赖真实新 run。 |
| 具体操作 | 替换 combinations() 的全积 sorted，惰性按 (sum(ranks), ranks) 输出最多 limit 项；保持重复边、边顺序、空池和边界行为；不静默截断每个候选池或修改候选排序。 |
| 涉及文件/模块 | src/sign_robot/sequence_assembly.py:combinations；tests/test_sequence_v1.py 或拟新增专项测试。 |
| 输入 | 现有组合顺序合同和小池参考实现。 |
| 输出 | 有界组合函数、顺序等价及规模测试。 |
| 完成定义 | 小池前 64 项逐项一致；大池只请求 64 项时不构造全积；原序列测试通过。 |
| 验证方法 | 不同维度/不等长/并列秩/重复边/空池/limit边界；大池生成数量和内存上界检查，避免仅用不稳定耗时断言。 |
| 风险 | 改变 tie-break 顺序，导致与历史选择规则不一致。 |
| 回滚方法 | 恢复本任务函数差异，保留失败测试证据；不触碰历史序列。 |
| 可并行 | 是；与 P0-2/P0-3/P0-4 并行；与 P0-6 测试文件写入需分配所有权。 |

### P0-6 — 记录逐用例阻塞并保持序列分母

| 字段 | 执行要求 |
|---|---|
| ID / 优先级 / 任务名称 | P0-6 / P0 / 记录逐用例阻塞并保持序列分母 |
| 目的 | 失败边不会让整批消失，也不会因只挑成功用例而高报通过率。 |
| 前置条件 | P0-1；集成依赖 P0-2/P0-5。 |
| 具体操作 | 在现有 sequence CLI/汇总层加入逐 case 依赖检查，区分 pair 缺失、规划未完、验证未完、无数值候选；未运行与阻塞有明确记录，固定用例分母。完整验证身份后才分类依赖；损坏/过期身份仍拒绝整个 run。序列也纳入P0-4资源驱动：每子批≤8例、软墙钟7,200 s、每case软预算600 s（含规划与验证）、保留64组合上限及5 GiB磁盘下限；在完整attempt/verification断点停，未处理例NOT_RUN，中断尝试不得选中，已完整通过的选中项保留。恢复采用新输出目录和同身份检查点清单，明确哪些旧尝试已处理；同case全部重试历史保留；P1-2回归输出单独留存，P1-4为全部111例预登记自己的canonical输出，二者不相加、不混算。拟在新批次driver内实现跨子批聚合：只读冻结case/subbatch清单及SHA，以预登记canonical输出引用归并，固定111分母、缺失NOT_RUN；重复case若身份/内容冲突必须拒绝，禁止last-write-wins或择优取结果。更新独立verifier汇总，blocked/未验证不计通过或全体一致；renderer只处理有效选中项，计入子批预算并单列媒体分母。 |
| 涉及文件/模块 | scripts/plan_sequences.py、scripts/verify_sequences.py、必要时 render_sequences.py；sequence_contract.py/sequence_assembly.py:load_candidate_pools；拟新增批次driver内的跨子批聚合模块、专项测试。 |
| 输入 | 冻结用例、同一 pair run 的完整或缺失/失败候选池。 |
| 输出 | 逐用例阻塞记录、总分母/通过/失败/阻塞/未运行汇总和测试。 |
| 完成定义 | 部分边失败仍可生成完整案例清单；每个原定 case 恰好出现一次；无跨 run 混池；身份损坏不能降级成普通 blocked 后继续。 |
| 验证方法 | 混合通过与缺失/未完成/无候选fixture、篡改身份/源SHA负例、原12例兼容性；注入case/subbatch小预算与低磁盘，验证安全停止、NOT_RUN、无部分选中、新目录恢复、canonical引用归并以及冲突/过期子批SHA拒绝；核对renderer计数与实验分母分离。 |
| 风险 | 吞掉真正完整性错误；把 blocked 写成数值失败或验证完成。 |
| 回滚方法 | 撤回新报告逻辑及调用差异，保留失败证据和旧接口行为；不重写旧结果。 |
| 可并行 | 是；P0-1 后与非序列模块并行；与 P0-5 合并串行并审查共享文件。 |

### P0-7 — 冻结批次、111 用例、测试和最终身份

| 字段 | 执行要求 |
|---|---|
| ID / 优先级 / 任务名称 | P0-7 / P0 / 冻结批次、111 用例、测试和最终身份 |
| 目的 | 保证后续回归和扩库使用同一已测试版本。 |
| 前置条件 | P0-2～P0-6 完成并审查；P0-3 诊断已分类。 |
| 具体操作 | 按下文固定 4+33+132+1056 互斥词对批次（每批≤16）；新序列 policy 一次冻结原12+新增99=111例并绑定新 pair policy 原文件 SHA，保留 2～5 词和旧数值/验证预算。明确根源阻塞、每批资源和停止条件。将新增导入/预检/批次/跨子批聚合脚本纳入代码身份；需要的双语 TASK 索引及 project_overview.py 哈希维护先完成。运行聚焦及完整 tests，保存 stdout/stderr/命令/退出码；以最终代码重新运行全部35词预检并核对输入/代码身份一致（P0-3早期输出只作开发诊断）；最后冻结全部代码、测试、政策、输入、环境、用例清单SHA。 |
| 涉及文件/模块 | pair_contract.py:freeze_library/run_identity；sequence_contract.py:sequence_identity；拟新增 config/sequence_policy_hospital35_v1.json、batches/*.json、case_manifest.json；tests、docs/README.md/.en.md、src/sign_robot/project_overview.py。 |
| 输入 | 所有已审查实现、35 词保护、批次与用例定义。 |
| 输出 | 完整测试日志、代码/输入身份、冻结 1225 对清单及 111 序列 policy。 |
| 完成定义 | 批次不重不漏，111例精确；测试通过且新脚本改动会改变身份；正式关闭，数值阈值未偷改；冻结后不再改代码/测试/索引哈希。 |
| 验证方法 | 集合并集/交集断言、case数/词实例数检查、脚本哈希篡改负例；pytest聚焦后完整套件；CLI --help；差异审查与冻结清单复算。 |
| 风险 | 最终写报告时才改索引并重钉代码哈希，使已有 run 失效；旧测试数当新验收目标。 |
| 回滚方法 | 冻结前按文件备份恢复本轮差异；冻结后发现必须改代码时保留旧 run 并新建版本，不能回填身份。 |
| 可并行 | 否；最终集成、测试和身份冻结必须串行。 |

### P1-1 — 用新保护范围重跑四个词对

| 字段 | 执行要求 |
|---|---|
| ID / 优先级 / 任务名称 | P1-1 / P1 / 用新保护范围重跑四个词对 |
| 目的 | 验证 NOW 新范围与全量 bundle 没有破坏基础连接。 |
| 前置条件 | P0-7；完整35词context无全局输入/绑定/加载阻塞。逐词源质量失败另列诊断，不能混作全局加载错误。 |
| 具体操作 | 新建唯一 pair run，规划 COME__NOW、NOW__COME、COME__COME、NOW__NOW；对每对全部保存候选完成独立验证后选择；逐条另存选中候选的全新 verify_saved_pair_v2 复核，不能只重复跳过 COMPLETE 的 CLI。记录候选数、选择和与旧结果的差异。 |
| 涉及文件/模块 | scripts/plan_all_pairs.py、scripts/verify_all_pairs.py；pair_verification_v2.py:verify_saved_pair_v2；新 pair_runs/。 |
| 输入 | 最终冻结新政策/身份、4 个 pair ID。 |
| 输出 | 4 对候选/完整验证/独立选中复核与日志。 |
| 完成定义 | 推进门槛为4/4数值通过、验证完整、保护保持，正式仍0；未达则标阻塞并保留失败，不以旧结果代替。 |
| 验证方法 | 从保存 JSON 重算分母/通过/候选数，核对新 policy/bundle SHA、COME/NOW 保护帧和源哈希；独立复核一致。 |
| 风险 | 新范围改变结果；墙钟造成候选数量变化；伪复用旧身份。 |
| 回滚方法 | 保留失败新 run；修改需新版本和新 run，不覆盖历史或反向扩回用户核心。 |
| 可并行 | 否；同一 run 单写，先规划后验证再全新复核。 |

### P1-2 — 回归 12 条序列并输出对照视频

| 字段 | 执行要求 |
|---|---|
| ID / 优先级 / 任务名称 | P1-2 / P1 / 回归 12 条序列并输出对照视频 |
| 目的 | 确认新 NOW 保护下多词组装、整链验证和显示一致。 |
| 前置条件 | P1-1 通过。 |
| 具体操作 | 新 sequence policy 中显式选择原12个case；只使用新同一pair run 候选。规划后独立复核，导出带实例编号/保护/保留/裁剪/新增标签的双视角视频；逐实例比较实际视频 replay 的保护姿态与时序。 |
| 涉及文件/模块 | scripts/plan_sequences.py、verify_sequences.py、render_sequences.py；新 sequences_regression_001/ 和 videos_regression_001/。 |
| 输入 | 新序列政策、4 对已完整验证候选、12 例ID。 |
| 输出 | 12 例轨迹/独立复核/保护比对/视频及日志。 |
| 完成定义 | 12/12 数值通过、44/44 实例保护姿态逐位不变、相对时序≤1e-12 s、32 connector组；12视频身份一致；正式0。 |
| 验证方法 | 独立保存文件复核与 JSON 计数；检查中间词保护仅出现一次、重复词不同实例；视频标签用 COME f132、NOW f51；抽查联系表。 |
| 风险 | 默认不加 --case 会提前运行111例；误用旧 NOW f76 视频。 |
| 回滚方法 | 保留失败轨迹和新输出；不覆盖旧序列/recheck/media目录；未通过不进入扩库验收。 |
| 可并行 | 否；依赖四对回归，规划→验证→渲染串行。 |

### P1-3 — 按冻结批次覆盖全部 1,225 对

| 字段 | 执行要求 |
|---|---|
| ID / 优先级 / 任务名称 | P1-3 / P1 / 按冻结批次覆盖全部 1,225 对 |
| 目的 | 用完整有序词对分母衡量“任意两词衔接”的工程覆盖。 |
| 前置条件 | P1-2通过，预算控制/预检/批次已冻结。 |
| 具体操作 | 同一新 run 依次增加其余33 self、132 hub双向边、1056其他异词边；每批≤16，规划→独立验证→汇总→清空积压→下一批。恢复只用于相同身份的未完成工作；已完成失败不会因 --resume 重试。所有失败/源阻塞/TIMEOUT/NOT_RUN保留；同一run不用多个进程写。 |
| 涉及文件/模块 | 现有 plan_all_pairs.py/verify_all_pairs.py/summarize_all_pairs.py，P0-4新增驱动、batches/*.json 与同一 pair_runs/。 |
| 输入 | 冻结批次、35 词新保护、同一最终代码/模型/环境身份。 |
| 输出 | 1225行矩阵、每批资源日志、候选与验证、失败根因表。 |
| 完成定义 | 完整路径要求1225对均有规划及独立审查记录（允许明确失败/诊断）；全部词对可用目标另要求1225/1225数值通过。未达目标必须明确剩余数和失败原因；绝不把扫描完成写成全通过。 |
| 验证方法 | 汇总1225、1190、35分母；核对已规划/NOT_RUN/数值通过/数值失败/验证未完成/DIAGNOSIS_ONLY/正式0；检查每候选验证完整性与固定批次并集。 |
| 风险 | 耗时/磁盘放大，源缺陷影响多对；无候选诊断被误认为轨迹通过；验证CLI会先处理旧积压。 |
| 回滚方法 | 在安全断点停下，保留全部已完成/未完成证据；需要调算法/预算时新版本新run，不给旧run换policy。 |
| 可并行 | 否；同一 run 单写串行，已封存输出的只读审核可并行。 |

### P1-4 — 执行冻结的 111 条序列覆盖

| 字段 | 执行要求 |
|---|---|
| ID / 优先级 / 任务名称 | P1-4 / P1 / 执行冻结的 111 条序列覆盖 |
| 目的 | 检查全词库中间词、重复词和双向连接组合。 |
| 前置条件 | P1-3完成或保留明确预算停止点；所需边状态已知，P0-6阻塞机制可用。 |
| 具体操作 | 在新输出目录处理全部111个冻结case（不得默默删除阻塞项）；原12与新增99分栏统计。按P0-6的case/子批/磁盘预算、每子批≤8例执行，汇总器按冻结恢复规则和ID去重/补齐NOT_RUN。成功项独立复核，失败/缺失边记录具体依赖；媒体覆盖数单列，新增词视频用于后续人工语义观看。候选池来自同一pair run。 |
| 涉及文件/模块 | 新 sequence policy/case_manifest，已扩展的序列 CLI、independent_recheck、videos 与覆盖汇总。 |
| 输入 | 111固定case、同一run已验证候选及失败状态。 |
| 输出 | 111例状态表、逐实例保护证据、序列与媒体清单。 |
| 完成定义 | 111条全都有状态；若全部通过应为341词实例、230 connector组，逐实例保护不变且时序≤1e-12 s；存在blocked/失败则不能宣称111/111通过。 |
| 验证方法 | 原12+33×3=111；44+99×3=341；32+99×2=230；固定分母与artifact/独立证据/媒体引用逐项核对；中间词和重复词篡改负例回归。 |
| 风险 | 这些是定向工程覆盖而非35³全部三词、所有五词或ASL句子；候选池规模仍可能耗时。 |
| 回滚方法 | 保留失败/blocked子批并补齐汇总，不替换难例；修改代码/政策需新版本，不能覆写旧子批。 |
| 可并行 | 默认否；受资源预算串行执行子批；封存结果可并行只读审查。 |

### P1-5 — 审查交付证据并更新双语状态

| 字段 | 执行要求 |
|---|---|
| ID / 优先级 / 任务名称 | P1-5 / P1 / 审查交付证据并更新双语状态 |
| 目的 | 交付可复核的真实进度、失败原因和下一步。 |
| 前置条件 | 前序执行已结束或有明确阻塞/预算检查点。 |
| 具体操作 | 独立审查差异、日志、JSON、保护/媒体比对和测试退出码；核对旧资产/原表/历史run哈希不变。填完预先登记的双语TASK、STATE/HANDOFF与实际命令；不得在此时再改冻结源码/测试/索引哈希。列人工语义观看、跨组审查和正式验收缺口，不伪造同学评审。 |
| 涉及文件/模块 | 预登记 TASK-XX.md/.en.md、STATE.md/.en.md、HANDOFF.md/.en.md、新run证据；不重写TASK-26。 |
| 输入 | 执行差异、所有成功/失败日志、最终哈希清单、测试与复核结果。 |
| 输出 | 双语执行报告、验收矩阵、剩余任务和可复现命令。 |
| 完成定义 | 事实/计划、旧/新版本、数值/正式清楚分开；中英数据一致；任何未完成都有分母/原因/最小复现；无保护或历史资产改动。 |
| 验证方法 | 最终范围/哈希检查、文档链接检查、从保存JSON重新汇总；独立评审不以执行者自报代替。 |
| 风险 | 扫描完成误写全部可用，诊断视频误写可实机，旧测试报告误写本轮通过。 |
| 回滚方法 | 仅恢复本轮文档差异且先核对安装后哈希，保留所有执行结果；不 reset/clean。 |
| 可并行 | 否；主代理最终整合，可委派只读独立审查。 |


## 冻结覆盖与验收标准

| 顺序 | 本阶段新增词对 | 累计 | 冻结定义 |
|---|---:|---:|---|
| 回归 | 4 | 4 | COME/NOW 的四个有序词对 |
| 其余 self | 33 | 37 | 其他每词与自身 |
| 双向 hub | 132 | 169 | 对每个其余词 w：COME→w、w→COME、NOW→w、w→NOW |
| 其余异词 | 1,056 | 1,225 | 其余33词的33×32有序异词对；按policy顺序拆66批，每批16 |

每个词对清单 JSON 为 `{"pair_ids":["SOURCE__TARGET", ...]}`；33与132组也按最多16分批。四组互斥且并集必须等于完整宇宙。病例/序列定义在看结果前冻结：原12条加每个其余词 w 的 `COME__w__NOW`、`NOW__w__COME`、`w__w__w`，新增99条，总111条。完整通过的理论数量是341词实例、230 connector组；blocked/未运行实例不得伪计为已保护验证。它们只构成定向工程覆盖。

逐实例保护姿态逐位相同、顺序不变、相对时序误差≤1e-12 s；每个中间词只取一个覆盖完整核心的源切片；connector系数和时长复用，只平移起始时刻。每个过渡区域沿用 v5 数值门槛：加速度120 rad/s²、jerk3000 rad/s³、平方jerk积分1,000,000 rad²/s⁵、connector≤6 s；全链限位/速度/耦合/边界/采样几何照常检查。核心内加速度/jerk仅信息，整链总积分仅报告，不能改口径换取通过。

验收分两层：**执行覆盖完成**允许明确诊断失败，但必须覆盖固定分母和独立记录；**用户目标的数值完成**要求1,225/1,225有合格连接。未达后者时交付实际缺口和下一轮失败修复计划，不声称任意两词已解决。正式验收继续单列关闭。

## 关键文件、接口和命令

现有：`pair_windows.py:load_user_protections`、`pair_contract.py:freeze_library/run_identity`、`pair_routes.py:build_pair_context_v2`、`pair_runner_v2.py:V2RunStore`、三个 `src/sign_robot/sequence_*.py`、`scripts/{plan,verify,render}_sequences.py`。`load_candidate_pools`只接受同一run候选，不混合旧/新run。`freeze_all_pairs_inputs.py`仍是v1路径，不能未经修改直接预检新保护政策；本计划使用拟新增v2预检入口。

上文标为“拟新增”的导入器/预检器/批次控制器与配置当前不存在，先实现并核对 `--help`，不要虚构已可运行命令。下列是现有CLI的命令模板；新配置/输出必须在P0完成后才使用。run名若被占用，P0-1统一登记新名并替换所有引用。新政策包含111例，因此回归必须显式列12个 `--case`。

```bash
cd /home/kingderman/Documents/ME5412-github-latest
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
git status --short
git branch --show-current
git rev-parse HEAD
.venv/bin/python scripts/plan_all_pairs.py --help
.venv/bin/python scripts/verify_all_pairs.py --help
.venv/bin/python scripts/plan_sequences.py --help
.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_user_protected_windows.py tests/test_user_protected_correction.py tests/test_pair_runner_v2.py tests/test_lift_off_arrival_v5.py tests/test_sequence_v1.py
.venv/bin/python -m pytest -q -p no:cacheprovider tests
```

```bash
.venv/bin/python scripts/plan_all_pairs.py \
  --library hospital_v1 --include-self \
  --policy config/transition_policy_user_protected_hospital35_v1.json \
  --run-id hospital35_protected_20261101_001 \
  --results-root results/hospital35_protected_20261101_001/pair_runs \
  --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW
.venv/bin/python scripts/verify_all_pairs.py \
  --run-id hospital35_protected_20261101_001 \
  --results-root results/hospital35_protected_20261101_001/pair_runs --max-pairs 4
```

```bash
.venv/bin/python scripts/plan_sequences.py \
  --sequence-policy config/sequence_policy_hospital35_v1.json \
  --pair-run-dir results/hospital35_protected_20261101_001/pair_runs/hospital35_protected_20261101_001 \
  --output results/hospital35_protected_20261101_001/sequences_regression_001 \
  --case COME__COME__COME --case COME__COME__NOW \
  --case COME__NOW__COME --case COME__NOW__NOW \
  --case NOW__COME__COME --case NOW__COME__NOW \
  --case NOW__NOW__COME --case NOW__NOW__NOW \
  --case COME__COME__COME__COME__COME \
  --case NOW__NOW__NOW__NOW__NOW \
  --case COME__NOW__COME__NOW__COME \
  --case NOW__COME__NOW__COME__NOW
.venv/bin/python scripts/verify_sequences.py \
  --run-dir results/hospital35_protected_20261101_001/sequences_regression_001
.venv/bin/python scripts/render_sequences.py \
  --run-dir results/hospital35_protected_20261101_001/sequences_regression_001 \
  --output results/hospital35_protected_20261101_001/videos_regression_001
```

```bash
.venv/bin/python scripts/plan_all_pairs.py \
  --library hospital_v1 --include-self \
  --policy config/transition_policy_user_protected_hospital35_v1.json \
  --run-id hospital35_protected_20261101_001 \
  --results-root results/hospital35_protected_20261101_001/pair_runs \
  --resume --pairs-file results/hospital35_protected_20261101_001/batches/rest_001.json \
  --max-pairs 16
.venv/bin/python scripts/verify_all_pairs.py \
  --run-id hospital35_protected_20261101_001 \
  --results-root results/hospital35_protected_20261101_001/pair_runs --max-pairs 16
.venv/bin/python scripts/summarize_all_pairs.py \
  --run-id hospital35_protected_20261101_001 \
  --results-root results/hospital35_protected_20261101_001/pair_runs
```


聚焦测试还必须加入实际新增的导入、预检、预算、组合与阻塞测试。命令由P0-4驱动在预算内执行并记录stdout/stderr和退出码；`rest_001`模板只在33 self与132 hub批次结束后使用。批量verify不支持 `--pairs-file`，每批前须无旧验证积压，`--max-pairs`按本批实际新增待验证数量调整。重新调用verify会跳过COMPLETE，不替代P1-1全新选中复核。新输出目录不能覆盖旧目录；序列独立recheck再次运行也要使用新证据位置或新输出，先检查脚本实际行为。

## 执行规则、风险、人工确认与回滚

- 每完成一项先运行对应验证；实际结构不一致先报告具体差异，继续不受影响的工作。不要把计划写成完成，不扩大范围或擅自重构。
- 使用真实 `gpt-6.1-sol`、`max` 子代理承担明确实现/测试/只读审查，主代理负责最终集成；无递归扩散，不同代理不同时改同一文件，不并发写同一run。
- 源动作、模型、原ODS、旧政策与历史run保持不变；不reset/clean/push，不发布，不实机。新增策略或预算变化必须版本化，不能修改旧identity、覆盖失败或复用旧通过标记。
- 高风险：错源/错帧、全局输入阻塞、保护内缺陷、组合爆炸、未完整验证就选择、墙钟恢复不一致、晚改索引使代码身份过期、只统计可组装序列。对应P0测试和分母审计必须覆盖。
- 人工确认只涉及真实语义歧义、必须修改受保护源动作或最终跨组/语义评审；提交具体词、帧、视频和失败证据。工程切点、预算与衔接参数由执行者负责，不重新要求用户认证。开发运行不假称完成正式人工验收。
- 不可逆操作：本轮不需要。删除历史结果、改原资产、发布/合并/实机不在本交接范围。
- 回滚按P0-1备份逐文件执行，恢复前确认当前文件等于本轮写后哈希，避免覆盖他人新改动。只撤回本轮差异，保留失败run、输入、日志、最后成功检查点、最小复现命令；TIMEOUT不等于无解证明。

## 最小可行路径与完整路径

最小路径：P0-1～P0-7→P1-1→P1-2→阶段性P1-5。得到35词已绑定、全词预检、资源/失败处理和新范围下4对/12序列的真实回归，不能宣称全库完成。完整路径继续P1-3→P1-4→最终P1-5，覆盖全部1,225对及固定111序列；失败边修复是根据实际根因另开版本，不保证一次全部通过。超出2～5词、neutral、语义验收和硬件仍需后续独立任务。

## 执行完成后必须报告

1. 修改/新增文件及原始资产未变的哈希证据。
2. 每个任务完成、失败、阻塞或未运行状态及原因。
3. 实际命令、参数、分支/HEAD/工作树身份、环境、输出目录与退出码。
4. 聚焦/完整测试原始日志、独立复核、固定分母、数值/正式状态、每词保护和媒体检查结果。
5. 与计划的偏差、预算中断、候选变化、缺失/诊断项及最小复现。
6. 剩余风险、人工需要判断的具体内容和下一阶段建议。

## 计划自检

已补齐：35输入不再等待；新NOW使旧结果不可沿用；序列能力已存在；严格35覆盖、核心预检、笛卡尔积开销、逐例阻塞、批次预算及索引哈希均放在最终冻结前。测试盲点重点是：原表公式/错源、保护内不可修缺陷、中间重复实例、部分验证恢复、身份损坏不能降级、保存检查与真正重算的区别。未验证风险保留在STATE，不承诺全库通过、连续碰撞或语义正确。

========== HANDOFF END ==========
