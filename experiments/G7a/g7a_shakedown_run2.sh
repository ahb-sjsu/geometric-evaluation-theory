#!/bin/bash
# G7a shakedown, second pass. The sample from the first pass is reused unchanged,
# since sampling never depended on the engine. Relabel it with raw scores at
# 50k nodes, relabel a slice of the same positions at 200k nodes for the engine
# sensitivity check, then the counts-only analysis.
set -u
cd /home/claude/g7a || exit 1
PY=/home/claude/env/bin/python3
SF=/home/claude/bin/sf/stockfish/stockfish-linux-x86-64-universal
LOG=/home/claude/g7a/shakedown2.log
: > "$LOG"
rm -f labels_raw_*.jsonl labels_deep_*.jsonl

echo "[label 50k] $(date -u +%H:%M:%S)" >> "$LOG"
for i in 0 1 2 3 4 5 6 7; do
  taskset -c $i nice -n 19 $PY g7a_label.py --todo todo_shakedown.jsonl \
    --out labels_raw_$i.jsonl --engine "$SF" --nodes 50000 --shard $i --of 8 > lraw_$i.log 2>&1 &
done
wait

echo "[label 200k slice] $(date -u +%H:%M:%S)" >> "$LOG"
for i in 0 1 2 3 4 5 6 7; do
  taskset -c $i nice -n 19 $PY g7a_label.py --todo todo_shakedown.jsonl \
    --out labels_deep_$i.jsonl --engine "$SF" --nodes 200000 --shard $i --of 8 --limit 400 > ldeep_$i.log 2>&1 &
done
wait

echo "[analyse] $(date -u +%H:%M:%S)" >> "$LOG"
taskset -c 0 nice -n 19 $PY g7a_shakedown.py --labels 'labels_raw_*.jsonl' \
  --labels-deep 'labels_deep_*.jsonl' --out shakedown2.json >> "$LOG" 2>&1
echo "SHAKEDOWN2_EXIT $?" >> "$LOG"
