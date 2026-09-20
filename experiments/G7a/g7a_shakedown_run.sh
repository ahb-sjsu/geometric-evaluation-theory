#!/bin/bash
# G7a shakedown on the June 2026 prefix. Sample, then label on eight pinned
# cores, then the counts-only analysis. June is never an evaluation month.
set -u
cd /home/claude/g7a || exit 1
export G7A_PLAYER_KEY="$(cat /home/claude/.g7a_player_key)"
PY=/home/claude/env/bin/python3
SF=/home/claude/bin/sf/stockfish/stockfish-linux-x86-64-universal
URL=https://database.lichess.org/standard/lichess_db_standard_rated_2026-06.pgn.zst
LOG=/home/claude/g7a/shakedown.log
: > "$LOG"

echo "[sample] $(date -u +%H:%M:%S)" >> "$LOG"
curl -s -r 0-1073741823 "$URL" | zstd -dc 2>/dev/null \
  | taskset -c 0 nice -n 19 $PY g7a_sample.py --out todo_shakedown.jsonl \
      --quota bullet=1500,blitz=6000,rapid=1500,classical=1500 >> "$LOG" 2>&1
wc -l todo_shakedown.jsonl >> "$LOG"

echo "[label] $(date -u +%H:%M:%S)" >> "$LOG"
for i in 0 1 2 3 4 5 6 7; do
  taskset -c $i nice -n 19 $PY g7a_label.py --todo todo_shakedown.jsonl \
    --out labels_shakedown_$i.jsonl --engine "$SF" --nodes 50000 --shard $i --of 8 \
    > label_$i.log 2>&1 &
done
wait
tail -q -n 1 label_*.log >> "$LOG"

echo "[analyse] $(date -u +%H:%M:%S)" >> "$LOG"
taskset -c 0 nice -n 19 $PY g7a_shakedown.py --labels 'labels_shakedown_*.jsonl' \
  --out shakedown.json >> "$LOG" 2>&1
echo "SHAKEDOWN_EXIT $?" >> "$LOG"
