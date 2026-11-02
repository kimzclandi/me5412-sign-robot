# TASK-26 — COME/NOW 多词序列试点

[English](TASK-26.en.md) · [当前状态](STATE.md) · [交接](HANDOFF.md) · [上一轮 v5 报告](TASK-25.md)

**12 条冻结工程用例数值通过 12/12，全新独立复核 12/12 一致；正式 PASS_SIM 仍为 0。** 44/44 词实例保护姿态逐位不变，32 组 connector，8/8 三词、4/4 五词压力用例。测试 836 passed（812 + 新 24）。执行日期 2026-10-31～11-01（Asia/Shanghai），按 HANDOFF P0-1 → P1-4。

这些是运动学工程用例，不是 ASL 句子或独立语义测试集；未经人工观看，未上实机。

## 任务状态

| 任务 | 状态 | 证据 |
|---|---|---|
| P0-1 冻结基线与用例 | 完成 | `results/sequence_pilot_20261031_001/P0-1/`：git HEAD/status、待改文件备份及哈希、run 002 身份核对（70 代码 / 144 输入一致）、代码冻结哈希 |
| P0-2 序列合同与评分 | 完成 | [sequence_policy_user_protected_v1.json](config/sequence_policy_user_protected_v1.json)、`src/sign_robot/sequence_contract.py`；在验证任何序列前冻结 |
| P1-1 每个词实例一个切片 | 完成 | `src/sign_robot/sequence_assembly.py`、`scripts/plan_sequences.py` |
| P1-2 独立整链验证 | 完成 | `src/sign_robot/sequence_verification.py`、`scripts/verify_sequences.py`（不导入组装器或规划器） |
| P1-3 新 run、12 用例、视频 | 完成 | `results/sequence_pilot_20261031_001/` |
| P1-4 审查与文档 | 完成 | 本报告、STATE/HANDOFF、文档目录 |

## 序列合同（开发 v1）

- **表示**：独立的 `user_protected_sequence_v1`；pair v2 仍拒绝三词，有测试覆盖。
  - **词实例**：每条序列 2～5 个实例，各有唯一 ID（`o{位置}_{GLOSS}`）与位置序号；序列从首词保护核心开始、到末词保护核心结束，不隐式加入 neutral。
  - **边**：每条边记录来源 pair run、attempt、候选文件 SHA-256 与轨迹哈希、出入口帧、手指策略和边界。
  - **身份**：分开记录两种。pair 身份是候选来源身份；序列身份覆盖 pair 身份、序列政策哈希，以及 `src/`、`tests/` 和三个新增 `scripts/*sequences.py` 入口。pair 代码哈希只收集固定脚本列表，所以新脚本被显式加入序列身份，并有测试确认改动会改变身份。
- **组装**：
  - **connector**：只复用 pair 候选的 connector，系数与时长原样复制，只平移起始时间。
  - **切片**：首词取首对的源切片，末词取末对的目标切片；中间词只取一段，从进入边入口到离开边出口，保护核心只出现一次。
  - **回退**：若整链失败，最多按秩和顺序尝试 64 种独立通过候选的组合。本轮未用到，所有用例第一组合即通过。
- **评分（在看结果前冻结）**：
  - **区域**：每个过渡的评分区为前一核心结束与后一核心开始之间（不含两端）的回放帧，即保留尾部 + connector + 保留头部。各区互不重叠，合起来恰好覆盖全部保护核心外帧，验证器断言这两点。
  - **逐过渡上限**：每个过渡各自满足 v5 上限：加速度 120、jerk 3000、平方 jerk 积分 1,000,000、connector 时长 ≤6 s；每个 connector 另做独立解析检查。
  - **整链**：总积分仅报告。限位、耦合、速度、边界、手指相位、采样几何按整链检查；保护核心内的加速度/jerk 与 v5 一样仅作信息。
- **预算**：沿用 pair 预算，仅墙钟时间由 30 s 改为 120 s，运行前设定。实际最大：9,114 个位姿、16.2 s。
- **正式状态**：单列。`ALGORITHM_WINDOWS_NOT_HUMAN_REVIEWED` 是自动窗口时期的旧措辞，只列在 `legacy_formal_wording_not_a_precondition`，不作为用户保护区间的前置条件。

## 全新 pair run `sequence_pilot_pairs_20261031_001`

