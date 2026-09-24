#!/bin/bash
# Keep rotating the GPU pools until the block schedules and finishes. run_any.sh exits 0 when the
# block is done, 1 when the job failed, 2 when no pool had a card in one pass. Only the last is
# retried, after a pause; a failed job is left for a person to read. Waits first for any earlier
# rotation screen to end, so one block never has two jobs in flight.
set -u
BLOCK=${1:-calibration}
cd /home/claude/gettheory/experiments/G3i/nrp
while screen -ls 2>/dev/null | grep -q '\.g3i_nrp_any\b'; do sleep 30; done
while true; do
  ./run_any.sh "$BLOCK"; rc=$?
  [ $rc -eq 2 ] || exit $rc
  sleep 300
done
