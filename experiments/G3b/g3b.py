"""G3b harness: the grid-channel law and the resolution-reliability split across model families,
tokenizers and a second consequence map.

What is new against G3 (experiments/G3/g3_threshold.py, sealed, not modified):

* One generation per value serves every report length. Greedy decoding with a budget of k
  tokens produces exactly the first k tokens of the unbounded greedy generation, so a report
  cell at budget k is derived by truncating the full generation to its first k tokens. The
  probe verifies the equivalence on real generations (``probe --check-truncation``) before
  sealing; it is not assumed.
* Every value's full generation is persisted with its token ids, its decoded prefix at every
  registered budget, its generated length and whether it stopped before the budget (Rule 8).
  Pair-level preferences are derived by the grader from these records, so a paired bootstrap
  over pairs is possible and every cell of a task uses the same pairs.
* A second consequence map (task B): the Euclidean distance of a point from a target point.
* A reference evaluator per cell: exact arithmetic on the rendered inputs, reported at three
  decimals, truncated to the report grid the model's tokenizer affords at budget k. It is the
  exact evaluator behind the channel, computed on the same pairs.
* Cells are sharded across processes or pods (``plan``), grouped so each shard loads each
  (model, precision) once, and merged afterwards (``merge``).
* A meter records, for the whole run and per phase, anonymous and file-backed resident memory,
  the cgroup's memory and working set when running in a container, CPU seconds, and GPU
  utilization, which is what an NRP submission has to be sized from.
* Model weights are loaded straight to the GPU; after loading the host heap is trimmed and
  the page cache of the weight files is dropped, so steady-state memory is not the load peak.

Commands
    python g3b.py plan    --config prereg_config.json --nshards 4 --out plan.json
    python g3b.py run     --config prereg_config.json --role pilot --plan plan.json --shard 0 --out OUT
    python g3b.py merge   --config prereg_config.json --role pilot --plan plan.json --out OUT
    python g3b.py probe   --config prereg_config.json --model qwen7b --out OUT

The grid-channel law is tested against a reference evaluator on the same pairs, not against the
nominal step alone: the reference carries every property of the design that the idealized law
ignores, such as the jitter that rounding task B's coordinates puts on its distance.
Synthetic judges (``model_id`` beginning ``synthetic:``) run the same code path without a GPU;
``g3b_selftest.py`` uses them.
"""
from __future__ import annotations

import argparse
import gc
import gzip
import json
import math
import os
import platform
import re
import subprocess
import sys
import threading
import time
import zlib
from pathlib import Path

import numpy as np

NUM_RE = re.compile(r"-?\d+(?:\.\d*)?")
TASK_INDEX = {"A": 0, "B": 1}


# ----------------------------------------------------------------------------- rendering

def render(x: float, decimals: int) -> str:
    return f"{x:.{decimals}f}"


def parse_report(text: str) -> float:
    m = NUM_RE.search(text.replace(",", ""))
    if not m:
        return float("nan")
    s = m.group(0).rstrip(".")
    return float(s) if s not in ("", "-") else float("nan")


def render_target(cfg: dict, task: str, dec: int) -> str:
    t = cfg["tasks"][task]["target"]
    if task == "A":
        return render(float(t), dec)
    return f"({render(float(t[0]), dec)}, {render(float(t[1]), dec)})"


def render_value(task: str, v, dec: int) -> str:
    if task == "A":
        return render(float(v), dec)
    return f"({render(float(v[0]), dec)}, {render(float(v[1]), dec)})"


def consequence_of_rendered(task: str, target_str: str, value_str: str) -> float:
    """Exact consequence of what the judge was shown."""
    if task == "A":
        return abs(float(value_str) - float(target_str))
    tx, ty = [float(s) for s in target_str.strip("()").split(",")]
    x, y = [float(s) for s in value_str.strip("()").split(",")]
    return math.hypot(x - tx, y - ty)


# ----------------------------------------------------------------------------- pairs

def distance_range(cfg: dict, task: str, gap: float) -> tuple[float, float]:
    for max_gap, dmin, dmax in cfg["tasks"][task]["distance_ranges"]:
        if gap <= max_gap:
            return float(dmin), float(dmax)
    raise ValueError(f"no distance range for gap {gap}")


