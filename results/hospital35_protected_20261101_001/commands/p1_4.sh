#!/bin/bash
# P1-4: the 14 frozen sequence sub-batches in order, the fixed-denominator aggregate, then videos of the cases that pass.
# Refuses (exit 4) unless P1-3 has finished: the pair run must not be read for sequence planning while it is still written.
# Stops at the first sub-batch that does not exit 0 (3 = budget or stop file, 4 = refused). Rerunning skips sub-batches whose
# latest log exited 0 and resumes the rest into <output>_resume_NN. Graceful stop: touch $R/batch_control/sequences.stop
# (delete it before resuming).
set -u
cd /home/kingderman/Documents/ME5412-github-latest
export PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
R=results/hospital35_protected_20261101_001
CASES="--sequence-policy config/sequence_policy_hospital35_v1.json --case-manifest $R/sequence_cases/case_manifest.json --case-manifest-sha256 3e453cfdb89281a2258db7b3719c8d18b9f261bab8d88d4872837d2457bbe8ab"
completed() {
  .venv/bin/python -c "import glob, json, sys; logs = sorted(glob.glob(sys.argv[1] + '/invocation_*.json')); sys.exit(0 if logs and json.load(open(logs[-1]))['exit_code'] == 0 else 1)" "$R/batch_control/sequence_subbatches/$1"
}
echo "== start $(date -Is)"
.venv/bin/python $R/commands/check_p1_3_finished.py || exit 4
for s in $(seq -f 's%03g' 1 14); do
  if completed $s; then echo "subbatch $s already complete"; continue; fi
  .venv/bin/python scripts/run_hospital35_batches.py sequences $CASES --subbatch $s --control-dir $R/batch_control
  code=$?; echo "subbatch $s exit $code"
  [ $code -eq 0 ] || { echo "== stopped $(date -Is)"; exit $code; }
done
.venv/bin/python scripts/run_hospital35_batches.py aggregate $CASES
echo "aggregate exit $?"
for s in $(seq -f 's%03g' 1 14); do
  out=$(ls -d $R/sequences_full_001/$s $R/sequences_full_001/${s}_resume_[0-9][0-9] 2>/dev/null | sort | tail -1)
  video=$R/videos_full_001/$(basename $out)
  if [ -e $video ]; then echo "render $(basename $out) already done"; continue; fi
  .venv/bin/python scripts/render_sequences.py --run-dir $out --output $video
  echo "render $(basename $out) exit $?"
done
echo "== end $(date -Is)"
