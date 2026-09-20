#!/bin/bash
# Create the volume, bring up the staging pod, and push the engine, the labeller
# and ONE smoke shard of shakedown positions. Runs on Atlas.
set -eu
NS=ssu-atlas-ai
cd /home/claude/g7a
kubectl apply -n $NS -f nrp/g7a_pvc.yaml
kubectl get pod g7a-stage -n $NS >/dev/null 2>&1 || kubectl apply -n $NS -f nrp/g7a_stage_pod.yaml
kubectl wait -n $NS --for=condition=Ready pod/g7a-stage --timeout=600s

S=/tmp/g7a_stage && rm -rf $S && mkdir -p $S/bin $S/code $S/smoke/todo_smoke
cp /home/claude/bin/sf/stockfish/stockfish-linux-x86-64-universal $S/bin/stockfish
cp g7a_label.py $S/code/
head -n 200 todo_shakedown.jsonl > $S/smoke/todo_smoke/shard_0000.jsonl
tar -C $S -cf /tmp/g7a_stage.tar .
ls -la /tmp/g7a_stage.tar | awk '{print "tar bytes", $5}'
kubectl cp -n $NS /tmp/g7a_stage.tar g7a-stage:/tmp/g7a_stage.tar
kubectl exec -n $NS g7a-stage -- sh -c 'tar -C /data -xf /tmp/g7a_stage.tar && rm /tmp/g7a_stage.tar && ls -la /data /data/bin /data/smoke/todo_smoke && /data/bin/stockfish --help 2>&1 | head -2 || true'
echo STAGED