def make_pairs(cfg: dict, task: str, seed: int) -> list[dict]:
    """Pairs of options whose true consequences differ by each ladder gap, drawn continuously so
    the phase of either consequence relative to any grid is uniform. The same seed gives the
    same pairs in every process, so every cell of a task is evaluated on the same pairs."""
    rng = np.random.default_rng([int(seed), TASK_INDEX[task]])
    t = cfg["tasks"][task]["target"]
    n = int(cfg["n_pairs_per_gap"])
    period = float(cfg.get("phase_period", 10.0))
    pairs = []
    for gap in cfg["gap_ladder"]:
        gap = float(gap)
        dmin, dmax = distance_range(cfg, task, gap)
        # The span of the closer distance is a whole number of periods of the coarsest grid, so
        # its phase relative to every grid that divides the period is uniform, which is the
        # hypothesis of the grid-channel law. G3 drew from the whole range, and at step 10 the
        # span of 25 at gap 5 put the one-token cell at 0.40 rather than 0.50.
        width = dmax - gap - dmin
        span = math.floor(width / period) * period if width >= period else width
        for i in range(n):
            d_close = float(dmin + rng.uniform(0.0, span))
            d_far = d_close + gap
            if task == "A":
                sc, sf = rng.choice([-1.0, 1.0]), rng.choice([-1.0, 1.0])
                close, far = float(t) + sc * d_close, float(t) + sf * d_far
            else:
                a1, a2 = rng.uniform(0.0, 2.0 * math.pi, 2)
                close = [float(t[0]) + d_close * math.cos(a1), float(t[1]) + d_close * math.sin(a1)]
                far = [float(t[0]) + d_far * math.cos(a2), float(t[1]) + d_far * math.sin(a2)]
            pairs.append({"pid": len(pairs), "gap": gap, "i": i, "close": close, "far": far,
                          "d_close": d_close, "d_far": d_far})
    return pairs


# ----------------------------------------------------------------------------- report grids

def afforded_steps(pieces: list[str], budgets: list[int]) -> dict[int, float]:
    """The resolution a report truncated to its first k tokens can express, from the token
    pieces of a representative two-digit report such as '27.375'. A prefix missing integer
    digits resolves 10 per missing digit, a prefix ending at or before the point resolves 1,
    a prefix with m decimals resolves 10**-m, and an unparsable prefix resolves nothing."""
    full = "".join(pieces)
    int_digits = len(full.split(".")[0].lstrip("-"))
    out = {}
    for k in budgets:
        pre = "".join(pieces[:k]).strip()
        if not NUM_RE.search(pre):
            out[int(k)] = float("inf")
            continue
        num = NUM_RE.search(pre).group(0)
        if "." in num and len(num.split(".")[1]) > 0:
            out[int(k)] = 10.0 ** (-len(num.split(".")[1]))
        else:
            have = len(num.split(".")[0].lstrip("-"))
            out[int(k)] = 10.0 ** max(0, int_digits - have)
    return out


def split_char(text: str) -> list[str]:
    return list(text)


def split_group3(text: str) -> list[str]:
    return re.findall(r"\d{1,3}|\D", text)


# ----------------------------------------------------------------------------- meter

