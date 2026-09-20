#!/bin/bash
# G3d pilot, pilot seeds, full design, Atlas GPU 1, after the G3c load tests free the card.
cd /home/claude/g3d_run/experiments/G3d
true
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
PY=/archive/kvbench/venv/bin/python
for b in calibration test; do
  echo "=== $(date -u +%FT%TZ) start $b"
  taskset -c 0-7 nice -n 10 $PY flip.py run --config flip_config.json --block $b --out /home/claude/g3d_run/pilot --role pilot || { echo PILOT_EXIT=1; exit 1; }
done
$PY flip_grade.py predict /home/claude/g3d_run/pilot/calibration --config flip_config.json --out /home/claude/g3d_run/pilot/predictions.json
$PY flip_grade.py grade /home/claude/g3d_run/pilot/test --config flip_config.json --predictions /home/claude/g3d_run/pilot/predictions.json --out /home/claude/g3d_run/pilot/pilot_grade.json
echo PILOT_EXIT=0
