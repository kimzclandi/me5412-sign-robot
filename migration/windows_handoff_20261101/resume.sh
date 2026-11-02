#!/bin/bash
# Resume after a crash or migration: the 4 parallel P1-3 runs (completed batches are skipped, partition reused), then the
# chain (final table + rechecks, then P1-4 and the budget retry side by side). Logs go to results/.../*.log.
set -u
cd /home/kingderman/Documents/ME5412-github-latest
R=results/hospital35_protected_20261101_001
C=$R/commands
if pgrep -f 'scripts/run_hospital35_batches\.py' >/dev/null; then echo "a driver is already running; refusing"; exit 4; fi
if [ -f "$HOME/.me5412_handed_off_to_windows" ]; then cat "$HOME/.me5412_handed_off_to_windows"; echo "refusing (source machine retired)"; exit 4; fi
rm -f $R/batch_control/hospital35_protected_20261101_00[1-4].stop
nohup bash $C/p1_3_parallel.sh >> $R/P1-3_parallel.log 2>&1 &
for i in $(seq 1 60); do pgrep -f '^[^ ]*python[^ ]* scripts/run_hospital35_batches\.py pairs' >/dev/null && break; sleep 2; done
pgrep -fc '^[^ ]*python[^ ]* scripts/run_hospital35_batches\.py pairs' | sed 's/^/drivers running: /'
nohup bash $C/after_p1_3.sh >> $R/after_p1_3.log 2>&1 &
echo "chain waiting (pid $!); progress: tail -f $R/P1-3_parallel_*.log $R/after_p1_3.log"
