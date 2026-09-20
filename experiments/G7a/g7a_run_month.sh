#!/bin/bash
# G7a sealed run for one month, on Atlas. Usage: g7a_run_month.sh 2026-07
#
# Four stages, each resumable. A stage whose output exists is skipped, so an
# interruption costs the stage in flight and not the run.
#
#   sample   engine-free draw of positions for the eight arms
#   screen   Stockfish at 50,000 nodes on every position, raw scores kept
#   select   positions whose screen labels say they may be two-alternative
#   deep     Stockfish at 1,000,000 nodes on those, raw scores kept
#   grade    thresholds, ratios, exponent and bars, from the deep labels
#
# Twelve cores, pinned, lowest priority. The machine is shared.
set -u
M="$1"
cd /home/claude/g7a || exit 1
export G7A_PLAYER_KEY="$(cat /home/claude/.g7a_player_key)"
PY=/home/claude/env/bin/python3
SF=/home/claude/bin/sf/stockfish/stockfish-linux-x86-64-universal
SRC=/archive/ahb-sjsu/lichess/lichess_db_standard_rated_${M}.pgn.zst
W=/home/claude/g7a/run_${M}
NCORE=12
mkdir -p "$W"
LOG="$W/run.log"
say() { echo "[$1] $(date -u +%Y-%m-%dT%H:%M:%SZ) ${2:-}" >> "$LOG"; }

git_commit="$(cat /home/claude/g7a/CODE_COMMIT 2>/dev/null || echo unknown)"
say start "month=$M code=$git_commit"

if [ ! -s "$W/todo.jsonl" ]; then
  say sample
  zstd -dc "$SRC" | taskset -c 0 nice -n 19 $PY g7a_sample_cohort.py \
     --cohorts "private/cohort_${M}.pkl" --counts "cohort_${M}.json" --target 100000 \
     --out "$W/todo.tmp" > "$W/sample.log" 2>&1 && mv "$W/todo.tmp" "$W/todo.jsonl"
fi
say sampled "$(wc -l < "$W/todo.jsonl") positions"

if [ ! -s "$W/screen.done" ]; then
  say screen
  for i in $(seq 0 $((NCORE-1))); do
    taskset -c $i nice -n 19 $PY g7a_label.py --todo "$W/todo.jsonl" --out "$W/screen_$i.jsonl" \
       --engine "$SF" --nodes 50000 --shard $i --of $NCORE > "$W/screen_$i.log" 2>&1 &
  done
  wait
  touch "$W/screen.done"
fi
say screened "$(cat "$W"/screen_*.jsonl | wc -l) labelled"

if [ ! -s "$W/todo_deep.jsonl" ]; then
  say select
  taskset -c 0 nice -n 19 $PY g7a_select_deep.py --screen "$W/screen_*.jsonl" \
     --out "$W/todo_deep.jsonl" > "$W/select.log" 2>&1
fi
say selected "$(wc -l < "$W/todo_deep.jsonl") sent to deep"

if [ ! -s "$W/deep.done" ]; then
  say deep
  for i in $(seq 0 $((NCORE-1))); do
    taskset -c $i nice -n 19 $PY g7a_label.py --todo "$W/todo_deep.jsonl" --out "$W/deep_$i.jsonl" \
       --engine "$SF" --nodes 1000000 --shard $i --of $NCORE > "$W/deep_$i.log" 2>&1 &
  done
  wait
  touch "$W/deep.done"
fi
say deep_done "$(cat "$W"/deep_*.jsonl | wc -l) labelled"

say grade
taskset -c 0-3 nice -n 19 $PY g7a_grade.py --labels "$W/deep_*.jsonl" --screen "$W/screen_*.jsonl" \
   --out "$W/grade.json" > "$W/grade.log" 2>&1
say finished "exit=$?"