| 词对 | 候选 / 数值通过 | 选中 | 与 run 002 比较 |
|---|---:|---|---|
| COME→NOW | 7 / 7 | attempt_00016 | 选中相同，曲线逐项一致 |
| NOW→NOW | 8 / 8 | attempt_00015 | 选中相同，曲线逐项一致 |
| NOW→COME | **18 / 18** | **attempt_00013** | **不同**：run 002 为 17/17，选 attempt_00023 |
| COME→COME | 13 / 13 | attempt_00003 | 选中相同，曲线逐项一致 |

**偏差**：NOW→COME 的 attempt_00013（ik_via2）在 run 002 中因 `TIMING_WALL_TIME_LIMIT` 中止（30 s 墙钟预算已用 16.1 s）；本次正常完成，成为第 18 个候选，并被冻结的选择规则排在第一。**墙钟预算使 pair 候选池受机器负载影响**，重跑不保证完全一致。序列使用本次新 run 的已验证候选；run 002 未修改。

## 12 条序列 `sequences_001`

全部在 attempt_0001（每条边取第 0 名）通过，并再次独立复核。下表为各序列所有过渡区中的最坏值；间隙为采样值，不是连续证明。

| 序列 | 时长 s | 峰值加速度 | 峰值 jerk | 区内积分 | 解析 connector 积分 | 间隙 mm |
|---|---:|---:|---:|---:|---:|---:|
| COME–COME–COME | 11.967 | 40.65 | 442.6 | 254,409 | 469,770 | 4.711 |
| COME–COME–NOW | 10.933 | 40.65 | 442.6 | 254,409 | 824,671 | 4.711 |
| COME–NOW–COME | 12.600 | 31.83 | 315.3 | 253,347 | 824,671 | 7.616 |
| COME–NOW–NOW | 10.133 | 28.60 | 269.4 | 162,442 | 824,671 | 4.418 |
| NOW–COME–COME | 12.567 | 40.65 | 442.6 | 254,409 | 469,770 | 4.711 |
| NOW–COME–NOW | 11.533 | 31.83 | 315.3 | 253,347 | 824,671 | 7.616 |
| NOW–NOW–COME | 11.767 | 31.83 | 315.3 | 253,347 | 580,753 | 4.418 |
| NOW–NOW–NOW | 9.300 | 28.60 | 269.4 | 162,442 | 580,753 | 4.418 |
| COME×5 | 20.433 | 40.65 | 442.6 | 254,409 | 469,770 | 4.711 |
| NOW×5 | 16.167 | 28.60 | 269.4 | 162,442 | 580,753 | 4.418 |
| COME–NOW–COME–NOW–COME | 21.700 | 31.83 | 315.3 | 253,347 | 824,671 | 7.616 |
| NOW–COME–NOW–COME–NOW | 20.633 | 31.83 | 315.3 | 253,347 | 824,671 | 7.616 |

- **全新复核**：`independent_recheck/summary.json` 为 12 用例、12 数值通过、44 实例、44 保护实例不变、32 组 connector，12 条均与规划一致。
- **保护时序**：任一保护实例的最大相对时序误差为 3.1e-15 s，在 1e-12 s 门槛内。
- **逐过渡指标**：与对应 pair 结果一致。有限差分模板只延伸进未改动的保护核心，所以串联不改变任何过渡自身的数值。
- **整链总积分**：最高为 COME×5 的 1,017,639，只报告、不设门槛。

## 视频

12 个视频位于 `results/sequence_pilot_20261031_001/videos/<序列>/comparison.mp4`：上排为完整原始片段拼接，下排为序列；左正面、右侧面；标签显示实例编号、保护/保留/裁剪/新增部分与过渡编号。渲染前重新运行独立验证器，并按绘制视频所用的回放比较保护实例：44/44 逐位一致。

执行模型查看了 COME–NOW–COME–NOW–COME 的联系表，标签与核心结束帧正确（COME f132、NOW f76）。这不是人工或第二组评审，也不是 ASL 可理解性检查。

## 启动命令（全部退出 0，合计 857 s）

```bash
cd /home/kingderman/Documents/ME5412-github-latest
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
```

