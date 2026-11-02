#!/bin/bash
# The user's nine hospital sentences under the connector-only v4 scope (2026-11-01; see make_inputs.py).
# 1. four pair runs in parallel (same identity, one writer each, cpu0-3), one sentence batch each
# 2. fresh independent recheck of every selected candidate, per run
# 3. assemble and verify the seven multi-word sentences from the four runs; 4. videos
# Rerunning resumes: completed pairs are skipped; an existing output step is skipped.
# Graceful stop of step 1: touch $D/batch_control/hospital_sentences_20261101_00N.stop
set -u
cd /home/kingderman/Documents/ME5412-github-latest
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
D=results/hospital_sentences_20261101_001
POLICY=config/transition_policy_hospital_sentences_connector_only_v1.json
SEQ=config/sequence_policy_hospital_sentences_v1.json
M=$D/batches/manifest.json
P=.venv/bin/python
echo "== start $(date -Is)"
if pgrep -f "scripts/run_hospital35_batches\.py pairs .*--results-root $D/" >/dev/null; then echo "a sentence driver is running; refusing"; exit 4; fi
pids=()
for w in 0 1 2 3; do
  run=hospital_sentences_20261101_00$((w + 1))
  rm -f $D/batch_control/$run.stop
  taskset -c $w $P scripts/run_hospital35_batches.py pairs --policy $POLICY --batch-manifest $M \
    --batch-manifest-sha256 $(sha256sum $M | cut -d' ' -f1) --batch sentences_00$((w + 1)) \
    --run-id $run --results-root $D/pair_runs --control-dir $D/batch_control >> $D/pairs_$run.log 2>&1 &
  pids+=($!); echo "worker $w $run cpu$w pid $!"
done
status=0
for i in 0 1 2 3; do wait ${pids[$i]}; code=$?; echo "worker $i exit $code $(date -Is)"; [ $code -eq 0 ] || status=$code; done
[ $status -eq 0 ] || { echo "== pairs incomplete (status $status) $(date -Is); rerun to resume"; exit $status; }
RUNS=""
for n in 1 2 3 4; do
  run=$D/pair_runs/hospital_sentences_20261101_00$n
  RUNS="$RUNS --pair-run-dir $run"
  [ -e $D/selected_recheck_00$n ] || { $P scripts/run_hospital35_batches.py recheck-pairs --run-dir $run \
    --output $D/selected_recheck_00$n; echo "recheck 00$n exit $?"; }
done
if [ ! -e $D/sequences ]; then
  $P scripts/plan_sequences.py --sequence-policy $SEQ $RUNS --output $D/sequences --case-budget-s 900
  echo "plan_sequences exit $?"
  $P scripts/verify_sequences.py --run-dir $D/sequences > $D/verify_sequences.log 2>&1
  echo "verify_sequences exit $?"
fi
[ -e $D/videos ] || { $P scripts/render_sequences.py --run-dir $D/sequences --output $D/videos; echo "render exit $?"; }
echo "== end $(date -Is)"
