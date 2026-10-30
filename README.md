# ME5412 机器人手语表达实验台

**中文** · [English](README.en.md) · [中英说明目录](docs/README.md)

> **当前演示：医院场景的英文 → ASL 机器人手语。** 一位聋人患者就诊、现场没有手语翻译：护士或医生输入英文，第一组用在线 LLM 加词表校验转成 ASL gloss，第二组为每个 gloss 提供 Unitree G1 + Inspire 手的关节轨迹，第三组负责衔接与播放。范围是 1 个场景、35 个 gloss、9 句脚本对话。
>
> 从这里开始：[医院端到端演示](docs/hospital-demo.md)（一条命令从句子到机器人视频，默认离线、不需要 API key）· [第一组 文字→gloss](group1_text_to_gloss/README.md) · [第二组交接](docs/group2-handoff.md) · [汇报要点](docs/presentation-notes.md) · [GitHub 协作](docs/github-collaboration.md)。

| 部分 | 状态 |
|---|---|
| 第一组 英文 → gloss | `group1_text_to_gloss/`，Gemini API 加 35 词表校验；20 句自测全对（原句 9/9、换说法 6/6、词库外 5/5 拒绝）；9 句对话另存离线结果 |
| 第二组 gloss → 动作 | 35/35 个 gloss 有轨迹：9 个来自 Studio Galt 动作捕捉，26 个来自公开 ASL 词典视频 + MediaPipe（评为“近似”） |
| 端到端 | `scripts/demo/hospital_demo.py`；9 句视频与 91 秒完整对话在 `results/demo/` |
| 第三组 衔接与播放 | 进行中；当前使用固定 0.5 秒过渡的基线拼接 |

机器人动作是候选手语动作，**未经 ASL 使用者评审**；第一组测试为组内自测，不是独立测试。

## 前期工作：三类网页原型

以下内容是项目前期的可运行研究原型，保留作为对照与历史记录。默认演示将英文或短语按钮映射到有限动作；“学习模型”实验入口从文字向量与连续相位生成关节轨迹。已完成一次小型 RBF 岭回归训练，使用 3 条自编轨迹、367 个训练帧及 365 个同轨迹验证帧。该原型仅覆盖 HELLO、THANK_YOU、PLEASE_WAIT；所有动作的 ASL 可理解性尚未经过真实使用者评审，PLEASE_WAIT 还存在词例到完整礼貌请求的表达缺口。十类学习动作的计划见 [十类语意指南](docs/ten-intent-learning-guide.md)，[六人接手说明](docs/six-person-handoff.md) 仅保留首版历史背景。

代码仓库现为 **GitHub 公开仓库**，组员以协作者身份提交 PR；网页展示版另行分享。

## 给组员的入口

