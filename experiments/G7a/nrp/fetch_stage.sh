#!/bin/bash
# Pull one stage's label shards back from the volume. Runs on Atlas.
#   fetch_stage.sh 2026-07 screen /home/claude/g7a/run_2026-07
set -eu
M="$1"; STAGE="$2"; W="$3"
NS=ssu-atlas-ai
kubectl get pod g7a-stage -n $NS >/dev/null 2>&1 || kubectl apply -n $NS -f /home/claude/g7a/nrp/g7a_stage_pod.yaml
kubectl wait -n $NS --for=condition=Ready pod/g7a-stage --timeout=900s
kubectl exec -n $NS g7a-stage -- sh -c "cd /data/$M && ls out_$STAGE/*.jsonl | wc -l && tar -cf /tmp/out.tar out_$STAGE/*.jsonl"
kubectl cp -n $NS g7a-stage:/tmp/out.tar /tmp/g7a_${M}_${STAGE}_out.tar
mkdir -p "$W/nrp_$STAGE" && tar -C "$W/nrp_$STAGE" -xf /tmp/g7a_${M}_${STAGE}_out.tar
ls "$W/nrp_$STAGE/out_$STAGE" | wc -l
cat "$W/nrp_$STAGE/out_$STAGE"/*.jsonl | wc -l
echo FETCHED