class Meter:
    """Samples this process's memory and CPU, the container cgroup when present, and GPU
    utilization, and summarizes them per phase. Nothing is estimated: every figure is a
    reading, which is what an NRP request has to be sized from."""

    def __init__(self, interval: float = 1.0, gpu_interval: float = 5.0):
        self.interval, self.gpu_interval = interval, gpu_interval
        self.samples: list[dict] = []
        self.marks: list[tuple[float, str]] = []
        self._stop = threading.Event()
        self._t0 = time.time()
        self._last_gpu = -1e9
        self._gpu = None
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        self.mark("start")
        self._thread.start()
        return self

    def mark(self, name: str):
        self.marks.append((time.time() - self._t0, name))

    def stop(self):
        self.mark("stop")
        self._stop.set()
        self._thread.join(timeout=5)

    @staticmethod
    def _proc_status() -> dict:
        out = {}
        try:
            for line in open("/proc/self/status"):
                k, _, v = line.partition(":")
                if k in ("VmRSS", "RssAnon", "RssFile", "VmHWM"):
                    out[k] = int(v.split()[0]) / 1048576.0   # GiB
        except OSError:
            pass
        return out

    @staticmethod
    def _cgroup() -> dict:
        out = {}
        try:
            out["cg_current"] = int(open("/sys/fs/cgroup/memory.current").read()) / 1073741824.0
            stat = dict(l.split() for l in open("/sys/fs/cgroup/memory.stat"))
            for k in ("anon", "file", "inactive_file"):
                if k in stat:
                    out[f"cg_{k}"] = int(stat[k]) / 1073741824.0
            if "cg_inactive_file" in out:
                out["cg_working_set"] = out["cg_current"] - out["cg_inactive_file"]
        except (OSError, ValueError):
            pass
        return out

    def _gpu_util(self):
        dev = os.environ.get("CUDA_VISIBLE_DEVICES", "").split(",")[0].strip()
        cmd = ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader,nounits"]
        if dev.isdigit():
            cmd += ["-i", dev]
        try:
            line = subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip().splitlines()[0]
            u, m = [float(x) for x in line.split(",")]
            return u, m / 1024.0
        except Exception:
            return None

    def _loop(self):
        while not self._stop.is_set():
            t = time.time() - self._t0
            s = {"t": round(t, 2)}
            s.update(self._proc_status())
            s.update(self._cgroup())
            tm = os.times()
            s["cpu_s"] = tm.user + tm.system
            if t - self._last_gpu >= self.gpu_interval:
                g = self._gpu_util()
                if g:
                    s["gpu_util"], s["gpu_mem_gib"] = g
                self._last_gpu = t
            self.samples.append(s)
            self._stop.wait(self.interval)

    def summary(self) -> dict:
        def phase(t0, t1):
            ss = [s for s in self.samples if t0 <= s["t"] <= t1]
            if len(ss) < 2:
                return None
            dt = ss[-1]["t"] - ss[0]["t"]
            rec = {"seconds": round(dt, 1), "mean_cores": round((ss[-1]["cpu_s"] - ss[0]["cpu_s"]) / dt, 3) if dt > 0 else None}
            for k in ("RssAnon", "RssFile", "VmRSS", "cg_current", "cg_working_set", "cg_anon", "cg_file"):
                v = [s[k] for s in ss if k in s]
                if v:
                    rec[f"{k}_mean_gib"] = round(float(np.mean(v)), 3)
                    rec[f"{k}_peak_gib"] = round(float(np.max(v)), 3)
            g = [s["gpu_util"] for s in ss if "gpu_util" in s]
            if g:
                g = np.asarray(g)
                rec["gpu_util_mean"] = round(float(g.mean()), 1)
                rec["gpu_util_share_above_40"] = round(float((g > 40).mean()), 3)
                rec["gpu_samples"] = int(g.size)
            return rec
        marks = sorted(self.marks)
        phases = {}
        for (t0, n0), (t1, _n1) in zip(marks, marks[1:]):
            p = phase(t0, t1)
            if p:
                phases[f"{t0:08.1f}_{n0}"] = p
        return {"whole_run": phase(0.0, 1e12), "phases": phases, "n_samples": len(self.samples),
                "VmHWM_gib": max((s.get("VmHWM", 0.0) for s in self.samples), default=None)}


# ----------------------------------------------------------------------------- judges

