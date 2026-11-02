# TASK-28：九个医院句子（仅衔接段），第 1–8 轮

> **公开交付更新（2026-11-02）：** 用户现已明确要求更新 GitHub。本次以公开提交 `86428693` 为基线同步第八轮非原始快照，排除原始运行存储。下文“先不推”及旧远端位置是当时的历史记录，已由本次发布替代；见根目录 README。

[English](TASK-28.en.md) · [当前状态](STATE.md) · [交接](HANDOFF.md) · [上一阶段 TASK-27](TASK-27.md)

状态：**第八轮完成，等待人工观看视频。** 执行时间 2026-11-01 13:54 至 2026-11-02 03:48（Asia/Shanghai）。本文件是这一阶段的总记录，在第八轮提交之后根据各轮 README、提交记录和本机文件整理，没有重新运行；每轮的细节与数字以各轮目录中的 README 为准。

**2026-11-01 用户把范围从全库 1,225 个词对缩小到九个医院句子，并规定第三组只负责两个词之间的衔接。经过八轮，七个多词句子全部数值通过（NUMERICAL_PASS），每句结尾回到双手垂下的初始姿态，衔接中途不再停顿；17 个衔接两核心间的总帧数从第二轮的 1,717 降到 310。另外两个"句子"是单词，直接播放源动作。24/24 个保护核心逐位不变，全套测试 1014 passed。第二轮之后的提交只在本地，没有推送。**

仅为开发证据：正式 PASS_SIM 为 0，`formal_acceptance_enabled=false`，不是已验证的 ASL；视频未经人工观看，未上实机。

## 范围

| 句子 | 词对衔接 |
|---|---|
| HELLO YOU APPOINTMENT HAVE | HELLO→YOU、YOU→APPOINTMENT、APPOINTMENT→HAVE |
| YOU NEED INTERPRETER | YOU→NEED、NEED→INTERPRETER |
| PLEASE WAIT DOCTOR COME SOON | PLEASE→WAIT、WAIT→DOCTOR、DOCTOR→COME、COME→SOON |
| YOU HURT WHERE | YOU→HURT、HURT→WHERE |
| NOW NURSE BLOOD-DRAW | NOW→NURSE、NURSE→BLOOD-DRAW |
| MEDICINE MORNING NIGHT TAKE | MEDICINE→MORNING、MORNING→NIGHT、NIGHT→TAKE |
| YOU UNDERSTAND | YOU→UNDERSTAND |
| BREATHE-DEEP；THANK-YOU | 单词，没有衔接，完整播放源动作 |

共 17 个词对、7 个多词句子；24 个词出现各有一个受保护核心（21 个不同的词）。从第一轮起，复核只对新增的衔接设门槛（`CONNECTOR_ONLY_METHOD_V4`）；源动作本身的碰撞、超速等问题写入 `source_side_findings`，归第二组，只记录、不判失败。

## 用户决定（按时间）

| 时间 | 用户决定 | 落实 |
|---|---|---|
| 11-01，第一轮前 | 只做九个句子，不再扫描全部 1,225 个词对 | hospital35 的 P1-3 停在 46/79 批（见第一轮 README）；[TASK-27](TASK-27.md) 中的 P1-4、预算重试和更快的扫描器没有运行 |
| 11-01，第一轮前 | 第三组只负责衔接，源动作缺陷属于第二组 | 复核范围 v4 |
| 11-01 | 新视频不入库 | `.gitignore`；mp4 只留在本机 |
| 11-01，第二轮后 | 句子结束后回到双手垂下的初始姿态；衔接段明显比手势慢，要提速 | 第三、四轮 |
| 11-01，第四轮后 | NOW NURSE BLOOD-DRAW 中左手异常扭曲（NURSE 第 81 帧） | 第五、六轮 |
| 11-02，第六轮后 | 上传到团队仓库的 group3 分支 | 准备了发布副本，推送中途停止，远端没有变化；随后用户决定"先不推" |
| 11-02，第六轮后 | MORNING 的保护截到第 38 帧；NURSE 的保护截到第 75 帧，之后右手先快速移开，再把左腕回正 | 第七轮。从 MORNING 第 38 帧出发接不出衔接（第 37→38 帧手指突然合拢），用户改选第 37 帧 |
| 11-02，第七轮后 | 衔接一顿一顿、仍比手势慢；如果是加速度类硬限制卡住，可以适当放宽 | 第八轮 |