```bash
.venv/bin/python scripts/plan_all_pairs.py --library hospital_v1 --include-self --policy config/transition_policy_user_protected_v5.json --run-id sequence_pilot_pairs_20261031_001 --results-root results/sequence_pilot_20261031_001/pair_runs --pair COME__NOW --pair NOW__COME --pair COME__COME --pair NOW__NOW --quiet
```

```bash
.venv/bin/python scripts/verify_all_pairs.py --run-id sequence_pilot_pairs_20261031_001 --results-root results/sequence_pilot_20261031_001/pair_runs
```

```bash
.venv/bin/python scripts/plan_sequences.py --pair-run-dir results/sequence_pilot_20261031_001/pair_runs/sequence_pilot_pairs_20261031_001 --output results/sequence_pilot_20261031_001/sequences_001
```

```bash
.venv/bin/python scripts/verify_sequences.py --run-dir results/sequence_pilot_20261031_001/sequences_001
```

```bash
.venv/bin/python scripts/render_sequences.py --run-dir results/sequence_pilot_20261031_001/sequences_001 --output results/sequence_pilot_20261031_001/videos
```

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_sequence_v1.py
```

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider tests
```

日志在 `results/sequence_pilot_20261031_001/P1-3.log`，表格在 `P1-3_tables.txt`。

- **测试**：序列测试 24 项，完整套件 836 项。
  - **合同**：12 用例、pair 政策哈希绑定、拒绝空输入/单词/超长；pair v2 仍拒绝三词。
  - **组装**：中间核心只出现一次、connector 原样复制、两词序列与原词对回放一致、重复词实例 ID 各不相同、引用不一致被拒。
  - **拒绝**：8 种格式错误合同；另有篡改 connector（含合同合法的改动）、候选哈希过期、候选被替换、代码身份过期、保护引用错误、调时、信封损坏，以及预算耗尽报 TIMEOUT 而非通过。
- **身份**：冻结的 pair 代码哈希 `4080b98e73a121c866115882483ef5b7631532d9add4bed4ff5dfbe214ad9cef`（74 个文件）；序列代码哈希 `1ecfcc9f95830071dfbffbb895cf4f664ca5aecd4b38398ceb91ececdea15bb0`。之后任何代码修改（包括文档目录哈希重钉）都会使本 run 过期。

## 文件

- **新增**：`config/sequence_policy_user_protected_v1.json`、`src/sign_robot/sequence_{contract,assembly,verification}.py`、`scripts/{plan,verify,render}_sequences.py`、`tests/test_sequence_v1.py`、TASK-26 中英文。
- **修改**：文档目录（中英各一行）、`project_overview.py` 中两个文档目录哈希（代码冻结前重钉）、STATE/HANDOFF 中英文。
- **未改**：原动作、v5 政策、保护 bundle、模型与历史结果均未修改；COME/NOW、v5 政策与保护 bundle 的 SHA-256 与 P0-1 一致。备份在 `P0-1/backup/`。

## 未验证限制

- 序列未经人工观看；新增过渡是否误导、12 条用例是否仍可理解均未检查。它们不是 ASL 句子。
- 正式 PASS_SIM 为 0；v5 和序列政策都是开发政策，待三组交叉评审。
- 碰撞为采样检查，非连续证明；保护核心内的导数连续性未认证。
- 只运行了 COME/NOW。其余 33 词没有保护区间，其 1,221 对及含这些词的序列都未运行。
- 无 neutral 起止姿态、无实机、未在新环境复现。
- 墙钟规划预算使 pair 候选池受机器负载影响，如上文 NOW→COME 所示。
- 未提交 git。

## 下一步：其余 33 词需要的保护输入

1,225 对扫描要扩展到 COME/NOW 以外，每个词需由用户为其当前动作文件提供保护区间（起止秒，或 30 Hz 帧号，两端包含）。来源（均 `motion_ready`）：

- `motions/studio_galt_v1/`：HELLO、PLEASE、YOU、APPOINTMENT、BREATHE-DEEP、BLOOD-DRAW、TAKE、WHERE
- `motions/wlasl_video_v1/`：THANK-YOU、SORRY、YES、NO、YOUR、ME、DEAF、DOCTOR、NURSE、INTERPRETER、MEDICINE、STOMACH、HEADACHE、HAVE、NEED、WAIT、HURT、UNDERSTAND、WRITE、NOT、SOON、LATER、TOMORROW、MORNING、NIGHT

本轮均未运行。
