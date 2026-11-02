# Group 3 Round 13c handoff — NURSE departure (f80x)

## 1. What this is

This is the Round 13c final handoff for the Group 3 transition planner on NURSE departure. The final choice is **NURSE:80 (f80x)**, selected through the named `TRIM_CAP_EXCEPTIONS` path. The strict trim rule elsewhere is `trim_frames / core_len <= 0.10`, with `max = floor(0.10*core)`. NURSE has `core_len=79`, so the floor budget is 7 and the earliest result without an exception is f81. The NURSE exception records 8/79 ≈ **10.126582%** and remains pending Thomas confirmation (as noted in the code comment).

本交接记录 Round 13c NURSE 离场的最终方案。最终选择 **NURSE:80 (f80x)**，通过命名的 `TRIM_CAP_EXCEPTIONS` 路径；其他动作仍严格遵守 `trim_frames / core_len <= 0.10`，即 `max = floor(0.10*core)`。NURSE 的 `core_len=79`，普通预算为 7，因此不使用例外时最早只能到 f81。NURSE 例外为 8/79 ≈ **10.126582%**，仍待 Thomas 确认（代码注释中已有说明）。

## 2. Upstream / GitHub remotes

There are two different histories and they must not be conflated.

**A. Upstream (canonical FBX / Group 2 base)**

- Remote: `https://github.com/kimzclandi/me5412-sign-robot.git`
- Branch: `group2/fbx-retarget-you` @ `bcdefc48c19f539e1166fe90da4c55a97828d7c1`
- This cloud worktree's `origin` already points here. R13c commits are descendants of `bcdefc4`.

**B. Course GitHub (unrelated history)**

- Remote: `https://github.com/Kingderman/ME5412-Project.git`
- Its `group3/r13c` branch has unrelated history. Do not force-push over it or assume shared ancestry with `kimzclandi`.

Ubuntu laptop / second clone workflow (copy-pasteable):

```bash
# Fresh clone of upstream base (if needed)
git clone https://github.com/kimzclandi/me5412-sign-robot.git me5412-sign-robot
cd me5412-sign-robot
git fetch origin group2/fbx-retarget-you
git checkout -B group3/r13c bcdefc48c19f539e1166fe90da4c55a97828d7c1   # or checkout existing local that already has 64c7ffa

# Apply thin bundle from handoff (requires local 64c7ffa)
git fetch /path/to/r13c_f80x-thin.bundle group3/r13c-f80x:group3/r13c-f80x
git checkout group3/r13c-f80x
# Optional: rename/land as group3/r13c locally
git branch -f group3/r13c HEAD

# Cherry-pick render script if not in bundle tip you use:
# git fetch <laptop-or-bundle> && git cherry-pick 81cc43ab821f30cc5911d93c35c38a0db26b190c

# Second remote for course GitHub — add only when Thomas asks to publish; DO NOT push from this handoff
# git remote add course https://github.com/Kingderman/ME5412-Project.git
# git push course group3/r13c   # ONLY after Thomas confirms; histories may be unrelated — prefer bundle or patch, not force
```

No push and no remote-add were done in the cloud. Do not push from this session.

## 3. Comparison

| | Baseline (round13 @ NURSE:88 style / r13 FAILED retract) | R13b (NURSE:88) | R13c-f81 (strict floor, NURSE:81) | **R13c-f80x FINAL (exception NURSE:80)** |
|---|---|---|---|---|
| Plan 19 | 17 PASS / 1 source_near / 1 FAILED | 19 PASS | 18 PASS + 1 source_near | **19 PASS** |
| NOW→NURSE | via1 0.6s clr≈9.37 | via1 0.6s clr 9.3656 | via2 1.033s clr 9.3656 | via2 1.033s clr 9.3656 |
| NURSE→BD | FAILED retract −91.7 mm (src 88) | rrt 0.3s clr 2.351 rev15/5 d2~507 | **source_near via2 −28.426881 mm** (src 81; RRT not run) | **rrt min-jerk 1.0s clr 3.470** rev0 d2~43.19 |
| NURSE trim | — | 0/79 (end 88) | 7/79 ≈ 8.860759% | **8/79 ≈ 10.126582%** (TRIM_CAP_EXCEPTIONS) |
| Other 17 vs r13b | — | — | 17/17 bit-identical | 17/17 bit-identical |
| Yaw margin @ departure | — | f88 ≈ 0 | f81 ≈ **1.816 rad** | f80 ≈ **2.316 rad** |
| Peak arm speed f74→dep | — | — | f74–81 yaw **15.0** / arm peak 15.0 | f74–80 yaw **6.321** / arm peak **12.147** |
| Full pytest | — | — | 6 failed / 533 passed (pre-existing) | 6 failed / 535 passed (pre-existing; +2 exception tests) |