## 各轮

| 轮 | 目录（`results/`） | 运行时间 | 起因 | 主要改动（代码提交） | 词对 / 序列策略 | 结果 |
|---|---|---|---|---|---|---|
| 1 | [`hospital_sentences_20261101_001`](results/hospital_sentences_20261101_001/README.md) | 11-01 13:54–14:28 | 范围改为九句、只做衔接 | 复核范围 v4（`5c536fb`） | `connector_only_v1` / `v1` | 3/7；5 个词对没有候选（切点处源动作的手指仍快速冲向限位） |
| 2 | [`…_002`](results/hospital_sentences_20261101_002/README.md) | 11-01 15:54–16:22 | 第一轮 5 对无候选 | 边界刹车、两端都能刹住的切点组合（`d1bd7dc`） | `braking_v1` / `v2` | 7/7 |
| 3 | [`…_003`](results/hospital_sentences_20261101_003/README.md) | 11-01 19:56–20:32 | 回到初始姿态、衔接提速 | 按两核心间帧数最少选优；最后一个词后规划收尾段（`0b2528d`） | `fast_v1` / `v3` | 6/7，**已被第四轮取代**（INTERPRETER 收尾段没找到） |
| 4 | [`…_004`](results/hospital_sentences_20261101_004/README.md) | 11-01 20:43–21:18 | 同上 | 收尾段两遍搜索（`843cd45`） | `fast_v1` / `v3` | 7/7，都回到初始姿态；两核心间 1,717 → 570 帧 |
| 5 | [`…_005`](results/hospital_sentences_20261101_005/README.md) | 11-01 22:14–22:48 | NURSE 第 81 帧左臂扭曲 | 保留边缘筛选 v1；被钳在限位上的关节在切点处按停止处理（`27b6304`） | `fast_v2` / `v4` | 5/7，**已被第六轮取代**（筛选过宽，卡住两句） |
| 6 | [`…_006`](results/hospital_sentences_20261101_006/README.md) | 11-01 22:55–23:32 | 同上 | 筛选 v2 只标记肩、肘的近端翻转（`368fc4b`） | `fast_v3` / `v5` | 7/7；NURSE 在第 80 帧离开，不再播放翻转 |
| 7 | [`…_007`](results/hospital_sentences_20261102_007/README.md) | 11-02 01:17–01:51 | 缩短 MORNING/NURSE 保护，NURSE 分步退出 | 保护表 v2、分阶段出口（`129891a`） | `fast_v4` / `v6` | 7/7；NURSE：右臂离开 → 左前臂抬起 → 左腕回正 → BLOOD-DRAW |
| 8 | [`…_008`](results/hospital_sentences_20261102_008/README.md) | 11-02 02:50–03:39 | 衔接一顿一顿、偏慢 | 不停顿的平滑定时、按停顿次数选优、门槛放宽（`1d07d2d`） | `fast_v5` / `v7` | 7/7；衔接内部停顿 16 → 0；两核心间 563 → 310 帧 |

策略文件全名为 `config/transition_policy_hospital_sentences_<名称>.json` 和 `config/sequence_policy_hospital_sentences_<版本>.json`。每轮的结果和原始词对存储分两次提交（例如第八轮 `fc9c7f9` 与 `70a61fa`）。第一轮的 run 用的是未提交的工作树（`2875e49`），代码随后在 `5c536fb` 提交。

## 当前交付：第八轮

- 代码 `1d07d2d`；结果 `fc9c7f9`，原始词对存储 `70a61fa`。
- 词对策略 `config/transition_policy_hospital_sentences_fast_v5.json`；序列策略 `config/sequence_policy_hospital_sentences_v7.json`；保护表 `config/user_protected_hospital35_v2.json`（相对 v1 只改了 NURSE [38,75] 和 MORNING [26,37]，v1 保留给之前的 run）。
- 17/17 个选中衔接、7/7 个句子全新复核一致；24/24 个保护核心逐位不变；每句都回到初始姿态，收尾段 8–12 帧。
- 衔接共 254 帧（第七轮 446），内部停顿 0（第七轮 16）；15 个衔接用最小加加速度样条，2 个用拐角平滑过渡（NURSE→BLOOD-DRAW、WAIT→DOCTOR）。
- 门槛（用户允许放宽，三项都在手势保护区间的上四分位以内）：峰值加速度 200 rad/s²、峰值加加速度 5000 rad/s³、加加速度积分 5e6 rad²/s⁵（原为 120、3000、1e6）。速度上限（手臂 15、手指 10 rad/s）不变。实测：峰值加加速度 819–2058，峰值加速度 ≤ 134，最大加加速度积分 4.89e6。
- 测试：全套 1014 passed（`results/hospital_sentences_20261102_008/tests/pytest_full.log`）。

