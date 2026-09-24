#!/bin/bash
# Submit the G3i block to one 32 GB-or-larger GPU pool after another until one schedules.
# A pending job holds no GPU and no node, so trying pools in turn costs the cluster nothing;
# each attempt goes through the submitter's preflight and the bursting controller.
#   ./run_any.sh calibration
set -u
export KUBECONFIG=/home/claude/.kube/config
BLOCK=${1:-calibration}
NS=ssu-atlas-ai
JOB="g3i-run-${BLOCK:0:3}-gemma12b"
LOG=/home/claude/g3i_nrp_${BLOCK}.log
cd /home/claude/gettheory/experiments/G3i/nrp
echo "=== run_any $BLOCK $(date -u +%FT%TZ) ===" >> "$LOG"
for P in NVIDIA-L40 NVIDIA-RTX-A6000 NVIDIA-A40 NVIDIA-L40S Tesla-V100-SXM2-32GB; do
  kubectl -n $NS delete job "$JOB" --ignore-not-found >> "$LOG" 2>&1
  for i in 1 2 3 4 5 6; do   # a deleted job's pod can take a while to go
    n=$(kubectl -n $NS get pods -l atlas.io/batch=g3i-flip --no-headers 2>/dev/null | wc -l)
    [ "$n" = "0" ] && break
    kubectl -n $NS wait --for=delete pod -l atlas.io/batch=g3i-flip --timeout=30s >> "$LOG" 2>&1
  done
  echo "--- trying $P $(date -u +%FT%TZ) ---" >> "$LOG"
  python3 submit.py run --block "$BLOCK" --product "$P" --no-wait >> "$LOG" 2>&1 || { echo "submit failed on $P" >> "$LOG"; continue; }
  for i in $(seq 1 16); do   # up to four minutes to schedule
    phase=$(kubectl -n $NS get pods -l atlas.io/batch=g3i-flip -o jsonpath='{.items[0].status.phase}' 2>/dev/null)
    node=$(kubectl -n $NS get pods -l atlas.io/batch=g3i-flip -o jsonpath='{.items[0].spec.nodeName}' 2>/dev/null)
    if [ "$phase" = "Running" ] || [ -n "$node" ]; then
      echo "SCHEDULED on $P node=$node phase=$phase $(date -u +%FT%TZ)" >> "$LOG"
      # follow the job to its end
      while true; do
        s=$(kubectl -n $NS get job "$JOB" -o jsonpath='{.status.succeeded},{.status.failed}' 2>/dev/null)
        case "$s" in 1,*) echo "G3I_NRP_${BLOCK}_DONE $(date -u +%FT%TZ)" >> "$LOG"; exit 0;; *,[1-9]*) echo "G3I_NRP_${BLOCK}_FAILED $(date -u +%FT%TZ)" >> "$LOG"; exit 1;; esac
        kubectl -n $NS logs "job/$JOB" --tail=1 2>/dev/null | grep '^{' >> "$LOG.progress" 2>/dev/null
        kubectl -n $NS wait --for=condition=complete "job/$JOB" --timeout=300s >/dev/null 2>&1
      done
    fi
    kubectl -n $NS wait --for=condition=Ready pod -l atlas.io/batch=g3i-flip --timeout=15s >/dev/null 2>&1
  done
  echo "no node on $P after four minutes" >> "$LOG"
done
echo "G3I_NRP_${BLOCK}_UNSCHEDULED $(date -u +%FT%TZ)" >> "$LOG"
exit 2
