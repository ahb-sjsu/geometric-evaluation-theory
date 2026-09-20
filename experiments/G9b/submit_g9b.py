#!/usr/bin/env python3
"""Submit the sealed G9b cells to NRP as exempt-class CPU jobs.

One cell per coordinate subset, twenty-six in all: ten pairs, ten triples, five
quadruples and one quintuple. Same shape as the G9 submitter, and sized from
the same measurement, because the loader, the statistic and the null are the
same and only the subset and the action space differ.

No GPU, for the reason in the G9 submitter: this is a stream of tiny linear
programs and would be reaped below the utilisation floor.
"""
import argparse
import itertools
import json
import os
import subprocess
import sys

sys.path.insert(0, "/home/claude/src/nats-bursting/python")

from nats_bursting.client import Client  # noqa: E402
from nats_bursting.descriptor import JobDescriptor, Resources, Volume  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FOOTPRINTS = os.path.join(HERE, "..", "G9", "footprints.json")
NAMESPACE = "ssu-atlas-ai"
CONFIGMAP = "g9b-code"
PREREG_BLOB = "adb0ad4bf2dabefbbd4af615b107a2eb2f8fe1cd"

COORDS = ("y1_epa", "y2_first_down", "y3_turnover", "y4_epa_sd", "y5_clock_stop")
SHORT = {"y1_epa": "epa", "y2_first_down": "fd", "y3_turnover": "to",
         "y4_epa_sd": "sd", "y5_clock_stop": "clk"}
# The chain the primary claim is about: every subset holding both expected
# points added and first down probability.
CHAIN = ("y1_epa", "y2_first_down")

FETCH = (
    "import hashlib,os,urllib.request\n"
    "os.makedirs('/tmp/nfl',exist_ok=True)\n"
    "h=open('/tmp/sources.sha256','w')\n"
    "for s in range(2015,2025):\n"
    "    u='https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_%d.parquet'%s\n"
    "    p='/tmp/nfl/pbp_%d.parquet'%s\n"
    "    for attempt in range(4):\n"
    "        try:\n"
    "            r=urllib.request.Request(u,headers={'User-Agent':'python-urllib'})\n"
    "            d=urllib.request.urlopen(r,timeout=600).read()\n"
    "            break\n"
    "        except Exception as e:\n"
    "            if attempt==3: raise\n"
    "    open(p,'wb').write(d)\n"
    "    h.write('%s  %s\\n'%(hashlib.sha256(d).hexdigest(),p))\n"
    "h.close()\n"
)


def subsets():
    out = []
    for k in (2, 3, 4, 5):
        for s in itertools.combinations(COORDS, k):
            out.append({"coords": s, "k": k,
                        "in_chain": all(c in s for c in CHAIN)})
    return out


def cell_name(c):
    return "g9b-" + "-".join(SHORT[x] for x in c["coords"])


def preflight(fp):
    problems = []
    if not fp.get("measured"):
        problems.append("footprints.json does not record a measurement")
    peak = fp.get("peak_rss_mb")
    share = fp.get("mean_cpu_share")
    if peak is None or share is None:
        problems.append("footprints.json missing peak_rss_mb or mean_cpu_share")
        return problems, None
    req = int(peak * 1.25)
    if req > 2048:
        problems.append("peak %.0f MB needs %d MB, above the exempt ceiling" % (peak, req))
    if share < 0.2:
        problems.append("measured CPU share %.2f below the 20 percent floor" % share)
    return problems, max(req, 512)


def ensure_configmap(dry):
    src = [os.path.join(HERE, "g9b_hull_law.py"),
           os.path.join(HERE, "..", "G2", "g2_hull_law.py")]
    for s in src:
        if not os.path.exists(s):
            raise SystemExit("missing %s" % s)
    cmd = ["kubectl", "create", "configmap", CONFIGMAP, "-n", NAMESPACE]
    cmd += ["--from-file=%s" % os.path.abspath(s) for s in src]
    cmd += ["--dry-run=client", "-o", "yaml"]
    y = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    if dry:
        print("configmap would be applied, %d bytes" % len(y))
        return
    subprocess.run(["kubectl", "apply", "-n", NAMESPACE, "-f", "-"],
                   input=y, text=True, check=True)
    print("configmap %s applied" % CONFIGMAP)


