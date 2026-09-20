#!/bin/bash
# G3e: run one block for each judge in the order the registration fixes.
#   g3e_run.sh calibration
#   g3e_run.sh test
# Resumable: the response cache beside each block means a restart asks the service
# only for what it has not already asked.
set -u
BLOCK="$1"
cd /home/claude/gettheory/experiments/G3e || exit 1
PY=/home/claude/env/bin/python3
LOG=run_${BLOCK}.log
say() { echo "[$(date -u +%H:%M:%S)] $*" >> "$LOG"; }

say "start block=$BLOCK prereg=4c0b1cb1a4f3705e7700a237cd09c1715838e36a"
if ! $PY g3e_preflight.py --config g3e_config.json --block "$BLOCK" >> "$LOG" 2>&1; then
  say "PREFLIGHT REFUSED, nothing run"
  echo "G3E_${BLOCK}_REFUSED" >> "$LOG"
  exit 2
fi
for M in gemma31b gemma12b qwen3_27b; do
  if [ -s "run_record/$BLOCK/${M}__served/results.json" ]; then
    say "$M already done"
    continue
  fi
  say "$M begin"
  taskset -c 3 nice -n 19 $PY -u api_judge.py run --config g3e_config.json \
      --block "$BLOCK" --model "$M" --out run_record >> "$LOG" 2>&1
  say "$M exit=$?"
done
say "finished block=$BLOCK"
echo "G3E_${BLOCK}_DONE" >> "$LOG"
