#!/usr/bin/env python3
"""Submit one labelling stage of the sealed G7a run to NRP, as exempt-class CPU jobs.

Runs on Atlas and submits through nats-bursting, never `kubectl apply`.

Why NRP and not Atlas. The first launch of this run put about 160 core-hours of
engine search on twelve Atlas cores, because the source files and the sampled
positions were already there. Atlas is a workstation whose electricity the owner
pays personally, and "the data is already here" was a convenience to me and a
cost to them. The engine work is a textbook exempt-class fit: one core, a few
hundred megabytes, fully used, embarrassingly parallel. What stays on Atlas is
the one-core engine-free draw from the 29 GB source, which has to read that file
where it lives, and the grading.

Why no GPU. Stockfish is a CPU engine.

Sizing is read from a measurement. `footprints.json` holds the labeller's peak
resident set and CPU share measured with `/usr/bin/time -v` at both node counts,
and this script refuses to submit without it.

Each pod reads one shard from the volume, labels it on local disk, and copies
one result file back at the end, so the volume sees one small read and one small
write per pod. The engine binary is copied to local disk before it is run.
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, "/home/claude/src/nats-bursting/python")

from nats_bursting.client import Client  # noqa: E402
from nats_bursting.descriptor import JobDescriptor, Resources, Volume  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
NAMESPACE = "ssu-atlas-ai"
PVC = "g7a-data"
PREREG_BLOB = "ae29671c248dc6c979e8429016d8dc3c24d44098"
NODES = {"screen": 50000, "deep": 1000000, "smoke": 50000}


def preflight():
    fp = json.load(open(os.path.join(HERE, "footprints.json")))
    problems = []
    if not fp.get("measured"):
        problems.append("footprints.json records no measurement")
    peak, share = fp.get("peak_rss_mb"), fp.get("mean_cpu_share")
    if peak is None or share is None:
        return ["footprints.json is missing peak_rss_mb or mean_cpu_share"], None
    req = max(int(peak * 1.6), 512)          # python and the engine are separate processes
    if req > 2048:
        problems.append("needs %d MB, above the exempt ceiling" % req)
    if share < 0.2:
        problems.append("measured CPU share %.2f is under the 20 percent floor" % share)
    return problems, req


def shell_for(month, stage, shard):
    base = "/data/%s" % month
    return (
        "set -e && pip install --quiet --no-warn-script-location 'chess==1.11.2' && "
        "cp /data/bin/stockfish /tmp/sf && chmod +x /tmp/sf && "
        "python3 /data/code/g7a_label.py --todo %s/todo_%s/shard_%04d.jsonl --out /tmp/out.jsonl "
        "--engine /tmp/sf --nodes %d && "
        "mkdir -p %s/out_%s && cp /tmp/out.jsonl %s/out_%s/shard_%04d.jsonl.part && "
        "mv %s/out_%s/shard_%04d.jsonl.part %s/out_%s/shard_%04d.jsonl && "
        "wc -l /tmp/out.jsonl && echo '===SHARD-DONE==='"
        % (base, stage, shard, NODES[stage], base, stage, base, stage, shard,
           base, stage, shard, base, stage, shard)
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", required=True)
    ap.add_argument("--stage", required=True, choices=sorted(NODES))
    ap.add_argument("--shards", type=int, required=True)
    ap.add_argument("--only", type=int, help="submit a single shard")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    problems, req = preflight()
    if problems:
        print("PREFLIGHT REFUSED")
        for p in problems:
            print("  -", p)
        raise SystemExit(2)
    print("preflight ok, requesting 1 CPU and %d Mi" % req)

    existing = set(subprocess.run(
        ["kubectl", "get", "jobs", "-n", NAMESPACE, "-o",
         "jsonpath={range .items[*]}{.metadata.name}{'\\n'}{end}"],
        capture_output=True, text=True).stdout.split())
    tag = a.month.replace("-", "")
    todo = [i for i in range(a.shards) if a.only is None or i == a.only]
    names = {i: "g7a-%s-%s-%04d" % (tag, a.stage, i) for i in todo}
    skipped = [names[i] for i in todo if names[i] in existing]
    todo = [i for i in todo if names[i] not in existing]
    if skipped:
        print("already present, not resubmitted: %d jobs" % len(skipped))
    print("jobs to submit:", len(todo))
    if a.dry_run:
        print(shell_for(a.month, a.stage, todo[0]) if todo else "")
        return 0

    res = Resources(cpu="1", memory="%dMi" % req, ephemeral_storage="2Gi")
    with Client() as client:
        for i in todo:
            d = JobDescriptor(
                name=names[i], image="python:3.12-slim",
                command=["sh", "-c", shell_for(a.month, a.stage, i)],
                env={"PYTHONDONTWRITEBYTECODE": "1", "G7A_PREREG_BLOB": PREREG_BLOB},
                resources=res,
                labels={"app": "get-g7a", "stage": a.stage, "atlas.io/batch": "get-g7a-%s" % tag},
                backoff_limit=1,
                volumes=[Volume(name="data", mount_path="/data", claim_name=PVC)],
            )
            # Submit and move on. The job runs for up to an hour, and waiting on
            # its completion, as submit_and_wait does, made the G9 submission take
            # three minutes a job.
            r = client.submit(d)
            print("%s job_id=%s" % (names[i], r.job_id), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