class LMScorer:
    """A causal language model shown a target and one value, asked how far apart they are, and
    answering with a number. Loaded straight to GPU 0 of the process."""

    def __init__(self, spec: dict, precision: str, cfg: dict):
        import torch
        import transformers
        from transformers import AutoTokenizer
        self.torch = torch
        mid, rev = spec["model_id"], spec.get("revision")
        self.tok = AutoTokenizer.from_pretrained(mid, revision=rev)
        kw = {"device_map": {"": 0}, "low_cpu_mem_usage": True}
        if rev:
            kw["revision"] = rev
        if precision == "full":
            kw["torch_dtype"] = torch.bfloat16
        elif precision in ("int8", "int4"):
            from transformers import BitsAndBytesConfig
            kw["quantization_config"] = (BitsAndBytesConfig(load_in_8bit=True) if precision == "int8" else
                                         BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                                            bnb_4bit_compute_dtype=torch.bfloat16))
        else:
            raise ValueError(precision)
        model = None
        for cls_name in ("AutoModelForCausalLM", "AutoModelForImageTextToText"):
            cls = getattr(transformers, cls_name, None)
            if cls is None:
                continue
            try:
                model = cls.from_pretrained(mid, **kw)
                self.model_class = cls_name
                break
            except ValueError:
                continue
        if model is None:
            raise RuntimeError(f"no auto class loads {mid}")
        self.model = model.eval()
        self.loaded_revision = getattr(self.model.config, "_commit_hash", None)
        self._release_host_memory(mid)
        self.chat = bool(cfg.get("use_chat_template", True)) and self.tok.chat_template is not None
        stop = set()
        for src in (getattr(self.model.generation_config, "eos_token_id", None), self.tok.eos_token_id,
                    self.tok.pad_token_id):
            if isinstance(src, int):
                stop.add(src)
            elif isinstance(src, (list, tuple)):
                stop.update(int(x) for x in src)
        self.stop_ids = stop
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token
        self.tok.padding_side = "left"
        self.templates = cfg["prompt_templates"]

    def _release_host_memory(self, mid: str):
        """The weights live on the GPU; return the loader's host heap to the OS and drop the
        page cache of the weight files, so the steady state is not the load peak."""
        gc.collect()
        try:
            import ctypes
            ctypes.CDLL("libc.so.6").malloc_trim(0)
        except Exception:
            pass
        try:
            from huggingface_hub import snapshot_download
            path = snapshot_download(mid, local_files_only=True)
            for f in Path(path).glob("*.safetensors"):
                fd = os.open(str(f), os.O_RDONLY)
                try:
                    os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
                finally:
                    os.close(fd)
        except Exception:
            pass

    def pieces(self, text: str) -> list[str]:
        ids = self.tok(text, add_special_tokens=False)["input_ids"]
        return [self.tok.decode([i]) for i in ids]

    def _prompt(self, task: str, target: str, value: str) -> str:
        user = self.templates[task].format(target=target, value=value)
        if self.chat:
            return self.tok.apply_chat_template([{"role": "user", "content": user}], tokenize=False,
                                                add_generation_prompt=True)
        return user

    def generate(self, task: str, target: str, values: list[str], k: int, budgets: list[int],
                 batch: int = 32) -> list[dict]:
        torch = self.torch
        out = []
        for i in range(0, len(values), batch):
            chunk = values[i:i + batch]
            enc = self.tok([self._prompt(task, target, v) for v in chunk], return_tensors="pt",
                           padding=True).to(self.model.device)
            with torch.no_grad():
                gen = self.model.generate(**enc, max_new_tokens=int(k), do_sample=False,
                                          pad_token_id=self.tok.pad_token_id)
            for v, row in zip(chunk, gen[:, enc["input_ids"].shape[1]:].tolist()):
                n = next((j for j, t in enumerate(row) if t in self.stop_ids), len(row))
                ids = row[:n]
                out.append({"value": v, "ids": ids, "text": self.tok.decode(ids, skip_special_tokens=True),
                            "n_gen": n, "stopped_early": n < int(k),
                            "prefix": {str(b): self.tok.decode(ids[:b], skip_special_tokens=True) for b in budgets}})
        return out

    def close(self):
        del self.model
        gc.collect()
        try:
            self.torch.cuda.empty_cache()
        except Exception:
            pass


class SyntheticScorer:
    """An evaluator of known structure for the self-test. It computes the exact consequence of
    the rendered inputs, optionally adds Gaussian noise, garbles a report with a probability
    that may depend on the weight precision, prints three decimals, and splits the report into
    tokens one character at a time or in digit groups of up to three. Reports are a
    deterministic function of the value, like greedy decoding."""

    def __init__(self, spec: dict, precision: str, cfg: dict):
        p = spec["synthetic"]
        self.kind = p.get("kind", "exact")
        self.noise_sd = float(p.get("noise_sd", 0.0))
        self.coarsen = float(p.get("coarsen", 1.0))   # kind "coarse": resolves this multiple of what it is shown
        self.garble = float(p.get("garble", {}).get(precision, 0.0))
        self.split = split_group3 if p.get("tokenizer", "char") == "group3" else split_char
        self.seed = int(p.get("seed", 0)) + {"full": 0, "int8": 1, "int4": 2}[precision]
        self.model_class = "synthetic"
        self.loaded_revision = "synthetic"

    def pieces(self, text: str) -> list[str]:
        return self.split(text)

    def generate(self, task: str, target: str, values: list[str], k: int, budgets: list[int],
                 batch: int = 32) -> list[dict]:
        out = []
        for v in values:
            rng = np.random.default_rng([self.seed, zlib.crc32(f"{task}|{target}|{v}".encode())])
            c = consequence_of_rendered(task, target, v)
            if self.kind == "coarse":
                m = NUM_RE.search(v)
                dec = len(m.group(0).split(".")[1]) if m and "." in m.group(0) else 0
                step = self.coarsen * 10.0 ** (-dec)
                c = math.floor(c / step + 1e-9) * step
            if self.noise_sd > 0:
                c = abs(c + rng.normal(0.0, self.noise_sd))
            if rng.random() < self.garble:
                c = float(rng.uniform(10.0, 40.0))
            pieces = self.split(f"{c:.3f}")[:int(k)]
            out.append({"value": v, "ids": list(range(len(pieces))), "text": "".join(pieces),
                        "n_gen": len(pieces), "stopped_early": len(pieces) < int(k),
                        "prefix": {str(b): "".join(pieces[:b]) for b in budgets}})
        return out

    def close(self):
        pass


