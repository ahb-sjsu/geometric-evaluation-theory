#!/bin/bash
# Four null workers of 250 replicates each, one core apiece on socket 1, BLAS at one thread.
cd /home/claude/g3c/nullbars
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
PY=/archive/kvbench/venv/bin/python
i=0
for s in 20260921 20260922 20260923 20260924; do
  taskset -c $((12+i)) nice -n 10 $PY null_bars.py --config prereg_config.json --pilot /home/claude/g3c/pilot --reps 250 --seed $s --rows-out rows_$s.json > log_$s.txt 2>&1 &
  i=$((i+1))
done
wait
echo NULLBARS_DONE
