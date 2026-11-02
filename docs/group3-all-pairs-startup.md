# 第三组全词对开发扫描：启动与复核

[English](group3-all-pairs-startup.en.md) · [任务规划](group3-all-pairs-transition-plan.md) · [本轮执行记录](group3-all-pairs-progress.md)

2026-10-31 开始实施。首轮交付是 T00/T01/T02 与 T04、T06 的基础设施：冻结输入、逐词审计、直接连接基线、全范围矩阵、原子检查点和保存文件的独立复核。T03 质量政策、T05 通用候选与搜索、T08 多词组合及最终 L2 验收仍需后续工作。

## 环境与命令

工作目录为 `/home/kingderman/Documents/ME5412-github-latest`。沿用仓库 Python 环境与资源恢复说明；完整锁定依赖见 `requirements-lock.txt`。运动扫描只导入 NumPy、SciPy、MuJoCo 和运动合同，不导入语义编码器。当前机器复用了已有的匹配依赖环境，`.venv` 是本地软链接，不属于交付资源；新机器应创建自己的虚拟环境。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install -e .
```

机器人必须具有 `assets/robot/upstream_manifest.json` 记录的全部资源。缺文件或哈希漂移会进入输入阻塞。恢复方式见 [机器人资源](../assets/robot/README.md)。MiniLM 仅用于修复旧学习模块的基线测试，不是词对扫描的前置依赖。

```bash
# 可单独生成 T00/T02 证据；正式运行会再次冻结到自己的结果目录。
.venv/bin/python scripts/freeze_all_pairs_inputs.py

# 先运行冻结的 40 对开发/性能校准样本。
.venv/bin/python scripts/plan_all_pairs.py --library hospital_v1 \
  --include-self --policy config/transition_policy.json \
  --run-id all_pairs_dev_20261031_v2 \
  --pairs-file config/transition_development_pairs.json

# 在同一冻结输入下续跑其余词对，再独立读取全部保存结果。
.venv/bin/python scripts/plan_all_pairs.py --library hospital_v1 \
  --include-self --policy config/transition_policy.json \
  --run-id all_pairs_dev_20261031_v2 --resume
.venv/bin/python scripts/verify_all_pairs.py --run-id all_pairs_dev_20261031_v2
.venv/bin/python scripts/summarize_all_pairs.py --run-id all_pairs_dev_20261031_v2

.venv/bin/python -m pytest -q tests/test_all_pairs_contract.py tests/test_all_pairs_pipeline.py \
  tests/test_plan_transitions.py tests/test_transition_endpoint_gate.py tests/test_rrt_connect.py
