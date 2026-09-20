#!/bin/bash
# Header-only cohort counts on the two evaluation months, from the local torrent
# copies. No move is parsed and no engine runs. grep does the line filtering at
# C speed so Python only sees the tags it needs and one line per game.
set -u
cd /home/claude/g7a || exit 1
export G7A_PLAYER_KEY="$(cat /home/claude/.g7a_player_key)"
PY=/home/claude/env/bin/python3
SRC=/archive/ahb-sjsu/lichess
mkdir -p /home/claude/g7a/private
core=8
for m in 2026-07 2026-08; do
  (
    sha256sum "$SRC/lichess_db_standard_rated_${m}.pgn.zst" > "cohort_${m}.sha256"
    zstd -dc "$SRC/lichess_db_standard_rated_${m}.pgn.zst" \
      | LC_ALL=C grep -E '^\[(White|Black|TimeControl|WhiteElo|BlackElo|Termination|WhiteTitle|BlackTitle) |^1\. ' \
      | taskset -c $core nice -n 19 $PY g7a_cohort_probe.py "cohort_${m}.json" "private/cohort_${m}.pkl" \
      > "cohort_${m}.log" 2>&1
    echo "COHORT_EXIT $?" >> "cohort_${m}.log"
  ) &
  core=$((core+1))
done
wait