| 句子 | 第二轮 | 第八轮 |
|---|---|---|
| HELLO YOU APPOINTMENT HAVE | 417 帧（13.9 s） | 235 帧（7.8 s） |
| YOU NEED INTERPRETER | 316 帧（10.5 s） | 168 帧（5.6 s） |
| PLEASE WAIT DOCTOR COME SOON | 765 帧（25.5 s） | 366 帧（12.2 s） |
| YOU HURT WHERE | 291 帧（9.7 s） | 120 帧（4.0 s） |
| NOW NURSE BLOOD-DRAW | 405 帧（13.5 s） | 271 帧（9.0 s） |
| MEDICINE MORNING NIGHT TAKE | 387 帧（12.9 s） | 164 帧（5.5 s） |
| YOU UNDERSTAND | 198 帧（6.6 s） | 97 帧（3.2 s） |

第二轮没有收尾段；第八轮的帧数包含回到初始姿态的收尾段。

### 视频与图

- 视频不入库，只在本机：`C:\Users\23971\Documents\5412\_runtime\render-out\round8_034002\<句子>\comparison.mp4`，共 7 个。画面上方为原始片段，下方为句子；左侧正面，右侧侧面。较早几轮的视频在同一目录下的 `round2_163226`、`round4_211920`、`round6_233300`、`round7_015209`。
- 入库：`results/hospital_sentences_20261102_008/videos_gpu/<句子>/` 中的 `report.json` 和 `contact_sheet.png`；手臂速度对比图 `arm_speed_round7_vs_round8.png`（MEDICINE MORNING NIGHT TAKE、NOW NURSE BLOOD-DRAW 两句）；NURSE 出口逐帧对比 `NOW__NURSE__BLOOD-DRAW/round7_vs_round8_nurse_exit.png`。

## 复现

各轮目录提交之后，其中的 run 不能在新 HEAD 上续跑或复核：冻结身份包含提交号以及 `src/`、`tests/`、`scripts/` 的哈希。新一轮按之前的做法新建目录：复制上一轮的 `make_inputs.py`、`run.sh`、`export_render_inputs.py`、`render_gpu_windows.py`，改目录名、run_id 和策略版本。以第八轮为例，在 WSL 中运行：

```bash
cd /home/kingderman/Documents/ME5412-github-latest
.venv/bin/python results/hospital_sentences_20261102_008/make_inputs.py          # 只在文件不存在时写入
bash results/hospital_sentences_20261102_008/run.sh                               # 16 个词对 run → 选中候选复核 → 收尾段 → 序列复核
.venv/bin/python results/hospital_sentences_20261102_008/export_render_inputs.py  # 导出渲染输入
```

渲染在 Windows 上用 GPU 完成，每次一句。MuJoCo 打不开 `\\wsl.localhost` 路径，所以模型用 `_runtime\render-assets\robot` 中的副本，它必须与仓库中的 `assets/robot` 逐文件一致：

```powershell
C:\Users\23971\Documents\5412\_runtime\render-venv\Scripts\python.exe \\wsl.localhost\Ubuntu\home\kingderman\Documents\ME5412-github-latest\results\hospital_sentences_20261102_008\render_gpu_windows.py --repo //wsl.localhost/Ubuntu/home/kingderman/Documents/ME5412-github-latest --model-copy C:/Users/23971/Documents/5412/_runtime/render-assets/robot --output C:/Users/23971/Documents/5412/_runtime/render-out/<输出目录> --case NOW__NURSE__BLOOD-DRAW
```

## 本机环境

