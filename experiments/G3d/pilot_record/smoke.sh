#!/bin/bash
# G3d smoke test: throughput at budgets 0 and 1024, 4 pairs per cell, after the 14B sizing run frees GPU 1.
cd /home/claude/g3d_run/experiments/G3d
while ! grep -q MEASURE14_EXIT /home/claude/g3c/measure14/measure14.log 2>/dev/null; do sleep 60; done
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
taskset -c 0-7 nice -n 10 /archive/kvbench/venv/bin/python flip.py run --config flip_config.json --block calibration --out /home/claude/g3d_run/smoke --role smoke --n-pairs 4 --budgets 0,1024
echo SMOKE_EXIT=$?
