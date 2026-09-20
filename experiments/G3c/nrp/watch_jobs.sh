#!/bin/bash
# Atlas-side watcher for the sealed G3c jobs of one block. Every 2 minutes: record each running
# pod's GPU utilization (nvidia-smi inside the pod) and phase; delete a job whose GPU sits under
# the NRP floor of 40 percent for three samples in a row, so no pod idles on a GPU; when every job
# has finished, fetch the block's results to Atlas. Runs on Atlas, not in the cluster.
BLOCK=${1:?block}
NS=ssu-atlas-ai
K="kubectl -n $NS --request-timeout=60s"
LOG=/home/claude/g3c/nrp/watch_${BLOCK}.log
declare -A low
while true; do
  now=$(date -u +%FT%TZ)
  active=0
  for j in $($K get jobs -l app=g3c,atlas.io/role=$BLOCK -o name 2>/dev/null); do
    n=${j#job.batch/}
    jst=$($K get $j -o jsonpath='{.status.succeeded}/{.status.failed}/{.status.active}')
    pod=$($K get pods -l job-name=$n -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    phase=$($K get pod $pod -o jsonpath='{.status.phase}' 2>/dev/null)
    node=$($K get pod $pod -o jsonpath='{.spec.nodeName}' 2>/dev/null)
    util=""; gmem=""; age=""
    if [ "$phase" = "Running" ]; then
      util=$($K exec $pod -- nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null | head -1)
      gmem=$($K exec $pod -- nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1)
      # Loading a judge and quantizing its weights leaves the GPU idle for minutes, so a low sample
      # counts only after the pod has run ten minutes AND the weights are on the card (over 2 GiB).
      # The first version of this guard read every judge's log on the shared volume and deleted a
      # healthy 4-bit job that was still loading (2026-09-20 02:53 UTC).
      st=$($K get pod $pod -o jsonpath='{.status.startTime}' 2>/dev/null)
      age=$(( $(date -u +%s) - $(date -u -d "${st:-now}" +%s 2>/dev/null || date -u +%s) ))
      if [ -n "$util" ] && [ "${gmem:-0}" -gt 2000 ] && [ "$age" -gt 600 ] && [ "$util" -lt 40 ]; then
        low[$n]=$(( ${low[$n]:-0} + 1 ))
      else
        low[$n]=0
      fi
      if [ "${low[$n]:-0}" -ge 3 ]; then
        echo "$now $n GPU under 40 percent three samples running, deleting" >> $LOG
        $K logs $j > /home/claude/g3c/nrp/record_lowutil_$n.txt 2>&1
        $K delete $j >> $LOG 2>&1
      fi
    fi
    echo "$now $n status=$jst phase=$phase node=$node gpu=$util gmem=${gmem:-} age=${age:-} low=${low[$n]:-0}" >> $LOG
    case "$jst" in */*/1) active=1 ;; //) active=1 ;; esac
    [ "$phase" = "Pending" ] && active=1
  done
  if [ $active -eq 0 ]; then
    echo "$now all jobs finished" >> $LOG
    /usr/bin/python3 /home/claude/g3c/nrp/submit.py fetch --role run --block $BLOCK >> $LOG 2>&1
    echo "WATCH_DONE $BLOCK" >> $LOG
    exit 0
  fi
  sleep 120
done
