# P0-2 逐词问题与第二组确认清单

运行基线：`all_pairs_dev_20261031_v2`；词库版本：`hospital_v1@4888de783967786d4e2860cfb3e55df3b2ee50fb259a0ed0f90abc0180652c31`。本清单只读取冻结审计和端点问题证据，不改变动作、保护核心、窗口或原词时序。

## 汇总

- 35 个词；端点角色问题 10 条，涉及 10 个词。
- 词内碰撞问题 30 个词；速率超限问题 8 个词。
- 端点阻塞直接影响的唯一词对 326 条；影响按 source 出边或 target 入边计算，未删除自对。
- 当前正式批准状态仍为 `review_status=pending`、`quality.freeze_status=pending`。

## 逐词清单

| 词 | 动作哈希 | 几何核心提示（未批准） | 原入口/出口帧 | 问题 | 影响端点词对 | 历史研究端点（均待批） |
|---|---|---:|---:|---|---:|---|
| APPOINTMENT | `a9ea24fd8be9e6044413a975f97bb8bd5619a54b25c3118c588605100883cdc2` | 24–162 | 55 / 147 | WORD_INTERNAL_COLLISION<br>WORD_SPEED_LIMIT_EXCESS | 0 | 无 |
| BLOOD-DRAW | `3a73dd8df7e4a925bf4a8d83bf4e101c009e784f1c28f0ee1255f44bf97da964` | 24–191 | 31 / 180 | WORD_INTERNAL_COLLISION<br>WORD_SPEED_LIMIT_EXCESS | 0 | 无 |
| BREATHE-DEEP | `b6d48bc7d01c0382ef8b3e3c449e0f8b5c8e2c046598b6eb0327c1ac41b70b16` | 24–114 | 31 / 102 | WORD_INTERNAL_COLLISION | 0 | 无 |
| COME | `75d6455408ce6584043baedbd0e049cbeabcad534eda65ef561d2c7293b477a4` | 24–176 | 66 / 161 | NO_DETECTED_GEOMETRIC_OR_SPEED_ISSUE | 0 | 无 |
| DEAF | `073f5453e484f9a63c445f8fdfabcf85679b9d04b28f972fe651841cb9b4d908` | 24–89 | 24 / 66 | WORD_INTERNAL_COLLISION | 0 | 无 |
| DOCTOR | `639f93c6b9c6985e8a898a1a8f7a438584e94ab61f353a10823490b252364461` | 24–96 | 24 / 78 | WORD_INTERNAL_COLLISION | 0 | 无 |
| HAVE | `0991bf7c0d0406c9c3e4049ea4b4ee1502a20a483a764b8cede54e2e1a8e4867` | 24–79 | 24 / 61 | WORD_INTERNAL_COLLISION | 0 | 无 |
| HEADACHE | `485f8cdef5773472c983a45f684096f4b55b11204cf0f30848f4dcbab6eb13ee` | 24–104 | 24 / 88 | WORD_INTERNAL_COLLISION | 0 | 无 |
| HELLO | `d26edc80c22c222c72afc2973746199de03245b9cdae040400c1fec8587f636a` | 24–89 | 33 / 77 | WORD_SPEED_LIMIT_EXCESS | 0 | 无 |
| HURT | `a17641061df3e08fab2a5178950c71cae01edca2791072e029590a2ae892e09d` | 24–91 | 24 / 70 | ENDPOINT_BLOCKED<br>WORD_INTERNAL_COLLISION | 35 | r13c-hurt-source-f66 f66 |
| INTERPRETER | `3a159a8bd9af71563d85fe25cf69dbf7dc8d62dcd1b76ac2fdee0e099495662c` | 24–77 | 24 / 64 | ENDPOINT_BLOCKED<br>WORD_INTERNAL_COLLISION | 35 | r13c-interpreter-target-f25 f25 |
| LATER | `b9722ab602e38fab95fc5b7e0c5e9a4c6eeeb9b9924675af4b77451d2deab3a8` | 24–57 | 24 / 54 | WORD_INTERNAL_COLLISION | 0 | 无 |
| ME | `7470dbf5e39cf402c5bc16187646beab2f0d2ea4335b5ed61002b05b814c3d0c` | 24–110 | 24 / 87 | WORD_INTERNAL_COLLISION<br>WORD_SPEED_LIMIT_EXCESS | 0 | 无 |
| MEDICINE | `b8c5e0b7ade5c7a30c19d0cb8f938214956e69754087bbb42889d3f0f2f7bfa6` | 24–93 | 24 / 74 | ENDPOINT_BLOCKED<br>WORD_INTERNAL_COLLISION | 35 | r13c-medicine-source-f73 f73 |
| MORNING | `88874e76d81466a7141badf0aa2a5bf98319036d76771a9c39f9b83609ad47f6` | 24–98 | 24 / 79 | WORD_INTERNAL_COLLISION<br>WORD_SPEED_LIMIT_EXCESS | 0 | 无 |
| NEED | `c4ab9fc0ea73c2378b17eaf197ff46a2c5dbd937e22d84b99c11b3ed6e18c173` | 24–117 | 24 / 102 | WORD_INTERNAL_COLLISION | 0 | 无 |
| NIGHT | `20dece3ae28795bfa9321f4922c3291efc0e979deab9f77f4c314ca9d8a8c4cd` | 24–78 | 35 / 64 | ENDPOINT_BLOCKED<br>WORD_INTERNAL_COLLISION | 35 | r13c-night-source-f61 f61 |
| NO | `4c8af90a878fc4d0919a8d8f2bed4270b9beada6eb632b3c7c04518c714c7247` | 24–129 | 24 / 118 | WORD_INTERNAL_COLLISION | 0 | 无 |
| NOT | `13b8b2c32a83d761114348853b458af71c4a74b9ef0d4ec08c00eb3ee8c810cf` | 24–86 | 24 / 70 | ENDPOINT_BLOCKED<br>WORD_INTERNAL_COLLISION | 35 | 无 |
| NOW | `2d494c13fdf1b44bb11e97004e7b212ea5c45b7b0f8d0b972bd3589ae63e15e3` | 24–79 | 24 / 57 | NO_DETECTED_GEOMETRIC_OR_SPEED_ISSUE | 0 | 无 |
| NURSE | `f75945f059ef18a5f8888c9499e9160ada02ad9aea5a37f2850fb9a4f4dd391f` | 24–102 | 24 / 88 | WORD_INTERNAL_COLLISION | 0 | r13c-nurse-source-f80 f80, r13c-nurse-source-f81 f81 |
| PLEASE | `644c8699d245751fca2944b3dc57fb700c789dcf42a628fcd74fa7ee8f31166f` | 24–84 | 35 / 76 | WORD_INTERNAL_COLLISION<br>WORD_SPEED_LIMIT_EXCESS | 0 | 无 |
| SOON | `0fe325e7186b5ddd21072d7d7f967eea7bf153f004ecf9d943d33fcd23dd6e97` | 24–125 | 24 / 94 | WORD_INTERNAL_COLLISION | 0 | 无 |
| SORRY | `4404913c8cad98430d4a0cd7c94ef5b18adf46e06c9b86ec598c3dfba9bbff2e` | 24–163 | 24 / 132 | WORD_INTERNAL_COLLISION | 0 | 无 |
| STOMACH | `23bb66ab1be21b944e11f6e599a2044b3e37636c1ce0ed109d04e6e3fe6d37e0` | 24–87 | 24 / 66 | ENDPOINT_BLOCKED<br>WORD_INTERNAL_COLLISION | 35 | 无 |
| TAKE | `d8d8d6f16ef1c3d388c5dd3582a912148d19d7bf90998f0afcbffea894a5167e` | 24–91 | 46 / 84 | WORD_INTERNAL_COLLISION<br>WORD_SPEED_LIMIT_EXCESS | 0 | 无 |
| THANK-YOU | `040c0cdea15d58744d32563d111ab2c85cd49293dda78c3183ff4225fe40818d` | 24–90 | 24 / 80 | WORD_INTERNAL_COLLISION | 0 | 无 |
| TOMORROW | `0228a0538c2007b1bb770b18207323a5c8413f999f4146e1f910559f011a934b` | 24–88 | 24 / 75 | ENDPOINT_BLOCKED<br>WORD_INTERNAL_COLLISION | 35 | 无 |
| UNDERSTAND | `e50fee8ab9342dc6005a8cfd90ecf69d9ef90dbed3d347f76b9994e9aad58e3a` | 24–100 | 24 / 85 | WORD_INTERNAL_COLLISION | 0 | 无 |
| WAIT | `d02a3d7b07708ab4fd772ec6aa91ffdc10b5fcfaff7b3e79c703cac7c660a579` | 24–106 | 24 / 93 | NO_DETECTED_GEOMETRIC_OR_SPEED_ISSUE | 0 | 无 |
| WHERE | `187ee5ade8ecac185776511354022e32707035c3d277c71b739a710e4aa8a2e2` | 24–111 | 40 / 94 | WORD_INTERNAL_COLLISION | 0 | 无 |
| WRITE | `a93d1bc2c5e9cea4ec0edaf7480acc75c9eea059f772117b461127468d57c124` | 24–107 | 24 / 94 | ENDPOINT_BLOCKED<br>WORD_INTERNAL_COLLISION | 35 | 无 |
| YES | `dd29f2430c76ef96a4530147def04625283f30ff057b588b8cbe95a080eedefe` | 24–90 | 24 / 76 | ENDPOINT_BLOCKED<br>WORD_INTERNAL_COLLISION | 35 | 无 |
| YOU | `ab42f2abccc3ad7275cb99fb518cd01627cfca5eb25664b95d2713abfb47649f` | 24–118 | 42 / 98 | WORD_SPEED_LIMIT_EXCESS | 0 | 无 |
| YOUR | `7e0b5dbdad5ccdbcd514129851de0f38ad6cdf3b3081ea3c5d1b14a43db98e6c` | 24–108 | 24 / 91 | ENDPOINT_BLOCKED<br>WORD_INTERNAL_COLLISION | 35 | 无 |

