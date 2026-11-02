#!/bin/bash
# Waits for the parallel P1-3 drivers to end, then: final table and rechecks; P1-4 (cpu0) and the budget retry (cpu1)
# side by side. Each step keeps its own guards; nothing runs if P1-3 did not finish all 79 batches.
set -u
cd /home/kingderman/Documents/ME5412-github-latest
R=results/hospital35_protected_20261101_001
C=$R/commands
echo "== waiting $(date -Is)"
while pgrep -f '^[^ ]*python[^ ]* scripts/run_hospital35_batches\.py pairs --batch-manifest results/hospital35_protected_20261101_001/batches/manifest\.json' >/dev/null; do sleep 20; done
echo "== P1-3 drivers ended $(date -Is)"
.venv/bin/python $C/check_p1_3_finished.py || exit 4
bash $C/p1_3_final.sh > $R/P1-3_final.log 2>&1; echo "p1_3_final exit $?"
taskset -c 0 bash $C/p1_4.sh > $R/P1-4.log 2>&1 & p4=$!
taskset -c 1 bash $C/retry_budget.sh > $R/retry_budget_001.log 2>&1 & rt=$!
wait $p4; echo "p1_4 exit $? $(date -Is)"
wait $rt; echo "retry exit $? $(date -Is)"
echo "== end $(date -Is)"
