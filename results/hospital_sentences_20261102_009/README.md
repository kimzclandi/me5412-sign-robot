# 九个医院句子，第九轮：YOU HURT WHERE 单独优化，HURT 从第 37 帧开始（2026-11-02）

**中文** · [English](README.en.md)

仅为开发证据：正式 PASS_SIM 为 0，`formal_acceptance_enabled=false`，不是已验证的 ASL，未经人工评审。
之前：第八轮 [`../hospital_sentences_20261102_008/README.md`](../hospital_sentences_20261102_008/README.md)。本轮只重做
YOU HURT WHERE，其余六句仍以第八轮为准。

用户要求（对话，2026-11-02）：HURT 这个词从第 37 帧开始，对 YOU HURT WHERE 这个句子单独再优化。代码 `dfe4bac`（规划与验证代码
与第八轮的 `1d07d2d` 相同，两者之间只改了 `project_overview.py` 中的两个文档哈希）；输入 `make_inputs.py`；运行 `run.sh`，
2 个词对 run 用 cpu0–1，14:21–15:03。

## 原因

- HURT 的保护区间 v1/v2 为 [27, 57]（0.9–1.9 s）。重定向后的 HURT 在第 29–34 帧左臂翻转：左肩 yaw 以 15 rad/s 的上限甩出又
  甩回（左肩 pitch、左腕 pitch 约 12–14 rad/s），左臂先伸向身体外侧，再回到胸前。整句手臂速度的峰值 28.2 rad/s 就在这里。
- 第八轮的 YOU→HURT 正好在第 27 帧进入 HURT，所以这段翻转被当作 HURT 的一部分播放了出来。

## 改动（不改代码）

- **保护表 v3**（`config/user_protected_hospital35_v3.json`）：只改 HURT 一条，[27, 57] → **[37, 57]**（1.24–1.9 s，
  floor(1.24×30) = 37），记录中写明了改动来源；v2 保留给之前的 run。
- **词对策略** `config/transition_policy_hospital_sentences_fast_v6.json`：即第八轮的 `fast_v5` 换用保护表 v3。这一轮只规划这句
  的两个词对、各占一个核，所以每对的搜索时间 720 → 1800 s（RRT 240 → 600 s）：第八轮这两对都是因墙钟上限
  （`PAIR_WALL_TIME_LIMIT`）停下的，还没有试完所有路线。平滑定时、门槛和选优规则都不变。
- **序列策略** `config/sequence_policy_hospital_sentences_v8.json`：只含 YOU HURT WHERE。

## 结果：NUMERICAL_PASS，HURT 从第 37 帧开始

- 2/2 个选中衔接、1/1 个句子全新复核一致；3/3 个保护核心逐位不变；结尾回到初始姿态。
- **YOU→HURT 正好在 HURT 第 37 帧进入**（`ik_via1`，11 帧，没有保留第 37 帧之前的任何源动作）。YOU 结束后右手收回、左臂从
  身侧抬起，两手到胸前时正好接上 HURT 第 37 帧；第八轮那段向外甩的左臂不再出现。
- 整句 120 → **109 帧**（3.97 → 3.60 s）；整句手臂速度峰值 28.2 → 22.6 rad/s；YOU→HURT 衔接的手臂平均速度 11.8 → 9.9 rad/s、
  峰值 21.0 → 16.4 rad/s；最小间隙 2.95 → 7.81 mm。整句（含保护核心）的加加速度积分 3.59e7 → 2.07e7 rad²/s⁵（只作参考）。
- HURT→WHERE：搜索加长后（131 次尝试）选中的仍是第八轮那条 11 帧衔接（同一切点、同一方法，指标完全相同）。收尾段也与
  第八轮相同（WHERE 第 81 帧出发，直接路线，9 帧）。

