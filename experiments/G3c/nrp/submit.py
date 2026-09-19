"""G3c on NRP Nautilus, namespace ssu-atlas-ai, through nats-bursting. Run on Atlas.

    python submit.py pvc                           # print the PVC manifest (apply it once)
    python submit.py setup    [--dry-run]          # CPU job: pinned venv, tarred onto the PVC
    python submit.py stage    [--dry-run]          # CPU jobs: model weights onto the PVC
    python submit.py run --role run --block calibration [--models qwen7b,...] [--dry-run]
    python submit.py run --role run --block test        [--models ...] [--dry-run]
    python submit.py fetch --role run --block calibration   # results back to Atlas via job logs

Policy (reference_nrp_job_policies.md, scored item by item in ``preflight``):
* requests from MEASUREMENT: GPU jobs are sized by nrp_sizing.py (vendored from turboquant-pro)
  from the meter record of a completed pilot on the same model; a model never measured is
  refused. CPU jobs sit in the exempt class, 1 CPU and 2 GiB.
* requests == limits (the renderer), ephemeral storage declared, backoff_limit 0.
* jobs terminate by themselves; nothing sleeps.
* GPU pods do no pip, clone or download: the venv and the weights are staged by CPU jobs.
* at most four heavy GPU pods in the namespace at once.
* untainted V100-SXM2-32GB nodes only: the pilot's hardware class (Volta, 32 GB), no toleration.
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
sys.path.insert(0, str(Path(__file__).resolve().parent))   # nrp_sizing.py, vendored from turboquant-pro

HERE = Path(__file__).resolve().parent
G3C = HERE.parent
NS = "ssu-atlas-ai"
PVC = "g3c-judge"
CODE_CM = "g3c-code"
BATCH = "g3c-judge"
IMAGE = "pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime"   # the pinned torch 2.8.0 + cu128
GPU_NODE = {"nvidia.com/gpu.product": "Tesla-V100-SXM2-32GB"}
# CPU jobs that write the venv and ~60 GB of weights sit on the Ceph campus; ucsd-nrp scheduled at
# once on 2026-09-15 where ucsd-suncave left pods pending for 40 minutes
CPU_ZONE = {"topology.kubernetes.io/zone": "ucsd-nrp"}
MAX_HEAVY = 4
PINS = "transformers==4.56.1 bitsandbytes==0.50.2 accelerate==1.14.0 huggingface_hub safetensors numpy"
METER_ROOT = Path("/home/claude/g3c")          # pilot results carrying the meter record

PVC_MANIFEST = f"""apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {PVC}
  namespace: {NS}
spec:
  accessModes: [ReadWriteMany]
  storageClassName: rook-cephfs
  resources:
    requests:
      storage: 120Gi
