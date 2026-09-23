#!/bin/bash
# G3g test blocks. Gated on the preflight, which refuses while no test seed exists, so this script
# cannot be started early by accident. One seed, so every cell scores the same pairs at a different
# length. Judges and cells run one after another at the registered concurrency.
set -u
cd /home/claude/gettheory/experiments/G3g
PY=/archive/kvbench/venv/bin/python
LOG=/home/claude/gettheory/experiments/G3g/test.log

echo "=== G3g test started $(date -u +%FT%TZ) ===" >> "$LOG"

$PY g3g_preflight.py --config g3g_config.json --block test >> "$LOG" 2>&1
if [ $? -ne 0 ]; then
  echo "G3G_TEST_REFUSED_BY_PREFLIGHT" >> "$LOG"
  exit 2
fi

for L in full 400 200; do
  for M in gemma31b gemma12b; do
    echo "--- trunc=$L $M $(date -u +%FT%TZ) ---" >> "$LOG"
    $PY g3g_judge.py run --config g3g_config.json --block test --model "$M" \
        --truncate "$L" --out run_record >> "$LOG" 2>&1
    rc=$?
    echo "--- trunc=$L $M exit=$rc $(date -u +%FT%TZ) ---" >> "$LOG"
    if [ $rc -ne 0 ]; then
      echo "G3G_TEST_FAILED trunc=$L $M rc=$rc" >> "$LOG"
      exit $rc
    fi
  done
done
echo "G3G_TEST_DONE $(date -u +%FT%TZ)" >> "$LOG"
