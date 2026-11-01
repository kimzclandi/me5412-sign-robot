# Invalidated pre-freeze smoke / 已作废的冻结前烟测

EN: Development smoke only, not evidence. During its pair-review step the executor edited
`src/sign_robot/batch_control.py` (02:45:41). From then on every fresh review correctly failed with
"Saved trajectory identity differs from fresh frozen inputs" (ERROR), and the later steps refused the
stale run. COME→COME 13/13 and the first two COME→NOW reviews were completed before the edit. This
smoke led to the identity-drift guard (drivers now stop with IDENTITY_CHANGED_DURING_RUN before any
new step). Files are kept unchanged. The clean repeat is `smoke_pre_freeze_002/`.

中文：仅为开发烟测，不作证据。在其词对复核步骤中，执行者于 02:45:41 修改了
`src/sign_robot/batch_control.py`；此后每次全新复核都按设计以“保存轨迹身份与当前冻结输入不同”报 ERROR，
后续步骤也拒绝了过期 run。修改前已完成 COME→COME 13/13 与 COME→NOW 前两条复核。此次烟测促成了身份漂移保护
（驱动现在会在任何新步骤前以 IDENTITY_CHANGED_DURING_RUN 停止）。文件保持原样；干净重做见 `smoke_pre_freeze_002/`。
