#!/bin/bash
# G3f calibration. Three judges, sequentially, so the gateway never sees more than the one
# registered concurrency of eight at a time. Predictions are NOT written here; that is a separate
# step whose output is committed with its hash before any test seed exists.
set -u
cd /home/claude/gettheory/experiments/G3f
PY=/archive/kvbench/venv/bin/python
LOG=/home/claude/gettheory/experiments/G3f/calibration.log

echo "=== G3f calibration started $(date -u +%FT%TZ) ===" >> "$LOG"
for M in gemma31b gemma12b qwen3_flash; do
  echo "--- $M $(date -u +%FT%TZ) ---" >> "$LOG"
  $PY g3f_judge.py run --config g3f_config.json --block calibration --model "$M" --out run_record >> "$LOG" 2>&1
  rc=$?
  echo "--- $M exit=$rc $(date -u +%FT%TZ) ---" >> "$LOG"
  if [ $rc -ne 0 ]; then
    echo "G3F_CALIBRATION_FAILED $M rc=$rc" >> "$LOG"
    exit $rc
  fi
done
echo "G3F_CALIBRATION_DONE $(date -u +%FT%TZ)" >> "$LOG"
