# TASK-28: Nine hospital sentences (connectors only), rounds 1–8

> **Public-delivery update, 2026-11-02:** the user has now explicitly requested the GitHub update. This curated round-8 snapshot is based on public commit `86428693` and excludes raw run stores. References below to the earlier push pause or remote tip are historical and superseded by this publication; see the root README.

[中文](TASK-28.md) · [Current state](STATE.en.md) · [Handoff](HANDOFF.en.md) · [Previous stage TASK-27](TASK-27.en.md)

Status: **round 8 is done and waiting for someone to watch the videos.** Executed 2026-11-01 13:54 to 2026-11-02 03:48 (Asia/Shanghai). This file is the record of the whole stage. It was compiled after round 8 was committed, from the round READMEs, the commit history and local files; nothing was rerun. The README in each round directory is authoritative for that round's details and numbers.

**On 2026-11-01 the user narrowed the scope from all 1,225 word pairs to nine hospital sentences, and limited Group 3 to the connectors between two words. After eight rounds, all seven multi-word sentences pass numerically (NUMERICAL_PASS), every sentence ends at the hands-down rest pose, and no connector halts partway; the frames between protected cores across the 17 connectors fell from 1,717 in round 2 to 310. The other two "sentences" are single words that play the source motion. 24/24 protected cores are bitwise unchanged and the full test suite has 1014 passed. Commits after round 2 are local only and have not been pushed.**

Development evidence only: formal PASS_SIM is 0, `formal_acceptance_enabled=false`, not verified ASL; the videos have not been watched by a person and nothing ran on hardware.

## Scope

| Sentence | Pair connectors |
|---|---|
| HELLO YOU APPOINTMENT HAVE | HELLO→YOU, YOU→APPOINTMENT, APPOINTMENT→HAVE |
| YOU NEED INTERPRETER | YOU→NEED, NEED→INTERPRETER |
| PLEASE WAIT DOCTOR COME SOON | PLEASE→WAIT, WAIT→DOCTOR, DOCTOR→COME, COME→SOON |
| YOU HURT WHERE | YOU→HURT, HURT→WHERE |
| NOW NURSE BLOOD-DRAW | NOW→NURSE, NURSE→BLOOD-DRAW |
| MEDICINE MORNING NIGHT TAKE | MEDICINE→MORNING, MORNING→NIGHT, NIGHT→TAKE |
| YOU UNDERSTAND | YOU→UNDERSTAND |
| BREATHE-DEEP; THANK-YOU | Single words, no connector; the full source motion plays |

17 word pairs and 7 multi-word sentences in total; each of the 24 word occurrences has one protected core (21 distinct words). From round 1 on, the review gates only the added connectors (`CONNECTOR_ONLY_METHOD_V4`); collisions, speed violations and other problems in the source motions go to `source_side_findings`, belong to Group 2, and are recorded but not counted as failures.

## User decisions (in order)

| When | User decision | Carried out |
|---|---|---|
| 11-01, before round 1 | Only the nine sentences; stop scanning all 1,225 pairs | hospital35's P1-3 stopped at 46/79 batches (see the round-1 README); P1-4, the budget retry and the faster scanner from [TASK-27](TASK-27.en.md) were not run |
| 11-01, before round 1 | Group 3 owns only the connectors; source-motion defects belong to Group 2 | Review scope v4 |
| 11-01 | New videos are not committed | `.gitignore`; mp4 files stay on this machine |
| 11-01, after round 2 | Return to the hands-down rest pose after each sentence; the connectors are clearly slower than the signs and should be faster | Rounds 3 and 4 |
| 11-01, after round 4 | The left hand twists abnormally in NOW NURSE BLOOD-DRAW (NURSE frame 81) | Rounds 5 and 6 |
| 11-02, after round 6 | Upload to the team repository's group3 branch | A publication copy was prepared; the push was stopped partway and the remote did not change; the user then decided "don't push yet" |
| 11-02, after round 6 | End MORNING's protection at frame 38; end NURSE's protection at frame 75, then move the right hand away quickly and straighten the left wrist | Round 7. No connector could leave MORNING at frame 38 (the fingers snap shut between frames 37 and 38), so the user chose frame 37 |
| 11-02, after round 7 | The connectors move in jerks and are still slower than the signs; acceleration-type hard limits may be widened if they are what binds | Round 8 |

