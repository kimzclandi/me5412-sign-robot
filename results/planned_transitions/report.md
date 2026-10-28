# 衔接规划结果

**中文** · [English](report.en.md)

时长按帧数 / 30 计算，包含最后一帧显示时间。通过/失败只统计插入的过渡；单词句没有过渡检查。详见[协议、启动命令与限制](../../docs/transition-planner.md)。

| 句子 | 过渡数 | 通过 | 失败 | 规划秒数 | 基线秒数 | 秒数差 |
|---|---:|---:|---:|---:|---:|---:|
| HELLO YOU APPOINTMENT HAVE | 3 | 3 | 0 | 10.567 | 11.200 | -0.633 |
| MEDICINE MORNING NIGHT TAKE | 3 | 2 | 1 | 9.300 | 10.067 | -0.767 |
| NOW NURSE BLOOD-DRAW | 2 | 0 | 2 | 12.267 | 12.533 | -0.267 |
| PLEASE WAIT DOCTOR COME SOON | 4 | 2 | 2 | 13.467 | 14.267 | -0.800 |
| YOU BUY BOOK | 2 | 2 | 0 | 9.667 | 10.300 | -0.633 |
| YOU HURT WHERE | 2 | 2 | 0 | 8.967 | 9.400 | -0.433 |
| YOU NEED INTERPRETER | 2 | 1 | 1 | 9.200 | 9.667 | -0.467 |
| YOU UNDERSTAND | 1 | 1 | 0 | 6.867 | 7.133 | -0.267 |
| BREATHE-DEEP | 0 | 0 | 0 | 4.633 | 4.633 | +0.000 |
| THANK-YOU | 0 | 0 | 0 | 4.300 | 4.300 | +0.000 |

失败详情（碰撞体名称保留原始标识；采样帧按过渡内位置编号）：

- **MEDICINE → MORNING: 失败** — 穿透 2.211 mm > 2 mm: L_thumb_distal | right_wrist_yaw_link, 采样帧 2 (内部); 穿透 8.437 mm > 2 mm: left_hip_roll_link | left_wrist_yaw_link, 采样帧 5 (内部); 穿透 10.744 mm > 2 mm: L_index_proximal | left_hip_roll_link, 采样帧 5 (内部); 穿透 21.741 mm > 2 mm: L_index_intermediate | left_hip_roll_link, 采样帧 6 (内部); 穿透 2.339 mm > 2 mm: L_middle_proximal | left_hip_roll_link, 采样帧 5 (内部); 穿透 45.904 mm > 2 mm: fixed_mount | left_wrist_yaw_link, 采样帧 9 (内部); 穿透 20.218 mm > 2 mm: L_thumb_distal | left_hip_pitch_link, 采样帧 8 (内部); 穿透 2.727 mm > 2 mm: L_thumb_intermediate | left_hip_roll_link, 采样帧 6 (内部); 穿透 15.048 mm > 2 mm: L_thumb_distal | left_hip_roll_link, 采样帧 6 (内部); 穿透 2.479 mm > 2 mm: L_middle_intermediate | left_hip_roll_link, 采样帧 6 (内部); 穿透 27.413 mm > 2 mm: L_index_proximal | fixed_mount, 采样帧 9 (内部); 穿透 21.389 mm > 2 mm: L_thumb_proximal | fixed_mount, 采样帧 9 (内部); 穿透 29.953 mm > 2 mm: L_thumb_intermediate | fixed_mount, 采样帧 9 (内部); 穿透 16.140 mm > 2 mm: L_middle_proximal | fixed_mount, 采样帧 9 (内部); 穿透 8.588 mm > 2 mm: L_thumb_intermediate | left_hip_pitch_link, 采样帧 8 (内部); 穿透 42.432 mm > 2 mm: L_thumb_distal | fixed_mount, 采样帧 9 (内部); 穿透 31.534 mm > 2 mm: L_index_intermediate | fixed_mount, 采样帧 9 (内部); 穿透 24.122 mm > 2 mm: L_middle_intermediate | fixed_mount, 采样帧 9 (内部); 穿透 3.003 mm > 2 mm: L_ring_proximal | fixed_mount, 采样帧 9 (内部); 穿透 6.350 mm > 2 mm: L_ring_intermediate | fixed_mount, 采样帧 9 (内部); 穿透 39.604 mm > 2 mm: left_wrist_yaw_link | right_elbow_link, 采样帧 11 (内部); 穿透 24.310 mm > 2 mm: left_wrist_yaw_link | right_wrist_roll_link, 采样帧 11 (内部); 穿透 11.616 mm > 2 mm: left_wrist_yaw_link | right_wrist_pitch_link, 采样帧 11 (内部); 穿透 8.117 mm > 2 mm: L_thumb_proximal_base | right_elbow_link, 采样帧 11 (内部); 穿透 12.158 mm > 2 mm: L_thumb_proximal | right_shoulder_yaw_link, 采样帧 11 (内部); 穿透 6.012 mm > 2 mm: L_thumb_proximal | right_elbow_link, 采样帧 11 (内部); 穿透 10.013 mm > 2 mm: L_thumb_intermediate | right_shoulder_yaw_link, 采样帧 11 (内部)