- **已有在线项目**：[原在线展示版](https://me5412-robot-signing-lab.kimzc0103.chatgpt.site)。本轮更新仓库的双语说明与网页源码，未同步线上站点；实时模型推理保留在本地。
- **代码与实验**：使用 `git clone https://github.com/kimzclandi/me5412-sign-robot.git`。仓库公开可读；提交代码需要仓库所有者邀请为协作者，`master` 受保护，须通过 PR 合并。
- **完整实验台**：按下方“环境和资源复现”准备 Python 环境，再启动本地服务。
- **网站源码**：[website/README.md](website/README.md) 包含已经发布的静态展示版及独立预览命令；GitHub 推送不会自动重新发布网站。

仓库保留原始提交、冻结实验及失败记录，并包括本项目训练得到的约 3 MB 回归检查点。第三方 MiniLM／LLM 预训练权重、机器人 vendor 网格、虚拟环境、运行会话日志和本机私有配置均不上传；基础依赖使用固定来源脚本恢复。How2Sign 文本索引按已记录的 CC BY-NC 4.0 范围用于非商业课程研究，未包含源视频。第三方来源和机器人 BSD 许可见 [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt)。

## 在当前电脑打开

双击 `run_demo.command`，或在本目录执行（重复运行会复用健康的本项目进程）：

```bash
.venv/bin/python -m sign_robot.service start --port 5412
```

浏览器打开 <http://127.0.0.1:5412>。启动器会等待健康检查通过，再报告后台服务已就绪；终端窗口关闭不会主动停止它。该地址仅在运行服务的这台电脑可用。电脑重启后需再次运行启动器；没有设置开机自启或公开服务器。

```bash
.venv/bin/python -m sign_robot.service status
.venv/bin/python -m sign_robot.service stop
```

若页面打不开，先执行 `start`。日志在 `results/session_logs/service-5412.log`。端口被其他或旧服务占用时，启动器会明确报错，不抢占端口、不自动杀进程。需要前台调试时仍可使用 `.venv/bin/python -m sign_robot.server --port 5412`，按 Ctrl+C 结束前台进程。

推荐演示顺序：

1. 输入 `Thank you.`，固定匹配会选中 THANK_YOU，默认不播放未评审动作。
2. 勾选“允许研究预览”后再次提交，查看真实 MuJoCo 渲染的候选轨迹。
3. 选择“语义匹配”，输入 `Many thanks`，检查改写到同一表达的选择。
4. 输入 `I do not want to wait.` 或 `Please wait and take two pills.`，检查拒绝且不播放。
5. 打开“验收与边界”查看当前结果，再用“六人协作”明确后续负责人。
6. 打开“动作检查”，点击“打开候选轨迹”，切换正面／右侧斜视、拖动帧位置，并查看关节角、差分速度和手指耦合关系。
7. 打开“学习模型”，输入 `Thank you`，选择延长 20%，点击“生成并检查研究候选”：实际得到 289 帧 × 53 坐标、9.6 秒的新模型输出。拖动帧位置，查看本次预测经 MuJoCo 正运动学计算的骨架，并下载 JSON。

## 项目可视化导航

网页顶部可切换中文／English，并在同一浏览器记住选择；`?lang=en` 可直接进入英文界面。说明下载随界面语言切换。网站默认进入“项目总览”，八个页面可通过侧栏或手机顶部导航访问；地址中的 `#overview`、`#learning` 等片段可直接定位页面，浏览器前进、后退和刷新保留页面位置。切换页面会暂停离开的播放器。

| 页面 | 小组讨论时怎样使用 |
|---|---|
| 项目总览 | 切换“动作库路线／学习模型路线”，点击五个流程节点，查看每步输入、输出和负责模块，再跳入实际功能。 |
| 交互演示 | 比较固定匹配、语义匹配及研究用本地大模型的选择行为；候选预览仍需显式勾选。 |
| 学习模型 | 实际生成、检查并逐帧查看本次模型输出；说明文字向量、相位基、26 到 53 坐标的重建关系。 |
| 动作检查 | 对照既有候选动作的正面／侧面视频、时间轴与关节曲线。 |
| 数据路线 | 查看 How2Sign 的原始划分，区分 35,263 条文本记录、尚缺的运动监督与现有三条自编示范。 |
| 实验评价 | 分开查看支持输入与库外输入，每组分母均为 30；展示错误拒绝、错误动作和接口错误，不只比较总分。 |
| 六人协作 | 当前页面仍展示此前的角色说明，尚未同步本次文档分工；现行三组职责以[六人分工指南](docs/ten-intent-learning-guide.md)为准，尚未绑定具体同学。 |
| 资料与汇报 | 手动播放既有学习模型输出的六段视角视频，按类别打开或下载 PPTX、PDF、讲稿及证据。 |

建议首次介绍沿“总览 → 交互演示 → 学习模型 → 数据路线 → 实验评价 → 六人协作 → 资料与汇报”展开。“动作检查”留给需要解释某个手型或关节问题时使用。

总览数据通过只读 `GET /api/project` 汇集现有证据。材料由固定白名单与 SHA-256 校验提供，不开放任意本地文件。页面上的 **206 项通过**明确属于学习升级时的冻结历史快照。本次可视化升级的 **222 项全仓测试通过**、**12 项导航回归检查通过**和桌面／手机浏览器检查另存于 `results/visualization-v1/`，没有覆盖旧验收结果，也没有新增训练、语料动作监督或 ASL 可理解性结论。

动作检查资料由 `.venv/bin/python scripts/export_inspection.py --allow-candidate-preview` 生成，保存在 `results/inspection/` 的独立版本目录。数据和视频 URL 固定运行编号，重新导出不会让已打开的旧页面混入新动作。该页依旧是运动学预渲染与轨迹数据同步展示。

“交互演示”和“动作检查”播放提前由真实 MuJoCo 逐帧渲染的 MP4；“学习模型”每次请求实际推理和检查，网页绘制本次生成轨迹的连杆骨架。两者均未运行执行器动力学。若要旋转视角、在原生 MuJoCo 中查看原始轨迹，请运行：

```bash
# macOS passive viewer 使用 mjpython
.venv/bin/mjpython scripts/play_motion.py --action HELLO --allow-candidate-preview
```

## 当前能力与边界

| 部分 | 当前实现 | 证据边界 |
|---|---|---|
| 模型 | Unitree G1 + Inspire DFQ，固定基座，53 个标量关节位置，保留 12 条 mimic 关系 | 没有执行器控制；不是 53 个独立驱动 |
| 动作 | 三条由 agent 编写手工关键帧、数值 IK 和插值制作的候选轨迹；THANK_YOU 和 WAIT 已实际观看来源视频作定性校准 | 没有从真人视频提取三维运动；没有真人 ASL 审查；头部与面部不动 |
| 固定匹配 | 公共拒绝规则 + 完整登记短语 | 不是任意英文理解 |
| 语义匹配 | 公共拒绝规则 + 本地 MiniLM，真实 384 维句向量 | 初始阈值不是校准概率，正确改写仍可能被拒绝 |
| 学习轨迹 | 冻结 MiniLM + 40 个高斯相位基 + 已训练的岭回归权重；26 主动上肢坐标重建成 53 坐标 | 只拟合 3 个自编示范；同轨迹插值，非新词泛化；独立实验入口，不替换默认动作库 |
| 公开语料 | How2Sign 35,263 条英文句子/ID/时间戳记录，原始 split 与 SHA 保留 | 新视频、人体姿态及机器人动作监督均为 0；不能称为已学会 35,263 个表达 |
| 大模型 | 本地 loopback 服务适配，严格检查返回 ID 与状态；现有 0.5B 级 Q8 模型已实际测试 | 开发正例只选对 2/3，未通过默认启用门槛；保留研究负结果，不自动调用远程 API |
| 评估 | 18 条开发样例、60 条冻结探索性测试，原始记录及失败逐条保存 | 样例由 agent 起草，尚未经人工标签复核；只评候选 ID 选择 |
| 临床与语言 | 无已验证结论 | 不证明治疗效果、安全部署、替代翻译员或任意句子翻译 |

首轮冻结文本测试中，固定匹配为 38/60，MiniLM 加相同规则为 47/60；支持输入选对分别为 8/30、17/30，错误拒绝分别为 22/30、13/30，库外错误执行均为 0/30。分母很小且标签尚未人审，不能将这个零写成普遍零风险。初次报告保存在 `results/evaluation/test-20261008T135255840626Z/`；后续独立运行另建目录并保留前次记录。

追加真实本地 LLM 研究对照保存在 `results/evaluation/test-20261008T142047221403Z/`，三方法总计 180 条原始记录，所有失败均保留。固定匹配和 MiniLM 分数未变。LLM 加公共规则为 48/60，但支持输入中选错 1 条、返回非法标签 2 条，库外错误选择动作 2/30；不能只按总分将其称为更好的方案。60 题中只有 35 题实际请求 LLM，另 25 题由公共规则处理；标签未经人工复核。前一次因受限沙箱无法访问本机端口的 `not_run` 记录也保留，随后仅修复了运行权限，未更改配置、题目或提示。

首版完整软件与轨迹测试 **143 项通过**，资源/数据哈希 **75 项通过**。实际浏览器演示已检查默认阻断、显式预览、真实语义匹配和混合意图拒绝；`results/acceptance.json` 保存首版范围。升级后的独立验收保存在 `results/phase2/`，不覆盖首版记录。

## 本次学习升级与课程材料

- [学习模型与实际指标](docs/学习型轨迹模型.md)：闭式回归而非深度生成模型；未知输入拒绝；预测直接使用实际文字向量，推理不读取原 `motions/*.npz`。
- [公开语料规模与下一步](docs/语料规模与模型升级.md)：已接入索引的数量、许可与视频/姿态缺口。
- `results/motion_learning/v1/`：冻结协议、权重、一次拟合日志、验证结果与 9 条生成 NPZ（6 条主检查、3 条改写探索）。六条主检查均满足冻结工程阈值；同示范奇数帧最大 RMSE 为 0.002528 rad。保留原始角度越界/投影修正和 0.644 mm 最大微穿透，不能声称完全无接触。
- `results/motion_learning/v1/previews/`：从新模型生成 NPZ 重新渲染的 6 段机器人正面/侧面视频。
- [14 页英文汇报 v4](deliverables/course-report-v4/ME5412_Text_to_Robot_Signing_v4.pptx)、[静态 PDF](deliverables/course-report-v4/ME5412_Text_to_Robot_Signing_v4.pdf)、[中文讲稿](deliverables/course-report-v4/speaker-notes.zh-CN.txt)：建议口述 14 分 25 秒，尚未实际计时排练。PPTX 可编辑，PDF 为图像预览；尚未在原生 PowerPoint 检查。
- `results/analysis/frozen-test-final/`：直接从历史 180 条原始结果重算的图表与失败解读，不重跑或调优冻结文本实验。

已有 v1 训练不可覆盖重跑；新实验应另建版本并先冻结协议。服务缓存 v1 检查点，因此不支持运行中替换同一目录的权重；升级模型版本后应重启本地服务。离线复核公开索引：

```bash
.venv/bin/python scripts/fetch_corpus_index.py --verify
```

首版历史任务卡为：A1 补有语境的动作来源，A2 做人体到机器人重定向，B1 整理文本与动作配对，B2 负责独立版本的学习模型，C1 冻结独立动作/使用者测试，C2 集成、复现与答辩。现行分工以[三组两人指南](docs/ten-intent-learning-guide.md)为准。没有独立姿态监督前，不通过扩大英文索引数量来宣称动作能力增长。

## 环境和资源复现

本机已验证 Python 3.12、Apple silicon、MuJoCo 3.15。其他操作系统尚未实际验证。`requirements-lock.txt` 记录本轮依赖，不含本机绝对路径。

在另一台有 Python 3.12 的 Mac 上，可按以下顺序准备；需要网络下载免费公开依赖与模型，但不需要付费 API：

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python scripts/fetch_robot.py
.venv/bin/python scripts/prepare_robot.py
.venv/bin/python scripts/fetch_embedding.py
# 原候选轨迹与 v1 检查点已保存，不重新制作或训练。
.venv/bin/python scripts/render_motions.py --allow-candidate-preview
.venv/bin/python scripts/verify_assets.py
.venv/bin/python -m pytest -q
```

原机器人网格约 27 MB，本地 MiniLM 权重约 87 MB；第三方资源保存在忽略目录，源码仓库本身不携带大权重或网格。恢复资源时按固定 revision 下载，并核对哈希。安装和模型转换不修改现有 AI Infra 项目的环境。

## 源码与接口

- `contracts/interfaces.json`：编号、选择状态、轨迹约定。
- `data/catalog.json`：含义、别名、排除条件与评审状态。
- `data/source_manifest.json`：一手来源、实际看过的内容、使用范围与冻结数据哈希。
- `src/sign_robot/language.py`：公共拒绝规则、exact、真实本地 embedding。
- `src/sign_robot/llm.py`：本地大模型白名单适配；异常不会回退成另一个方法。
- `src/sign_robot/motion.py`：按关节名装载和回放轨迹。
- `src/sign_robot/pipeline.py`：区分选中表达和允许候选预览。
- `src/sign_robot/server.py`、`web/`：仅监听本机的演示界面。
- `motions/*.npz`：时间戳 `[T]`、关节名 `[J]`、关节位置 `[T,J]`；转动关节单位为弧度。
- `motions/development_failures/`：已发现穿透等问题的开发版本，保留用于失败分析。

每个编号还带一个 JSON，记录上游模型提交、制作方式、IK 误差及限制。语言模块只能选编号，不向机器人输出关节命令。

## 评价与验收

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/verify_assets.py
.venv/bin/python scripts/evaluate.py --split test
```

最后一条会新建结果目录，禁止覆盖前次。不要根据冻结测试成绩回调阈值后将新成绩称为独立验证。若以后增加真实本地 LLM，可显式使用 `--include-llm`；方法不可用时报告 not_run，不把规则拒绝当作模型效果。

当前 LLM 默认仍未配置，已停止本轮专用 5413 服务。仅研究复现时，按 `config/local_runtime.example.json` 配置已有本地模型与 MLX 环境（本机私有路径不入库），运行 `scripts/start_local_llm.command`，再使用：

```bash
SIGN_ROBOT_LLM_CONFIG=config/llm_experimental.json .venv/bin/python scripts/evaluate.py --include-llm --run-reason '按原配置复现本地LLM研究对照'
```

研究配置没有通过默认启用门槛，不应换入默认 `config/llm.json`。本轮重用的本地检查点及既有 MLX 环境独立于 MiniLM 安装流程；它不是新电脑安装基础依赖后就自动可用的模型。具体架构、权重哈希和历史不确定性见 `config/llm_local_provenance.json`。若在受限执行环境中运行，需允许访问本机 5413 端口；连接失败不是模型质量结果。

测试分别检查非法 ID 和 JSON、失败不执行、候选预览门槛、真实 HTTP 路由、视频 Range、轨迹形状、关节限位、耦合、速度和上游已有碰撞几何。已有碰撞几何的检查通过，不等于完整自碰撞安全证明。首版汇总见 `results/acceptance.json`；网页升级验收见 `results/visualization-v1/acceptance.json`。

## 来源与使用范围

机器人来自 [Unitree 官方模型](https://github.com/unitreerobotics/unitree_ros/tree/master/robots/g1_description)，上游提交与逐文件哈希见 `assets/robot/upstream_manifest.json`。导入时修复了上游 meshdir 与 filename 的重复路径，原始 vendor 文件保持不变。

手语参考来自 [ASL University / Lifeprint](https://www.lifeprint.com/)，具体页面及观察见 [来源审查](docs/source-review.md) 和 [视频校准记录](docs/video-calibration.md)。THANK_YOU 的起手、前下移动与终掌向上有逐时对照；WAIT 仍只是词例。这里只保存链接和自行编写的观察，没有打包原图片、视频或课程材料。机器人候选轨迹是本项目工程近似，不代表来源作者或 ASL 使用者认可。

语义模型来自 [Sentence Transformers MiniLM](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)，固定提交和哈希见 `config/embedding_download_manifest.json`。

当前是课程研究原型。公开发布前需要另行检查第三方模型、代码、媒体的许可及课程要求；未替团队申请数据或联系评审。已有网站保留原有访问状态，本轮未重新发布。代码仓库已由所有者于 2026-10 改为公开；第三方视频、模型权重和 API key 仍不入库。