## Rounds

| Round | Directory (`results/`) | Run time | Trigger | Main change (code commit) | Pair / sequence policy | Result |
|---|---|---|---|---|---|---|
| 1 | [`hospital_sentences_20261101_001`](results/hospital_sentences_20261101_001/README.en.md) | 11-01 13:54–14:28 | Scope changed to nine sentences, connectors only | Review scope v4 (`5c536fb`) | `connector_only_v1` / `v1` | 3/7; 5 pairs had no candidate (at the cut, the source fingers were still rushing towards their limits) |
| 2 | [`…_002`](results/hospital_sentences_20261101_002/README.en.md) | 11-01 15:54–16:22 | 5 pairs without candidates in round 1 | Boundary braking and cut pairs that can stop at both ends (`d1bd7dc`) | `braking_v1` / `v2` | 7/7 |
| 3 | [`…_003`](results/hospital_sentences_20261101_003/README.en.md) | 11-01 19:56–20:32 | Return to rest; faster connectors | Select by fewest frames between cores; plan a rest tail after the last word (`0b2528d`) | `fast_v1` / `v3` | 6/7, **superseded by round 4** (no rest tail found for INTERPRETER) |
| 4 | [`…_004`](results/hospital_sentences_20261101_004/README.en.md) | 11-01 20:43–21:18 | Same | Two-pass rest-tail search (`843cd45`) | `fast_v1` / `v3` | 7/7, all end at rest; frames between cores 1,717 → 570 |
| 5 | [`…_005`](results/hospital_sentences_20261101_005/README.en.md) | 11-01 22:14–22:48 | Left arm twists at NURSE frame 81 | Retained-edge screen v1; joints clamped on a limit are treated as stopped at the cut (`27b6304`) | `fast_v2` / `v4` | 5/7, **superseded by round 6** (the screen flagged too much and blocked two sentences) |
| 6 | [`…_006`](results/hospital_sentences_20261101_006/README.en.md) | 11-01 22:55–23:32 | Same | Screen v2 flags only proximal (shoulder/elbow) flips (`368fc4b`) | `fast_v3` / `v5` | 7/7; NURSE leaves at frame 80 and the flip no longer plays |
| 7 | [`…_007`](results/hospital_sentences_20261102_007/README.en.md) | 11-02 01:17–01:51 | Shorter MORNING/NURSE protection, NURSE exits in steps | Protection bundle v2, staged exits (`129891a`) | `fast_v4` / `v6` | 7/7; NURSE: right arm away → left forearm up → left wrist straight → BLOOD-DRAW |
| 8 | [`…_008`](results/hospital_sentences_20261102_008/README.en.md) | 11-02 02:50–03:39 | Connectors halt partway and are slow | Stop-free smooth timing, selection by fewest stops, widened limits (`1d07d2d`) | `fast_v5` / `v7` | 7/7; interior stops 16 → 0; frames between cores 563 → 310 |

Full policy names are `config/transition_policy_hospital_sentences_<name>.json` and `config/sequence_policy_hospital_sentences_<version>.json`. Each round's results and raw pair stores are two separate commits (round 8: `fc9c7f9` and `70a61fa`). Round 1's runs used an uncommitted working tree (`2875e49`); that code was committed afterwards in `5c536fb`.

## Current delivery: round 8

- Code `1d07d2d`; results `fc9c7f9`, raw pair stores `70a61fa`.
- Pair policy `config/transition_policy_hospital_sentences_fast_v5.json`; sequence policy `config/sequence_policy_hospital_sentences_v7.json`; protection bundle `config/user_protected_hospital35_v2.json` (only NURSE [38,75] and MORNING [26,37] differ from v1, which stays for the earlier runs).
- 17/17 selected connectors and 7/7 sentences agree on fresh rechecks; 24/24 protected cores are bitwise unchanged; every sentence ends at rest, with rest tails of 8–12 frames.
- Connectors total 254 frames (round 7: 446) with 0 interior stops (round 7: 16); 15 use the minimum-jerk spline and 2 the corner blend (NURSE→BLOOD-DRAW, WAIT→DOCTOR).
- Limits (widened with the user's permission, each within the upper quartile of the signs' protected cores): peak acceleration 200 rad/s², peak jerk 5000 rad/s³, jerk integral 5e6 rad²/s⁵ (previously 120, 3000 and 1e6). The speed caps (15 arm, 10 finger rad/s) are unchanged. Measured: peak jerk 819–2058, peak acceleration ≤ 134, largest jerk integral 4.89e6.
- Tests: full suite 1014 passed (`results/hospital_sentences_20261102_008/tests/pytest_full.log`).