The f80x `planned_sentence_*.npz` files are bit-identical to `results/planned_transitions/round13c/`.

## 4. Why not f81

The f81 endpoint has torso penetration: **−28.426881 mm** at `left_wrist_pitch_link / torso_link`. Absolute PASS requires clearance ≥2 mm; `source_near` is not absolute certification. The via2 candidate was accepted as `source_near`, so RRT never ran for f81 NURSE→BLOOD-DRAW. RRT cannot repair a penetrating retained endpoint. The shoulder motion is also harsher: f74→f81 reaches yaw 15 rad/s, compared with 6.32 for f74→f80.

## 5. Laptop handoffs

Use `/workspace/me5412/_outgoing/r13c_f80x_render/` for final renders. `/workspace/me5412/_outgoing/r13c_f81_render/` is diagnostic only. Each directory contains a thin bundle (`64c7ffa..tip`), planned npz tgz, `report.json`, `acceptance.json`, README, `*_render_cmd.txt`, and `SHA256SUMS.txt`.

Do not git-track bundles, npz files, or videos. Point operators to `_outgoing/` and `results/planned_transitions/round13c_f80x/` (with a symlink or copy under worktrees as needed). The f80x bundle SHA256 is `e9adf53de60dc6c5fc03ea5baa4034ac411fed11bb0b443a72dd44f36e006448`; the f81 bundle SHA256 is `fb9184d6caa55998efac0ac818d165c240ce7caa9875790c4d5d4c56db5d5d8c`.

Render with `r13c_f80x_render_cmd.txt`. Transition-only clips use the repo-root `render_transitions_only.py` from cherry-pick `81cc43a`.

## 6. Known issues and limits

1. Six pre-existing pytest failures occur on both variants and are unrelated to the R13c planner:
   - `tests/test_learned_motion.py::test_model_inference_does_not_load_demonstration_files`
   - `tests/test_learned_motion.py::test_slow_generation_changes_sampling_without_replay`
   - `tests/test_learning_api.py::test_real_adapter_pose_matches_generated_joint_frames[...]` ×3 (Hello, Thank you, Please wait)
   - `tests/test_project_overview.py::test_real_overview_preserves_data_units_and_snapshot_scope`
2. MuJoCo float noise can change clearance and speed values by about 1e-N across machines. Use `report.json` statuses and the npz SHA for acceptance.
3. The NURSE left shoulder motion drives `left_shoulder_yaw` toward its limit near the sign end (f88 margin ≈0). Early departure at f80/f81 mitigates this; f80 still leaves ≈2.32 rad yaw margin at departure while using 10.13% core trim.
4. During cloud work, `website/dist` briefly went missing in the `wt-r13` working tree only. `git diff bcdefc4..<group3/r13c|r13c-f80x|r13c-f81> -- website/` stayed empty and it was restored with `git restore website/dist` from HEAD. This was incomplete worktree materialization in an adjacent worktree, not a Codex build or clean on the final tip. The final tip has no website diff versus bcdefc4.
5. `TRIM_CAP_EXCEPTIONS` for NURSE is explicit and pending Thomas confirmation.
6. `source_near` is not an absolute 2 mm PASS.
7. Do not commit `data/`, videos, bundles, or large npz files.

## 7. Commits on the final tip before this docs commit

```text
18c26b1 render: per-transition R13 baseline vs planned clips
42f1e08 feat(group3): R13c-f80x NURSE:80 via TRIM_CAP_EXCEPTIONS (strict 10% elsewhere)
1346cf1 docs(group3): Round 13c NURSE departure f80 and min-jerk RRT timing
4c205aa feat(group3): R13c NURSE:80 + via2 NOW→NURSE + min-jerk RRT NURSE→BD
```

Earlier R13/R13b commits continue back to `bcdefc4`. Keep sibling branches `group3/r13c-f80x` @ `42f1e08` and `group3/r13c-f81` @ `4462638` (and any docs tip on f81).

## 8. Done criteria

- `docs/HANDOFF_group3.md` exists with the sections above.
- One local docs commit is made on `group3/r13c`.
- No push, remote addition, planner change, data change, render, replanning, or pytest run is part of this handoff.