## 端点角色问题

| 词 | 角色 | 帧 | 端点间隙 mm | 最近碰撞对 | 影响词对 | 动作哈希 |
|---|---|---:|---:|---|---:|---|
| HURT | source | 70 | -13.417172 | L_thumb_distal × right_wrist_yaw_link | 35（HURT__*（source）） | `a17641061df3e08fab2a5178950c71cae01edca2791072e029590a2ae892e09d` |
| INTERPRETER | target | 24 | -26.744698 | L_index_intermediate × right_wrist_yaw_link | 35（*__INTERPRETER（target）） | `3a159a8bd9af71563d85fe25cf69dbf7dc8d62dcd1b76ac2fdee0e099495662c` |
| MEDICINE | source | 74 | 1.963783 | L_ring_intermediate × R_thumb_distal | 35（MEDICINE__*（source）） | `b8c5e0b7ade5c7a30c19d0cb8f938214956e69754087bbb42889d3f0f2f7bfa6` |
| NIGHT | source | 64 | 0.424539 | left_wrist_yaw_link × right_wrist_pitch_link | 35（NIGHT__*（source）） | `20dece3ae28795bfa9321f4922c3291efc0e979deab9f77f4c314ca9d8a8c4cd` |
| NOT | target | 24 | -16.156179 | L_thumb_distal × left_hip_pitch_link | 35（*__NOT（target）） | `13b8b2c32a83d761114348853b458af71c4a74b9ef0d4ec08c00eb3ee8c810cf` |
| STOMACH | target | 24 | -17.206276 | L_thumb_distal × left_hip_roll_link | 35（*__STOMACH（target）） | `23bb66ab1be21b944e11f6e599a2044b3e37636c1ce0ed109d04e6e3fe6d37e0` |
| TOMORROW | target | 24 | -30.864839 | left_hip_pitch_link × left_wrist_yaw_link | 35（*__TOMORROW（target）） | `0228a0538c2007b1bb770b18207323a5c8413f999f4146e1f910559f011a934b` |
| WRITE | target | 24 | -24.888589 | left_wrist_yaw_link × right_wrist_yaw_link | 35（*__WRITE（target）） | `a93d1bc2c5e9cea4ec0edaf7480acc75c9eea059f772117b461127468d57c124` |
| YES | target | 24 | -41.437488 | L_thumb_proximal × left_hip_pitch_link | 35（*__YES（target）） | `dd29f2430c76ef96a4530147def04625283f30ff057b588b8cbe95a080eedefe` |
| YOUR | source | 91 | -7.838878 | L_thumb_distal × left_hip_roll_link | 35（YOUR__*（source）） | `7e0b5dbdad5ccdbcd514129851de0f38ad6cdf3b3081ea3c5d1b14a43db98e6c` |

