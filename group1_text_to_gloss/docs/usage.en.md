# Usage

[中文](usage.md) · **English**

## 1. Start

On first use, open the module in PowerShell and create the local configuration file:

```powershell
cd D:\me5412_project
Copy-Item .env.example .env
```

Edit the new `.env` on your own machine and fill in `GEMINI_API_KEY`. Do not edit or fill in `.env.example`, and never post a real key in chat or commit it to Git. The program loads `.env` automatically from then on. If a system environment variable with the same name is set, it takes precedence.

## 2. Enter English

Translate one sentence:

```powershell
.\.venv\Scripts\python.exe scripts\translate.py "Where does it hurt?"
```

Interactive input:

```powershell
.\.venv\Scripts\python.exe scripts\translate.py
```

Type `exit` or `quit` to leave.

## 3. Read the JSON

Direct mode returns the full dictionary:

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

`latency_ms` differs on every run; the above only shows the format.

## 4. Get the gloss array

```python
from src.sign_robot.gloss import text_to_gloss

result = text_to_gloss("Where does it hurt?")
if result["status"] == "ok":
    glosses = result["glosses"]
    print(glosses)
```

## 5. When to hand over to Group 2

Only when `status=ok` may the ordered `glosses` be passed to the motion module. Group 2 looks up motions strictly in list order.

In normal mode, `ok` only guarantees that the words belong to the 35-gloss vocabulary, not that Group 2 has prepared their motions.

## 6. Unsupported

`status=unsupported` means the input contains important information the vocabulary cannot express. Check `unknown` and tell the user it cannot be expressed; no robot motion may be executed.

## 7. Error

`status=error` means an API, network, JSON or validation error. `reason`, `error_category`, `http_status` and `validation_detail` are safe to show; never show or log the API key. An error status forbids robot motion.

## 8. Demo-only

To guarantee that output contains only glosses with `motion_ready=true`:

```powershell
.\.venv\Scripts\python.exe scripts\translate.py --demo-only
```

From Python:

```python
result = text_to_gloss("Hello", demo_only=True)
```

Group 2 should still confirm that `motion_ready` is accurate before use (as of 2026-10-31, all 35 are ready).

## 9. Minimal Python example

```python
from src.sign_robot.gloss import text_to_gloss

result = text_to_gloss("Do you need an interpreter?", demo_only=False)
if result["status"] == "ok":
    send_to_motion_module(result["glosses"])
elif result["status"] == "unsupported":
    print("Cannot express:", result["unknown"])
else:
    print("Conversion failed:", result.get("reason"))
```

`send_to_motion_module` only stands for the interface Group 2 provides; this module does not implement it.

## 10. Command-line example

```powershell
.\.venv\Scripts\python.exe scripts\translate.py "Do you need an interpreter?"
```

Only when `status` in the returned JSON is `ok` may the motions for `glosses` be executed.