| Sentence | Round 2 | Round 8 |
|---|---|---|
| HELLO YOU APPOINTMENT HAVE | 417 fr (13.9 s) | 235 fr (7.8 s) |
| YOU NEED INTERPRETER | 316 fr (10.5 s) | 168 fr (5.6 s) |
| PLEASE WAIT DOCTOR COME SOON | 765 fr (25.5 s) | 366 fr (12.2 s) |
| YOU HURT WHERE | 291 fr (9.7 s) | 120 fr (4.0 s) |
| NOW NURSE BLOOD-DRAW | 405 fr (13.5 s) | 271 fr (9.0 s) |
| MEDICINE MORNING NIGHT TAKE | 387 fr (12.9 s) | 164 fr (5.5 s) |
| YOU UNDERSTAND | 198 fr (6.6 s) | 97 fr (3.2 s) |

Round 2 had no rest tails; the round-8 frame counts include the return to rest.

### Videos and charts

- Videos are not committed and exist only on this machine: `C:\Users\23971\Documents\5412\_runtime\render-out\round8_034002\<sentence>\comparison.mp4`, seven in all. The original clips are on top and the sentence below; front view on the left, side view on the right. Earlier rounds' videos are in `round2_163226`, `round4_211920`, `round6_233300` and `round7_015209` in the same folder.
- Committed: `report.json` and `contact_sheet.png` in `results/hospital_sentences_20261102_008/videos_gpu/<sentence>/`; arm-speed comparisons `arm_speed_round7_vs_round8.png` (for MEDICINE MORNING NIGHT TAKE and NOW NURSE BLOOD-DRAW); the NURSE exit frame by frame in `NOW__NURSE__BLOOD-DRAW/round7_vs_round8_nurse_exit.png`.

## Reproduction

Once a round directory is committed, its runs cannot be resumed or rechecked on the new HEAD: the frozen identity includes the commit and the hashes of `src/`, `tests/` and `scripts/`. A new round gets a new directory, as before: copy the previous round's `make_inputs.py`, `run.sh`, `export_render_inputs.py` and `render_gpu_windows.py`, then change the directory name, run IDs and policy versions. Round 8 as the example, in WSL:

```bash
cd /home/kingderman/Documents/ME5412-github-latest
.venv/bin/python results/hospital_sentences_20261102_008/make_inputs.py          # writes only files that do not exist yet
bash results/hospital_sentences_20261102_008/run.sh                               # 16 pair runs → recheck of selected candidates → rest tails → sequence recheck
.venv/bin/python results/hospital_sentences_20261102_008/export_render_inputs.py  # export the render inputs
```

Rendering runs on the Windows GPU, one sentence per call. MuJoCo cannot open `\\wsl.localhost` paths, so the model is the copy in `_runtime\render-assets\robot`, which must match the repository's `assets/robot` file by file:

```powershell
C:\Users\23971\Documents\5412\_runtime\render-venv\Scripts\python.exe \\wsl.localhost\Ubuntu\home\kingderman\Documents\ME5412-github-latest\results\hospital_sentences_20261102_008\render_gpu_windows.py --repo //wsl.localhost/Ubuntu/home/kingderman/Documents/ME5412-github-latest --model-copy C:/Users/23971/Documents/5412/_runtime/render-assets/robot --output C:/Users/23971/Documents/5412/_runtime/render-out/<output folder> --case NOW__NURSE__BLOOD-DRAW
```

## This machine