## 内部问题的帧与影响

几何审计保存每帧最小间隙和整个词的最坏碰撞对；下表不虚构每个问题帧的全部碰撞对。各词最坏碰撞对、精确帧和速率逐关节区间见 JSON。影响词对只计实际保留前缀/后缀包含问题帧或速率区间的角色。

| 词 | 词内碰撞帧（审计采样） | 最小间隙 mm | 速率超限 rad/s | 保留词片段受影响词对数 |
|---|---|---:|---:|---:|
| APPOINTMENT | 46, 47, 48, 49, 50, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142 | -19.415991 | 11.169373 | 69 |
| BLOOD-DRAW | 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 78, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176 | -3.265277 | 8.751564 | 69 |
| BREATHE-DEEP | 53, 54, 55, 56, 57, 58, 59, 66, 67, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 84, 85, 86, 87, 88, 89, 96 | -0.948268 | 0.000000 | 69 |
| DEAF | 27, 68 | -7.838974 | 0.000000 | 69 |
| DOCTOR | 43, 104, 105, 106, 107, 108, 109, 110, 111 | -2.443129 | 0.000000 | 69 |
| HAVE | 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 59, 65, 67, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91 | -78.646101 | 0.000000 | 69 |
| HEADACHE | 79, 83, 84, 85, 86, 87, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121 | -40.140269 | 0.000000 | 69 |
| HELLO | 无 | 7.811563 | 9.999940 | 69 |
| HURT | 25, 33, 59, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102 | -23.769275 | 0.000000 | 69 |
| INTERPRETER | 17, 18, 19, 20, 21, 22, 23, 24, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35 | -26.744698 | 0.000000 | 69 |
| LATER | 33, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71 | -37.927946 | 0.000000 | 69 |
| ME | 71, 72, 80 | -7.205097 | 1.896337 | 69 |
| MEDICINE | 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 25, 26, 30, 31, 32, 74, 89, 90, 91, 92, 95, 96, 97, 98, 99, 100, 101 | -32.765346 | 0.000000 | 69 |
| MORNING | 39, 40, 41, 42, 43, 44, 45, 65, 66, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 108, 109, 111, 112, 113, 114 | -25.771110 | 1.936875 | 69 |
| NEED | 40, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132 | -29.946521 | 0.000000 | 69 |
| NIGHT | 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 38, 40, 41, 42, 43, 51, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95 | -62.551976 | 0.000000 | 69 |
| NO | 136, 137, 138, 139, 140, 141, 142, 143, 144, 145 | -23.893804 | 0.000000 | 35 |
| NOT | 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101 | -76.558349 | 0.000000 | 69 |
| NURSE | 30, 32, 36, 78, 79, 81, 82, 83, 84, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117 | -91.695417 | 0.000000 | 69 |
| PLEASE | 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99 | -67.752434 | 9.999940 | 69 |
| SOON | 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136 | -19.627153 | 0.000000 | 35 |
| SORRY | 34, 129, 130, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176 | -24.271424 | 0.000000 | 69 |
| STOMACH | 18, 19, 20, 21, 22, 23, 24, 25, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100, 101, 102, 103, 104 | -66.327079 | 0.000000 | 69 |
| TAKE | 94, 95, 96, 97, 98, 99, 100 | -20.527598 | 15.349300 | 69 |
| THANK-YOU | 27, 28, 30, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105 | -38.435364 | 0.000000 | 69 |
| TOMORROW | 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 70, 72 | -59.525102 | 0.000000 | 69 |
| UNDERSTAND | 28, 29, 84, 88, 109, 110, 111, 112, 113, 114 | -10.774651 | 0.000000 | 69 |
| WHERE | 114, 115, 116, 117, 118, 119, 120 | -22.596513 | 0.000000 | 35 |
| WRITE | 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 45, 46, 47, 48, 65, 66, 67, 68, 69, 70, 71, 73, 74, 75, 76, 77, 78, 79, 88, 89, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 122, 123 | -38.747328 | 0.000000 | 69 |
| YES | 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 73, 74, 75, 77, 78, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107 | -77.221813 | 0.000000 | 69 |
| YOU | 无 | 7.811563 | 3.712843 | 69 |
| YOUR | 36, 91, 92, 93 | -42.954773 | 0.000000 | 69 |

