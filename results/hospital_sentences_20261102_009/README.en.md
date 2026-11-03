# Nine hospital sentences, round 9: YOU HURT WHERE on its own, HURT from frame 37 (2026-11-02)

[中文](README.md) · **English**

Development evidence only: formal PASS_SIM is 0, `formal_acceptance_enabled=false`, not verified ASL, no human review.
Earlier: round 8 [`../hospital_sentences_20261102_008/README.en.md`](../hospital_sentences_20261102_008/README.en.md). This
round redoes only YOU HURT WHERE; the other six sentences stay as in round 8.

User request (chat, 2026-11-02): HURT starts at frame 37; optimise the sentence YOU HURT WHERE on its own. Code `dfe4bac`
(planning and verification code identical to round 8's `1d07d2d`; only two document hashes in `project_overview.py` changed
in between); inputs `make_inputs.py`; run `run.sh`, 2 pair runs on cpu0-1, 14:21-15:03.

## Cause

- HURT's v1/v2 protection was [27, 57] (0.9-1.9 s). At frames 29-34 the retargeted HURT flips the left arm: the left shoulder
  yaw swings out and back at the 15 rad/s cap (left shoulder pitch and wrist pitch near 12-14 rad/s), so the left arm first
  reaches out to the side and then comes back in front of the chest. The sentence's peak arm speed, 28.2 rad/s, is there.
- Round 8's YOU->HURT entered HURT exactly at frame 27, so this flip played as part of HURT.

## Changes (no code changes)

- **Protection bundle v3** (`config/user_protected_hospital35_v3.json`): only HURT's record changes, [27, 57] → **[37, 57]**
  (1.24-1.9 s, floor(1.24×30) = 37), with the source of the change recorded; v2 stays for the earlier runs.
- **Pair policy** `config/transition_policy_hospital_sentences_fast_v6.json`: round 8's `fast_v5` with protection bundle v3.
  Because this round plans only the sentence's two pairs, one core each, every pair gets a longer search, 720 → 1800 s
  (RRT 240 → 600 s): in round 8 both pairs stopped on the wall-time limit (`PAIR_WALL_TIME_LIMIT`) before trying every route.
  Smooth timing, limits and the selection rule are unchanged.
- **Sequence policy** `config/sequence_policy_hospital_sentences_v8.json`: YOU HURT WHERE only.

## Result: NUMERICAL_PASS, HURT starts at frame 37

- 2/2 selected connectors and 1/1 sentence agree on fresh rechecks; 3/3 protected cores are bitwise unchanged; the sentence
  ends at rest.
- **YOU->HURT enters HURT exactly at frame 37** (`ik_via1`, 11 frames, no source frames before 37 retained). After YOU, the
  right hand draws back and the left arm rises from the side; both hands reach the chest just as HURT's frame 37 begins, and
  round 8's outward swing of the left arm is gone.
- Sentence 120 → **109 frames** (3.97 → 3.60 s); peak arm speed 28.2 → 22.6 rad/s; YOU->HURT connector mean arm speed
  11.8 → 9.9 rad/s, peak 21.0 → 16.4 rad/s; minimum clearance 2.95 → 7.81 mm. The whole sentence's jerk integral, protected
  cores included, 3.59e7 → 2.07e7 rad²/s⁵ (for reference only).
- HURT->WHERE: the longer search (131 attempts) still selected round 8's 11-frame connector (same cut, same method, identical
  metrics). The rest tail is also round 8's (leaving WHERE at frame 81, direct route, 9 frames).

| Pair | Round | Attempts | Pass | Selected | Method | Cut | Connector fr | Stops | Between cores | Peak jerk | Peak accel | Jerk integral | Min clearance |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| YOU→HURT | 8 | 40 | 15 | attempt_00015 | ik_via1 | 72→27 | 12 | 0 | 12 | 1103 | 90 | 3.19e6 | 2.95 mm |
| YOU→HURT | **9** | 113 | 86 | attempt_00068 | ik_via1 | **72→37** | 11 | 0 | 11 | 1136 | 75 | 4.24e6 | 9.50 mm |
| HURT→WHERE | 8 | 66 | 43 | attempt_00028 | ik_via1 | 57→51 | 11 | 0 | 11 | 1679 | 91 | 4.77e6 | 8.87 mm |
| HURT→WHERE | **9** | 131 | 96 | attempt_00067 | ik_via1 | 57→51 | 11 | 0 | 11 | 1679 | 91 | 4.77e6 | 8.87 mm |

"Pass" counts candidates that pass the independent numerical checks. Peak jerk (rad/s³) and peak acceleration (rad/s²) are the
finite differences inside the connector and the jerk integral (rad²/s⁵) is the analytic connector's, as in round 8's README;
the limits are 5000, 200 and 5e6. Minimum clearance here is the pair recheck's; the sentence recheck's is given above.

## Videos and charts

- `videos_gpu/YOU__HURT__WHERE/`: `comparison.mp4` (not committed, user decision), `report.json`, `contact_sheet.png`. The video
  is on this machine at `C:\Users\23971\Documents\5412\_runtime\render-out\round9_150418\YOU__HURT__WHERE\comparison.mp4`.
- `round8_vs_round9_hurt_entry.png`: from the end of YOU's protected core to HURT frame 45, every 2 frames, front and side;
  round 8 in the top two rows, round 9 below.
- `arm_speed_round8_vs_round9.png`: arm speed over the sentence (norm of the shoulder, elbow and wrist joint speeds), round 8
  above and round 9 below; green background for user protection, yellow for added connectors.
- `compare_round8_vs_round9.py`: the script that draws both (Windows render-venv, GPU).
- Rendered on the Intel Arc B390 integrated GPU again (127 s), same script and output format as round 8. Not watched by a person.

## Limits

- HURT's new protected core [37, 57] still contains fast source motion: the left wrist pitch and left shoulder yaw swing back
  and forth at 11-14 rad/s at frames 39-41 and 47-49 (left wrist pitch acceleration 211 rad/s² at frame 39 and jerk
  5754 rad/s³ at frame 48, both above the connector limits), and the right thumb reaches the 10 rad/s finger cap at frame 49.
  They are inside the user's protection, so they are recorded (`protected_source_audit`) and not changed; the sentence's
  22.6 rad/s arm-speed peak is there. If they also look unnatural, the protection would need to shrink further, or Group 2
  would need to revise HURT's source motion.
- The other six sentences were not rerun and remain round 8's (protection bundle v2); every word they use has the same record
  in v3 as in v2.
- This round searched longer than round 8, so the two rounds' candidate counts are not directly comparable; the wall-clock
  budget lets machine load change the candidate pool.
- Sampled collision checks are not a continuous-collision proof; after this directory is committed, these runs cannot be
  resumed or rechecked on the new HEAD.

## Reproduction

```bash
.venv/bin/python results/hospital_sentences_20261102_009/make_inputs.py          # writes only files that do not exist yet
bash results/hospital_sentences_20261102_009/run.sh
.venv/bin/python results/hospital_sentences_20261102_009/export_render_inputs.py
```

Rendering (Windows): run `render_gpu_windows.py` with the Python in `C:\Users\23971\Documents\5412\_runtime\render-venv`, with
`--repo //wsl.localhost/Ubuntu/home/kingderman/Documents/ME5412-github-latest`,
`--model-copy C:/Users/23971/Documents/5412/_runtime/render-assets/robot`, `--output <output folder>` and
`--case YOU__HURT__WHERE`.
