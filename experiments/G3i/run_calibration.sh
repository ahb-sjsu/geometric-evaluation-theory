#!/bin/bash
# G3i calibration block for Gemma 3 12B on GPU 1. Waits until the card is free (nothing else
# resident on it) rather than sharing it, since the judge needs the whole card, and never
# touches another process. The registered run; the seal precedes it.
set -u
export CUDA_VISIBLE_DEVICES=1
PY=/archive/kvbench/venv/bin/python
G3D=/home/claude/g3d_run/experiments/G3d
CFG=/home/claude/g3d_run/experiments/G3i/flip_config_gemma12b.json
OUT=/home/claude/g3i_run/gemma12b
LOG=/home/claude/g3i_cal_gemma12b.log

echo "=== G3i calibration script started $(date -u +%FT%TZ) ===" >> "$LOG"
while true; do
  used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i 1 | tr -d ' ')
  if [ "${used:-99999}" -lt 2000 ]; then break; fi
  sleep 60
done
echo "--- GPU 1 free, calibration $(date -u +%FT%TZ) ---" >> "$LOG"
( cd "$G3D" && taskset -c 0-7 nice -n 10 $PY flip.py run --config "$CFG" --block calibration --out "$OUT" ) >> "$LOG" 2>&1
rc=$?
echo "--- calibration exit=$rc $(date -u +%FT%TZ) ---" >> "$LOG"
[ $rc -eq 0 ] && echo G3I_CAL_DONE >> "$LOG" || echo G3I_CAL_FAILED >> "$LOG"
