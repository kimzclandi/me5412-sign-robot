# Nine hospital sentences, round 5: retained-edge screen v1 (2026-11-01)

[中文](README.md) · **English**

Development evidence only: formal PASS_SIM is 0, `formal_acceptance_enabled=false`, not verified ASL, no human review.
**Superseded by round 6** ([`../hospital_sentences_20261101_006/README.en.md`](../hospital_sentences_20261101_006/README.en.md)).
Kept as evidence of the over-broad screen below.

The user saw a twisted left arm in round 4's NOW NURSE BLOOD-DRAW (NURSE frame 81). The NURSE cut had kept source
frames 80-98, where the retargeted clip swings the left shoulder yaw onto its -2.62 rad stop at the 15 rad/s cap.
Code `27b6304` adds `endpoints.retained_edge_screen` = `no_new_arm_limit_contact_v1` (frames strictly between a core and
its cut may not press any arm joint on a stop the core never touches) and `endpoints.clamped_joint_stop` =
`clamped_joint_stop_v1` (a joint clamped on its stop at a cut, slope pointing beyond it, rests there). Inputs:
`make_inputs.py`; run `run.sh`, 22:14-22:48.

## Result: 5/7 sentences NUMERICAL_PASS

- NOW NURSE BLOOD-DRAW passes with the NURSE exit at frame 80: the flip is no longer played.
- **MEDICINE MORNING NIGHT TAKE** and **PLEASE WAIT DOCTOR COME SOON**: BLOCKED_DEPENDENCY. The screen also flagged
  MEDICINE frames 73-86 and DOCTOR frames 28-33, where only a wrist rests on its stop; rendered, those poses look like
  their unflagged neighbours. MEDICINE→MORNING (exits 69-73) and WAIT→DOCTOR (entries 33-34) then found no connector
  within the pair budget (collisions and joint limits).
- 15/15 selected connectors and 5/5 sentences agree on fresh rechecks; 15/15 protected cores unchanged.
- Fix (round 6): screen v2 flags only the proximal flip (a shoulder/elbow run outside its core range that reaches a new
  stop), wrists excluded.