- The repository is in WSL2 Ubuntu: `/home/kingderman/Documents/ME5412-github-latest` (Windows path `\\wsl.localhost\Ubuntu\home\kingderman\Documents\ME5412-github-latest`), with Python at `.venv/bin/python`. The Windows folder `C:\Users\23971\Documents\5412` is not a git repository. The project moved here from the Ubuntu machine on 2026-11-01; the archive is `C:\Users\23971\Documents\5412\ME5412_migration_20261101.tar.zst`, explained in [`migration/windows_handoff_20261101/`](migration/windows_handoff_20261101/START_HERE.en.md).
- 16 CPU cores and 15 GB of memory in WSL. Each round's 16 pair runs are pinned one per core (cpu0–15); rest-tail planning uses 7 processes.
- Rendering has two steps: `export_render_inputs.py` exports the replay and labels in WSL, and `render_gpu_windows.py` draws them on Windows. Recent rounds actually rendered on the Intel Arc B390 integrated GPU (94–231 s per sentence in round 8); setting `SHIM_MCCOMPAT` for the render process did not move it to the RTX 5060, and no system settings were changed.
- Do not edit `src/`, `tests/` or `scripts/` while a run is going: the frozen identity would change and the run stops with `IDENTITY_CHANGED_DURING_RUN`.

## Git and pushing

- The local development branch and public branch are both named `group3/trajectory-planning`, but their histories differ. The source repository is at `dfe4bacde` and contains local raw-store commits; do not directly push that history into the cleaned public branch.
- The public repository is `kimzclandi/me5412-sign-robot`. Its verified baseline is the successfully pushed cleanup commit `86428693`. This update follows the user's new request on 2026-11-02 and adds a curated, non-raw round-8 snapshot on that baseline.
- The publication copy is `C:\Users\23971\Documents\5412\_publish\group3-trajectory-planning-20261102`. Code, policies, root records, sequence results and independent rechecks come from the source revision. Raw candidates, attempts, checkpoints and timing stores are excluded; compact metadata is retained under `run_summaries/`. See `PUBLICATION_MANIFEST.json`.
- The source worktree and local raw evidence are preserved. Earlier public history is not rewritten; round-7 and round-8 raw-store commits are not imported. No change to master, visibility or Releases is included.

## Rules kept in this stage

- Protection data and old policies only get new versions and are never overwritten: protection bundles v1 and v2 coexist, as do pair policies `connector_only_v1`, `braking_v1`, `fast_v1` … `fast_v5` and sequence policies v1 … v7.
- Evidence is never deleted or edited. The superseded rounds 3 and 5 are kept and marked as such in their READMEs.
- Public delivery excludes raw pair stores for every round; no per-round `.gitignore` exceptions are carried over. Local raw evidence is preserved, curated metadata is published, and new videos remain local.
- Documentation is bilingual ([AGENTS.en.md](AGENTS.en.md)).
- No merges, PRs, visibility changes, releases or paid APIs; push only when the user explicitly asks.

## To do and to decide

1. **Watch the round-8 videos**, especially the fastest connectors (9–10 frames, about 0.3 s) and NURSE's staged exit, to confirm they look natural. Nobody has watched them yet.
2. **Publication follow-up**: this update synchronizes the non-raw round-8 snapshot at the user's request. Future updates must preserve the public cleanup rules and start from the latest public tip.
3. **Sentence start**: sentences still begin directly on the first word's protected core, with no lead-in from the rest pose (the end already returns to rest). The user has not raised this; not addressed.
4. **Margins**: MEDICINE MORNING NIGHT TAKE's minimum clearance is exactly the 2.0 mm threshold; the largest connector jerk integral, 4.89e6, is close to the 5e6 limit.
5. **hospital35's 24 source-blocked words** ([TASK-27](TASK-27.en.md)): the full-library goal has stopped and that decision is still open; within the nine-sentence scope such problems are recorded, not counted as failures.
6. Formal acceptance, cross-group review and hardware tests: none done yet.

## Unverified limits

- Videos and stills have not been watched by a person; these are kinematic engineering results, not verified ASL sentences.
- Collisions are checked by sampling, not proven continuously; the corner blend cuts corners, and collisions are checked on the actual curve.
- The wall-clock planning budget lets machine load change the candidate pool, so reruns are not bitwise identical.
- This file was compiled after the fact; its numbers come from the round READMEs and the commit history and were not recomputed.
