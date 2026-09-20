#!/bin/bash
# Stream the first 1.5 GB of the shakedown month through the probe. The zstd
# stream is cut mid-frame on purpose, so its trailing error is expected and is
# discarded; everything before the cut decodes normally.
URL=https://database.lichess.org/standard/lichess_db_standard_rated_2026-06.pgn.zst
cd /home/claude
curl -s -r 0-1610612735 "$URL" \
  | zstd -dc 2>/dev/null \
  | taskset -c 0-3 nice -n 19 /home/claude/env/bin/python3 -u g7a_probe.py > /home/claude/g7a_probe.log 2>&1
echo "PROBE_EXIT $?" >> /home/claude/g7a_probe.log
