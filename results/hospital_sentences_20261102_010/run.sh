#!/bin/bash
# Round 10 of the user's nine hospital sentences: round 8's planner on clips-v2 with protection bundle v5 (make_inputs.py).
# 1. twelve pair runs in parallel (same identity, one writer each, cpu0-11)
# 2. fresh independent recheck of every selected candidate, per run
# 3. plan one rest tail per last word (7 processes), assemble and verify the seven multi-word sentences
# 4. one render process per passing sentence (render_sequences.py, cpu0-11 shared)
# Rerunning resumes: completed pairs are skipped; an existing output step is skipped.
# Graceful stop of step 1: touch $D/batch_control/hospital_sentences_20261102_010_NN.stop
set -u
cd "$(dirname "$0")/../.."
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
D=results/hospital_sentences_20261102_010
POLICY=config/transition_policy_hospital_sentences_fast_v7.json
SEQ=config/sequence_policy_hospital_sentences_v9.json
M=$D/batches/manifest.json
P=.venv/bin/python
WORKERS=12
echo "== start $(date -Is)"
if pgrep -f "scripts/run_hospital35_batches\.py pairs .*--results-root $D/" >/dev/null; then echo "a round-10 driver is running; refusing"; exit 4; fi
pids=()
for w in $(seq 0 $((WORKERS - 1))); do
  n=$(printf %02d $((w + 1)))
  run=hospital_sentences_20261102_010_$n
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
  run=$D/pair_runs/hospital_sentences_20261102_010_$n
  RUNS="$RUNS --pair-run-dir $run"
  [ -e $D/selected_recheck_$n ] || { taskset -c $((w - 1)) $P scripts/run_hospital35_batches.py recheck-pairs --run-dir $run \
    --output $D/selected_recheck_$n > $D/selected_recheck_$n.log 2>&1; echo "recheck $n exit $?"; } &
done
wait
if [ ! -e $D/sequences ]; then
  taskset -c 0-$((WORKERS - 1)) $P scripts/plan_sequences.py --sequence-policy $SEQ $RUNS --output $D/sequences \
    --case-budget-s 900 --tail-workers 7
  echo "plan_sequences exit $? $(date -Is)"
  $P scripts/verify_sequences.py --run-dir $D/sequences > $D/verify_sequences.log 2>&1
  echo "verify_sequences exit $?"
fi
CASES=($($P -c 'import json, sys; print(" ".join(c["sequence_id"] for c in json.load(open(sys.argv[1]))["cases"] if c.get("selected_attempt")))' $D/sequences/summary.json))
pids=()
for k in "${!CASES[@]}"; do
  [ -e $D/videos_${CASES[$k]} ] && continue
  taskset -c $(( (k * 12 / ${#CASES[@]}) ))-$(( ((k + 1) * 12 / ${#CASES[@]}) - 1 )) $P scripts/render_sequences.py \
    --run-dir $D/sequences --output $D/videos_${CASES[$k]} --case ${CASES[$k]} >> $D/render.log 2>&1 &
  pids+=($!)
done
for i in "${!pids[@]}"; do wait ${pids[$i]}; echo "render $i exit $?"; done
$P -c 'import json, sys; s = json.load(open(sys.argv[1])); print("status", s["status_counts"]); [print(" ", c["sequence_id"], c.get("status")) for c in s["cases"]]' $D/sequences/summary.json
echo "== end $(date -Is)"
