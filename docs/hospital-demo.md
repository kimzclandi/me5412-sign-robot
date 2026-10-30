# 医院场景端到端演示

**中文** · [English](hospital-demo.en.md) · [第二组交接](group2-handoff.md)

一条命令走完整条流程：护士或医生的英文句子 →【第一组】ASL gloss →【第二组】每个词的 G1 关节轨迹 → 拼成整句 → MuJoCo 播放或带字幕的视频。默认读取第一组 9 句脚本对话的离线结果，**现场不需要联网，也不需要 API key**。

```
英文句子 → gloss（离线缓存，或 --live 调第一组 Gemini）→ motions/hospital_v1_motions.json 查动作
        → 基线拼接（scripts/mocap/stitch_baseline.py，第三组的衔接方法替换这一步）→ 播放 / 视频
```

## 1. 下载后准备（一次）

只需 Python 3.12，演示用的精简依赖不含 torch 和 MiniLM，几分钟装完：

```bash
git clone https://github.com/kimzclandi/me5412-sign-robot && cd me5412-sign-robot
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-demo.txt
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python scripts/fetch_robot.py      # 下载 Unitree G1 + Inspire 手的官方模型（约 27 MB，固定提交并核对哈希）
.venv/bin/python scripts/prepare_robot.py
.venv/bin/python -m pytest -q tests/test_hospital_demo.py tests/test_retarget.py
```

Windows 把 `.venv/bin/python` 换成 `.venv\Scripts\python`。完整原型（网页、MiniLM、学习模型）的环境见仓库 [README](../README.md)。

## 2. 演示命令

| 用途 | 命令 |
|---|---|
| 交互 3D 窗口播放一句（可拖动视角） | `.venv/bin/python scripts/demo/hospital_demo.py --line s4 --view`（macOS 用 `.venv/bin/mjpython`） |
| 用原句选择 | `.venv/bin/python scripts/demo/hospital_demo.py "Where does it hurt?" --view` |
| 生成带字幕的视频 | `MUJOCO_GL=egl .venv/bin/python scripts/demo/hospital_demo.py --line s4 --render`（macOS／Windows 去掉 `MUJOCO_GL=egl`） |
| 9 句全部生成，并拼成完整对话视频 | `MUJOCO_GL=egl .venv/bin/python scripts/demo/hospital_demo.py --all --render` |
| 现场输入任意句子（调用第一组在线模型） | `.venv/bin/python scripts/demo/hospital_demo.py "Where is the pain?" --live --view` |

9 句脚本对话（s1–s9）见 `group1_text_to_gloss/data/offline/hospital_dialogue_gloss.json`，例如 s4 `Where does it hurt?` → `YOU HURT WHERE`。视频顶部是英文原句，底部 gloss 逐词高亮，并标明 gloss 来源、拼接方法和“未经 ASL 评审”。

## 3. 在线模式与失败处理

`--live` 在子进程里运行 `group1_text_to_gloss/scripts/translate.py --demo-only`，只允许有动作的词。需要联网和 `group1_text_to_gloss/.env` 里的 `GEMINI_API_KEY`（复制 `.env.example` 后各自填写，**不要上传或发到群里**）。

| 情况 | 行为 |
|---|---|
| 模型返回 gloss | 正常播放，来源标 `live_gemini` |
| 句子超出词表（如 `Please show me your insurance card.`） | 显示拒绝原因，**不播放任何动作** |
| 网络或 API 失败，句子在 9 句缓存里 | 改用离线结果，来源标 `offline_cache_after_live_failure` |
| 网络或 API 失败，句子不在缓存里 | 报错，不播放 |
| 不加 `--live` 且句子不在缓存里 | 报错并列出可用的 s1–s9 |

2026-10-31 实测：9 句在线全部正确，多数 1–2 秒，一次请求重试后约 46 秒。因此现场建议默认用离线缓存，`--live` 只作为加演。

## 4. 输出

- `results/demo/<名称>.npz`：整句轨迹，与仓库动作同一格式（`timestamps_s`、`joint_names`、`positions`，弧度，30 fps）。
- `results/demo/<名称>.json`：原句、gloss、来源、每个词的帧范围和来源库（动作捕捉或视频）。
- `results/demo/<名称>.mp4`、`results/demo/hospital_dialogue.mp4`（9 句连播，约 91 秒）：已入库，可直接放进 PPT 或在断网、电脑出问题时作为备份播放。

## 5. 与第三组的衔接

拼接现在是最简单的基线：每个词裁到 `sign_frames`，词间固定 0.5 秒平滑过渡，词与词之间手臂会短暂下沉。第三组完成衔接方法后，替换 `hospital_demo.py` 里的 `stitch(...)` 调用即可，其余流程不变；基线保留作为“直接回放对照”。

## 6. 限制

- 机器人动作是候选手语动作，未经 ASL 使用者评审；26 个视频词评为“近似”。
- 离线缓存只覆盖 9 句脚本对话；其他句子需要 `--live`。缓存是在线结果的保存，不是独立测试。
- 运动学回放（固定底座，不含动力学），不代表真实机器人可以以同样速度执行。
- 只在 Linux（Ubuntu，Python 3.12）上实际从全新下载跑通；macOS 和 Windows 未实测。
