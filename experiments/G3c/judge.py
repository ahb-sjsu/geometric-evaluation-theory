"""G3c harness: the resolution of a language-model judge on graded answers, and whether its
symbol budget predicts that resolution before it is measured.

Stimulus. A worksheet of N single-digit multiplications with a student's answers, e of them
wrong. Its quality is known exactly: q = 1 - e/N. Worksheets are generated from a seed and
stored, so every elicitation sees the same text.

Elicitations, all on the same worksheets.
  score      the judge rates one worksheet on a scale (1-5, 0-9, 0-100). One forward pass gives
             three read-outs of different symbol budgets:
               argmax    the greedy integer it writes (one symbol from its codebook)
               expected  the probability-weighted score over the codebook, from the first-token
                         logits (single-token scales only): the report is a probability vector
               mean_n    the mean of n samples at temperature T (n symbols, dithered)
  pairwise   the judge is shown two worksheets and asked which has more right, both orders,
             read from the letter logits with no deliberation.

Blocks.
  calibration  n_cal worksheets at every error count 0..N. Measures the codebook the judge
               actually uses and its score distribution at each quality level. Everything the
               grader predicts comes from this block alone.
  test         fresh worksheets in pairs whose error counts differ by each ladder gap. Drawn
               from a seed that is fixed only after the predictions are committed.

    python judge.py stimuli --config prereg_config.json --block calibration --out OUT
    python judge.py run     --config prereg_config.json --block calibration --model qwen7b --precision full --out OUT
    python judge.py run     --config prereg_config.json --block test        --model qwen7b --precision full --out OUT
Synthetic judges (model_id beginning "synthetic:") exercise the same path without a GPU.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import re
import sys
import time
import zlib
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "G3b"))
import g3b  # noqa: E402  (Meter, env_versions, host-memory release)

INT_RE = re.compile(r"-?\d+")
BLOCK_INDEX = {"calibration": 0, "test": 1}


# ----------------------------------------------------------------------------- stimuli

def make_worksheet(rng: np.random.Generator, n_items: int, e: int) -> dict:
    a = rng.integers(2, 10, n_items); b = rng.integers(2, 10, n_items)
    wrong = set(rng.choice(n_items, size=e, replace=False).tolist()) if e else set()
    lines, answers = [], []
    for i in range(n_items):
        c = int(a[i] * b[i])
        if i in wrong:
            while True:
                d = int(rng.choice([-10, -int(a[i]), -int(b[i]), -2, -1, 1, 2, int(a[i]), int(b[i]), 10]))
                if c + d > 0:
                    c = c + d
                    break
        answers.append(c)
        lines.append(f"{i + 1}. {int(a[i])} × {int(b[i])} = {c}")
    return {"e": int(e), "text": "\n".join(lines)}


def make_block(cfg: dict, block: str, seed: int) -> dict:
    """calibration: n_cal worksheets per error count. test: pairs (good, bad) per gap, the good
    sheet's error count uniform on what the gap allows. Worksheets carry ids; pairs refer to them."""
    rng = np.random.default_rng([int(seed), BLOCK_INDEX[block]])
    N = int(cfg["n_items"])
    sheets, pairs = [], []
    if block == "calibration":
        for e in range(N + 1):
            for _ in range(int(cfg["n_cal_per_level"])):
                w = make_worksheet(rng, N, e); w["id"] = len(sheets); sheets.append(w)
    else:
        for gap in cfg["gap_ladder"]:
            for i in range(int(cfg["n_pairs_per_gap"])):
                e_good = int(rng.integers(0, N - int(gap) + 1))
                g = make_worksheet(rng, N, e_good); g["id"] = len(sheets); sheets.append(g)
                b = make_worksheet(rng, N, e_good + int(gap)); b["id"] = len(sheets); sheets.append(b)
                pairs.append({"pid": len(pairs), "gap": int(gap), "good": g["id"], "bad": b["id"],
                              "good_first": bool(rng.integers(2))})
    return {"block": block, "seed": int(seed), "n_items": N, "sheets": sheets, "pairs": pairs}


def score_prompt(cfg: dict, sheet_text: str, scale: dict) -> str:
    return cfg["prompts"]["score"].format(n=cfg["n_items"], sheet=sheet_text, lo=scale["lo"], hi=scale["hi"])