def make_judge(spec: dict, precision: str, cfg: dict):
    if str(spec["model_id"]).startswith("synthetic:"):
        return SyntheticScorer(spec, precision, cfg)
    return LMScorer(spec, precision, cfg)


# ----------------------------------------------------------------------------- cells and plan

def model_specs(cfg: dict) -> dict:
    return {m["key"]: m for m in cfg["models"] if not m.get("skip")}


def generation_cells(cfg: dict) -> list[dict]:
    """One generation cell per (model, precision, task, rendering decimals). Report cells at
    every registered budget are derived from it by truncation."""
    cells = []
    for m in cfg["models"]:
        if m.get("skip"):
            continue
        for p in m["precisions"]:
            for task in m.get("tasks", ["A", "B"]):
                if task == "B" and p != "full":
                    continue
                for dec in cfg["decimals_ladder"]:
                    cells.append({"id": f"{m['key']}__{p}__{task}__d{dec}", "model": m["key"], "precision": p,
                                  "task": task, "dec": int(dec)})
    return cells


def cell_cost(cfg: dict, c: dict) -> float:
    return float(model_specs(cfg)[c["model"]].get("cost", 1.0)) * float(cfg["tasks"][c["task"]].get("cost", 1.0))


def plan(cfg: dict, nshards: int) -> dict:
    """Longest-processing-time assignment of (model, precision) groups to shards, splitting a
    group across shards only when it is larger than an even share, so that most shards load
    each model once."""
    load = float(cfg.get("load_cost", 0.15))
    groups: dict[tuple, list] = {}
    for c in generation_cells(cfg):
        groups.setdefault((c["model"], c["precision"]), []).append(c)
    total = sum(cell_cost(cfg, c) for g in groups.values() for c in g) + load * len(groups)
    share = total / nshards
    chunks = []
    for key, cs in groups.items():
        cs = sorted(cs, key=lambda c: -cell_cost(cfg, c))
        cur, cost = [], load
        for c in cs:
            if cur and cost + cell_cost(cfg, c) > share:
                chunks.append((cost, cur)); cur, cost = [], load
            cur.append(c); cost += cell_cost(cfg, c)
        if cur:
            chunks.append((cost, cur))
    shards = [{"cost": 0.0, "cells": []} for _ in range(nshards)]
    for cost, cs in sorted(chunks, key=lambda x: -x[0]):
        s = min(shards, key=lambda s: s["cost"])
        s["cost"] += cost
        s["cells"] += [c["id"] for c in cs]
    return {"nshards": nshards, "total_cost": round(total, 3),
            "shards": [{"shard": i, "cost": round(s["cost"], 3), "cells": s["cells"]} for i, s in enumerate(shards)]}


# ----------------------------------------------------------------------------- run

def env_versions() -> dict:
    out = {"python": platform.python_version(), "host": platform.node()}
    for mod in ("numpy", "torch", "transformers", "bitsandbytes", "accelerate", "huggingface_hub"):
        try:
            out[mod] = __import__(mod).__version__
        except Exception:
            out[mod] = None
    try:
        import torch
        if torch.cuda.is_available():
            out["gpu"] = torch.cuda.get_device_name(0)
            out["cuda"] = torch.version.cuda
            out["capability"] = ".".join(map(str, torch.cuda.get_device_capability(0)))
    except Exception:
        pass
    return out


