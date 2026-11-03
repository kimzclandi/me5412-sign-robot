#!/bin/bash
# Round 9 of the user's nine hospital sentences: YOU HURT WHERE alone, HURT protected from frame 37 (see make_inputs.py).
# 1. two pair runs in parallel (same identity, one writer each, cpu0-1), one sentence batch each
# 2. fresh independent recheck of every selected candidate, per run
# 3. plan the rest tail after WHERE, assemble and verify the sentence
# Videos are rendered separately (export_render_inputs.py, then render_gpu_windows.py on Windows; not committed).
# Rerunning resumes: completed pairs are skipped; an existing output step is skipped.
# Graceful stop of step 1: touch $D/batch_control/hospital_sentences_20261102_009_NN.stop
set -u
cd /home/kingderman/Documents/ME5412-github-latest
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
D=results/hospital_sentences_20261102_009
POLICY=config/transition_policy_hospital_sentences_fast_v6.json
SEQ=config/sequence_policy_hospital_sentences_v8.json
M=$D/batches/manifest.json
P=.venv/bin/python
WORKERS=2
echo "== start $(date -Is)"
if pgrep -f "scripts/run_hospital35_batches\.py pairs .*--results-root $D/" >/dev/null; then echo "a round-9 driver is running; refusing"; exit 4; fi
pids=()
for w in $(seq 0 $((WORKERS - 1))); do
  n=$(printf %02d $((w + 1)))
  run=hospital_sentences_20261102_009_$n
  rm -f $D/batch_control/$run.stop
  taskset -c $w $P scripts/run_hospital35_batches.py pairs --policy $POLICY --batch-manifest $M \
    --batch-manifest-sha256 $(sha256sum $M | cut -d' ' -f1) --batch sentences_0$n \
    --run-id $run --results-root $D/pair_runs --control-dir $D/batch_control >> $D/pairs_$run.log 2>&1 &
  pids+=($!); echo "worker $w $run cpu$w pid $!"
done
status=0
for i in "${!pids[@]}"; do wait ${pids[$i]}; code=$?; echo "worker $i exit $code $(date -Is)"; [ $code -eq 0 ] || status=$code; done
[ $status -eq 0 ] || { echo "== pairs incomplete (status $status) $(date -Is); rerun to resume"; exit $status; }
RUNS=""
for w in $(seq 1 $WORKERS); do
  n=$(printf %02d $w)
  run=$D/pair_runs/hospital_sentences_20261102_009_$n
  RUNS="$RUNS --pair-run-dir $run"
  [ -e $D/selected_recheck_$n ] || { taskset -c $((w - 1)) $P scripts/run_hospital35_batches.py recheck-pairs --run-dir $run \
    --output $D/selected_recheck_$n > $D/selected_recheck_$n.log 2>&1; echo "recheck $n exit $?"; } &
done
wait
if [ ! -e $D/sequences ]; then
  $P scripts/plan_sequences.py --sequence-policy $SEQ $RUNS --output $D/sequences --case-budget-s 900 --tail-workers 1
  echo "plan_sequences exit $?"
  $P scripts/verify_sequences.py --run-dir $D/sequences > $D/verify_sequences.log 2>&1
  echo "verify_sequences exit $?"
fi
echo "== end $(date -Is)"