## 速率问题帧区间

| 词 | 超限区间数量（含每个关节） | 起帧（区间为 f→f+1） |
|---|---:|---|
| APPOINTMENT | 38 | 61, 62, 63, 75, 136, 137, 138 |
| BLOOD-DRAW | 10 | 174, 175, 176 |
| HELLO | 11 | 31, 37, 38, 66, 75, 76 |
| ME | 1 | 80 |
| MORNING | 1 | 76 |
| PLEASE | 2 | 44 |
| TAKE | 28 | 72, 73, 87, 88, 89 |
| YOU | 4 | 42 |

## 第二组确认模板

每个词至少需要逐项返回以下内容：

1. 与本清单动作哈希一致的批准动作，或修复动作的新文件与 SHA-256。
2. 保护核心帧范围，明确是否允许任何入口/出口窗口，分别给出 source exit 与 target entry 的范围。
3. 对每个端点异常给出角色、帧、几何/语义理由和批准人/版本；未批准时保持阻塞。
4. NURSE f80 与 f81 必须分别给出确认；f80 当前研究提案裁剪 8/79，f81 另有独立端点结果，不能合并。
5. 确认原词时间顺序和核心不被执行模型擅自改变；记录真实评审人、时间、证据文件和哈希。

所有 35 词仍需核心/窗口审批；表中“无”仅表示没有历史替代端点提案。机器可读待填模板：[`group2_review_template.json`](../results/group3_execution_20261031_001/P0-2/group2_review_template.json)。

逐词结构化材料见 [`word_issue_manifest.json`](../results/group3_execution_20261031_001/P0-2/word_issue_manifest.json)。

本任务只完成问题定位和材料模板；不代表任何词已获得批准或可进入 `PASS_SIM`。
