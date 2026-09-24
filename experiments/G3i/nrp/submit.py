"""G3i on NRP Nautilus, namespace ssu-atlas-ai, through nats-bursting. Run on Atlas.

    python submit.py code                            # ConfigMap with the harness and the sealed config
    python submit.py stage  [--dry-run]              # CPU job: Gemma 3 12B weights onto the volume
    python submit.py run --block calibration [--dry-run]
    python submit.py run --block test        [--dry-run]
    python submit.py fetch --block calibration       # results back to Atlas via the job's log

G3c's submitter (../../G3c/nrp/submit.py), with the judge harness swapped for G3d's flip.py and
one judge. Policy (reference_nrp_job_policies.md), scored item by item in ``preflight``:
* requests from MEASUREMENT: the GPU job is sized by nrp_sizing.py from the meter record of the
  completed pilot of this judge on the same hardware class; CPU jobs sit in the exempt class.
* requests == limits (the renderer), ephemeral storage declared, backoff_limit 0.
* jobs terminate by themselves; nothing sleeps.
* the GPU pod does no pip, clone or download: the venv (G3c's, already on the volume) and the
  weights are staged by CPU jobs, and it loads with HF_HUB_OFFLINE=1.
* at most four heavy GPU pods in the namespace at once.
* untainted Tesla-V100-SXM2-32GB nodes: the pilot's hardware class (Volta, 32 GB), no toleration.
* a completed job name is deleted before it is reused, and the fresh creationTimestamp checked.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import subprocess
import sys
import tarfile
import time
from pathlib import Path

sys.path.insert(0, "/home/claude/src/nats-bursting/python")
HERE = Path(__file__).resolve().parent
G3I = HERE.parent
EXP = G3I.parent
sys.path.insert(0, str(EXP / "G3c" / "nrp"))   # nrp_sizing.py, stage_models.py

NS = "ssu-atlas-ai"
PVC = "g3c-judge"            # G3c's volume: the venv tar is already on it under /data/env
CODE_CM = "g3i-code"
BATCH = "g3i-flip"
IMAGE = "pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime"   # the image G3c's venv was built in
GPU_PRODUCT = "Tesla-V100-SXM2-32GB"
CPU_ZONE = {"topology.kubernetes.io/zone": "ucsd-nrp"}
MAX_HEAVY = 4
JUDGE = "gemma12b"
CONFIG = "flip_config_gemma12b.json"
nl = chr(10)

ENV = """set -euo pipefail
export PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True G3C_MODEL_ROOT=/data/models
tar -xf /data/env/g3c-env.tar -C /tmp
export PATH=/tmp/venv/bin:$PATH
mkdir -p /work/g3b /work/g3c /work/g3d /work/G3i
cp /code/g3b.py /work/g3b/ && cp /code/judge.py /work/g3c/ && cp /code/flip.py /work/g3d/ && cp /code/flip_config_gemma12b.json /work/G3i/
export PYTHONPATH=/work:${PYTHONPATH:-}
cd /work/g3d
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
"""


def cfg() -> dict:
    return json.load(open(G3I / CONFIG, encoding="utf-8"))


def kubectl(*args, check=False):
    r = subprocess.run(["kubectl", "-n", NS, "--request-timeout=60s", *args], capture_output=True, text=True, timeout=120)
    if check and r.returncode:
        raise SystemExit(f"kubectl {' '.join(args)}: {r.stderr.strip()}")
    return r


# ----------------------------------------------------------------------------- sizing

def measured_usage():
    """The meter record of the completed pilot calibration of this judge, on the same hardware
    class (a 32 GB Volta card), as the time-averaged usage the NRP floors are judged on. Peak
    memory follows G3c's rule: the post-load resident peak, or the load-phase anonymous peak plus
    the post-load file-backed peak, whichever is larger; the file-backed pages of the load are
    reclaimable and set no floor."""
    import nrp_sizing as sizing
    p = G3I / "pilot_record" / f"pilot_{JUDGE}" / "calibration" / "results.json"
    if not p.exists():
        return None, None, None
    m = json.load(open(p)).get("meter") or {}
    w, ph = m.get("whole_run"), m.get("phases") or {}
    if not w or w.get("seconds", 0) < 300:
        return None, None, None
    load = [v for k, v in ph.items() if k.endswith("_load")]
    after = [v for k, v in ph.items() if not k.endswith("_load") and v.get("VmRSS_peak_gib") is not None]
    if not load or not after:
        return None, None, None
    post_peak = max(v["VmRSS_peak_gib"] for v in after)
    post_file = max(v.get("RssFile_peak_gib", 0.0) for v in after)
    peak = max(post_peak, load[0].get("RssAnon_peak_gib", 0.0) + post_file)
    return sizing.Usage(mean_cpu_cores=float(w["mean_cores"]), mean_mem_gib=float(w.get("VmRSS_mean_gib", 0.0)),
                        peak_mem_gib=float(peak)), str(p), w


def preflight(desc, usage, gpu: bool) -> list[str]:
    import nrp_sizing as sizing
    bad = []
    res = desc.resources
    cpu = float(res.cpu); mem = float(str(res.memory).rstrip("Gi"))
    if not res.ephemeral_storage:
        bad.append("ephemeral-storage not declared")
    if desc.backoff_limit != 0:
        bad.append("backoff_limit is not 0")
    script = " ".join(desc.command)
    if "sleep" in script:
        bad.append("the command contains sleep")
    if gpu:
        if usage is None:
            bad.append("no measured usage for this judge: its pilot record is missing")
        else:
            bad += sizing.check(int(cpu), mem, usage)
        if any(w in script for w in ("pip install", "git clone", "snapshot_download", "apt-get")):
            bad.append("a GPU job installs or downloads")
        if "test" in cfg().get("seeds", {}) and "--block calibration" in script:
            bad.append("a test seed exists; the calibration block must precede it")
        if "--block test" in script and "test" not in cfg().get("seeds", {}):
            bad.append("no test seed in the config; it is drawn only after predictions are committed")
    else:
        if cpu > 1 or mem > 2:
            bad.append("a CPU job outside the exempt class (1 CPU, 2 GiB)")
    return bad


# ----------------------------------------------------------------------------- descriptors

def descriptor(name, script, cpu, memory, eph, role, gpu=0, extra=None):
    from nats_bursting import JobDescriptor, Resources, Volume
    vols = [Volume(name="data", mount_path="/data", claim_name=PVC),
            Volume(name="code", mount_path="/code", config_map=CODE_CM, read_only=True)]
    labels = {"app": "g3i", "atlas.io/batch": BATCH, "atlas.io/role": role, **(extra or {})}
    return JobDescriptor(name=name, image=IMAGE, command=["/bin/bash", "-lc", script],
                         resources=Resources(cpu=str(cpu), memory=memory, gpu=gpu, ephemeral_storage=eph),
                         labels=labels,
                         node_selector={"nvidia.com/gpu.product": GPU_PRODUCT} if gpu else dict(CPU_ZONE),
                         backoff_limit=0, volumes=vols)


def stage_script(model_id: str, revision: str) -> str:
    return ("set -euo pipefail\n"
            "export PIP_ROOT_USER_ACTION=ignore PYTHONUNBUFFERED=1\n"
            "tar -xf /data/env/g3c-env.tar -C /tmp\n"
            f"/tmp/venv/bin/python /code/stage_models.py --model-id {model_id} --revision {revision} --dest /data/models/{JUDGE}\n")


def run_script(block: str) -> str:
    return (ENV + f"python flip.py run --config ../G3i/{CONFIG} --block {block} --out /data/runs/g3i/{JUDGE} 2>&1\n"
            f"echo RUN_DONE {JUDGE} {block}\n")


def job_name(*parts) -> str:
    return "g3i-" + "-".join(str(p).replace("_", "-").replace(".", "") for p in parts).lower()


# ----------------------------------------------------------------------------- submission

def submit(desc):
    from nats_bursting import Client
    kubectl("delete", "job", desc.name, "--ignore-not-found")
    t0 = time.time()
    with Client() as c:
        c.submit(desc)
    for _ in range(60):
        r = kubectl("get", "job", desc.name, "-o", "jsonpath={.metadata.creationTimestamp}")
        if r.returncode == 0 and r.stdout.strip():
            created = time.mktime(time.strptime(r.stdout.strip(), "%Y-%m-%dT%H:%M:%SZ")) - time.timezone
            if created >= t0 - 120:
                return r.stdout.strip()
            raise SystemExit(f"{desc.name}: creationTimestamp {r.stdout.strip()} predates this submission")
        time.sleep(5)
    raise SystemExit(f"{desc.name}: no job object appeared")


def heavy_running() -> int:
    r = kubectl("get", "pods", "-l", "atlas.io/batch", "-o", "json")
    n = 0
    for p in json.loads(r.stdout or "{}").get("items", []):
        if p["status"].get("phase") in ("Pending", "Running"):
            for c in p["spec"]["containers"]:
                if int(c.get("resources", {}).get("limits", {}).get("nvidia.com/gpu", 0)):
                    n += 1
    return n


def wait(names: list[str]) -> dict:
    state = {}
    while len(state) < len(names):
        for nm in names:
            if nm in state:
                continue
            r = kubectl("get", "job", nm, "-o", "jsonpath={.status.succeeded},{.status.failed}")
            if r.returncode:
                state[nm] = "MISSING"; continue
            s, f = (r.stdout.split(",") + ["", ""])[:2]
            if s == "1":
                state[nm] = "SUCCEEDED"
            elif f and int(f) > 0:
                state[nm] = "FAILED"
        print(time.strftime("%H:%M:%S"), {k: v for k, v in state.items()}, flush=True)
        if len(state) < len(names):
            time.sleep(60)
    return state


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["code", "stage", "run", "fetch"])
    ap.add_argument("--block", default="calibration", choices=["calibration", "test"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-wait", action="store_true")
    a = ap.parse_args(argv)
    c = cfg()
    if a.cmd == "code":
        files = [EXP / "G3b" / "g3b.py", EXP / "G3c" / "judge.py", EXP / "G3d" / "flip.py", G3I / CONFIG,
                 EXP / "G3c" / "nrp" / "stage_models.py"]
        missing = [str(f) for f in files if not f.exists()]
        if missing:
            raise SystemExit(f"code: missing {missing}")
        args = ["create", "configmap", CODE_CM, "--dry-run=client", "-o", "yaml"] + [f"--from-file={f}" for f in files]
        y = kubectl(*args, check=True).stdout
        r = subprocess.run(["kubectl", "-n", NS, "apply", "-f", "-"], input=y, capture_output=True, text=True)
        print(r.stdout or r.stderr); return r.returncode
    items = []
    if a.cmd == "stage":
        m = c["model"]
        items = [(descriptor(job_name("stage", JUDGE), stage_script(m["model_id"], m["revision"]), 1, "2Gi", "10Gi", "stage"), None, False)]
    elif a.cmd == "run":
        import nrp_sizing as sizing
        usage, src, w = measured_usage()
        if usage is None:
            print("REFUSED: the judge was never measured"); return 2
        req = sizing.request_for(usage, want_cpu=1)
        if isinstance(req, sizing.Refusal):
            print(f"REFUSED: {req}"); return 2
        # The exempt class (1 CPU, 2 GiB) is what the pilot's averages allow, but the 24 GB of
        # weights are mapped through the page cache at load and a 2 GiB limit makes that load
        # crawl. 3 GiB keeps the mean at 45 percent of the request, inside the floor.
        mem = max(req.memory_gib, 3)
        d = descriptor(job_name("run", a.block[:3], JUDGE), run_script(a.block), req.cpu, f"{mem}Gi", "20Gi", a.block, gpu=1,
                       extra={"g3i/gpu": GPU_PRODUCT})
        items.append((d, usage, True))
        print(f"{d.name} on {GPU_PRODUCT}: cpu={req.cpu} memory={mem}Gi from {src}: {req.note}; pilot gpu util {w['gpu_util_mean']}%")
    elif a.cmd == "fetch":
        script = (f"set -euo pipefail\ncd /data/runs/g3i/{JUDGE}\n"
                  f"tar -czf - {a.block} | base64 -w0\necho\necho FETCH_DONE\n")
        items = [(descriptor(job_name("fetch", a.block[:3]), script, 1, "2Gi", "2Gi", "fetch"), None, False)]
    problems = {d.name: preflight(d, u, g) for d, u, g in items}
    bad = {k: v for k, v in problems.items() if v}
    for k, v in bad.items():
        print(f"PREFLIGHT VETO {k}: " + "; ".join(v))
    if bad:
        return 2
    print(f"{a.cmd}: {len(items)} descriptors pass preflight")
    if a.dry_run:
        print(json.dumps(items[0][0].to_dict(), indent=1)[:3000]) if items else None
        return 0
    names = []
    for d, _, gpu in items:
        while gpu and heavy_running() >= MAX_HEAVY:
            print("four heavy GPU pods running; waiting", flush=True)
            time.sleep(120)
        print(d.name, "created", submit(d), flush=True)
        names.append(d.name)
    if a.no_wait:
        return 0
    state = wait(names)
    if a.cmd == "fetch" and state.get(names[0]) == "SUCCEEDED":
        log = kubectl("logs", f"job/{names[0]}").stdout
        blob = next(l for l in log.splitlines() if l and not l.startswith(("tar", "FETCH")))
        dest = Path("/home/claude/g3i_nrp") / JUDGE
        dest.mkdir(parents=True, exist_ok=True)
        tarfile.open(fileobj=io.BytesIO(base64.b64decode(blob)), mode="r:gz").extractall(dest)
        kubectl("delete", "job", names[0])
        print("fetched into", dest)
    return 0 if all(v == "SUCCEEDED" for v in state.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
