#!/bin/bash
# G3f test block. Gated on the preflight, which refuses while no test seed exists, so this script
# cannot be started early by accident. Judges run one after another so the gateway never sees more
# than the one registered concurrency of eight.
set -u
cd /home/claude/gettheory/experiments/G3f
PY=/archive/kvbench/venv/bin/python
LOG=/home/claude/gettheory/experiments/G3f/test.log

echo "=== G3f test started $(date -u +%FT%TZ) ===" >> "$LOG"

# The guard is the first thing that runs and a refusal stops everything.
$PY g3f_preflight.py --config g3f_config.json --block test >> "$LOG" 2>&1
if [ $? -ne 0 ]; then
  echo "G3F_TEST_REFUSED_BY_PREFLIGHT" >> "$LOG"
  exit 2
fi

for M in gemma31b gemma12b qwen3_flash; do
  echo "--- $M $(date -u +%FT%TZ) ---" >> "$LOG"
  $PY g3f_judge.py run --config g3f_config.json --block test --model "$M" --out run_record >> "$LOG" 2>&1
  rc=$?
  echo "--- $M exit=$rc $(date -u +%FT%TZ) ---" >> "$LOG"
  if [ $rc -ne 0 ]; then
    echo "G3F_TEST_FAILED $M rc=$rc" >> "$LOG"
    exit $rc
  fi
done
echo "G3F_TEST_DONE $(date -u +%FT%TZ)" >> "$LOG"