def pair_prompt(cfg: dict, first: str, second: str) -> str:
    return cfg["prompts"]["pairwise"].format(n=cfg["n_items"], first=first, second=second)


def parse_int(text: str, scale: dict) -> float:
    m = INT_RE.search(text)
    if not m:
        return float("nan")
    v = int(m.group(0))
    return float(v) if scale["lo"] <= v <= scale["hi"] else float("nan")


# ----------------------------------------------------------------------------- judges

class LMJudge:
    def __init__(self, spec: dict, precision: str, cfg: dict):
        self.inner = g3b.LMScorer({"model_id": spec["model_id"], "revision": spec.get("revision")}, precision,
                                  {"use_chat_template": True, "prompt_templates": {}})
        self.tok, self.model, self.torch = self.inner.tok, self.inner.model, self.inner.torch
        self.model_class, self.loaded_revision = self.inner.model_class, self.inner.loaded_revision
        self.cfg = cfg
        self.letters = [self._single("A"), self._single("B")]

    def _single(self, s: str) -> int:
        ids = self.tok.encode(s, add_special_tokens=False)
        if len(ids) != 1:
            raise ValueError(f"{s!r} is not a single token: {ids}")
        return ids[0]

    def _chat(self, user: str) -> str:
        return self.tok.apply_chat_template([{"role": "user", "content": user}], tokenize=False, add_generation_prompt=True)

    def score(self, texts: list[str], scale: dict, n_samples: int, temperature: float, batch: int) -> list[dict]:
        torch = self.torch
        single = all(len(self.tok.encode(str(s), add_special_tokens=False)) == 1 for s in range(scale["lo"], scale["hi"] + 1))
        code_ids = [self._single(str(s)) for s in range(scale["lo"], scale["hi"] + 1)] if single else None
        out = []
        for i in range(0, len(texts), batch):
            prompts = [self._chat(score_prompt(self.cfg, t, scale)) for t in texts[i:i + batch]]
            enc = self.tok(prompts, return_tensors="pt", padding=True).to(self.model.device)
            L = enc["input_ids"].shape[1]
            with torch.no_grad():
                g = self.model.generate(**enc, max_new_tokens=4, do_sample=False, output_scores=True,
                                        return_dict_in_generate=True, pad_token_id=self.tok.pad_token_id)
                first = g.scores[0].float()
                samp = None
                if n_samples > 0:
                    # sampled in sub-batches: n_samples sequences per prompt multiply the KV cache, and
                    # 16 prompts x 16 samples of a 350-token prompt ran a 32 GB card out of memory
                    sb = int(self.cfg.get("batch_sample", 4))
                    parts = []
                    for s in range(0, enc["input_ids"].shape[0], sb):
                        sub = {k: v[s:s + sb] for k, v in enc.items()}
                        parts.append(self.model.generate(**sub, max_new_tokens=4, do_sample=True, temperature=float(temperature),
                                                         top_p=1.0, top_k=0, num_return_sequences=int(n_samples),
                                                         pad_token_id=self.tok.pad_token_id)[:, L:])
                    width = max(x.shape[1] for x in parts)
                    samp = torch.cat([torch.nn.functional.pad(x, (0, width - x.shape[1]), value=self.tok.pad_token_id) for x in parts])
            greedy = [self.tok.decode(r, skip_special_tokens=True) for r in g.sequences[:, L:]]
            for j, txt in enumerate(greedy):
                rec = {"text": txt, "argmax": parse_int(txt, scale)}
                if single:
                    p = torch.softmax(first[j, code_ids], dim=-1).cpu().numpy()
                    rec["p"] = [round(float(x), 6) for x in p]
                    rec["mass_on_codebook"] = round(float(torch.softmax(first[j], dim=-1)[code_ids].sum()), 6)
                if samp is not None:
                    rows = samp[j * n_samples:(j + 1) * n_samples]
                    rec["samples"] = [parse_int(self.tok.decode(r, skip_special_tokens=True), scale) for r in rows]
                out.append(rec)
        return out

    def pairwise(self, firsts: list[str], seconds: list[str], batch: int) -> list[float]:
        torch = self.torch
        out = []
        for i in range(0, len(firsts), batch):
            prompts = [self._chat(pair_prompt(self.cfg, a, b)) + self.cfg["prompts"].get("pairwise_prefix", "")
                       for a, b in zip(firsts[i:i + batch], seconds[i:i + batch])]
            enc = self.tok(prompts, return_tensors="pt", padding=True).to(self.model.device)
            with torch.no_grad():
                lg = self.model(**enc).logits[:, -1, :].float()
            out += torch.sigmoid(lg[:, self.letters[0]] - lg[:, self.letters[1]]).cpu().tolist()
        return out

    def close(self):
        self.inner.close()


