#!/bin/bash
# G7a sealed run for one month with the engine work on NRP. Runs on Atlas in a
# screen session and only stages, polls and fetches, so it costs Atlas almost
# nothing. Usage: g7a_nrp_pipeline.sh 2026-07
#
# Resumable. Each step is skipped when its product exists.
set -u
M="$1"; N=96
NS=ssu-atlas-ai
G=/home/claude/g7a; W=$G/run_$M; PY=/home/claude/env/bin/python3
LOG=$W/nrp_pipeline.log
say() { echo "[$1] $(date -u +%Y-%m-%dT%H:%M:%SZ) ${2:-}" >> "$LOG"; }
mkdir -p "$W"; cd "$G" || exit 1

stage_pod() {   # the staging pod has a two hour deadline, so make sure a live one exists
  ph=$(kubectl get pod g7a-stage -n $NS -o jsonpath='{.status.phase}' 2>/dev/null || true)
  if [ "$ph" != "Running" ]; then
    kubectl delete pod g7a-stage -n $NS --ignore-not-found --wait=true >/dev/null 2>&1
    kubectl apply -n $NS -f $G/nrp/g7a_stage_pod.yaml >/dev/null
    kubectl wait -n $NS --for=condition=Ready pod/g7a-stage --timeout=900s >/dev/null
  fi
}

run_stage() {   # run_stage <stage> <todo file>
  STAGE="$1"; TODO="$2"
  if [ -s "$W/${STAGE}_fetched.done" ]; then say skip "$STAGE already fetched"; return 0; fi
  stage_pod
  if [ ! -s "$W/${STAGE}_staged.done" ]; then
    say stage "$STAGE $(wc -l < "$TODO") positions in $N shards"
    $G/nrp/stage_month.sh "$M" "$STAGE" "$TODO" $N >> "$W/${STAGE}_stage.log" 2>&1 || { say error "staging $STAGE failed"; exit 1; }
    echo done > "$W/${STAGE}_staged.done"
  fi
  say submit "$STAGE"
  ( cd $G/nrp && $PY submit_g7a_nrp.py --month "$M" --stage "$STAGE" --shards $N ) >> "$W/${STAGE}_submit.log" 2>&1
  tag=$(echo "$M" | tr -d '-')
  while true; do
    stage_pod
    have=$(kubectl exec -n $NS g7a-stage -- sh -c "ls /data/$M/out_$STAGE/*.jsonl 2>/dev/null | wc -l" 2>/dev/null || echo 0)
    failed=$(kubectl get jobs -n $NS -l app=get-g7a,stage=$STAGE --no-headers 2>/dev/null | grep -ciE 'failed' || true)
    say poll "$STAGE outputs=$have of $N failed_jobs=$failed"
    [ "$have" -ge "$N" ] && break
    if [ "${failed:-0}" -gt 0 ]; then
      # A failed job is resubmitted once by deleting it, since a name is not
      # reusable while the old Job object exists.
      for j in $(kubectl get jobs -n $NS -l app=get-g7a,stage=$STAGE --no-headers | grep -iE 'failed' | awk '{print $1}'); do
        kubectl delete job "$j" -n $NS --wait=true >/dev/null 2>&1
      done
      ( cd $G/nrp && $PY submit_g7a_nrp.py --month "$M" --stage "$STAGE" --shards $N ) >> "$W/${STAGE}_submit.log" 2>&1
    fi
    sleep 180
  done
  say fetch "$STAGE"
  $G/nrp/fetch_stage.sh "$M" "$STAGE" "$W" >> "$W/${STAGE}_fetch.log" 2>&1 || { say error "fetch $STAGE failed"; exit 1; }
  echo done > "$W/${STAGE}_fetched.done"
  kubectl delete jobs -n $NS -l app=get-g7a,stage=$STAGE >/dev/null 2>&1
  say fetched "$STAGE $(cat "$W/nrp_$STAGE/out_$STAGE"/*.jsonl | wc -l) labels"
}

say start "month=$M code=$(cat $G/CODE_COMMIT 2>/dev/null)"
while [ ! -s "$W/todo.jsonl" ]; do sleep 120; done
say sampled "$(wc -l < "$W/todo.jsonl") positions"

run_stage screen "$W/todo.jsonl"

if [ ! -s "$W/todo_deep_nrp.jsonl" ]; then
  say select
  taskset -c 0 nice -n 19 $PY g7a_select_deep.py --screen "$W/nrp_screen/out_screen/*.jsonl" \
      --out "$W/todo_deep_nrp.jsonl" > "$W/select_nrp.log" 2>&1
  say selected "$(cat "$W/select_nrp.log")"
fi

run_stage deep "$W/todo_deep_nrp.jsonl"

kubectl delete pod g7a-stage -n $NS --ignore-not-found >/dev/null 2>&1
say grade
taskset -c 0-3 nice -n 19 $PY g7a_grade.py --labels "$W/nrp_deep/out_deep/*.jsonl" \
    --screen "$W/nrp_screen/out_screen/*.jsonl" --out "$W/grade.json" > "$W/grade.log" 2>&1
say finished "exit=$?"
