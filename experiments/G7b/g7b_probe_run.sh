#!/bin/bash
# Engine-free count for the phase after G7a, one core, one month at a time.
# Usage: g7b_probe_run.sh 2026-08
set -u
M="$1"
cd /home/claude/g7a || exit 1
export G7A_PLAYER_KEY="$(cat /home/claude/.g7a_player_key)"
SRC=/archive/ahb-sjsu/lichess/lichess_db_standard_rated_${M}.pgn.zst
zstd -dc "$SRC" \
  | LC_ALL=C grep -E '^\[(Event|White|Black|TimeControl|WhiteElo|BlackElo|Termination|WhiteTitle|BlackTitle) |^1\. ' \
  | taskset -c 1 nice -n 19 /home/claude/env/bin/python3 -u g7b_probe.py "g7b_probe_${M}.json" > "g7b_probe_${M}.log" 2>&1
echo "G7B_PROBE_EXIT $?" >> "g7b_probe_${M}.log"