```

`--max-pairs N` 可用于检查中断恢复；未执行的词对仍为 NOT_RUN，分母始终是 1,225。`--pair SOURCE__TARGET` 可重复指定调试词对；词库外名称会被拒绝。三个新入口支持 `--results-root`，默认 `results/all_pairs/`。`plan_transitions.py --all` 继续表示原来的固定十句。

运行和复核入口固定四个常用计算库线程环境变量为 1，并保存实际依赖和机器架构。续跑校验代码提交与源码哈希、策略、实际机器人资源、动作与元数据、开发集、词表和依赖环境；变化后应使用新 run_id。修改代码后不能把旧目录当作本版实验继续。程序正常返回 0 只表示命令完成，不表示 L2 通过。

## 冻结合同和输出

`config/transition_policy.json` 固定 35 个 gloss、1,225 个有向词对和 35 个自对。范围不使用旧规划器的额外词库回退。当前规划方法是单个、限速、至少 0.3 秒的五次最小跃度直接连接，搜索预算为一个候选及有限碰撞采样量。失败保留诊断轨迹；这不是通用 RRT 的完成记录。

端点采用动作索引中原始 `sign_frames`。这些帧是几何提示，不是已批准的语义核心。旧的 MEDICINE/NIGHT/HURT/NURSE/INTERPRETER 帧覆盖迁入政策中的研究对照清单，绑定动作哈希并保留 pending 状态，扫描不采用这些覆盖。NURSE f80 的 8/79 裁剪和 f81 对照都在逐词审计中；新动作版本不继承旧例外。

每轮结果包含：

| 文件 | 内容 |
|---|---|
| `policy.json`、`library_manifest.json` | 政策快照、动作/模型/环境/源码版本与哈希、53 个关节和 12 条耦合关系 |
| `word_audit.json` | 35 词格式、时间、限位、耦合、原词碰撞、端点和边界导数；核心/窗口审核状态 |
| `pair_universe.json` | 固定的全部有向词对，含 35 个自对 |
| `checkpoints/*.json` | 每对原子写入的记录及内容哈希 |
| `trajectories/*.npz` | 两次词动作及连接的完整候选，保留原词样本；非播放批准 |
| `verification/*.json` | 独立文件读取、原词样本/边界/时间/哈希检查及加密几何和质量指标 |
| `pairs.jsonl`、`matrix.csv`、`summary.json` | 唯一主状态、35×35 矩阵，以及全部/异词/同词分列统计 |
| `manifest.json` | 冻结输入、完成状态与整轮文件清单和 SHA-256 |

结果目录中的 `.part` 文件不作为检查点。崩溃前已完成的检查点可以续用；损坏的策略、记录或轨迹会被拒绝。`--resume` 不自动重试已记录的 ERROR/TIMEOUT，也不改变预算；增加预算应另开版本。本期只实现第一次 attempt，不声称已有重试实验。

数组哈希将关节名编码为 UTF-8 JSON，时间与位置按固定顺序规范化成小端 float64、C 顺序，统一负零。它用于比较数值内容；NPZ 文件 SHA 用于传输完整性。运行耗时不进入数值数组哈希。

## 复核范围与状态解释

复核器不调用规划函数，也不导入历史 PASS。它重新读取原词和保存的两词 NPZ，确认两次词动作和连接端点，再沿声明的五次曲线以 1×、2×、4× 分辨率及每步不超过 0.04 rad 的约束采样。原词采用已保存样本之间的线性回放曲线，同样做加密；完全一致的原词片段可复用本轮独立测得的缓存。相同采样数的连接查询可复用测量结果，报告仍列出每档实际采样数。

检查沿用当前上游碰撞几何、MuJoCo 原生碰撞对过滤和同手排除；静态结构对另外报告。它没有完成过滤规则的最终审核，也没有实现连续碰撞证明或按小间隙/高曲率自适应细分。边界速度/加速度采用固定 5 帧单侧二次最小二乘估计；加速度和 jerk 另报完整保存轨迹在播放时刻的数值差分指标，不能当作连续导数证明。

原词内部碰撞和速度问题独立列出，不因过渡段合格而隐藏。原词帧和时间没有被修订。语义核心未知时 `protected_core_preserved` 保持 null；`original_word_slices_preserved` 只证明保存的片段没被改写。

当前所有新轨迹的 `playback_eligible` 均为 false，本版不会产生 PASS_SIM。即使仅把政策中的审核字符串改成 approved，尚未实现的批准核心合同仍会阻止通过。`FAILED_QUALITY` 可以表示质量阈值/窗口待确认，应结合 `reason_codes` 和复核文件的 `numerical_checks_passed` 阅读。`FAILED_SEARCH` 表示这个固定直接候选或其加密检查失败，不是路径不存在的证明。BLOCKED_ENDPOINT 分别列出 source/target；不能以 SOURCE_NEAR 替代 +2 mm 的绝对要求。

原始大结果保存在被忽略的 `results/all_pairs/`。代码审查用的摘要和实际测试日志另存在 `results/group3_all_pairs_startup/`。只有本机路径不构成跨机器交付包；T10 的资源交付与新环境复核仍未完成。人工、语言和实机评审继续保持未验证。

v1 校准运行保留归档。最终 v2 用 `planning_evidence` 单独保留规划阶段证据；11 对加密新增失败不会因覆盖播放帧指标而丢失。新实验使用新 run_id；读取现有完整运行时使用续跑或汇总命令。