class SyntheticJudge:
    """A judge of known structure. It perceives z = q + noise, writes the nearest entry of a
    codebook (heaped for 0-100, whatever the nominal scale allows), exposes a probability vector
    over a single-token codebook, samples from it, and compares two sheets through the same z with
    a position bias. ``drift`` multiplies the perception noise on the test block only, which is the
    known defect the prediction check has to catch."""

    def __init__(self, spec: dict, precision: str, cfg: dict):
        p = spec["synthetic"]
        self.sd = float(p.get("noise_sd", 0.04)) * float(p.get("precision_noise", {}).get(precision, 1.0))
        self.drift = float(p.get("drift", 1.0))
        self.tau = float(p.get("tau", 0.35))
        self.bias = float(p.get("position_bias", 1.5))
        self.pair_sd = float(p.get("pair_sd", 0.03))
        self.heaped = p.get("heaped_codebooks", {})
        self.seed = int(p.get("seed", 0))
        self.N = int(cfg["n_items"])
        self.block = "calibration"
        self.model_class = self.loaded_revision = "synthetic"

    def _z(self, text: str, tag: str) -> float:
        e = sum(1 for ln in text.split("\n") if not _line_correct(ln))
        rng = np.random.default_rng([self.seed, zlib.crc32((tag + text).encode())])
        sd = self.sd * (self.drift if self.block == "test" else 1.0)
        return 1.0 - e / self.N + rng.normal(0.0, sd)

    def score(self, texts, scale, n_samples, temperature, batch):
        key = f"{scale['lo']}-{scale['hi']}"
        book = np.array(self.heaped.get(key, list(range(scale["lo"], scale["hi"] + 1))), float)
        single = scale["hi"] <= 9
        out = []
        for t in texts:
            z = self._z(t, "score" + key)
            target = scale["lo"] + np.clip(z, 0, 1) * (scale["hi"] - scale["lo"])
            rng = np.random.default_rng([self.seed + 1, zlib.crc32((key + t).encode())])
            logits = -((book - target) ** 2) / (2 * (self.tau * (book[1] - book[0] if len(book) > 1 else 1)) ** 2)
            p = np.exp(logits - logits.max()); p /= p.sum()
            rec = {"text": str(int(book[int(np.argmax(p))])), "argmax": float(book[int(np.argmax(p))])}
            if single:
                full = np.zeros(scale["hi"] - scale["lo"] + 1)
                for s, ps in zip(book, p):
                    full[int(s) - scale["lo"]] = ps
                rec["p"] = [round(float(x), 6) for x in full]; rec["mass_on_codebook"] = 1.0
            if n_samples > 0:
                pt = p ** (1.0 / max(temperature, 1e-6)); pt /= pt.sum()
                rec["samples"] = [float(x) for x in rng.choice(book, size=n_samples, p=pt)]
            out.append(rec)
        return out

    def pairwise(self, firsts, seconds, batch):
        out = []
        for a, b in zip(firsts, seconds):
            d = (self._z(a, "pair") - self._z(b, "pair")) / self.pair_sd + self.bias
            out.append(float(1.0 / (1.0 + math.exp(-d))))
        return out

    def close(self):
        pass


def _line_correct(line: str) -> bool:
    m = re.match(r"\d+\. (\d+) × (\d+) = (-?\d+)", line)
    return bool(m) and int(m.group(1)) * int(m.group(2)) == int(m.group(3))


def make_judge(spec: dict, precision: str, cfg: dict):
    return SyntheticJudge(spec, precision, cfg) if str(spec["model_id"]).startswith("synthetic:") else LMJudge(spec, precision, cfg)


# ----------------------------------------------------------------------------- run

def block_seed(cfg: dict, block: str) -> int:
    role = cfg.get("_role", "run")
    s = cfg["seeds"].get(f"pilot_{block}" if role == "pilot" else block)
    if s is None:
        raise SystemExit(f"no {block} seed in the config; the test seed is drawn only after the predictions are committed")
    return int(s)


