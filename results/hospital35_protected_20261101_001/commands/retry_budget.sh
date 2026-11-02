#!/bin/bash
# Retry after P1-3 (runs alongside P1-4; separate run, policy and outputs, no dependency): clear-word TIMEOUT pairs under the versioned retry-budget policy, in a new run, then the
# sequence cases they blocked. The P1-3 run, its failures and the P1-4 outputs are not touched.
# Refuses (exit 4) unless P1-3 has finished and its final table exists.
# Definitions are generated once from P1-3/progress_final.json and then reused (hash-bound). A pairs stop (exit 3)
# stops the script; rerunning resumes the same run. Graceful stop: touch $D/batch_control/hospital35_retry_budget_001.stop
set -u
cd /home/kingderman/Documents/ME5412-github-latest
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
R=results/hospital35_protected_20261101_001
D=$R/retry_budget_001
echo "== start $(date -Is)"
.venv/bin/python $R/commands/check_p1_3_finished.py || exit 4
[ -f $R/P1-3/progress_final.json ] || { echo "missing $R/P1-3/progress_final.json (run p1_3_final.sh); refusing"; exit 4; }
[ -f $D/definitions.json ] || .venv/bin/python $D/generate_retry_definitions.py $R/P1-3/progress_final.json || exit 4
get() { .venv/bin/python -c "import json, sys; d = json.load(open('$D/definitions.json')); v = eval(sys.argv[1], {}, {'d': d}); print(' '.join(v) if isinstance(v, list) else ('' if v is None else v))" "$1"; }
BATCHES=""
for b in $(get "d['retry_batches']"); do BATCHES="$BATCHES --batch $b"; done
.venv/bin/python scripts/run_hospital35_batches.py pairs --policy $(get "d['pair_policy']['path']") \
  --batch-manifest $(get "d['batch_manifest']['path']") --batch-manifest-sha256 $(get "d['batch_manifest']['sha256']") \
  $BATCHES --run-id $(get "d['run_id']") --results-root $D/pair_runs --control-dir $D/batch_control
code=$?; echo "pairs exit $code"
[ $code -eq 0 ] || { echo "== stopped $(date -Is)"; exit $code; }
RUN=$D/pair_runs/$(get "d['run_id']")
[ -e $D/selected_recheck ] || { .venv/bin/python scripts/run_hospital35_batches.py recheck-pairs --run-dir $RUN --output $D/selected_recheck; echo "recheck exit $?"; }
[ -e $D/progress.json ] || { .venv/bin/python $R/P1-3/scan_progress.py $RUN $(get "d['batch_manifest']['path']") $R/preflight_final/preflight.json $D/progress.json; echo "progress exit $?"; }
if [ -z "$(get "d['case_manifest']")" ]; then echo "no sequence cases in scope"; echo "== end $(date -Is)"; exit 0; fi
CASES="--sequence-policy $(get "d['sequence_policy']['path']") --case-manifest $(get "d['case_manifest']['path']") --case-manifest-sha256 $(get "d['case_manifest']['sha256']")"
completed() {
  .venv/bin/python -c "import glob, json, sys; logs = sorted(glob.glob(sys.argv[1] + '/invocation_*.json')); sys.exit(0 if logs and json.load(open(logs[-1]))['exit_code'] == 0 else 1)" "$D/batch_control/sequence_subbatches/$1"
}
for s in $(get "d['case_manifest']['subbatches']"); do
  if completed $s; then echo "subbatch $s already complete"; continue; fi
  .venv/bin/python scripts/run_hospital35_batches.py sequences $CASES --subbatch $s --control-dir $D/batch_control
  code=$?; echo "subbatch $s exit $code"
  [ $code -eq 0 ] || { echo "== stopped $(date -Is)"; exit $code; }
done
.venv/bin/python scripts/run_hospital35_batches.py aggregate $CASES
echo "aggregate exit $?"
for s in $(get "d['case_manifest']['subbatches']"); do
  out=$(ls -d $D/sequences_001/$s $D/sequences_001/${s}_resume_[0-9][0-9] 2>/dev/null | sort | tail -1)
  video=$D/videos_001/$(basename $out)
  if [ -e $video ]; then echo "render $(basename $out) already done"; continue; fi
  .venv/bin/python scripts/render_sequences.py --run-dir $out --output $video
  echo "render $(basename $out) exit $?"
done
echo "== end $(date -Is)"
