#!/bin/bash
# Load and score each judge inside a hard 2 GiB cgroup limit, as an NRP exempt-class pod would run.
# Gemma after the 14B sizing run; the 14B and the 7B after the G3d smoke test frees GPU 1.
cd /home/claude/g3c/nrp
while ! grep -q MEASURE14_EXIT /home/claude/g3c/measure14/measure14.log 2>/dev/null; do sleep 30; done
run() {
  sudo -n systemd-run --scope --quiet -p MemoryMax=2G -p MemorySwapMax=0 --uid=claude --gid=claude \
    --setenv=HOME=/home/claude --setenv=CUDA_VISIBLE_DEVICES=1 --setenv=HF_HUB_OFFLINE=1 \
    --setenv=PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True --setenv=OMP_NUM_THREADS=4 --setenv=OPENBLAS_NUM_THREADS=4 \
    --working-directory=/home/claude/g3c/nrp \
    taskset -c 8-11 /archive/kvbench/venv/bin/python load_under_limit.py --config ../prereg_config.json --model $1 --precision $2 --out limit_$1_$2.json
  echo "LIMIT_EXIT $1 $2 $?"
}
run gemma4b full
while ! grep -q SMOKE_EXIT /home/claude/g3d_run/smoke.log 2>/dev/null; do sleep 30; done
run qwen14b full
run qwen7b full
echo LOADTESTS_DONE
