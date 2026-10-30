# ME5412 — English to ASL Gloss Conversion

## 项目简介

本项目把医院场景中的英文句子转换为固定词库内的美国手语（ASL）gloss 有序序列。例如，`Where does it hurt?` 可以转换为 `YOU HURT WHERE`。

第一组仅负责“英文文本 → gloss”。本项目不下载手语动作，不生成机器人轨迹，也不负责 MuJoCo 或其他机器人仿真。

## 目录结构

```text
data/vocab/hospital_v1.json       35 个固定 gloss 及英文同义词
data/gloss_eval/gloss_test.csv    20 条评估句
src/sign_robot/llm.py             Gemini OpenAI 兼容接口客户端
src/sign_robot/gloss.py           text_to_gloss() 转换与严格校验
scripts/translate.py              单句和交互式翻译入口
scripts/check_gloss.py            可恢复、有限额的自动评估脚本
docs/usage.md                     面向组员的简明使用说明
docs/integration.md               第二组安全调用与状态处理约定
results/gloss_check/              测试结果
tests/test_offline.py             不访问 Gemini 的离线回归测试
```

## 环境要求

- Windows 10/11
- Python 3.12（项目验证版本为 3.12.7）
- 可访问 Google Gemini API 的网络
- Google AI Studio API Key

## 安装

在 PowerShell 中执行：

```powershell
cd D:\me5412_project
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

如果 PowerShell 阻止激活脚本，也可以不激活，直接使用 `.\.venv\Scripts\python.exe`。

## API 配置

首次使用时，在项目根目录复制配置模板：

```powershell
Copy-Item .env.example .env
```

然后只在本机用文本编辑器打开 `.env`，把 `GEMINI_API_KEY=` 后面填写为自己的 Google AI Studio API Key。不要在聊天、源码、README 或 Git 中提供真实密钥。

程序启动时会自动读取项目根目录的 `.env`。`.env` 已被 `.gitignore` 排除，`.env.example` 可以安全提交。已经存在的系统环境变量优先，不会被 `.env` 覆盖。`GEMINI_MODEL` 和 `GEMINI_BASE_URL` 可省略，默认分别为 `gemini-3.1-flash-lite` 和 `https://generativelanguage.googleapis.com/v1beta/openai/`。

## 当前运行架构

原始实施指南描述的是 Mac 本地模型方案；当前交付版本已经改为通过 OpenAI 兼容接口调用在线 Google Gemini。运行时需要网络和有效的 Google AI Studio API Key，不应再把本版本描述为离线大模型部署。

## 输入英文

直接输入一句英文，输出完整 JSON：

```powershell
python scripts/translate.py "Where does it hurt?"
```

交互模式：

```powershell
python scripts/translate.py
```

输入 `exit` 或 `quit` 退出。只允许使用动作已准备 Gloss 时：

```powershell
python scripts/translate.py --demo-only
```

## 输出字段

- `status`：`ok`、`unsupported` 或 `error`。
- `glosses`：有序 Gloss 列表；只有 `status=ok` 时可以交给动作模块。
- `question`：输入是否为问句。
- `dropped`：转换时没有手语化的英文虚词或片段。
- `unknown`：词库无法表达的重要信息。
- `latency_ms`：本次转换耗时。
- `reason`、`error_category`、`http_status`、`validation_detail`：安全错误诊断字段。

`unsupported` 表示重要内容超出词库；`error` 表示 API、JSON 或校验失败。这两种状态都禁止执行机器人动作。

## 运行20条测试

默认 dry-run，绝不调用 Gemini：

```powershell
python scripts/check_gloss.py
```

受限真实测试：

```powershell
python scripts/check_gloss.py --live --max-requests 3 --delay 5
```

只测试指定 ID：

```powershell
python scripts/check_gloss.py --live --ids s1 s2 p1 --max-requests 9
```

从同模型、同测试数据、同 ID 选择的 live 报告恢复：

```powershell
python scripts/check_gloss.py --live --ids s1 s2 p1 --resume "results\gloss_check\之前的报告.json" --max-requests 9
```

所有请求（包括重试）均计入 `--max-requests`。报告保存在 `results/gloss_check/`，不会覆盖旧报告。

离线回归测试不会请求 Gemini：

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

## 与第二组对接

第二组读取返回字典中的 `glosses` 列表，并按顺序查找同名动作。只有 `status=ok` 时才允许对接动作模块：

```python
result = text_to_gloss(sentence)
if result["status"] == "ok":
    ordered_motion_names = result["glosses"]
```

普通模式的 `ok` 只保证 Gloss 属于35词库，不保证对应动作已经就绪。需要保证动作可用时使用 `demo_only=True`，并由第二组确认词库中的 `motion_ready` 状态。

完整的状态处理和动作组调用约定见 `docs/integration.md`。

## 35词库限制

模型可执行输出严格限制在 `hospital_v1.json` 的35个 Gloss 内。保险、精确时间、X-ray、过敏信息等重要内容无法完整表达时，程序应返回 `unsupported`，不会猜测或输出部分动作。

## 常见错误

- `401`：API Key 无效；重新检查 `GEMINI_API_KEY`。
- `403`：项目、区域或 API 权限不足；检查 Google AI Studio 项目权限。
- `404`：模型对当前项目不可见，或模型名/兼容端点不匹配。
- `429`：达到速率或配额限制；遵守 Retry-After，稍后再运行。
- `503`：Gemini 服务暂时不可用；测试脚本会在额度内有限重试。
- `timeout`：网络或服务响应超时；可使用测试报告断点续测。

程序不会自动切换模型，也不会无限重试。

## 当前测试结果

最终完整真实测试报告：`results/gloss_check/20261027T011211_866109+0800.json`。

- 20/20 通过
- API 请求26次，其中重试6次
- 最终 API 失败0次

100%只代表这20条固定测试句在该次运行中全部通过，不代表所有英文输入都能正确转换。

## 已知限制

- 使用在线 Gemini API，必须联网。
- 只支持35个预定义 Gloss。
- 当前参考词序和临时项目约定尚未经过专业 ASL 人员审核。
- Gemini 输出可能随服务状态和模型行为波动。
- 不保证所有新英文句子都能正确转换。
