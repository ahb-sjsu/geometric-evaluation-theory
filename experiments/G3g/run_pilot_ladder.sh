#!/bin/bash
# G3g pilot, the truncation ladder. One judge, both blocks at each input budget, on the pilot
# seeds. The full-length cell already ran; its record is moved under its cell name first. The
# L=100 calibration already ran too, so only its test block is added here. Nothing is graded.
# Its purposes: show thresholds ordered by input budget, and give each cell the population its
# design-matched null draws replicates from.
set -u
cd /home/claude/gettheory/experiments/G3g
PY=/archive/kvbench/venv/bin/python
LOG=/home/claude/gettheory/experiments/G3g/pilot_ladder.log
M=gemma31b

echo "=== G3g pilot ladder started $(date -u +%FT%TZ) ===" >> "$LOG"

# The full-length pilot predates the per-cell layout. Move it, never copy, so there is one record.
if [ -d pilot_record/pilot/calibration ] && [ ! -d pilot_record/pilot/full ]; then
  mkdir -p pilot_record/pilot/full
  mv pilot_record/pilot/calibration pilot_record/pilot/test pilot_record/pilot/full/
  echo "moved full-length pilot under pilot_record/pilot/full" >> "$LOG"
fi

run() {  # $1 = truncate, $2 = block
  echo "--- trunc=$1 $2 $(date -u +%FT%TZ) ---" >> "$LOG"
  $PY g3g_judge.py run --config g3g_config.json --block "$2" --model "$M" \
      --role pilot --truncate "$1" --out pilot_record/pilot >> "$LOG" 2>&1
  rc=$?
  echo "--- trunc=$1 $2 exit=$rc $(date -u +%FT%TZ) ---" >> "$LOG"
  [ $rc -ne 0 ] && { echo "G3G_LADDER_FAILED trunc=$1 $2 rc=$rc" >> "$LOG"; exit $rc; }
}

run 100 test
run 200 calibration
run 200 test
run 400 calibration
run 400 test
echo "G3G_LADDER_DONE $(date -u +%FT%TZ)" >> "$LOG"