def run_block(cfg: dict, block: str, model_key: str, precision: str, out_dir: str, judge_factory=make_judge) -> dict:
    spec = {m["key"]: m for m in cfg["models"]}[model_key]
    out = Path(out_dir) / block / f"{model_key}__{precision}"
    out.mkdir(parents=True, exist_ok=True)
    data = make_block(cfg, block, block_seed(cfg, block))
    with gzip.open(out / "stimuli.json.gz", "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    meter = g3b.Meter().start()
    meter.mark("load")
    judge = judge_factory(spec, precision, cfg)
    if hasattr(judge, "block"):
        judge.block = block
    meter.mark("loaded")
    texts = [s["text"] for s in data["sheets"]]
    result = {"gate": cfg["gate"], "block": block, "seed": data["seed"], "model": model_key, "precision": precision,
              "model_class": judge.model_class, "loaded_revision": judge.loaded_revision, "env": g3b.env_versions(),
              "n_sheets": len(texts), "n_pairs": len(data["pairs"]), "files": {},
              "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    for scale in cfg["scales"]:
        key = f"{scale['lo']}-{scale['hi']}"
        meter.mark(f"score_{key}")
        t0 = time.time()
        recs = judge.score(texts, scale, int(cfg["n_samples"]), float(cfg["temperature"]), int(cfg["batch"]))
        fn = f"scores_{key}.jsonl.gz"
        with gzip.open(out / fn, "wt", encoding="utf-8") as f:
            for s, r in zip(data["sheets"], recs):
                f.write(json.dumps({"id": s["id"], "e": s["e"], **r}) + "\n")
        bad = sum(1 for r in recs if r["argmax"] != r["argmax"])
        result["files"][key] = {"file": fn, "seconds": round(time.time() - t0, 1), "unparsed_argmax": bad}
        print(json.dumps({"scale": key, "seconds": result["files"][key]["seconds"], "unparsed": bad}), flush=True)
    if data["pairs"] and cfg.get("pairwise", True):
        meter.mark("pairwise")
        t0 = time.time()
        by_id = {s["id"]: s["text"] for s in data["sheets"]}
        g = [by_id[p["good"]] for p in data["pairs"]]; b = [by_id[p["bad"]] for p in data["pairs"]]
        p_good_first = judge.pairwise(g, b, int(cfg["batch_pairwise"]))
        p_bad_first = judge.pairwise(b, g, int(cfg["batch_pairwise"]))
        with gzip.open(out / "pairwise.jsonl.gz", "wt", encoding="utf-8") as f:
            for p, x, y in zip(data["pairs"], p_good_first, p_bad_first):
                f.write(json.dumps({"pid": p["pid"], "gap": p["gap"], "p_first_when_good_first": round(x, 6),
                                    "p_first_when_bad_first": round(y, 6)}) + "\n")
        result["files"]["pairwise"] = {"file": "pairwise.jsonl.gz", "seconds": round(time.time() - t0, 1)}
        print(json.dumps({"pairwise_seconds": result["files"]["pairwise"]["seconds"]}), flush=True)
    judge.close()
    meter.stop()
    result["meter"] = meter.summary()
    result["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    json.dump(result, open(out / "results.json", "w"), indent=1)
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["stimuli", "run"])
    ap.add_argument("--config", required=True)
    ap.add_argument("--block", choices=["calibration", "test"], required=True)
    ap.add_argument("--model"); ap.add_argument("--precision", default="full")
    ap.add_argument("--out", default="out")
    ap.add_argument("--role", choices=["pilot", "run"], default="run", help="pilot uses the pilot seeds")
    a = ap.parse_args(argv)
    cfg = json.load(open(a.config, encoding="utf-8"))
    cfg["_role"] = a.role
    if a.cmd == "stimuli":
        d = make_block(cfg, a.block, block_seed(cfg, a.block))
        Path(a.out).mkdir(parents=True, exist_ok=True)
        with gzip.open(Path(a.out) / f"stimuli_{a.block}.json.gz", "wt", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        print(len(d["sheets"]), "sheets", len(d["pairs"]), "pairs")
    else:
        run_block(cfg, a.block, a.model, a.precision, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
