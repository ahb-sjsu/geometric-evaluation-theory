#!/bin/bash
# G3d sealed calibration block, Atlas GPU 1, 80 pairs per cell.
cd /home/claude/g3d_run/experiments/G3d
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
PY=/archive/kvbench/venv/bin/python
echo "=== $(date -u +%FT%TZ) start sealed calibration"
taskset -c 0-7 nice -n 10 $PY flip.py run --config flip_config.json --block calibration --out /home/claude/g3d_run/run || { echo RUN_CAL_EXIT=1; exit 1; }
$PY flip_grade.py predict /home/claude/g3d_run/run/calibration --config flip_config.json --out /home/claude/g3d_run/run/predictions.json
echo RUN_CAL_EXIT=0
