#!/bin/bash
# Shard one stage's positions and push them to the volume. Runs on Atlas.
#   stage_month.sh 2026-07 screen /home/claude/g7a/run_2026-07/todo.jsonl 96
#
# Resumable. The first version pushed one tar and extracted it in one step, and
# the volume took about forty seconds a shard, so 96 shards outlived the staging
# pod's two hour deadline. This version compares byte sizes on the volume with
# the local shards, sends only what is missing or short, and repeats until the
# two agree, so a pod that expires costs the shards in flight and not the stage.
set -u
M="$1"; STAGE="$2"; TODO="$3"; N="$4"
NS=ssu-atlas-ai
S=/tmp/g7a_${M}_${STAGE}; D=$S/$M/todo_$STAGE
BATCH=24          # shards per round, about a quarter of an hour on the volume

live_pod() {
  ph=$(kubectl get pod g7a-stage -n $NS -o jsonpath='{.status.phase}' 2>/dev/null || true)
  if [ "$ph" != "Running" ]; then
    kubectl delete pod g7a-stage -n $NS --ignore-not-found --wait=true >/dev/null 2>&1
    kubectl apply -n $NS -f /home/claude/g7a/nrp/g7a_stage_pod.yaml >/dev/null
    kubectl wait -n $NS --for=condition=Ready pod/g7a-stage --timeout=900s >/dev/null || return 1
  fi
}

# Shard once. Round-robin, so every shard sees every part of the month.
if [ "$(ls "$D" 2>/dev/null | wc -l)" -ne "$N" ]; then
  rm -rf "$S" && mkdir -p "$D"
  awk -v n="$N" -v d="$D" '{ f=sprintf("%s/shard_%04d.jsonl", d, (NR-1)%n); print > f }' "$TODO"
fi
echo "local shards $(ls "$D" | wc -l), lines $(cat "$D"/*.jsonl | wc -l), source lines $(wc -l < "$TODO")"
( cd "$D" && stat -c '%n %s' shard_*.jsonl | sort ) > "$S/local.sizes"

for round in $(seq 1 12); do
  live_pod || { echo "no staging pod"; sleep 60; continue; }
  kubectl exec -n $NS g7a-stage -- sh -c "mkdir -p /data/$M/todo_$STAGE && cd /data/$M/todo_$STAGE && for f in shard_*.jsonl; do [ -f \"\$f\" ] && echo \"\$f \$(wc -c < \"\$f\")\"; done | sort" > "$S/remote.sizes" 2>/dev/null
  comm -23 "$S/local.sizes" "$S/remote.sizes" | awk '{print $1}' > "$S/missing"
  left=$(wc -l < "$S/missing")
  echo "round $round: $left of $N shards missing or short"
  if [ "$left" -eq 0 ]; then echo STAGED; exit 0; fi
  head -n $BATCH "$S/missing" > "$S/batch"
  tar -C "$D" -cf "$S/batch.tar" -T "$S/batch"
  kubectl cp -n $NS "$S/batch.tar" g7a-stage:/tmp/in.tar || continue
  kubectl exec -n $NS g7a-stage -- sh -c "tar -C /data/$M/todo_$STAGE -xf /tmp/in.tar; rm -f /tmp/in.tar" || true
done
echo "STAGING INCOMPLETE after 12 rounds"
exit 1
