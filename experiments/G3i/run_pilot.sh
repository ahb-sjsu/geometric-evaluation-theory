#!/bin/bash
# G3i smoke tests and pilots, unattended, on GPU 1. Waits for the weight downloads to finish,
# then for each judge: a smoke test of four pairs at budgets 0 and 96 (grades nothing), then the
# pilot calibration and test blocks at the pilot seeds. Nothing here is a registered run: the
# registered blocks start only after PREREG-G3I.md is sealed with these records inside it.
set -u
export CUDA_VISIBLE_DEVICES=1
PY=/archive/kvbench/venv/bin/python
G3D=/home/claude/g3d_run/experiments/G3d
G3I=/home/claude/g3d_run/experiments/G3i
LOG=/home/claude/g3i_pilot.log
OUT=/home/claude/g3i_run
mkdir -p "$OUT"

echo "=== G3i pilot script started $(date -u +%FT%TZ) ===" >> "$LOG"
while screen -ls 2>/dev/null | grep -q hfdl; do sleep 30; done
echo "--- downloads finished $(date -u +%FT%TZ) ---" >> "$LOG"

run_block() {  # $1 = key, $2 = config path, $3 = block, $4 = out dir, $5 = label
  echo "--- $1 $5 $3 $(date -u +%FT%TZ) ---" >> "$LOG"
  ( cd "$G3D" && taskset -c 0-7 nice -n 10 $PY flip.py run --config "$2" --block "$3" --role pilot --out "$4" ) >> "$LOG" 2>&1
  rc=$?
  echo "--- $1 $5 $3 exit=$rc $(date -u +%FT%TZ) ---" >> "$LOG"
  if [ $rc -ne 0 ]; then echo "G3I_PILOT_FAILED $1 $5 $3 rc=$rc" >> "$LOG"; exit $rc; fi
}

for K in llama8b gemma12b; do
  CFG="$G3I/flip_config_$K.json"
  SMOKE="$G3I/smoke_config_$K.json"
  $PY - "$CFG" "$SMOKE" <<'EOF'
import json, sys
c = json.load(open(sys.argv[1]))
c["n_pairs"] = 4
c["budgets"] = [0, 96]
c["status"] = "SMOKE TEST: four pairs at two budgets, grades nothing"
json.dump(c, open(sys.argv[2], "w"), indent=1)
EOF
  run_block "$K" "$SMOKE" calibration "/home/claude/g3i_smoke/$K" smoke
  run_block "$K" "$CFG" calibration "$OUT/pilot_$K" pilot
  run_block "$K" "$CFG" test "$OUT/pilot_$K" pilot
done
echo "G3I_PILOT_DONE $(date -u +%FT%TZ)" >> "$LOG"