"""

SETUP = f"""set -euo pipefail
export PIP_ROOT_USER_ACTION=ignore PYTHONUNBUFFERED=1
if [ -f /data/env/g3c-env.tar ]; then echo "env exists"; exit 0; fi
python -m venv --system-site-packages /tmp/venv
/tmp/venv/bin/pip install -q --no-cache-dir {PINS}
/tmp/venv/bin/python -c "import torch, transformers, bitsandbytes; print(torch.__version__, transformers.__version__, bitsandbytes.__version__)"
/tmp/venv/bin/pip freeze > /tmp/freeze.txt
mkdir -p /data/env && tar -cf /data/env/g3c-env.tar.tmp -C /tmp venv freeze.txt
mv /data/env/g3c-env.tar.tmp /data/env/g3c-env.tar && cp /tmp/freeze.txt /data/env/freeze.txt
echo SETUP_DONE
"""

ENV = """set -euo pipefail
export PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True G3C_MODEL_ROOT=/data/models
tar -xf /data/env/g3c-env.tar -C /tmp
export PATH=/tmp/venv/bin:$PATH
mkdir -p /work/g3b /work/g3c && cp /code/g3b.py /work/g3b/ && cp /code/judge.py /code/judge_grade.py /code/prereg_config.json /work/g3c/
cd /work/g3c
"""


def cfg() -> dict:
    return json.load(open(G3C / "prereg_config.json", encoding="utf-8"))


def kubectl(*args, check=False):
    r = subprocess.run(["kubectl", "-n", NS, "--request-timeout=60s", *args], capture_output=True, text=True, timeout=120)
    if check and r.returncode:
        raise SystemExit(f"kubectl {' '.join(args)}: {r.stderr.strip()}")
    return r


# ----------------------------------------------------------------------------- sizing

def measured_usage(model: str, precision: str):
    """The meter record of a completed pilot calibration on this model and precision, as the
    time-averaged usage the NRP floors are judged on. None if the model was never measured."""
    import nrp_sizing as sizing
    cands = sorted(METER_ROOT.glob(f"pilot*/calibration/{model}__{precision}/results.json"))
    for p in reversed(cands):
        r = json.load(open(p))
        w = (r.get("meter") or {}).get("whole_run")
        if w and w.get("seconds", 0) > 600:
            return sizing.Usage(mean_cpu_cores=float(w["mean_cores"]),
                                mean_mem_gib=float(w.get("VmRSS_mean_gib", 0.0)),
                                peak_mem_gib=float(w.get("VmRSS_peak_gib", 0.0))), str(p), w
    return None, None, None


def preflight(desc, usage, gpu: bool) -> list[str]:
    """Every row of the NRP checklist that can be checked before submission."""
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
            bad.append("no measured usage for this model and precision: run its pilot first")
        else:
            bad += sizing.check(int(cpu), mem, usage)
        if any(w in script for w in ("pip install", "git clone", "snapshot_download", "apt-get")):
            bad.append("a GPU job installs or downloads")
    else:
        if cpu > 1 or mem > 2:
            bad.append("a CPU job outside the exempt class (1 CPU, 2 GiB)")
    return bad


# ----------------------------------------------------------------------------- descriptors

def descriptor(name, script, cpu, memory, eph, role, gpu=0, extra=None):
    from nats_bursting import JobDescriptor, Resources, Volume
    vols = [Volume(name="data", mount_path="/data", claim_name=PVC),
            Volume(name="code", mount_path="/code", config_map=CODE_CM, read_only=True)]
    labels = {"app": "g3c", "atlas.io/batch": BATCH, "atlas.io/role": role, **(extra or {})}
    return JobDescriptor(name=name, image=IMAGE, command=["/bin/bash", "-lc", script],
                         resources=Resources(cpu=str(cpu), memory=memory, gpu=gpu, ephemeral_storage=eph),
                         labels=labels, node_selector=dict(GPU_NODE) if gpu else dict(CPU_ZONE), backoff_limit=0, volumes=vols)


def stage_script(key: str, model_id: str, revision: str | None) -> str:
    rev = f" --revision {revision}" if revision else ""
    return ("set -euo pipefail\n"
            "export PIP_ROOT_USER_ACTION=ignore PYTHONUNBUFFERED=1\n"
            "tar -xf /data/env/g3c-env.tar -C /tmp\n"
            f"/tmp/venv/bin/python /code/stage_models.py --model-id {model_id}{rev} --dest /data/models/{key}\n")


def run_script(model: str, precision: str, block: str, role: str) -> str:
    return (ENV + f"python judge.py run --config prereg_config.json --role {role} --block {block} "
            f"--model {model} --precision {precision} --out /data/runs/{role}\n"
            f"echo RUN_DONE {model} {precision} {block}\n")


def job_name(*parts) -> str:
    return "g3c-" + "-".join(str(p).replace("_", "-").replace(".", "") for p in parts).lower()


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
    """Poll job status until every job has succeeded or failed; a missing job is a failure."""
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
    ap.add_argument("cmd", choices=["pvc", "code", "setup", "stage", "run", "fetch"])
    ap.add_argument("--role", default="run"); ap.add_argument("--block", default="calibration")
    ap.add_argument("--models", default=""); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    c = cfg()
    if a.cmd == "pvc":
        print(PVC_MANIFEST); return 0
    if a.cmd == "code":
        files = [G3C.parent / "G3b" / "g3b.py", G3C / "judge.py", G3C / "judge_grade.py", G3C / "prereg_config.json", HERE / "stage_models.py"]
        args = ["create", "configmap", CODE_CM, "--dry-run=client", "-o", "yaml"] + [f"--from-file={f}" for f in files]
        y = kubectl(*args, check=True).stdout
        r = subprocess.run(["kubectl", "-n", NS, "apply", "-f", "-"], input=y, capture_output=True, text=True)
        print(r.stdout or r.stderr); return r.returncode
    items = []
    if a.cmd == "setup":
        items = [(descriptor(job_name("setup"), SETUP, 1, "2Gi", "12Gi", "setup"), None, False)]
    elif a.cmd == "stage":
        want = set(a.models.split(",")) if a.models else None
        for m in c["models"]:
            if want and m["key"] not in want:
                continue
            items.append((descriptor(job_name("stage", m["key"]), stage_script(m["key"], m["model_id"], m.get("revision")),
                                     1, "2Gi", "10Gi", "stage"), None, False))
    elif a.cmd == "run":
        want = set(a.models.split(",")) if a.models else None
        import nrp_sizing as sizing
        for m in c["models"]:
            if want and m["key"] not in want:
                continue
            for prec in m["precisions"]:
                usage, src, _ = measured_usage(m["key"], prec)
                req = sizing.request_for(usage, want_cpu=1)
                if isinstance(req, sizing.Refusal):
                    print(f"REFUSED {m['key']} {prec}: {req}"); continue
                d = descriptor(job_name(a.role, a.block[:3], m["key"], prec), run_script(m["key"], prec, a.block, a.role),
                               req.cpu, f"{req.memory_gib}Gi", "16Gi", a.block, gpu=1,
                               extra={"g3c/model": m["key"], "g3c/precision": prec})
                items.append((d, usage, True))
                print(f"{d.name}: {req} (measured in {src})")
    elif a.cmd == "fetch":
        script = (f"set -euo pipefail\ncd /data/runs/{a.role}\n"
                  f"tar -czf - {a.block} | base64 -w0\necho\necho FETCH_DONE\n")
        items = [(descriptor(job_name("fetch", a.role, a.block[:3]), script, 1, "2Gi", "2Gi", "fetch"), None, False)]
    problems = {d.name: preflight(d, u, g) for d, u, g in items}
    bad = {k: v for k, v in problems.items() if v}
    for k, v in bad.items():
        print(f"PREFLIGHT VETO {k}: " + "; ".join(v))
    if bad:
        return 2
    print(f"{a.cmd}: {len(items)} descriptors pass preflight")
    if a.dry_run:
        print(json.dumps(items[0][0].to_dict(), indent=1)[:2500]) if items else None
        return 0
    names = []
    for d, _, gpu in items:
        while gpu and heavy_running() >= MAX_HEAVY:
            print("four heavy GPU pods running; waiting", flush=True)
            time.sleep(120)
        print(d.name, "created", submit(d), flush=True)
        names.append(d.name)
    state = wait(names)
    if a.cmd == "fetch" and state.get(names[0]) == "SUCCEEDED":
        log = kubectl("logs", f"job/{names[0]}").stdout
        blob = next(l for l in log.splitlines() if l and not l.startswith(("tar", "FETCH")))
        dest = METER_ROOT / "nrp" / a.role
        dest.mkdir(parents=True, exist_ok=True)
        tarfile.open(fileobj=io.BytesIO(base64.b64decode(blob)), mode="r:gz").extractall(dest)
        kubectl("delete", "job", names[0])
        print("fetched into", dest)
    return 0 if all(v == "SUCCEEDED" for v in state.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
