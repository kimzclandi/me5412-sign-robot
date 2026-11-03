# 第二组单词片段 v2：交给第三组重跑（2026-11-02）

**中文** · [English](group2-clips-v2.en.md) · [第二组交接](group2-handoff.md) · [医院演示](hospital-demo.md)

分支 `group2/clips-v2`。第三组确认要把下面两项一起做进最终版本，所以视频词片段重新生成，需要第三组在这些片段上重新绑定保护记录并重跑规划。**`master` 在第三组重跑并验证前不动。**

## 改了什么

1. **碰撞修复打开**（`scripts/video/retarget_video.py` 的 `COLLISION_REPAIR = True`）：滤波和限速在逆运动学之后进行，会把手推进身体或另一只手；对穿模帧从上一个无碰撞帧出发重新求解两只手臂。32 个视频词最大穿模 **91.7 → 2.9 mm**，超过 5 mm 的词 **29 → 0**；选中的源视频全部不变；动作捕捉词不变。
2. **NURSE 人工修正**（`scripts/video/manual_corrections.py`）：StartASL 视频里签名者左手在画面最下边被切掉，MediaPipe 把左手估计成垂在胯旁。对照本机 4 段 NURSE 词典视频（StartASL、Spread The Sign、ASL Deafined、SignSchool），左手改为**掌心朝上、手指弯曲、在腰前**，右手改为 **N 手型（食指、中指伸出）水平搭在左手腕上方**，右手腕轨迹（点击动作）仍取自视频。为抵消两臂分别按各自肩膀缩放造成的分离，新增可选的 `contact` 设置（`G1Retargeter.targets`），只对 NURSE 生效。右手指尖在左手腕正上方约 2.5 cm，穿模 0 mm；这是人工修正，不是视频识别结果。

## 变化的片段（30 个；NOW、WAIT 不变）

| 词 | 旧 sha256（前 12 位） | 新 sha256（前 12 位） | 旧最大穿模 mm | 新最大穿模 mm |
|---|---|---|---|---|
| COME | `6c4a913fb105` | `ae555e0c1c98` | 11.2 | 0.0 |
| DEAF | `073f5453e484` | `d03abe86acac` | 7.8 | 0.0 |
| DOCTOR | `639f93c6b9c6` | `285cad1a3fc5` | 2.4 | 0.0 |
| HAVE | `0991bf7c0d04` | `ad4110ec387b` | 78.7 | 0.0 |
| HEADACHE | `485f8cdef577` | `8a9263ace636` | 40.1 | 1.1 |
| HELLO | `4bbb39ec1e4e` | `a1335d032605` | 28.1 | 0.0 |
| HURT | `a17641061df3` | `ea696f24ec37` | 23.8 | 0.0 |
| INTERPRETER | `3a159a8bd9af` | `28b47641d859` | 26.8 | 0.0 |
| LATER | `b9722ab602e3` | `3d5c3fd50057` | 38.0 | 0.0 |
| ME | `7470dbf5e39c` | `51dc56733a90` | 7.2 | 0.0 |
| MEDICINE | `b8c5e0b7ade5` | `af1b9b3a1193` | 32.8 | 2.9 |
| MORNING | `88874e76d814` | `19c42f008e08` | 25.8 | 0.0 |
| NEED | `c4ab9fc0ea73` | `a118fe4dc96a` | 29.9 | 0.0 |
| NIGHT | `20dece3ae287` | `f717e35c1179` | 62.6 | 0.0 |
| NO | `4c8af90a878f` | `6e4b2a0e3e2a` | 23.9 | 0.0 |
| NOT | `13b8b2c32a83` | `592363fe1fc1` | 76.6 | 0.0 |
| NURSE | `f75945f059ef` | `e06a52bad350` | 91.7 | 0.0 |
| PLEASE | `6b7b31ab5ff1` | `94708465fc6d` | 39.6 | 0.0 |
| SOON | `0fe325e7186b` | `254411342854` | 19.6 | 0.0 |
| SORRY | `4404913c8cad` | `b3c3893cbab5` | 24.2 | 0.0 |
| STOMACH | `23bb66ab1be2` | `dcabb55275b0` | 66.4 | 0.0 |
| TAKE | `3a99139dfee3` | `88cd19a1cc32` | 7.3 | 0.0 |
| THANK-YOU | `040c0cdea15d` | `09d8295e70a4` | 38.4 | 0.0 |
| TOMORROW | `0228a0538c20` | `9a203ead3dc0` | 59.5 | 0.0 |
| UNDERSTAND | `e50fee8ab934` | `d41eea30720c` | 10.8 | 0.0 |
| WHERE | `d7ec7d39eec7` | `f88bfec4942f` | 59.9 | 1.2 |
| WRITE | `a93d1bc2c5e9` | `c854122677a3` | 38.7 | 0.0 |
| YES | `dd29f2430c76` | `e0ff56fbb911` | 77.2 | 1.5 |
| YOU | `80c5de0eb7ed` | `cc24bbfbdddb` | 51.0 | 1.6 |
| YOUR | `7e0b5dbdad5c` | `92deb7259cc7` | 43.0 | 0.0 |

## 第三组需要做的

7 个多词句都包含变化的词，需要全部重跑：s1（HAVE）、s2（NEED、INTERPRETER）、s3（DOCTOR、SOON）、s4（HURT）、s6（NURSE）、s7（MEDICINE、MORNING、NIGHT）、s8（UNDERSTAND）。

1. 在本分支上重新绑定保护记录：当前记录按哈希绑定旧片段（`bcdefc4`），会报 `STALE_USER_PROTECTION_MOTION`；在本分支上，第三组的 28 项测试因此失败，属预期。
2. 重跑第 8 轮规划，输出与之前相同格式的 `render_inputs/<句子>/replay.npz`。
3. 交回后第二组用 `scripts/demo/compare_stitching.py` 与基线比较，不比现在差才合并，再重新生成演示视频。

## 本分支其他改动

- `scripts/demo/hospital_demo.py`：第三组的旧规划与新片段对不上时，自动退回基线并提示，演示不报错。
- `results/video_previews/`：32 个视频词对照视频与总览图已按新片段重新渲染。
- 测试：第二组相关测试全部通过（视频词须带碰撞修复记录且剩余穿模 ≤ 5 mm；NURSE 须来自 39089 且带人工修正记录）。

## 限制

- NURSE 的左手和两只手的手型是人工设定的，依据是词典视频，不是识别结果；未经 ASL 使用者评审。
- 右手指没有完全贴在左手腕上（约 2.5 cm 间隙），因为避碰使用比真实手更粗的凸包外形。
