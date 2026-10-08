# ME5412 机器人手语表达实验台

这是六人课程项目的第一版可运行研究原型：英文或短语按钮选择一个有限含义，然后预览同一编号的机器人候选动作。当前使用真实 MuJoCo 模型、手工关键帧与本地句向量模型。项目支持 HELLO、THANK_YOU、PLEASE_WAIT 三个候选编号；所有动作的 ASL 可理解性尚未经过真实使用者评审，PLEASE_WAIT 还存在词例到完整礼貌请求的表达缺口。

本目录是独立本地 Git 项目，没有配置远端，没有公开上传。先看 [实施路线与课程交付节奏](docs/实施路线.md)，再按 [六人接手说明](docs/six-person-handoff.md) 分配每人的 agent。

## 在当前电脑打开

双击 `run_demo.command`，或在本目录执行：

```bash
.venv/bin/python -m sign_robot.server --port 5412
```

浏览器打开 <http://127.0.0.1:5412>。如果端口已被本项目占用，直接打开页面，不需要再启动一份服务。按 `Ctrl+C` 停止你启动的服务。

推荐演示顺序：

1. 输入 `Thank you.`，固定匹配会选中 THANK_YOU，默认不播放未评审动作。
2. 勾选“允许研究预览”后再次提交，查看真实 MuJoCo 渲染的候选轨迹。
3. 选择“语义匹配”，输入 `Many thanks`，检查改写到同一表达的选择。
4. 输入 `I do not want to wait.` 或 `Please wait and take two pills.`，检查拒绝且不播放。
5. 打开“验收与边界”查看当前结果，再用“六人协作”明确后续负责人。

网页播放的是提前由真实 MuJoCo 逐帧渲染的 MP4，现场执行的是文字选择和播放器调用。它不是浏览器内实时物理仿真。若要旋转视角、在原生 MuJoCo 中查看轨迹，请运行：

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
| 大模型 | 本地 loopback 服务适配，严格检查返回 ID 与状态；现有 0.5B 级 Q8 模型已实际测试 | 开发正例只选对 2/3，未通过默认启用门槛；保留研究负结果，不自动调用远程 API |
| 评估 | 18 条开发样例、60 条冻结探索性测试，原始记录及失败逐条保存 | 样例由 agent 起草，尚未经人工标签复核；只评候选 ID 选择 |
| 临床与语言 | 无已验证结论 | 不证明治疗效果、安全部署、替代翻译员或任意句子翻译 |

首轮冻结文本测试中，固定匹配为 38/60，MiniLM 加相同规则为 47/60；支持输入选对分别为 8/30、17/30，错误拒绝分别为 22/30、13/30，库外错误执行均为 0/30。分母很小且标签尚未人审，不能将这个零写成普遍零风险。初次报告保存在 `results/evaluation/test-20261008T135255840626Z/`；后续独立运行另建目录并保留前次记录。

追加真实本地 LLM 研究对照保存在 `results/evaluation/test-20261008T142047221403Z/`，三方法总计 180 条原始记录，所有失败均保留。固定匹配和 MiniLM 分数未变。LLM 加公共规则为 48/60，但支持输入中选错 1 条、返回非法标签 2 条，库外错误选择动作 2/30；不能只按总分将其称为更好的方案。60 题中只有 35 题实际请求 LLM，另 25 题由公共规则处理；标签未经人工复核。前一次因受限沙箱无法访问本机端口的 `not_run` 记录也保留，随后仅修复了运行权限，未更改配置、题目或提示。

最终完整软件与轨迹测试 **143 项通过**，资源/数据哈希 **75 项通过**。实际浏览器演示已检查默认阻断、显式预览、真实语义匹配和混合意图拒绝；`results/acceptance.json` 保存详细范围。

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
.venv/bin/python scripts/build_motions.py
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

测试分别检查非法 ID 和 JSON、失败不执行、候选预览门槛、真实 HTTP 路由、视频 Range、轨迹形状、关节限位、耦合、速度和上游已有碰撞几何。已有碰撞几何的检查通过，不等于完整自碰撞安全证明。最终汇总见 `results/acceptance.json`。

## 来源与使用范围

机器人来自 [Unitree 官方模型](https://github.com/unitreerobotics/unitree_ros/tree/master/robots/g1_description)，上游提交与逐文件哈希见 `assets/robot/upstream_manifest.json`。导入时修复了上游 meshdir 与 filename 的重复路径，原始 vendor 文件保持不变。

手语参考来自 [ASL University / Lifeprint](https://www.lifeprint.com/)，具体页面及观察见 [来源审查](docs/source-review.md) 和 [视频校准记录](docs/video-calibration.md)。THANK_YOU 的起手、前下移动与终掌向上有逐时对照；WAIT 仍只是词例。这里只保存链接和自行编写的观察，没有打包原图片、视频或课程材料。机器人候选轨迹是本项目工程近似，不代表来源作者或 ASL 使用者认可。

语义模型来自 [Sentence Transformers MiniLM](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)，固定提交和哈希见 `config/embedding_download_manifest.json`。

当前是课程研究原型。公开发布前需要另行检查第三方模型、代码、媒体的许可及课程要求；本次没有替团队申请数据、联系评审或发布网站。