- **NOW → NURSE: 失败** — 穿透 16.466 mm > 2 mm: left_wrist_pitch_link | right_wrist_yaw_link, 采样帧 9 (内部); 穿透 3.657 mm > 2 mm: R_ring_proximal | left_wrist_pitch_link, 采样帧 9 (内部); 穿透 19.921 mm > 2 mm: R_pinky_proximal | left_wrist_pitch_link, 采样帧 9 (内部); 穿透 32.334 mm > 2 mm: left_wrist_yaw_link | right_wrist_yaw_link, 采样帧 10 (终点); 穿透 13.301 mm > 2 mm: R_thumb_proximal | left_wrist_yaw_link, 采样帧 9 (内部); 穿透 14.973 mm > 2 mm: R_thumb_intermediate | left_wrist_yaw_link, 采样帧 9 (内部); 穿透 14.406 mm > 2 mm: R_thumb_distal | left_wrist_yaw_link, 采样帧 9 (内部); 穿透 32.893 mm > 2 mm: R_index_proximal | left_wrist_yaw_link, 采样帧 10 (终点); 穿透 8.179 mm > 2 mm: R_index_intermediate | left_wrist_yaw_link, 采样帧 9 (内部); 穿透 15.641 mm > 2 mm: R_middle_proximal | left_wrist_yaw_link, 采样帧 9 (内部); 穿透 3.454 mm > 2 mm: R_middle_intermediate | left_wrist_yaw_link, 采样帧 9 (内部); 穿透 19.827 mm > 2 mm: R_ring_proximal | left_wrist_yaw_link, 采样帧 9 (内部); 穿透 12.253 mm > 2 mm: R_ring_intermediate | left_wrist_yaw_link, 采样帧 9 (内部); 穿透 30.455 mm > 2 mm: R_pinky_proximal | left_wrist_yaw_link, 采样帧 9 (内部); 穿透 8.026 mm > 2 mm: R_pinky_intermediate | left_wrist_yaw_link, 采样帧 9 (内部)

- **NURSE → BLOOD-DRAW: 失败** — 穿透 2.006 mm > 2 mm: R_index_proximal | right_hip_roll_link, 采样帧 4 (内部)

- **DOCTOR → COME: 失败** — 穿透 7.011 mm > 2 mm: R_thumb_intermediate | left_elbow_link, 采样帧 0 (起点); 穿透 7.854 mm > 2 mm: R_thumb_distal | left_elbow_link, 采样帧 0 (起点)

- **COME → SOON: 失败** — 穿透 13.729 mm > 2 mm: left_wrist_yaw_link | right_wrist_yaw_link, 采样帧 6 (内部); 穿透 30.859 mm > 2 mm: R_thumb_proximal | left_wrist_yaw_link, 采样帧 6 (内部); 穿透 24.461 mm > 2 mm: R_thumb_intermediate | left_wrist_yaw_link, 采样帧 6 (内部); 穿透 7.968 mm > 2 mm: R_index_proximal | left_wrist_yaw_link, 采样帧 6 (内部)

- **NEED → INTERPRETER: 失败** — 穿透 19.312 mm > 2 mm: L_thumb_proximal | left_hip_pitch_link, 采样帧 1 (内部); 穿透 13.981 mm > 2 mm: L_thumb_intermediate | left_hip_pitch_link, 采样帧 1 (内部); 穿透 7.723 mm > 2 mm: L_thumb_intermediate | left_hip_roll_link, 采样帧 1 (内部); 穿透 8.288 mm > 2 mm: L_thumb_distal | left_hip_roll_link, 采样帧 1 (内部); 穿透 6.855 mm > 2 mm: left_wrist_yaw_link | right_wrist_yaw_link, 采样帧 6 (内部); 穿透 8.063 mm > 2 mm: R_middle_proximal | left_wrist_yaw_link, 采样帧 6 (内部); 穿透 23.456 mm > 2 mm: R_ring_proximal | left_wrist_yaw_link, 采样帧 6 (内部); 穿透 22.656 mm > 2 mm: R_ring_intermediate | left_wrist_yaw_link, 采样帧 6 (内部); 穿透 13.542 mm > 2 mm: R_pinky_proximal | left_wrist_yaw_link, 采样帧 6 (内部); 穿透 20.035 mm > 2 mm: R_pinky_intermediate | left_wrist_yaw_link, 采样帧 6 (内部); 穿透 38.422 mm > 2 mm: L_thumb_proximal | right_wrist_yaw_link, 采样帧 6 (内部); 穿透 33.253 mm > 2 mm: L_thumb_intermediate | right_wrist_yaw_link, 采样帧 6 (内部); 穿透 2.593 mm > 2 mm: L_thumb_distal | right_wrist_yaw_link, 采样帧 6 (内部); 穿透 8.972 mm > 2 mm: L_index_proximal | right_wrist_yaw_link, 采样帧 6 (内部); 穿透 12.777 mm > 2 mm: L_index_proximal | R_middle_proximal, 采样帧 6 (内部); 穿透 2.844 mm > 2 mm: L_index_proximal | R_ring_proximal, 采样帧 6 (内部); 穿透 10.098 mm > 2 mm: L_middle_proximal | R_ring_proximal, 采样帧 6 (内部)