- 仓库在 WSL2 Ubuntu 中：`/home/kingderman/Documents/ME5412-github-latest`（Windows 路径为 `\\wsl.localhost\Ubuntu\home\kingderman\Documents\ME5412-github-latest`），Python 用 `.venv/bin/python`。Windows 目录 `C:\Users\23971\Documents\5412` 不是 git 仓库。2026-11-01 从 Ubuntu 机器迁来，压缩包为 `C:\Users\23971\Documents\5412\ME5412_migration_20261101.tar.zst`，说明见 [`migration/windows_handoff_20261101/`](migration/windows_handoff_20261101/START_HERE.md)。
- CPU 为 16 核，WSL 内存 15 GB。每轮的 16 个词对 run 各绑定一个核（cpu0–15），收尾段规划用 7 个进程。
- 渲染分两步：WSL 中由 `export_render_inputs.py` 导出回放与标签，Windows 中由 `render_gpu_windows.py` 绘制。最近几轮实际跑在 Intel Arc B390 核显上（第八轮每句 94–231 s）；给渲染进程设置 `SHIM_MCCOMPAT` 没能切到 RTX 5060，也没有改系统设置。
- run 运行期间不要修改 `src/`、`tests/`、`scripts/`，否则冻结身份改变，run 会以 `IDENTITY_CHANGED_DURING_RUN` 停止。

## Git 与推送

- 本地开发分支与公开分支都名为 `group3/trajectory-planning`，但提交链不同。源仓库当前为 `dfe4bacde`，包含本地原始运行存储提交；不得直接把该提交链推入已清理的公开分支。
- 公开仓库为 `kimzclandi/me5412-sign-robot`。本次核实其基线为已成功推送的清理提交 `86428693`，并按用户 2026-11-02 的新要求在其上同步第八轮非原始快照。
- 发布副本为 `C:\Users\23971\Documents\5412\_publish\group3-trajectory-planning-20261102`。代码、配置、根目录记录、序列结果和独立复核来自源版本；原始候选、尝试、检查点及调时存储被排除，小型元数据另存 `run_summaries/`。清单见 `PUBLICATION_MANIFEST.json`。
- 源工作树及本地原始证据保持不动。此前公开历史未改写；本次没有引入第七、八轮原始存储提交，也未修改 master、仓库可见性或发布 Release。

## 本阶段沿用的规则

- 保护数据和旧策略只新增版本，不覆盖：保护表 v1、v2 并存；词对策略 `connector_only_v1`、`braking_v1`、`fast_v1` … `fast_v5` 并存；序列策略 v1 … v7 并存。
- 证据不删、不改。被取代的第三、五轮保留，并在各自的 README 中标注。
- 公开交付对所有轮次排除原始词对存储，不携带 `.gitignore` 的逐轮例外；本地原始证据保留，公开整理后的元数据，新视频仍不入库。
- 说明文档中英双语（[AGENTS.md](AGENTS.md)）。
- 不合并、不开 PR、不改仓库可见性、不发 Release、不用付费 API；只在用户明确要求时推送。

## 待办与需要决定

1. **人工观看第八轮视频**，尤其是最快的几段衔接（9–10 帧，约 0.3 s）和 NURSE 的分步退出，确认动作自然。目前还没有人看过。
2. **发布后续**：本次按用户要求同步第八轮非原始快照；以后更新须继续保留公开清理规则，并以当时最新公开提交为基线。
3. **句子开头**：句子仍从第一个词的保护核心直接开始，没有从初始姿态进入的引入段（结尾已经回到初始姿态）。用户没有提出，尚未处理。
4. **余量**：MEDICINE MORNING NIGHT TAKE 的最小间隙正好等于 2.0 mm 门槛；最大的衔接加加速度积分 4.89e6 接近门槛 5e6。
5. **hospital35 的 24 个源动作受阻词**（[TASK-27](TASK-27.md)）：全库目标已停止，这个决定仍未作出；在九句话范围内，这类问题只记录、不判失败。
6. 正式验收、跨组评审、实机测试：都还没有做。

## 未验证限制

- 视频和静帧未经人工观看；这些是运动学工程结果，不是已验证的 ASL 句子。
- 碰撞为采样检查，不是连续碰撞证明；拐角平滑过渡会切角，碰撞按实际曲线检查。
- 墙钟预算使候选池受机器负载影响，重跑不保证逐位相同。
- 本文件是事后整理的，数字取自各轮 README 和提交记录，没有重新计算。