def seed_for(cfg: dict, role: str) -> int:
    s = cfg["seeds"].get(role)
    if s is None:
        raise SystemExit(f"no {role} seed in the config; the run seed is drawn only after sealing")
    return int(s)


def run_cells(cfg: dict, role: str, cell_ids: list[str], out_dir: str, judge_factory=make_judge,
              meter: Meter | None = None) -> dict:
    seed = seed_for(cfg, role)
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    by_id = {c["id"]: c for c in generation_cells(cfg)}
    cells = [by_id[i] for i in cell_ids]
    specs = model_specs(cfg)
    budgets = [int(b) for b in cfg["report_token_budgets"]]
    full_k = int(cfg["full_report_tokens"])
    pairs = {t: make_pairs(cfg, t, seed) for t in sorted({c["task"] for c in cells})}
    own_meter = meter is None
    meter = meter or Meter().start()
    result = {"gate": cfg.get("gate"), "role": role, "seed": seed, "cells": [], "env": env_versions(),
              "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    groups: dict[tuple, list] = {}
    for c in cells:
        groups.setdefault((c["model"], c["precision"]), []).append(c)
    for (mk, prec), cs in groups.items():
        meter.mark(f"load_{mk}_{prec}")
        judge = judge_factory(specs[mk], prec, cfg)
        meter.mark(f"loaded_{mk}_{prec}")
        for c in cs:
            meter.mark(f"cell_{c['id']}")
            t0 = time.time()
            tstr = render_target(cfg, c["task"], c["dec"])
            values = list(dict.fromkeys(render_value(c["task"], p[side], c["dec"])
                                        for p in pairs[c["task"]] for side in ("close", "far")))
            gens = judge.generate(c["task"], tstr, values, full_k, budgets, int(cfg.get("batch", 32)))
            fn = out / f"gens_{c['id']}.jsonl.gz"
            with gzip.open(fn, "wt", encoding="utf-8") as f:
                for g in gens:
                    f.write(json.dumps(g) + "\n")
            by_v = {g["value"]: g for g in gens}
            acc = []
            for p in pairs[c["task"]]:
                if p["gap"] != 20.0:
                    continue
                a = parse_report(by_v[render_value(c["task"], p["close"], c["dec"])]["text"])
                b = parse_report(by_v[render_value(c["task"], p["far"], c["dec"])]["text"])
                acc.append(1.0 if (a == a and b == b and a < b) else 0.0)
            meta = dict(c, target=tstr, n_values=len(values), gens_file=fn.name, seconds=round(time.time() - t0, 1),
                        model_class=judge.model_class, loaded_revision=judge.loaded_revision,
                        unparsed=int(sum(1 for g in gens if parse_report(g["text"]) != parse_report(g["text"]))),
                        stopped_early=int(sum(1 for g in gens if g["stopped_early"])),
                        acc_gap20=round(float(np.mean(acc)), 4) if acc else None)
            result["cells"].append(meta)
            print(json.dumps({k: meta[k] for k in ("id", "n_values", "seconds", "unparsed", "stopped_early", "acc_gap20")}),
                  flush=True)
            json.dump(result, open(out / "results.json", "w"), indent=1)
        judge.close()
        del judge
        gc.collect()
    result["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if own_meter:
        meter.stop()
    result["meter"] = meter.summary()
    with gzip.open(out / "meter_samples.json.gz", "wt") as f:
        json.dump({"samples": meter.samples, "marks": meter.marks}, f)
    json.dump(result, open(out / "results.json", "w"), indent=1)
    return result


def merge(cfg: dict, role: str, plan_obj: dict, out_dir: str) -> dict:
    out = Path(out_dir)
    want = [c for s in plan_obj["shards"] for c in s["cells"]]
    merged = {"gate": cfg.get("gate"), "role": role, "seed": seed_for(cfg, role), "cells": [], "shards": []}
    for s in plan_obj["shards"]:
        r = json.load(open(out / f"shard_{s['shard']}" / "results.json"))
        if r["seed"] != merged["seed"] or r["role"] != role:
            raise SystemExit(f"shard {s['shard']} has seed {r['seed']} role {r['role']}")
        for c in r["cells"]:
            c["gens_file"] = f"shard_{s['shard']}/{c['gens_file']}"
            merged["cells"].append(c)
        merged["shards"].append({"shard": s["shard"], "env": r["env"], "meter": r.get("meter"),
                                 "started": r.get("started"), "finished": r.get("finished")})
    have = [c["id"] for c in merged["cells"]]
    missing = sorted(set(want) - set(have))
    if missing:
        raise SystemExit(f"missing cells: {missing}")
    merged["config"] = cfg
    json.dump(merged, open(out / "results.json", "w"), indent=1)
    return merged


# ----------------------------------------------------------------------------- probe

def probe(cfg: dict, model_key: str, out_dir: str, check_truncation: bool = True, judge_factory=make_judge) -> dict:
    """Tokenizer audit, a generation sample, the truncation equivalence check, and the two
    full-precision generation cells at three decimals that decide anti-vacuity."""
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    spec = model_specs(cfg)[model_key]
    budgets = [int(b) for b in cfg["report_token_budgets"]]
    full_k = int(cfg["full_report_tokens"])
    rec = {"model": model_key, "env": env_versions()}
    meter = Meter().start()
    meter.mark("load")
    judge = judge_factory(spec, "full", cfg)
    meter.mark("loaded")
    rec["tokenizer"] = {}
    for s in cfg.get("tokenizer_examples", ["27.375", "10.123", "10", "0.001"]):
        rec["tokenizer"][s] = judge.pieces(s)
    rec["afforded_steps_from_tokenizer"] = {str(k): v for k, v in
                                            afforded_steps(judge.pieces("27.375"), budgets).items()}
    rec["loaded_revision"] = judge.loaded_revision
    rec["model_class"] = judge.model_class
    seed = int(cfg["seeds"]["probe"])
    for task in spec.get("tasks", ["A", "B"]):
        pairs = make_pairs(cfg, task, seed)
        tstr = render_target(cfg, task, 3)
        sample_vals = [render_value(task, p[s], 3) for p in pairs[:4] + pairs[-4:] for s in ("close", "far")]
        rec[f"sample_{task}"] = judge.generate(task, tstr, sample_vals, full_k, budgets)
        if check_truncation:
            vals = list(dict.fromkeys(render_value(task, p["close"], 3) for p in pairs[::max(1, len(pairs) // 32)]))[:32]
            full = judge.generate(task, tstr, vals, full_k, budgets)
            chk = {}
            for k in [b for b in budgets if b < full_k]:
                part = judge.generate(task, tstr, vals, k, budgets)
                chk[str(k)] = int(sum(1 for a, b in zip(full, part) if a["ids"][:k] == b["ids"][:k]))
            rec[f"truncation_equivalence_{task}"] = {"n": len(vals), "identical_by_k": chk}
    judge.close()
    meter.stop()
    rec["meter_load"] = meter.summary()
    json.dump(rec, open(out / f"probe_{model_key}.json", "w"), indent=1)
    probe_cells = [c["id"] for c in generation_cells(cfg)
                   if c["model"] == model_key and c["precision"] == "full" and c["dec"] == 3]
    cfg_probe = dict(cfg, seeds=dict(cfg["seeds"], probe_run=cfg["seeds"]["probe"]))
    run_cells(cfg_probe, "probe_run", probe_cells, str(out / f"probe_cells_{model_key}"), judge_factory)
    return rec


# ----------------------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["plan", "run", "merge", "probe", "cells"])
    ap.add_argument("--config", required=True)
    ap.add_argument("--role", default="pilot")
    ap.add_argument("--plan")
    ap.add_argument("--shard", type=int)
    ap.add_argument("--nshards", type=int, default=4)
    ap.add_argument("--model")
    ap.add_argument("--out", required=False, default="out")
    a = ap.parse_args(argv)
    cfg = json.load(open(a.config, encoding="utf-8"))
    if a.cmd == "cells":
        for c in generation_cells(cfg):
            print(c["id"])
    elif a.cmd == "plan":
        p = plan(cfg, a.nshards)
        json.dump(p, open(a.out, "w"), indent=1)
        for s in p["shards"]:
            print(s["shard"], s["cost"], len(s["cells"]))
    elif a.cmd == "run":
        p = json.load(open(a.plan))
        ids = p["shards"][a.shard]["cells"]
        run_cells(cfg, a.role, ids, str(Path(a.out) / f"shard_{a.shard}"))
    elif a.cmd == "merge":
        merge(cfg, a.role, json.load(open(a.plan)), a.out)
    elif a.cmd == "probe":
        probe(cfg, a.model, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
