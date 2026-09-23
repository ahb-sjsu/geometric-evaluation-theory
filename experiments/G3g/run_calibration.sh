#!/bin/bash
# G3g calibration. Every cell of the truncation ladder for both judges, one block at a time, so
# the gateway never sees more than the one registered concurrency of eight. The calibration seed
# is one number, so each cell scores the SAME reviews cut to a different length. Predictions are
# NOT written here; that is a separate step whose output is committed with its hash before any
# test seed exists.
set -u
cd /home/claude/gettheory/experiments/G3g
PY=/archive/kvbench/venv/bin/python
LOG=/home/claude/gettheory/experiments/G3g/calibration.log

echo "=== G3g calibration started $(date -u +%FT%TZ) ===" >> "$LOG"

$PY g3g_preflight.py --config g3g_config.json --block calibration >> "$LOG" 2>&1
if [ $? -ne 0 ]; then
  echo "G3G_CALIBRATION_REFUSED_BY_PREFLIGHT" >> "$LOG"
  exit 2
fi

for L in full 400 200; do
  for M in gemma31b gemma12b; do
    echo "--- trunc=$L $M $(date -u +%FT%TZ) ---" >> "$LOG"
    $PY g3g_judge.py run --config g3g_config.json --block calibration --model "$M" \
        --truncate "$L" --out run_record >> "$LOG" 2>&1
    rc=$?
    echo "--- trunc=$L $M exit=$rc $(date -u +%FT%TZ) ---" >> "$LOG"
    if [ $rc -ne 0 ]; then
      echo "G3G_CALIBRATION_FAILED trunc=$L $M rc=$rc" >> "$LOG"
      exit $rc
    fi
  done
done
echo "G3G_CALIBRATION_DONE $(date -u +%FT%TZ)" >> "$LOG"
