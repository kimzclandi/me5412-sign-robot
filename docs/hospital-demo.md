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
| 另外按 PPT 第 13–16 页生成 4 幕视频 | `MUJOCO_GL=egl .venv/bin/python scripts/demo/hospital_demo.py --acts` |
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
- 第 13–16 页的 4 幕视频（只有机器人，带英文原句和逐词 gloss 字幕）：`act1_registration.mp4`（第 1–2 句，约 23 秒）、`act2_consultation.mp4`（第 3–5 句，约 33 秒）、`act3_treatment.mp4`（第 6–7 句，约 22 秒）、`act4_discharge.mp4`（第 8–9 句，约 13 秒）。PPT 讲稿提到的右侧真人词典视频属于各网站，不入库，需要时在本地另行拼接并注明来源。

## 5. 与第三组的衔接

拼接现在是最简单的基线：每个词裁到 `sign_frames`，词间固定 0.5 秒平滑过渡，词与词之间手臂会短暂下沉。第三组完成衔接方法后，替换 `hospital_demo.py` 里的 `stitch(...)` 调用即可，其余流程不变；基线保留作为“直接回放对照”。

**第三组交付格式**（与仓库所有轨迹一致，对上后接入约半小时）：

- 每句一个 `.npz`，按句子编号命名 `s1.npz` … `s9.npz`；或者交一个与 `stitch(glosses, transition_s, spans)` 同签名的函数。
- 字段：`timestamps_s[T]`（秒，严格递增，30 fps）、`joint_names[53]`（与 `results/demo/s1.npz` 相同的 53 个关节名）、`positions[T,53]`（弧度）。
- 拇指和手指的耦合关节按 `assets/robot/model_info.json` 的 `couplings` 计算；首尾为同一个中立姿势（肘 0.25、拇指 yaw 0.35、pitch 0.08，其余 0）。

**和基线对比**（第 11 页的数字和图）：

```bash
MUJOCO_GL=egl .venv/bin/python scripts/demo/compare_stitching.py <第三组文件夹> --label group3_v1
```

输出 `results/stitch_compare/group3_v1/`：`summary.md`、`summary.json` 和每句的对比图（手腕高度、手臂最大关节速度随时间变化）。指标：格式检查（53 个关节、30 fps、关节限位、耦合、首尾中立）、时长、手臂和手指的峰值与 95 分位速度、手臂 RMS jerk（越小越平滑）、打手语过程中手回落到休息高度的时间比例和次数（基线的“下沉”）、碰撞体最大穿模深度。单个手语自身的下落也会计入“回落”，因此比较两种方法的相对变化，不看绝对值。

基线现状（9 句）：词间过渡和回到中立姿势的过程都没有做碰撞检查，穿模最大 79 mm（s1 结尾右手腕与胯部）；打手语阶段最大 41 mm，来自视频词（视频词的滤波和限速在逆运动学之后进行，可能重新引入少量重叠）。这两项都是衔接方法可以改进的地方。

## 6. 限制

- 机器人动作是候选手语动作，未经 ASL 使用者评审；26 个视频词评为“近似”。
- 离线缓存只覆盖 9 句脚本对话；其他句子需要 `--live`。缓存是在线结果的保存，不是独立测试。
- 运动学回放（固定底座，不含动力学），不代表真实机器人可以以同样速度执行。
- 只在 Linux（Ubuntu，Python 3.12）上实际从全新下载跑通；macOS 和 Windows 未实测。