| 词对 | 轮 | 尝试 | 通过 | 选中 | 方法 | 切点 | 衔接帧 | 停顿 | 两核心间帧数 | 峰值加加速度 | 峰值加速度 | 加加速度积分 | 最小间隙 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| YOU→HURT | 8 | 40 | 15 | attempt_00015 | ik_via1 | 72→27 | 12 | 0 | 12 | 1103 | 90 | 3.19e6 | 2.95 mm |
| YOU→HURT | **9** | 113 | 86 | attempt_00068 | ik_via1 | **72→37** | 11 | 0 | 11 | 1136 | 75 | 4.24e6 | 9.50 mm |
| HURT→WHERE | 8 | 66 | 43 | attempt_00028 | ik_via1 | 57→51 | 11 | 0 | 11 | 1679 | 91 | 4.77e6 | 8.87 mm |
| HURT→WHERE | **9** | 131 | 96 | attempt_00067 | ik_via1 | 57→51 | 11 | 0 | 11 | 1679 | 91 | 4.77e6 | 8.87 mm |

"通过"为通过独立数值检查的候选数。峰值加加速度（rad/s³）和峰值加速度（rad/s²）取衔接段内的有限差分，加加速度积分
（rad²/s⁵）取解析衔接，与第八轮 README 的口径相同；门槛分别为 5000、200、5e6。最小间隙为词对复核的值；整句复核的最小间隙
见上文。

## 视频与图

- `videos_gpu/YOU__HURT__WHERE/`：`comparison.mp4`（按用户决定不入库）、`report.json`、`contact_sheet.png`。视频在本机
  `C:\Users\23971\Documents\5412\_runtime\render-out\round9_150418\YOU__HURT__WHERE\comparison.mp4`。
- `round8_vs_round9_hurt_entry.png`：从 YOU 的保护核心结束到 HURT 第 45 帧，每 2 帧一格，正面与侧面；上两行为第八轮，下两行
  为第九轮。
- `arm_speed_round8_vs_round9.png`：整句手臂速度（肩、肘、腕关节速度的范数），上为第八轮，下为第九轮；底色绿为用户保护，黄为
  新增衔接。
- `compare_round8_vs_round9.py`：生成这两张图的脚本（Windows render-venv，GPU）。
- 仍在 Intel Arc B390 核显上渲染（127 s），脚本和输出格式与第八轮相同。未经人工观看。

## 限制

- HURT 新的保护区间 [37, 57] 内仍有源动作的快速段：左腕 pitch 与左肩 yaw 在第 39–41、47–49 帧先后以 11–14 rad/s 来回摆动
  （左腕 pitch 第 39 帧加速度 211 rad/s²、第 48 帧加加速度 5754 rad/s³，都超过衔接门槛），右手拇指在第 49 帧到达手指速度
  上限 10 rad/s。它们在用户保护之内，按规则只记录（`protected_source_audit`），不改；整句 22.6 rad/s 的手臂速度峰值就在这里。
  如果这些也不自然，需要再缩短保护区间，或请第二组修订 HURT 的源动作。
- 其余六句没有重跑，仍是第八轮的结果（保护表 v2）；它们用到的词在 v3 中的记录与 v2 完全相同。
- 本轮的搜索时间比第八轮长，两轮的候选数量不能直接比较；墙钟预算使候选池受机器负载影响。
- 采样碰撞检查不是连续碰撞证明；本目录提交后，这些 run 不能在新 HEAD 上续跑或复核。

## 复现

```bash
.venv/bin/python results/hospital_sentences_20261102_009/make_inputs.py          # 只在文件不存在时写入
bash results/hospital_sentences_20261102_009/run.sh
.venv/bin/python results/hospital_sentences_20261102_009/export_render_inputs.py
```

渲染（Windows）：用 `C:\Users\23971\Documents\5412\_runtime\render-venv` 中的 Python 运行 `render_gpu_windows.py`，参数
`--repo //wsl.localhost/Ubuntu/home/kingderman/Documents/ME5412-github-latest`、
`--model-copy C:/Users/23971/Documents/5412/_runtime/render-assets/robot`、`--output <输出目录>`、`--case YOU__HURT__WHERE`。
