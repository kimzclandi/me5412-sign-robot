# Group 3 all-pairs development scan: running and verification

[中文](group3-all-pairs-startup.md) · [Task plan](group3-all-pairs-transition-plan.en.md) · [Execution record](group3-all-pairs-progress.en.md)

Implementation started on October 31, 2026. The first delivery covers T00/T01/T02 and the infrastructure portions of T04/T06: frozen inputs, word audits, a direct-connector baseline, a complete matrix, atomic checkpoints, and independent reading of saved artifacts. T03 quality policy, T05 general candidates/search, T08 multiword integration and final L2 acceptance remain future work.

## Environment and commands

The working directory is `/home/kingderman/Documents/ME5412-github-latest`. Follow the existing Python and asset restoration instructions; `requirements-lock.txt` records the full dependency set. Motion scanning imports the numerical and motion modules without a semantic encoder. This machine reuses an existing environment matching the recorded dependencies through a local `.venv` symlink. That symlink is not a deliverable; create a new environment on another machine.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install -e .
```

All resources listed in `assets/robot/upstream_manifest.json` must be present. Missing files or hash drift block the inputs. See [robot assets](../assets/robot/README.en.md). MiniLM restoration repairs the historical learning tests; it is not a scanning prerequisite.

```bash
# Optional standalone T00/T02 evidence; each run also freezes its own copy.
.venv/bin/python scripts/freeze_all_pairs_inputs.py

# First run the frozen 40-pair development/performance sample.
.venv/bin/python scripts/plan_all_pairs.py --library hospital_v1 \
  --include-self --policy config/transition_policy.json \
  --run-id all_pairs_dev_20261031_v2 \
  --pairs-file config/transition_development_pairs.json

# Resume the remaining pairs with the same inputs, then independently read them.
.venv/bin/python scripts/plan_all_pairs.py --library hospital_v1 \
  --include-self --policy config/transition_policy.json \
  --run-id all_pairs_dev_20261031_v2 --resume
.venv/bin/python scripts/verify_all_pairs.py --run-id all_pairs_dev_20261031_v2
.venv/bin/python scripts/summarize_all_pairs.py --run-id all_pairs_dev_20261031_v2

.venv/bin/python -m pytest -q tests/test_all_pairs_contract.py tests/test_all_pairs_pipeline.py \
  tests/test_plan_transitions.py tests/test_transition_endpoint_gate.py tests/test_rrt_connect.py
```

Use `--max-pairs N` to exercise interruption recovery. Unattempted pairs remain NOT_RUN and the denominator stays 1,225. Repeat `--pair SOURCE__TARGET` for debugging; out-of-scope names are rejected. The three new run commands accept `--results-root`, defaulting to `results/all_pairs/`. The old `plan_transitions.py --all` still means ten fixed sentences.

Planning and verification set four common numerical-library thread variables to 1 and record actual dependencies and machine architecture. Resume checks the commit and source hashes, policy, actual model resources, motions/metadata, development sample, vocabulary and environment. Changed inputs require a new run_id; edited code cannot continue an old experiment. Exit code 0 indicates command completion, not L2 success.

## Frozen contract and output

`config/transition_policy.json` fixes 35 glosses, 1,225 ordered pairs and 35 self-pairs, without the old planner's extra-vocabulary fallback. This baseline has one rate-limited minimum-jerk quintic candidate with a duration of at least 0.3 seconds and a finite collision-sample budget. Failed candidates remain diagnostic. This is not a completed general RRT implementation.

Endpoints use the index's original `sign_frames`, which are geometric hints rather than approved semantic cores. Historical MEDICINE/NIGHT/HURT/NURSE/INTERPRETER overrides are migrated into a hash-bound research comparison list with pending approval and are not selected by the scan. The word audit includes NURSE f80's 8/79 trim and the f81 comparison. A new motion version cannot inherit an old exception.

Each run contains:

| File | Content |
|---|---|
| `policy.json`, `library_manifest.json` | Policy snapshot, motion/model/environment/source hashes, 53 named joints and 12 coupling rules |
| `word_audit.json` | Format, times, limits, coupling, original collisions, endpoints and derivatives for every word; core/window review states |
| `pair_universe.json` | All ordered pairs, including 35 self-pairs |
| `checkpoints/*.json` | Atomically written per-pair records with content hashes |
| `trajectories/*.npz` | Complete two-occurrence candidates and connectors, preserving original word samples; no playback approval |
| `verification/*.json` | Independent artifact, original-slice, boundary, time/hash checks plus dense geometry and quality measurements |
| `pairs.jsonl`, `matrix.csv`, `summary.json` | Unique statuses, a 35×35 matrix, and separate all/non-self/self denominators |
| `manifest.json` | Frozen inputs, completion state, complete file inventory and SHA-256 hashes |

Temporary `.part` files are not checkpoints. Completed records survive interruption; damaged policies, records and trajectories are rejected. Resume does not automatically retry recorded ERROR/TIMEOUT outcomes or change budgets. A larger budget belongs in a new version. This delivery implements first attempts only and makes no retry-experiment claim.

Numerical hashes encode joint names as UTF-8 JSON and canonicalize time/position arrays into fixed-order little-endian float64 C arrays, including negative-zero normalization. They identify numerical content; NPZ SHA-256 verifies transfer integrity. Runtime measurements are excluded from numerical array hashes.

## Verification scope and status interpretation

The verifier does not invoke planning or import historical PASS decisions. It re-reads original motions and the saved two-word NPZ, checks both word occurrences and connector endpoints, then samples the declared quintic at 1×/2×/4× resolution with an additional maximum 0.04 rad step. Original words use linear interpolation between delivered samples and are also densified. Exactly matching word slices can reuse geometry independently measured within this verification run. Identical connector sample counts can share a query; each requested resolution reports its actual count.

Checks retain delivered collision geometry, native MuJoCo eligibility and the same-hand exclusion. Static structural gaps are separate. Final filtering review, continuous collision proof and clearance/curvature-driven adaptive subdivision are not implemented. Boundary derivatives use fixed five-frame one-sided quadratic least squares. Full-clip acceleration/jerk are finite-difference measurements at playback times, not continuous derivative certificates.

Original-word collisions and rate violations are reported separately and cannot be hidden by a clear connector. Original frames/times are unchanged. Unknown semantic cores keep `protected_core_preserved` null; `original_word_slices_preserved` only establishes that the retained slices were not modified.

All new candidates have `playback_eligible: false`; this development contract cannot emit PASS_SIM. Changing review strings to approved still cannot bypass the missing approved-core contract. FAILED_QUALITY may mean pending thresholds/windows, so inspect reason codes and the verification's `numerical_checks_passed`. FAILED_SEARCH means this fixed direct candidate or its dense check failed, not that no path exists. BLOCKED_ENDPOINT names source/target separately; SOURCE_NEAR cannot replace absolute +2 mm clearance.

Large raw results live in ignored `results/all_pairs/`. Reviewable summaries and actual test logs are saved separately in `results/group3_all_pairs_startup/`. A local path alone is not a cross-machine delivery package; T10 asset delivery and new-environment reproduction remain incomplete. Human, language and hardware reviews remain unvalidated.

The v1 calibration remains archived. The final v2 preserves `planning_evidence` separately from verification; its 11 additional dense failures are not hidden by overwriting playback-sample measurements. Use a new run_id for a new experiment, or resume the existing completed run.