def shell_for(c):
    return (
        "set -e && "
        "pip install --quiet --no-warn-script-location "
        "'pandas==2.3.3' 'pyarrow==23.0.1' 'numpy==2.4.6' 'scipy==1.18.1' && "
        "mkdir -p /tmp/code/G9b /tmp/code/G2 && "
        "cp /work/g9b_hull_law.py /tmp/code/G9b/ && cp /work/g2_hull_law.py /tmp/code/G2/ && "
        "python3 -c \"$G9_FETCH\" && "
        "cd /tmp/code/G9b && G9_CACHE=/tmp/nfl python3 g9b_hull_law.py "
        "--coords %s --shuffles 200 --out /tmp/out.json && "
        "echo '===RECORD-BEGIN===' && cat /tmp/out.json && echo && "
        "cat /tmp/sources.sha256 && echo '===RECORD-END==='"
        % ",".join(c["coords"])
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    fp = json.load(open(FOOTPRINTS))
    problems, req = preflight(fp)
    if problems:
        print("PREFLIGHT REFUSED")
        for p in problems:
            print("  -", p)
        raise SystemExit(2)
    print("preflight ok: peak %.0f MB measured, requesting %d MB, cpu share %.2f"
          % (fp["peak_rss_mb"], req, fp["mean_cpu_share"]))

    ensure_configmap(a.dry_run)
    todo = subsets()

    existing = set(subprocess.run(
        ["kubectl", "get", "jobs", "-n", NAMESPACE, "-o",
         "jsonpath={range .items[*]}{.metadata.name}{'\\n'}{end}"],
        capture_output=True, text=True).stdout.split())
    skipped = [cell_name(c) for c in todo if cell_name(c) in existing]
    todo = [c for c in todo if cell_name(c) not in existing]
    if skipped:
        print("already present, not resubmitted:", ", ".join(sorted(skipped)))
    print("cells to submit:", len(todo))

    if a.dry_run:
        for c in todo:
            print(" ", cell_name(c), c["k"], "chain" if c["in_chain"] else "")
        return 0

    res = Resources(cpu="1", memory="%dMi" % req, ephemeral_storage="4Gi")
    submitted = []
    with Client() as client:
        for c in todo:
            name = cell_name(c)
            d = JobDescriptor(
                name=name,
                image="python:3.12-slim",
                command=["sh", "-c", shell_for(c)],
                env={"PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": "1",
                     "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                     "NUMEXPR_NUM_THREADS": "1", "G9_FETCH": FETCH,
                     "G9B_PREREG_BLOB": PREREG_BLOB},
                resources=res,
                labels={"app": "get-g9b", "stage": "sealed-run",
                        "atlas.io/batch": "get-g9b-2026-09-19"},
                backoff_limit=1,
                volumes=[Volume(name="code", mount_path="/work", read_only=True,
                                config_map=CONFIGMAP)],
            )
            r = client.submit_and_wait(d, timeout=60.0)
            print("%-26s job_id=%s accepted=%s" % (name, r.job_id, r.accepted), flush=True)
            submitted.append({"cell": name, "coords": list(c["coords"]), "k": c["k"],
                              "in_chain": c["in_chain"], "job_id": r.job_id,
                              "k8s_job": r.k8s_job_name, "accepted": r.accepted})
    path = os.path.join(HERE, "submitted.json")
    prior = json.load(open(path)) if os.path.exists(path) else []
    by = {r["cell"]: r for r in prior}
    for r in submitted:
        by[r["cell"]] = r
    with open(path, "w") as f:
        json.dump(sorted(by.values(), key=lambda r: r["cell"]), f, indent=1, sort_keys=True)
    print("wrote submitted.json, %d cells" % len(by))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
