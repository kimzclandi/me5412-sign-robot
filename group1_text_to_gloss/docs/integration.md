# 第二组调用约定

**中文** · [English](integration.en.md)

## 稳定入口

从项目根目录运行 Python，并把 `src` 加入模块搜索路径后导入：

```python
from sign_robot import text_to_gloss

result = text_to_gloss(sentence, demo_only=True)
```

也可以通过 `scripts/translate.py` 调用。不要复制 Prompt 或重新实现校验逻辑。

在主仓库中，本模块的包同样叫 `sign_robot`，因此 `scripts/demo/hospital_demo.py` 以子进程运行 `scripts/translate.py --demo-only`，不在同一进程中导入。

## 输入

- `sentence`：非空英文字符串，最长 200 个字符。
- `demo_only=True`：只允许当前词库中 `motion_ready=true` 的 Gloss。机器人演示建议使用该模式。
- `demo_only=False`：允许全部35个 Gloss，适合语言模块开发；并不代表所有动作已经准备好。

## 返回状态

### `status=ok`

只有该状态允许消费 `glosses`。动作模块必须严格保持列表顺序，并在执行前再次确认每个动作文件存在。

### `status=unsupported`

输入包含35词库无法表达的重要含义。`glosses` 必须为空；不得播放部分动作。

### `status=error`

发生 API、网络、JSON 或校验错误。不得播放动作，也不得把上一次成功结果当作本次结果。

## 最小安全调用

```python
from sign_robot import text_to_gloss

result = text_to_gloss(user_sentence, demo_only=True)
if result["status"] == "ok":
    ordered_glosses = result["glosses"]
    # 逐个检查动作存在后，再交给轨迹衔接模块。
elif result["status"] == "unsupported":
    show_message("当前词库无法完整表达该句子")
else:
    show_message("转换服务暂时不可用")
```

`show_message` 和动作模块接口由调用方实现。

## 可复现性

固定代码、词库、Prompt、模型 ID 和环境配置可以保持接口与校验行为一致，但在线生成式模型不保证每次返回完全相同的 Gloss。调用方必须按状态处理每一次独立结果，不能依赖历史输出。

端到端演示在失败时回退到离线缓存，只适用于已缓存的 9 句脚本对话，并标注 `offline_cache_after_live_failure`，不会复用任意的历史结果。

## 动作词库责任

`motion_ready` 表示第二组确认的动作准备状态。第二组完成或撤销动作后，应与第一组共同核对该字段。不要仅因为 Gloss 属于35词库就假定机器人一定拥有对应动作。
