#!/usr/bin/env python3
"""Submit the sealed G9 cells to NRP as exempt-class CPU jobs.

Runs on Atlas. Submits through nats-bursting, never `kubectl apply`, because
the burst flow is what keeps a run inside the cluster's rules.

Why no GPU. The work is convex-hull feasibility on four points in a plane,
repeated over a few hundred units and two hundred shuffles. That is a stream of
tiny linear programs. On any modern device it would hold single-digit GPU
utilisation and be removed by enforcement inside a couple of minutes, which is
what happened to seven jobs in August 2026 before the workload-class rule was
written down. It requests none.

Why the sizing is read from a file and not typed here. A preflight fed an
invented estimate is theatre. `footprints.json` carries a measured peak RSS and
a measured time-averaged CPU share for one real cell, taken with
`/usr/bin/time -v` on Atlas, and this script refuses to submit any class that
file does not cover.
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
FOOTPRINTS = os.path.join(HERE, "footprints.json")
NAMESPACE = "ssu-atlas-ai"
CONFIGMAP = "g9-code"
SEASONS = list(range(2015, 2025))
PBP = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_%d.parquet"

# The six planes that cleared the anti-vacuity bar carry verdicts. The four that
# did not are run anyway so their counts are on the record, and the registration
# already says they carry none.
BARRED = [
    ("y1_epa", "y3_turnover"),        # primary
    ("y3_turnover", "y4_epa_sd"),
    ("y1_epa", "y2_first_down"),
    ("y1_epa", "y4_epa_sd"),
    ("y2_first_down", "y4_epa_sd"),
    ("y2_first_down", "y5_clock_stop"),
]
VACUOUS = [
    ("y1_epa", "y5_clock_stop"),
    ("y2_first_down", "y3_turnover"),
    ("y3_turnover", "y5_clock_stop"),
    ("y4_epa_sd", "y5_clock_stop"),
]


def cells():
    out = []
    for p in BARRED + VACUOUS:
        out.append({"plane": p, "floor": 5, "bar": p in BARRED})
    # The sensitivity at a floor of ten, registered without a bar, on the
    # planes that carry one at the sealed floor.
    for p in BARRED:
        out.append({"plane": p, "floor": 10, "bar": False})
    return out


def cell_name(c):
    short = {"y1_epa": "epa", "y2_first_down": "fd", "y3_turnover": "to",
             "y4_epa_sd": "sd", "y5_clock_stop": "clk"}
    return "g9-%s-%s-f%d" % (short[c["plane"][0]], short[c["plane"][1]], c["floor"])


def preflight(fp):
    """Score the submission against the cluster rules, on measurements."""
    problems = []
    if not fp.get("measured"):
        problems.append("footprints.json does not record a measurement")
    peak_mb = fp.get("peak_rss_mb")
    cpu_share = fp.get("mean_cpu_share")
    if peak_mb is None or cpu_share is None:
        problems.append("footprints.json is missing peak_rss_mb or mean_cpu_share")
        return problems, None

    # Request covers the measured peak with headroom, and keeps the mean above
    # the 20 percent floor from the other side.
    req_mem_mb = int(peak_mb * 1.25)
    if req_mem_mb > 2048:
        problems.append(
            "measured peak %.0f MB needs a %d MB request, above the exempt class ceiling of 2048; "
            "this cell cannot go out as exempt and must be sized and justified separately"
            % (peak_mb, req_mem_mb))
    if peak_mb > 0 and fp.get("mean_rss_mb") and peak_mb > 5 * fp["mean_rss_mb"]:
        problems.append("peak is more than five times the mean, so no single memory request "
                        "satisfies both the ceiling and the 20 percent floor")
    if cpu_share < 0.2:
        problems.append("measured CPU share %.2f is below the 20 percent floor of one CPU"
                        % cpu_share)
    if cpu_share > 2.0:
        problems.append("measured CPU share %.2f exceeds 200 percent of one CPU" % cpu_share)
    return problems, max(req_mem_mb, 512)


def ensure_configmap(dry):
    src = [os.path.join(HERE, "g9_hull_law.py"),
           os.path.join(HERE, "..", "G2", "g2_hull_law.py")]
    for s in src:
        if not os.path.exists(s):
            raise SystemExit("missing %s" % s)
    cmd = ["kubectl", "create", "configmap", CONFIGMAP, "-n", NAMESPACE]
    for s in src:
        cmd += ["--from-file=%s" % os.path.abspath(s)]
    cmd += ["--dry-run=client", "-o", "yaml"]
    y = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    if dry:
        print("configmap would be applied, %d bytes of yaml" % len(y))
        return
    subprocess.run(["kubectl", "apply", "-n", NAMESPACE, "-f", "-"],
                   input=y, text=True, check=True)
    print("configmap %s applied" % CONFIGMAP)


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


def shell_for(c):
    """The image is slim and carries no curl, so the fetch is plain urllib.

    The sha256 of every source file is written beside the result, because the
    registration says the run records what it read.
    """
    return (
        "set -e && "
        "pip install --quiet --no-warn-script-location "
        "'pandas==2.3.3' 'pyarrow==23.0.1' 'numpy==2.4.6' 'scipy==1.18.1' && "
        "mkdir -p /tmp/code/G9 /tmp/code/G2 && "
        "cp /work/g9_hull_law.py /tmp/code/G9/ && cp /work/g2_hull_law.py /tmp/code/G2/ && "
        "python3 -c \"$G9_FETCH\" && "
        "cd /tmp/code/G9 && G9_CACHE=/tmp/nfl python3 g9_hull_law.py "
        "--plane %s --floor %d --shuffles 200 --out /tmp/out.json && "
        "echo '===RECORD-BEGIN===' && cat /tmp/out.json && echo && "
        "cat /tmp/sources.sha256 && echo '===RECORD-END==='"
        % (",".join(c["plane"]), c["floor"])
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", help="submit one cell by name")
    a = ap.parse_args()

    if not os.path.exists(FOOTPRINTS):
        raise SystemExit("no footprints.json; measure a cell before submitting anything")
    fp = json.load(open(FOOTPRINTS))
    problems, req_mem_mb = preflight(fp)
    if problems:
        print("PREFLIGHT REFUSED")
        for p in problems:
            print("  -", p)
        raise SystemExit(2)
    print("preflight ok: peak %.0f MB measured, requesting %d MB, cpu share %.2f"
          % (fp["peak_rss_mb"], req_mem_mb, fp["mean_cpu_share"]))

    ensure_configmap(a.dry_run)

    todo = [c for c in cells() if not a.only or cell_name(c) == a.only]

    # A job name is not reusable while the old Job object exists. Submitting a
    # descriptor whose name matches one silently fails at the controller and
    # still returns a job id, and a watcher on that name then reports the old
    # job's outcome. So existing names are skipped here and listed, and the
    # operator deletes them deliberately rather than by accident.
    existing = set(subprocess.run(
        ["kubectl", "get", "jobs", "-n", NAMESPACE, "-o",
         "jsonpath={range .items[*]}{.metadata.name}{'\\n'}{end}"],
        capture_output=True, text=True).stdout.split())
    skipped = [cell_name(c) for c in todo if cell_name(c) in existing]
    todo = [c for c in todo if cell_name(c) not in existing]
    if skipped:
        print("already present, not resubmitted:", ", ".join(sorted(skipped)))
    print("cells to submit:", len(todo))

    # Exempt class, and limits equal to requests so nothing drifts outside the
    # 20 percent band the admission webhook checks.
    res = Resources(cpu="1", memory="%dMi" % req_mem_mb, ephemeral_storage="4Gi")

    if a.dry_run:
        for c in todo:
            print(" ", cell_name(c), c["plane"], "floor", c["floor"], "bar", c["bar"])
        print("dry run, nothing submitted")
        return 0

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
                     "G9_PREREG_BLOB": "f8a18aea4d82bded364b78a6da6c1a39f1fd9f51"},
                resources=res,
                labels={"app": "get-g9", "stage": "sealed-run",
                        "atlas.io/batch": "get-g9-2026-09-19"},
                backoff_limit=1,
                volumes=[Volume(name="code", mount_path="/work", read_only=True,
                                config_map=CONFIGMAP)],
            )
            r = client.submit_and_wait(d, timeout=180.0)
            print("%-28s job_id=%s accepted=%s k8s=%s" % (name, r.job_id, r.accepted,
                                                          r.k8s_job_name))
            submitted.append({"cell": name, "plane": list(c["plane"]), "floor": c["floor"],
                              "bar": c["bar"], "job_id": r.job_id,
                              "k8s_job": r.k8s_job_name, "accepted": r.accepted})
    # Merge rather than overwrite, so a second call for the remaining cells does
    # not erase the record of the first.
    path = os.path.join(HERE, "submitted.json")
    prior = json.load(open(path)) if os.path.exists(path) else []
    by_name = {r["cell"]: r for r in prior}
    for r in submitted:
        by_name[r["cell"]] = r
    with open(path, "w") as f:
        json.dump(sorted(by_name.values(), key=lambda r: r["cell"]), f, indent=1, sort_keys=True)
    print("wrote submitted.json, %d cells recorded" % len(by_name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
