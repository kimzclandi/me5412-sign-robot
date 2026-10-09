# 来源与探索性评价记录

**中文** · [English](source-review.en.md) · [说明目录](README.md)

核对日期：2026-10-08（Asia/Singapore）。这是 agent 的资料核对与工程记录；没有 ASL 使用者审查，没有临床验证。机器可读细节在 `data/source_manifest.json`。

## 当前三条候选

| ID | 已查证来源 | 当前能支持的制作依据 | 尚不能声称 |
|---|---|---|---|
| HELLO | [Lifeprint / ASLU hello](https://www.lifeprint.com/asl101/pages-signs/h/hello.htm) | 文字明确允许自然侧向挥手问候 | 未规定数值手型、掌向和时长；机器人是否可理解仍待审查 |
| THANK_YOU | [Lifeprint / ASLU thank you](https://www.lifeprint.com/asl101/pages-signs/t/thankyou.htm) | 平掌从近唇处向对方前伸略下；已在浏览器看示范图末姿与路径图，末姿掌面朝上 | 微笑未由机器人验证，不能与 GOOD 混淆 |
| PLEASE_WAIT | [WAIT](https://www.lifeprint.com/asl101/pages-signs/w/wait.htm)、[PLEASE](https://www.lifeprint.com/asl101/pages-signs/p/please.htm) | WAIT 的文字和连续照片已看：双手略抬偏侧、掌面向上或斜上，摆动手指 | 没有核验到完整 PLEASE_WAIT 请求示范；两个词例不能当成完整句子或礼貌表达审查 |

首轮来源核对使用 THANK_YOU、WAIT 页面图片/动画截取和连续照片；随后按用户明确要求实际播放了这两条官方视频，并逐帧查看关键姿态，详见 `docs/video-calibration.md`。`source_manifest.json` 已更新实际观看状态与观察时间点。HELLO、PLEASE 仍只使用公开教学文字核对。数值关节角、手臂长度适配、时长和插值均是项目自制的工程近似。

PLEASE 的页面明确讨论请求的表情和语用，并说明其常作为句末附加。当前保持接口 ID `PLEASE_WAIT` 只是软件兼容；若动作只实现 WAIT，界面和元数据必须展示“WAIT 候选，完整请稍等表达未核验”。不得将字典词汇按英文顺序拼接后标为已验证 ASL。

## 使用范围

已读 [Lifeprint 权限页](https://www.lifeprint.com/asl101/pages-layout/permission.htm)：允许链接和自学，公开复制/嵌入其图片、视频、课程材料不包含在现有许可中。本项目不下载、复制或嵌入这些媒体，仅留链接、简短自写观察与自行制作的工程轨迹。未联系作者，未提交个人信息申请，未获得其对机器人动作的背书。未来公开发布须独立复核实际材料与条款，不能把网页可访问写成媒体可再分发。

新加坡本地应用也需语言本地化：[SADeaf 说明 SgSL](https://sadeaf.org.sg/sgsl-course/)是当地 Deaf community 使用的手语。本阶段 ASL 选型只用于课程工程探索，不代表面向所有新加坡聋人可直接使用。

## 评价协议 v1

- 开发集 18 条、最终集 60 条（30 条支持输入、30 条库外/否定/角色变化/混合/医疗请求/不明确输入）。全部由 agent 拟写并初标，尚未人工复核；这不是先前建议的 120 条正式人工集。
- 含义范围以 catalog 为准：整句必须与单一候选一致。附带时长、地点、条件或第二意图不能部分执行。
- 语言实现者可看开发集，不读取最终题调参。最终集在首个实验前冻结；运行脚本强制对比 SHA256，失败案例原样保留。
- 最终集 SHA256：`83a4f5310f28f45a5cc2aeecf6660742c2bf93b0b0f99660ad08d6d02f2f4231`。
- 开发集 SHA256：`e33fc62e3280cbbf6b61578e99c5ca9a08c492139e683cec0178f2e500bfdf04`。
- 评价只测试“英文 → 候选 ID/拒绝”。返回候选 ID 的正确，不表示机器人动作能执行、已通过 ASL 审查或可用于医疗沟通。
- 主准确率将库外的 clarify/unsupported 都视为正确不执行；error 计错误。另保存严格 status 一致率，避免把拒绝与澄清的区别藏起来。
- 支持集正确选择率 = 支持输入中 execute 且 ID 正确 / 支持输入数。
- 支持集错误拒绝率 = 支持输入中 clarify 或 unsupported / 支持输入数；运行错误单独统计，不能当成功拒绝。
- 库外错误执行率 = 库外输入中 execute / 库外输入数。
- 执行覆盖率 = 所有 execute / 全部样本数；执行正确率 = 执行且正确 ID / 所有 execute。零执行时后者为 null，不能写 100%。
- 原始决策、错误样例和 summary 同目录另存。不要为通过改题、降低阈值，或把看过错误后的重跑称独立结果。
- 延迟为 evaluator 测得的单条调用墙钟时间，含 guard 与方法执行；每方法一个不触发 guard 的 catalog alias readiness/warmup 单独记录，不计入稳定调用分布。报告中位数、P95、最大值；它不是机器人首次可见动作延迟。
- 缺后端时跳过整种方法，不能把公共 guard 拦下的题当成 LLM 已运行的成绩。默认 LLM 未执行；可用本地服务并明确启用后再测。

运行：

```sh
.venv/bin/python scripts/evaluate.py --split dev
.venv/bin/python scripts/evaluate.py --split test
```

每次输出新目录，默认拒绝覆盖已有结果。若模型未准备好，在 summary 里保留未执行原因。最终集的人工标注复核和 ASL 使用者开放复述实验是后续工作，不伪造已完成。

## 首次冻结集结果（2026-10-08）

运行目录：`results/evaluation/test-20261008T135255840626Z/`，包含 `summary.json`、120 条真实调用记录 `raw.jsonl` 和 35 条失败记录 `counterexamples.jsonl`。语言源码 SHA256 为 `f0a9a40be70ce1bdd0d55672f24b8fcdfc7cf4e8d24ecc2ffc54ca7333568e0f`；测试集与方法源码在运行前后哈希一致。未按最终集结果调阈值或重做题目。

| 指标 | exact + shared guard | MiniLM embedding + shared guard |
|---|---:|---:|
| 整体行为准确率 | 38/60（63.3%） | 47/60（78.3%） |
| 支持输入选对 | 8/30（26.7%） | 17/30（56.7%） |
| 支持输入错误拒绝 | 22/30（73.3%） | 13/30（43.3%） |
| 库外错误执行 | 0/30 | 0/30 |
| 执行覆盖 | 8/60（13.3%） | 17/60（28.3%） |
| 本次执行正确率 | 8/8 | 17/17 |
| 运行错误 | 0/60 | 0/60 |
| 单条调用中位数 / P95 | 0.0076 / 0.0142 ms | 3.2399 / 3.7593 ms |
| 独立 readiness / 冷加载调用 | 0.3303 ms | 2430.7508 ms |

LLM 未配置且未启用，标记 `not_run`，没有模型成绩。观察到 embedding 在这个小型 agent 拟题集上多选对 9 个支持输入，同时仍拒绝 13 个支持输入。这里的 0/30 错误执行和执行正确率不代表总体零风险；公共规则、简单库外样本和未经人审标签都限制结论。运动仿真和 ASL 可理解性不在该评价范围内。

## 本地 LLM 开发可行性负结果

随后 B2 复用了本机已有免费小模型服务，只对三个固定开发正例做了以下预先限定试验，未读取或调整 60 条最终测试题：

- V1：HTTP 请求实际成功，但三个回答均只有 `execute`，缺少 JSON 与动作 ID；严格客户端解析全部报 `llm_invalid_response`。原始请求/回复在 `config/llm_local_feasibility_v1.json`。
- V2：在明确授权的一次工程修复中，输出协议改为五种完整标签，程序严格匹配后封装统一 Selection。`Hello → HELLO`、`Thank you → THANK_YOU`、`Please wait → CLARIFY`：3/3 格式合法、2/3 选择正确，未通过预设三个正例全部选对的启用门槛。原始记录在 `config/llm_local_feasibility_v2_label.json`。
- 开发阶段没有继续改提示词，也没有将 V2 拒绝当正确；`config/llm.json` 继续保持未配置。两次开发试验都保留，不能当最终集泛化成绩。

该开发门槛失败后，经明确授权将相同 V2 后端作为负结果研究对照；没有改写启用结论，也没有改题、阈值、提示词或模型。默认配置仍关闭，只有显式 `SIGN_ROBOT_LLM_CONFIG=config/llm_experimental.json` 才选择该研究配置。

## 追加真实本地 LLM 研究对照（2026-10-08）

新结果：`results/evaluation/test-20261008T142047221403Z/`。首轮结果完整保留。另保留 `test-20261008T141909955017Z/`：它在受限沙箱中无法连接 loopback，本机服务未收到该请求，LLM readiness 为 `request_attempted=true`、`response_received=false`，方法整体 `not_run`；不能把它算作模型质量失败。随后只修复本机访问权限，运行原因记录为“仅修复受限沙箱阻断loopback访问；保留前次not_run；不改模型或协议”。两个追加目录记录的所有来源、源码、配置哈希完全相同，运行前后也一致。

这是同一冻结小型集上的追加方法研究比较，不是新采集的人工确认集。原 60 题的 SHA256 未变，B1/B2 没有读取最终题调参。研究配置 SHA256 为 `029a9a8cac30db39bee31c3c3dee2c8de8fd12c298875afa04317760189393b9`；所有实际 HTTP 调用的提示词前缀 SHA256 均为 `763a7102f8acc89dab9ed133d2303ec9feda94cf24b11379df198d4eac53f379`，与 V2 开发试验一致。模型的实际文件哈希、架构及已有转换来源记录在 `config/llm_local_provenance.json`；其原始调优历史未在本任务独立确立，不称为新训练或纯净官方基线。

| 指标 | exact + guard | MiniLM + guard | 本地 0.5B 类 LLM + guard |
|---|---:|---:|---:|
| 整体行为准确率 | 38/60（63.3%） | 47/60（78.3%） | 48/60（80.0%） |
| 支持输入选对 | 8/30 | 17/30 | 20/30 |
| 支持输入错误拒绝 | 22/30 | 13/30 | 7/30 |
| 支持输入执行错误 ID | 0/30 | 0/30 | 1/30 |
| 库外错误执行 | 0/30 | 0/30 | 2/30 |
| 执行覆盖 | 8/60 | 17/60 | 23/60 |
| 本次执行正确率 | 8/8 | 17/17 | 20/23（87.0%） |
| error（包括非法模型标签） | 0/60 | 0/60 | 2/60 |
| 单条 selector 中位数 / P95 | 0.0080 / 0.0160 ms | 3.0392 / 3.2139 ms | 18.7660 / 24.4787 ms |
| 独立 readiness 调用 | 0.3842 ms | 2063.5158 ms | 38.5327 ms |

LLM 的 60 题中，25 题在共享 guard 阶段结束，35 题收到真实 HTTP 回答；此外只有一个独立 readiness 请求，不计入 60 题。实际 HTTP 子集选对或正确拒绝为 25/35，其 selector 调用中位数 / P95 为 20.0599 / 36.5609 ms。这是通过 guard 后的条件子集，不是随机总体，也不是剥离程序开销后的纯模型延迟。服务在评价前已启动，LLM readiness 不能称为从零冷启动；MiniLM readiness 包含本评价进程加载。

本次 LLM 总分略高，但它把两条库外输入错误选择成感谢，并在支持输入中出现错误 ID 和两个非法标签。严格解析保留 `error`，没有回退到固定规则伪装成功。因此当前证据不支持启用该 LLM 作默认选择器，也不证明它比 embedding 更可靠。具体失败在同目录 `counterexamples.jsonl`；180 条原始决策在 `raw.jsonl`，每条保留完整 Selection、执行路径、真实返回文字与 HTTP 元数据。47 条失败记录没有删除。

评价程序新增了实际配置的前后哈希、模型 provenance 与 V1/V2 开发门槛证据哈希，以及“guard / 收到 HTTP / 尝试但未收到 / HTTP 前失败”的归因。单元测试验证缺后端不计成绩、错误分母与原始输出保留；这不替代标签人审、ASL 可理解性或真实机器人验收。

