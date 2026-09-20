#!/bin/bash
# Shard one stage's positions and push them to the volume. Runs on Atlas.
#   stage_month.sh 2026-07 screen /home/claude/g7a/run_2026-07/todo.jsonl 96
set -eu
M="$1"; STAGE="$2"; TODO="$3"; N="$4"
NS=ssu-atlas-ai
kubectl get pod g7a-stage -n $NS >/dev/null 2>&1 || kubectl apply -n $NS -f /home/claude/g7a/nrp/g7a_stage_pod.yaml
kubectl wait -n $NS --for=condition=Ready pod/g7a-stage --timeout=900s
S=/tmp/g7a_${M}_${STAGE} && rm -rf $S && mkdir -p $S/$M/todo_$STAGE
# Round-robin sharding so every shard sees every part of the month.
awk -v n=$N -v d="$S/$M/todo_$STAGE" '{ f=sprintf("%s/shard_%04d.jsonl", d, (NR-1)%n); print > f }' "$TODO"
ls $S/$M/todo_$STAGE | wc -l
tar -C $S -cf /tmp/g7a_${M}_${STAGE}.tar .
ls -la /tmp/g7a_${M}_${STAGE}.tar | awk '{print "tar bytes", $5}'
kubectl cp -n $NS /tmp/g7a_${M}_${STAGE}.tar g7a-stage:/tmp/in.tar
kubectl exec -n $NS g7a-stage -- sh -c "tar -C /data -xf /tmp/in.tar && rm /tmp/in.tar && ls /data/$M/todo_$STAGE | wc -l"
echo STAGED
