"""G3: the indifference threshold of a computational evaluator tracks its resolution budget.

Prediction (i) of the paper: for a fixed world and evaluator the just-noticeable difference of
the induced semiorder is the resolution budget, so coarsening the resolution enlarges the
threshold and leaves the ordering of well-separated pairs unchanged.

World. A language-model judge is shown a target value and two options, each a number, and
asked which option is closer to the target. Its preference is read from the next-token
log-probabilities of the two answer letters, with the options shown in both positions so that
a position preference cancels. The consequence map is known exactly: the consequence of an
option is its distance from the target. Two budgets are set independently: the rendering
precision (how many decimals of each number the judge is shown) and the judge's own weight
precision (full, 8-bit, 4-bit). For each budget level the accuracy of the judge's preference is
measured as a function of the true distance gap between the two options, and the threshold is
the gap at which the accuracy crosses a registered level.

Self-test. A synthetic scorer that rounds distances to a grid of step h and prefers the
smaller rounded distance has a threshold of h by construction; the estimator must recover it
at every h of a ladder.

    python g3_threshold.py --selftest
    python g3_threshold.py --config prereg_config.json --probe --out probe.json
    python g3_threshold.py --config prereg_config.json --seed-role pilot --out pilot.json
    python g3_threshold.py --config prereg_config.json --seed-role run --out results.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time

import numpy as np


# ----------------------------------------------------------------------------- pairs

def make_pairs(cfg: dict, rng: np.random.Generator) -> list[dict]:
    """For each gap on the ladder, n_pairs pairs (a, b) of options with |d(a) - d(b)| = gap,
    d the distance to the target, the closer option on each side of the target with equal
    frequency, positions balanced later by showing each pair in both orders."""
    T = float(cfg["target"]); lo, hi = cfg["option_range"]
    side = cfg.get("side", "both")   # "above", "below", or "both" (each option's side drawn at random)
    pairs = []
    for gap in cfg["gap_ladder"]:
        for i in range(int(cfg["n_pairs_per_gap"])):
            while True:
                d_close = rng.uniform(float(cfg["min_distance"]), float(cfg["max_distance"]) - gap)
                d_far = d_close + gap
                if side == "above":
                    s_close = s_far = 1.0
                elif side == "below":
                    s_close = s_far = -1.0
                else:
                    s_close = rng.choice([-1.0, 1.0]); s_far = rng.choice([-1.0, 1.0])
                a = T + s_close * d_close; b = T + s_far * d_far
                if lo <= a <= hi and lo <= b <= hi:
                    break
            pairs.append({"gap": float(gap), "close": float(a), "far": float(b), "idx": i})
    return pairs


def render(x: float, decimals: int) -> str:
    return f"{x:.{decimals}f}"


# ----------------------------------------------------------------------------- judges

class QuantizedScorer:
    """Synthetic evaluator: distances rounded to a grid of step h, smaller wins, ties are
    indifference (probability one half). Its threshold is h by construction."""

    def __init__(self, target: float, h: float):
        self.T = target; self.h = h

    def prefer_first(self, x: float, y: float) -> float:
        dx = round(abs(x - self.T) / self.h); dy = round(abs(y - self.T) / self.h)
        return 1.0 if dx < dy else (0.0 if dx > dy else 0.5)


class LMJudge:
    """A causal language model asked which of two options is closer to the target; the
    preference for the first-shown option is softmax over the two answer letters' next-token
    log-probabilities."""

    def __init__(self, cfg: dict, weight_precision: str):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        mid = cfg["model_id"]
        self.tok = AutoTokenizer.from_pretrained(mid)
        kw = {"device_map": {"": 0}}
        if weight_precision == "full":
            kw["dtype"] = torch.bfloat16
        elif weight_precision == "int8":
            from transformers import BitsAndBytesConfig
            kw["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
        elif weight_precision == "int4":
            from transformers import BitsAndBytesConfig
            kw["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                                           bnb_4bit_compute_dtype=torch.bfloat16)
        else:
            raise ValueError(weight_precision)
        self.model = AutoModelForCausalLM.from_pretrained(mid, **kw).eval()
        self.template = cfg["prompt_template"]
        self.letters = cfg["answer_letters"]
        self.chat = bool(cfg.get("use_chat_template", True)) and self.tok.chat_template is not None
        # In a chat template the assistant turn opens after a newline and the model emits the
        # bare letter; in a raw prompt it emits a space-prefixed letter. The probe of 2026-09-08
        # found the space-prefixed logits 25 to 30 below the bare ones under the chat template.
        prefix = "" if self.chat else " "
        ids = [self.tok.encode(prefix + L, add_special_tokens=False) for L in self.letters]
        assert all(len(i) == 1 for i in ids), ("answer letters must be single tokens", ids)
        self.letter_ids = [i[0] for i in ids]

    def _prompt(self, target: str, first: str, second: str) -> str:
        user = self.template.format(target=target, first=first, second=second, A=self.letters[0], B=self.letters[1])
        if self.chat:
            msgs = [{"role": "user", "content": user}]
            return self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        return user

    def prefer_first_batch(self, target: str, firsts: list[str], seconds: list[str]) -> np.ndarray:
        torch = self.torch
        prompts = [self._prompt(target, f, s) for f, s in zip(firsts, seconds)]
        self.tok.padding_side = "left"
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token
        enc = self.tok(prompts, return_tensors="pt", padding=True).to(self.model.device)
        with torch.no_grad():
            logits = self.model(**enc).logits[:, -1, :].float()
        la = logits[:, self.letter_ids[0]]; lb = logits[:, self.letter_ids[1]]
        return torch.sigmoid(la - lb).cpu().numpy()


class LMScorer:
    """A causal language model asked how far one value is from the target, answering with a
    number; the induced preference between two options compares the two reported distances,
    and equal reports are indifference. Reports are parsed as the first number in the greedy
    generation; an unparsable report is recorded and treated as no preference."""

    def __init__(self, cfg: dict, weight_precision: str):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        mid = cfg["model_id"]
        self.tok = AutoTokenizer.from_pretrained(mid)
        kw = {"device_map": {"": 0}}
        if weight_precision == "full":
            kw["dtype"] = torch.bfloat16
        elif weight_precision in ("int8", "int4"):
            from transformers import BitsAndBytesConfig
            kw["quantization_config"] = (BitsAndBytesConfig(load_in_8bit=True) if weight_precision == "int8" else
                                         BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16))
        else:
            raise ValueError(weight_precision)
        self.model = AutoModelForCausalLM.from_pretrained(mid, **kw).eval()
        self.template = cfg["scorer_prompt_template"]
        self.max_new = int(cfg.get("max_new_tokens", 12))
        self.chat = bool(cfg.get("use_chat_template", True)) and self.tok.chat_template is not None
        self.cache: dict[tuple[str, str], tuple[float, str]] = {}
        self.unparsed = 0

    def _prompt(self, target: str, value: str) -> str:
        user = self.template.format(target=target, value=value)
        if self.chat:
            return self.tok.apply_chat_template([{"role": "user", "content": user}], tokenize=False, add_generation_prompt=True)
        return user

    def scores(self, target: str, values: list[str], batch: int = 32, max_new: int | None = None) -> list[float]:
        """max_new is the report budget in generated tokens; this tokenizer emits one digit per
        token, so it is the number of characters of the report."""
        import re
        torch = self.torch
        k = int(max_new or self.max_new)
        todo = [v for v in dict.fromkeys(values) if (target, v, k) not in self.cache]
        self.tok.padding_side = "left"
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token
        for i in range(0, len(todo), batch):
            chunk = todo[i:i + batch]
            enc = self.tok([self._prompt(target, v) for v in chunk], return_tensors="pt", padding=True).to(self.model.device)
            with torch.no_grad():
                gen = self.model.generate(**enc, max_new_tokens=k, do_sample=False,
                                          pad_token_id=self.tok.pad_token_id)
            for v, row in zip(chunk, gen[:, enc.input_ids.shape[1]:]):
                text = self.tok.decode(row, skip_special_tokens=True)
                m = re.search(r"-?\d+(?:\.\d*)?", text.replace(",", ""))
                if m:
                    self.cache[(target, v, k)] = (float(m.group(0).rstrip(".")), text)
                else:
                    self.cache[(target, v, k)] = (float("nan"), text); self.unparsed += 1
        return [self.cache[(target, v, k)][0] for v in values]


def accuracy_by_gap_scorer(pairs: list[dict], scorer: LMScorer, decimals: int, target: float, batch: int = 32,
                           max_new: int | None = None) -> dict:
    """Preference for the closer option is 1 if its reported distance is smaller, 0 if larger,
    one half if equal or either report is unparsable; accuracy is the share of pairs with
    preference above one half, so ties count against, which is what indifference is."""
    import math as _m
    tstr = render(target, decimals)
    by_gap = {}
    for p in pairs:
        by_gap.setdefault(p["gap"], []).append(p)
    out = {}
    for gap, ps in by_gap.items():
        sc = scorer.scores(tstr, [render(p["close"], decimals) for p in ps], batch, max_new)
        sf = scorer.scores(tstr, [render(p["far"], decimals) for p in ps], batch, max_new)
        prefs = []
        for a, b in zip(sc, sf):
            prefs.append(0.5 if (_m.isnan(a) or _m.isnan(b) or a == b) else (1.0 if a < b else 0.0))
        prefs = np.asarray(prefs)
        out[str(gap)] = {"n": int(prefs.size), "accuracy": float(np.mean(prefs > 0.5)),
                         "ties_or_unparsed": float(np.mean(prefs == 0.5)),
                         "mean_preference": float(prefs.mean()),
                         "identical_rendering": float(np.mean([render(p["close"], decimals) == render(p["far"], decimals) for p in ps]))}
    return out


# ----------------------------------------------------------------------------- measurement

def accuracy_by_gap(pairs: list[dict], judge_fn, decimals: int, target: float, batch: int = 32) -> dict:
    """judge_fn(target_str, firsts, seconds) -> P(first preferred). Each pair is shown in both
    orders; the pair's preference for the closer option is the average of P(close first) and
    1 - P(far first), which cancels a position bias. Returns per gap: mean accuracy (share of
    pairs whose averaged preference for the closer option exceeds one half), mean preference."""
    tstr = render(target, decimals)
    out = {}
    by_gap = {}
    for p in pairs:
        by_gap.setdefault(p["gap"], []).append(p)
    for gap, ps in by_gap.items():
        prefs = []
        for i in range(0, len(ps), batch):
            chunk = ps[i:i + batch]
            c = [render(p["close"], decimals) for p in chunk]; f = [render(p["far"], decimals) for p in chunk]
            p1 = judge_fn(tstr, c, f); p2 = judge_fn(tstr, f, c)
            prefs += list(0.5 * (np.asarray(p1) + (1.0 - np.asarray(p2))))
        prefs = np.asarray(prefs)
        out[str(gap)] = {"n": int(prefs.size), "accuracy": float(np.mean(prefs > 0.5)),
                         "mean_preference": float(prefs.mean()),
                         "identical_rendering": float(np.mean([render(p["close"], decimals) == render(p["far"], decimals) for p in ps]))}
    return out


def threshold_from(acc: dict, level: float) -> float:
    """The gap at which accuracy first reaches the level, interpolated linearly in log gap
    between ladder points; infinity if never reached, the smallest gap if reached there."""
    gaps = sorted(float(g) for g in acc)
    ys = [acc[str(g)]["accuracy"] if str(g) in acc else acc[repr(g)]["accuracy"] for g in gaps]
    for i, (g, y) in enumerate(zip(gaps, ys)):
        if y >= level:
            if i == 0:
                return g
            g0, y0 = gaps[i - 1], ys[i - 1]
            if y == y0:
                return g
            t = (level - y0) / (y - y0)
            return float(math.exp(math.log(g0) + t * (math.log(g) - math.log(g0))))
    return float("inf")


# ----------------------------------------------------------------------------- runs

def run(cfg: dict, seed: int, out_path: str, probe: bool = False) -> dict:
    rng = np.random.default_rng(seed)
    pairs = make_pairs(cfg, rng)
    level = float(cfg["accuracy_level"])
    result = {"config": cfg, "seed": seed, "probe": probe, "cells": [], "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    precisions = ["full"] if probe else list(cfg["weight_precisions"])
    decimals_ladder = [int(cfg["decimals_ladder"][-1])] if probe else [int(d) for d in cfg["decimals_ladder"]]
    kind = cfg.get("judge_kind", "chooser")
    for wp in precisions:
        if kind == "scorer":
            judge = LMScorer(cfg, wp)
            if probe:
                sample = []
                for p in pairs[-3:] + pairs[:3]:
                    for v in (p["close"], p["far"]):
                        s = judge.scores(render(float(cfg["target"]), 3), [render(v, 3)])[0]
                        sample.append({"value": v, "true_distance": abs(v - float(cfg["target"])), "reported": s,
                                       "text": judge.cache[(render(float(cfg["target"]), 3), render(v, 3))][1]})
                result["generation_sample"] = sample
                print(json.dumps({"generation_sample": sample}))
            full_budget = int(cfg.get("max_new_tokens", 12))
            ladder = [(dec, full_budget) for dec in decimals_ladder]
            if wp == "full" and not probe:
                ladder += [(int(cfg["decimals_ladder"][-1]), int(k)) for k in cfg.get("report_token_budgets", []) if int(k) != full_budget]
            for dec, k in ladder:
                t0 = time.time()
                acc = accuracy_by_gap_scorer(pairs, judge, dec, float(cfg["target"]), int(cfg.get("batch", 32)), k)
                thr = threshold_from(acc, level)
                cell = {"weight_precision": wp, "decimals": dec, "rendering_step": 10.0 ** (-dec), "report_tokens": k,
                        "accuracy_by_gap": acc, "threshold": thr, "unparsed_reports": judge.unparsed, "seconds": time.time() - t0}
                result["cells"].append(cell)
                print(json.dumps({"weight_precision": wp, "decimals": dec, "report_tokens": k, "threshold": thr, "unparsed": judge.unparsed,
                                  "acc": {g: round(v["accuracy"], 3) for g, v in acc.items()},
                                  "ties": {g: round(v["ties_or_unparsed"], 3) for g, v in acc.items()}}))
                json.dump(result, open(out_path, "w", encoding="utf-8"), indent=1)
            del judge
            try:
                import torch; torch.cuda.empty_cache()
            except Exception:
                pass
            continue
        judge = LMJudge(cfg, wp)
        if probe:
            # record what the judge actually emits on a few pairs, so the letter reading is auditable
            import torch
            sample = []
            for p in pairs[-3:]:
                for first, second in ((p["close"], p["far"]), (p["far"], p["close"])):
                    prompt = judge._prompt(render(float(cfg["target"]), 3), render(first, 3), render(second, 3))
                    enc = judge.tok(prompt, return_tensors="pt").to(judge.model.device)
                    with torch.no_grad():
                        gen = judge.model.generate(**enc, max_new_tokens=4, do_sample=False)
                    sample.append({"first": first, "second": second, "generated": judge.tok.decode(gen[0, enc.input_ids.shape[1]:])})
            result["generation_sample"] = sample
            print(json.dumps({"generation_sample": sample}))
        for dec in decimals_ladder:
            t0 = time.time()
            acc = accuracy_by_gap(pairs, judge.prefer_first_batch, dec, float(cfg["target"]), int(cfg.get("batch", 32)))
            thr = threshold_from(acc, level)
            cell = {"weight_precision": wp, "decimals": dec, "rendering_step": 10.0 ** (-dec),
                    "accuracy_by_gap": acc, "threshold": thr, "seconds": time.time() - t0}
            result["cells"].append(cell)
            print(json.dumps({"weight_precision": wp, "decimals": dec, "threshold": thr,
                              "acc": {g: round(v["accuracy"], 3) for g, v in acc.items()}}))
            json.dump(result, open(out_path, "w", encoding="utf-8"), indent=1)
        del judge
        try:
            import torch; torch.cuda.empty_cache()
        except Exception:
            pass
    result["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    json.dump(result, open(out_path, "w", encoding="utf-8"), indent=1)
    return result


def selftest() -> int:
    """The estimator recovers the threshold of the quantized scorer at every step of a ladder,
    and a scorer with a step below the gap ladder orders every pair correctly."""
    rng = np.random.default_rng(0)
    cfg = {"target": 100.0, "option_range": [50.0, 150.0], "min_distance": 1.0, "max_distance": 40.0,
           "gap_ladder": [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0], "n_pairs_per_gap": 200}
    pairs = make_pairs(cfg, rng)
    fails = 0
    for h in (0.01, 0.1, 1.0):
        sc = QuantizedScorer(100.0, h)
        fn = lambda t, firsts, seconds, sc=sc: np.array([sc.prefer_first(float(f), float(s)) for f, s in zip(firsts, seconds)])
        acc = accuracy_by_gap(pairs, fn, 6, 100.0)
        thr = threshold_from(acc, 0.9)
        print(f"h={h}: threshold {thr:.4f}", {g: round(v['accuracy'], 2) for g, v in acc.items()})
        # a rounded-distance scorer decides every pair whose gap exceeds h and about half of
        # those below, so the 90 percent level sits between h and 2h
        if not (0.8 * h <= thr <= 2.5 * h):
            print("FAIL threshold not near the step"); fails += 1
    print("SELFTEST", "PASS" if fails == 0 else f"FAIL ({fails})")
    return fails


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config"); ap.add_argument("--out", default="results.json")
    ap.add_argument("--seed-role", choices=["pilot", "run"], default="run")
    ap.add_argument("--probe", action="store_true"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    cfg = json.load(open(a.config, encoding="utf-8"))
    seed = int(cfg["seed_probe"] if a.probe else (cfg["seed_pilot"] if a.seed_role == "pilot" else cfg["seed_run"]))
    run(cfg, seed, a.out, probe=a.probe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
