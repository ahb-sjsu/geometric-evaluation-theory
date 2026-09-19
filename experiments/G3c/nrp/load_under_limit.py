"""Load a judge and score a few worksheets inside a hard memory limit, to check that the loading
peak of the pilots, which is clean file-backed pages of the weight files, is reclaimable and sets
no floor on an NRP memory request. Not a registered stage. Run on Atlas under a cgroup limit:

    sudo systemd-run --scope -p MemoryMax=2G -p MemorySwapMax=0 --uid=claude --setenv=... \\
        python load_under_limit.py --config ../prereg_config.json --model gemma4b --out limit_gemma4b.json

The judge is loaded exactly as in the run (judge.LMJudge), then scores 16 calibration worksheets
on all three scales through the same code path. The record keeps the load time, the scoring time,
the cgroup's own peak (memory.peak) and the process's resident peaks. Passing means the process
was not killed and its results match the same worksheets scored without a limit, which the
caller checks against the pilot's records.
"""
from __future__ import annotations

import argparse
import copy
import json
import resource
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import judge  # noqa: E402


def cgroup_file(name: str) -> str | None:
    try:
        rel = open("/proc/self/cgroup").read().strip().split("::")[-1]
        return open(f"/sys/fs/cgroup{rel}/{name}").read().strip()
    except Exception:
        return None


def status() -> dict:
    out = {}
    for line in open("/proc/self/status"):
        k, _, v = line.partition(":")
        if k in ("VmHWM", "VmRSS", "RssAnon", "RssFile"):
            out[k + "_gib"] = round(int(v.split()[0]) / 2**20, 3)
    return out


def evict(spec: dict) -> dict:
    """Drop this model's weight files from the page cache, file by file, so that loading faults
    them into this cgroup. Pages cached earlier stay charged to whoever read them first, and a
    test that skipped this step would pass without testing anything."""
    import os
    from huggingface_hub import snapshot_download
    snap = Path(snapshot_download(spec["model_id"], revision=spec.get("revision"), local_files_only=True))
    files = [f for f in snap.rglob("*") if f.is_file() or f.is_symlink()]
    resident = {}
    for f in files:
        real = f.resolve()
        fd = os.open(real, os.O_RDONLY)
        try:
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        finally:
            os.close(fd)
    for f in files:
        if f.name.endswith(".safetensors"):
            resident[f.name] = [resident_bytes(f.resolve()), os.path.getsize(f.resolve())]
    return {"snapshot": str(snap), "resident_and_size_bytes_after_evict": resident}


def resident_bytes(path) -> int:
    """Bytes of the file in the page cache, by mincore on a mapping that faults nothing in."""
    import ctypes
    import os
    libc = ctypes.CDLL("libc.so.6", use_errno=True)
    libc.mmap.restype = ctypes.c_void_p
    libc.mmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_long]
    size = os.path.getsize(path)
    if size == 0:
        return 0
    fd = os.open(path, os.O_RDONLY)
    try:
        addr = libc.mmap(None, size, 1, 1, fd, 0)          # PROT_READ, MAP_SHARED
        pages = (size + 4095) // 4096
        vec = (ctypes.c_ubyte * pages)()
        libc.mincore(ctypes.c_void_p(addr), ctypes.c_size_t(size), vec)
        libc.munmap(ctypes.c_void_p(addr), ctypes.c_size_t(size))
        return int(sum(v & 1 for v in vec)) * 4096
    finally:
        os.close(fd)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True); ap.add_argument("--model", required=True)
    ap.add_argument("--precision", default="full"); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8"))
    spec = {m["key"]: m for m in cfg["models"]}[a.model]
    cfg = {**cfg, **{k: spec[k] for k in ("batch", "batch_tree", "batch_pairwise", "tree_rows") if k in spec}}
    rec = {"model": a.model, "precision": a.precision, "memory_max": cgroup_file("memory.max"), "evict": evict(spec)}
    t0 = time.time()
    J = judge.LMJudge(spec, a.precision, cfg)
    rec["load_seconds"] = round(time.time() - t0, 1); rec["after_load"] = status()
    small = copy.deepcopy(cfg); small["n_cal_per_level"] = 1
    data = judge.make_block(small, "calibration", int(cfg["seeds"]["pilot_calibration"]))
    texts = [s["text"] for s in data["sheets"]][::4][:16]
    rec["scores"] = {}
    t1 = time.time()
    for scale in cfg["scales"]:
        key = f"{scale['lo']}-{scale['hi']}"
        recs = J.score(texts, scale, int(cfg["n_samples"]), 1.0, int(cfg["batch"]))
        rec["scores"][key] = [r["argmax"] for r in recs]
    rec["score_seconds"] = round(time.time() - t1, 1)
    rec["after_score"] = status()
    rec["ru_maxrss_gib"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20, 3)
    rec["cgroup_memory_peak_gib"] = (round(int(cgroup_file("memory.peak")) / 2**30, 3)
                                     if (cgroup_file("memory.peak") or "").isdigit() else None)
    rec["cgroup_oom_events"] = cgroup_file("memory.events")
    J.close()
    json.dump(rec, open(a.out, "w"), indent=1)
    print(json.dumps({k: v for k, v in rec.items() if k != "scores"}))
    print("LIMIT_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
