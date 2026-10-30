# 使用说明

## 1. 启动

首次使用时，在 PowerShell 中进入项目并创建本地配置文件：

```powershell
cd D:\me5412_project
Copy-Item .env.example .env
```

在本机编辑新建的 `.env`，填写 `GEMINI_API_KEY`。不要修改或填写 `.env.example`，也不要把真实 Key 发到聊天或提交到 Git。以后程序会自动加载 `.env`，无需每次重新输入。若系统环境变量中已经设置了同名配置，系统环境变量优先。

## 2. 输入英文

直接翻译一句：

```powershell
.\.venv\Scripts\python.exe scripts\translate.py "Where does it hurt?"
```

交互输入：

```powershell
.\.venv\Scripts\python.exe scripts\translate.py
```

使用 `exit` 或 `quit` 退出。

## 3. 读取 JSON

直接模式返回完整字典：

```json
{
  "status": "ok",
  "glosses": ["YOU", "HURT", "WHERE"],
  "question": true,
  "dropped": ["does", "it"],
  "unknown": [],
  "latency_ms": 1234.5
}
```

`latency_ms` 每次不同，上面只是格式示例。

## 4. 取得 Gloss 数组

```python
from src.sign_robot.gloss import text_to_gloss

result = text_to_gloss("Where does it hurt?")
if result["status"] == "ok":
    glosses = result["glosses"]
    print(glosses)
```

## 5. 交给第二组的条件

只有 `status=ok` 时，才允许把有序 `glosses` 交给动作模块。第二组应严格按列表顺序查找动作。

普通模式的 `ok` 只保证词汇属于35词库，不保证第二组已经准备好动作。

## 6. Unsupported

`status=unsupported` 表示输入包含词库无法表达的重要信息。查看 `unknown`，向用户提示无法表达；禁止执行任何机器人动作。

## 7. Error

`status=error` 表示 API、网络、JSON 或校验错误。可以安全显示 `reason`、`error_category`、`http_status` 和 `validation_detail`；不要显示或记录 API Key。错误状态禁止执行机器人动作。

## 8. Demo-only

要保证输出只包含 `motion_ready=true` 的 Gloss：

```powershell
.\.venv\Scripts\python.exe scripts\translate.py --demo-only
```

Python 调用：

```python
result = text_to_gloss("Hello", demo_only=True)
```

使用前仍应由第二组确认 `motion_ready` 状态准确。

## 9. 最小 Python 示例

```python
from src.sign_robot.gloss import text_to_gloss

result = text_to_gloss("Do you need an interpreter?", demo_only=False)
if result["status"] == "ok":
    send_to_motion_module(result["glosses"])
elif result["status"] == "unsupported":
    print("无法表达：", result["unknown"])
else:
    print("转换失败：", result.get("reason"))
```

`send_to_motion_module` 仅表示第二组提供的接口，本项目没有实现该函数。

## 10. 命令行示例

```powershell
.\.venv\Scripts\python.exe scripts\translate.py "Do you need an interpreter?"
```

只有返回 JSON 中的 `status` 为 `ok` 时，才可以执行 `glosses` 对应动作。
