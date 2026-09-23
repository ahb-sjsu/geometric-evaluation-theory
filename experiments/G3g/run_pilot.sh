#!/bin/bash
# G3g pilot. One judge, both blocks, on the pilot seeds. Its purpose is to fix the one bar that
# was never a transferred null quantile, vacuity_bits_min, and to supply the population the
# design-matched null simulation draws its replicates from. It grades nothing.
set -u
cd /home/claude/gettheory/experiments/G3g
PY=/archive/kvbench/venv/bin/python
LOG=/home/claude/gettheory/experiments/G3g/pilot.log
M=gemma31b

echo "=== G3g pilot started $(date -u +%FT%TZ) ===" >> "$LOG"
for B in calibration test; do
  echo "--- $B $(date -u +%FT%TZ) ---" >> "$LOG"
  $PY g3g_judge.py run --config g3g_config.json --block "$B" --model "$M" \
      --role pilot --out pilot_record/pilot >> "$LOG" 2>&1
  rc=$?
  echo "--- $B exit=$rc $(date -u +%FT%TZ) ---" >> "$LOG"
  if [ $rc -ne 0 ]; then
    echo "G3G_PILOT_FAILED $B rc=$rc" >> "$LOG"
    exit $rc
  fi
done
echo "G3G_PILOT_DONE $(date -u +%FT%TZ)" >> "$LOG"
