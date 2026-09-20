"""G3d harness: a deliberation budget reverses a judge's preference, and where it reverses is
predicted from measurements that never show the reversal.

Two worksheets of N multiplications, one with fewer wrong answers. A decoration, a confident
header and a check mark on every line, is a cue that carries no information about quality. The
judge reasons for at most k tokens, then "Final answer (A or B): " is forced and the letter
logits are read. Both presentation orders are run. For a pair, the order-averaged log-odds that
the judge prefers the sheet of interest is

    L = ( D(sheet of interest shown first) - D(sheet of interest shown second) ) / 2,

where D is the logit of "A" minus the logit of "B". L is unbounded, so it does not saturate the
way a probability does, and a position bias cancels in the difference.

Cells, all at the same budget ladder:
  evidence   plain against plain, the better sheet has `gap` fewer errors.   L = log-odds of the better
  cue        equal error counts, one sheet decorated.                         L = log-odds of the decorated
  reversal   gap as in evidence, the WORSE sheet decorated.                   L = log-odds of the better
  control    gap as in evidence, the BETTER sheet decorated.                  L = log-odds of the better

The calibration block holds evidence and cue. The test block holds reversal and control, from a
seed drawn only after the predictions are committed. If evidence and cue add on the log-odds
scale, the calibration predicts both test cells at every budget, and the budget at which the
judge stops preferring the decorated worse sheet.

    python flip.py run --config flip_config.json --block calibration --out OUT [--role pilot]
    python flip.py run --config flip_config.json --block test        --out OUT [--role pilot]
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "G3c"))
sys.path.insert(0, str(HERE.parent / "g3c"))
import judge as g3c  # noqa: E402  (worksheet generator, LMJudge, Meter via g3b)

BLOCK_INDEX = {"calibration": 0, "test": 1}
CELLS = {"calibration": ("evidence", "cue"), "test": ("reversal", "control")}


# ----------------------------------------------------------------------------- stimuli

def decorate(cfg: dict, text: str) -> str:
    d = cfg["decoration"]
    return d["header"] + "\n" + "\n".join(line + d["mark"] for line in text.split("\n"))


def make_block(cfg: dict, block: str, seed: int) -> dict:
    """Pairs of worksheets. `first` is the sheet of interest: the better sheet in evidence,
    reversal and control, the decorated sheet in cue."""
    rng = np.random.default_rng([int(seed), BLOCK_INDEX[block]])
    N, gap, n = int(cfg["n_items"]), int(cfg["gap"]), int(cfg["n_pairs"])
    pairs = []
    for cell in CELLS[block]:
        for _ in range(n):
            if cell == "cue":
                e = int(rng.integers(0, N + 1))
                a, b = g3c.make_worksheet(rng, N, e), g3c.make_worksheet(rng, N, e)
                interest, other = decorate(cfg, a["text"]), b["text"]
                ea, eb = e, e
            else:
                eg = int(rng.integers(0, N - gap + 1))
                a, b = g3c.make_worksheet(rng, N, eg), g3c.make_worksheet(rng, N, eg + gap)
                good, bad = a["text"], b["text"]
                if cell == "reversal":
                    bad = decorate(cfg, bad)
                elif cell == "control":
                    good = decorate(cfg, good)
                interest, other = good, bad
                ea, eb = eg, eg + gap
            pairs.append({"pid": len(pairs), "cell": cell, "e_interest": ea, "e_other": eb,
                          "interest": interest, "other": other})
    return {"block": block, "seed": int(seed), "pairs": pairs}


def prompt(cfg: dict, first: str, second: str, think: bool) -> str:
    p = cfg["prompts"]
    return p["pair"].format(n=cfg["n_items"], first=first, second=second,
                            instruction=p["think"] if think else p["now"])


# ----------------------------------------------------------------------------- judges

class DeliberatingJudge:
    """The G3c judge, allowed k tokens of greedy reasoning before a forced answer. The reasoning
    is cut at the first stop token, the forced suffix is appended as token ids (no decode and
    re-encode round trip), and the letter logits are read in one forward pass."""

    def __init__(self, spec: dict, precision: str, cfg: dict):
        self.j = g3c.LMJudge(spec, precision, {**cfg, "prompts": {}})
        self.tok, self.model, self.torch = self.j.tok, self.j.model, self.j.torch
        self.cfg = cfg
        self.letters = self.j.letters
        self.final = self.tok.encode(cfg["prompts"]["final"], add_special_tokens=False)
        self.stop = set(self.j.inner.stop_ids)
        self.model_class, self.loaded_revision = self.j.model_class, self.j.loaded_revision

    def D(self, texts: list[str], k: int, batch: int) -> list[dict]:
        torch = self.torch
        out = []
        for i in range(0, len(texts), batch):
            chunk = [self.j._chat(t) for t in texts[i:i + batch]]
            enc = self.tok(chunk, return_tensors="pt", padding=True).to(self.model.device)
            L = enc["input_ids"].shape[1]
            rows, n_reason, reasons = [], [], []
            gen = None
            if k > 0:
                with torch.no_grad():
                    gen = self.model.generate(**enc, max_new_tokens=k, do_sample=False,
                                              pad_token_id=self.tok.pad_token_id)
            for r in range(len(chunk)):
                p_ids = enc["input_ids"][r][enc["attention_mask"][r].bool()].tolist()
                g = gen[r, L:].tolist() if gen is not None else []
                cut = next((j for j, t in enumerate(g) if t in self.stop), len(g))
                rows.append(p_ids + g[:cut] + self.final)
                n_reason.append(cut)
                reasons.append(self.tok.decode(g[:cut], skip_special_tokens=True))
            m = max(len(x) for x in rows)
            pad = self.tok.pad_token_id
            # The forced-answer pass attends over prompt plus reasoning, so its cost grows with the
            # budget: at 32 rows of 1,700 tokens the attention alone is several GB per layer and ran
            # two pilots out of memory. Rows are taken in chunks that hold the token count fixed,
            # while generation keeps the configured batch. Only the last position's logits are read.
            sub = max(1, int(self.cfg.get("final_tokens", 8192)) // max(m, 1))
            d = []
            for c0 in range(0, len(rows), sub):
                part = rows[c0:c0 + sub]
                ids = torch.tensor([[pad] * (m - len(x)) + x for x in part], device=self.model.device)
                mask = torch.tensor([[0] * (m - len(x)) + [1] * len(x) for x in part], device=self.model.device)
                with torch.no_grad():
                    lg = self.model(input_ids=ids, attention_mask=mask, position_ids=(mask.cumsum(-1) - 1).clamp(min=0),
                                    logits_to_keep=1).logits[:, -1, :].float()
                d += (lg[:, self.letters[0]] - lg[:, self.letters[1]]).cpu().tolist()
                del ids, mask, lg
            for r in range(len(chunk)):
                out.append({"D": d[r], "n_reason": n_reason[r], "hit_budget": bool(k > 0 and n_reason[r] >= k),
                            "reason": reasons[r]})
            del gen
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        return out

    def close(self):
        self.j.close()


class SyntheticDeliberator:
    """Known structure, for the self-test. Log-odds of preferring the first sheet shown:
        D = position(k) + a(k) * (e_second - e_first) + c(k) * (dec_first - dec_second) + noise
    with a(k) growing and c(k) shrinking in the budget. `interaction` > 0 breaks additivity:
    the cue is discounted by exp(-interaction * |evidence|), so it bites only when the evidence is
    weak, which is the defect the gate has to catch."""

    def __init__(self, spec: dict, precision: str, cfg: dict):
        p = spec["synthetic"]
        self.p, self.cfg = p, cfg
        self.model_class = self.loaded_revision = "synthetic"
        self.rng = np.random.default_rng(int(p.get("seed", 0)))

    def _sheet(self, text: str) -> tuple[int, int]:
        lines = text.split("\n")
        dec = int(lines[0] == self.cfg["decoration"]["header"])
        body = [ln.replace(self.cfg["decoration"]["mark"], "") for ln in lines[dec:]]
        return sum(1 for ln in body if not g3c._line_correct(ln)), dec

    def D_pair(self, first: str, second: str, k: int) -> float:
        p = self.p
        lk = np.log2(1 + k)
        a = p["a0"] + p["a1"] * lk
        c = p["c0"] * np.exp(-p["c_decay"] * lk)
        (e1, d1), (e2, d2) = self._sheet(first), self._sheet(second)
        ev = a * (e2 - e1)
        cue = c * (d1 - d2) * np.exp(-p.get("interaction", 0.0) * abs(ev))
        return float(p.get("position", 0.8) + ev + cue + self.rng.normal(0, p["noise"]))

    def close(self):
        pass


def make_judge(spec, precision, cfg):
    return SyntheticDeliberator(spec, precision, cfg) if str(spec["model_id"]).startswith("synthetic:") else \
        DeliberatingJudge(spec, precision, cfg)


# ----------------------------------------------------------------------------- run

def block_seed(cfg: dict, block: str, role: str) -> int:
    s = cfg["seeds"].get(f"{role}_{block}" if role in ("pilot", "smoke") else block)
    if s is None:
        raise SystemExit(f"no {block} seed; the test seed is drawn only after the predictions are committed")
    return int(s)


def run_block(cfg: dict, block: str, out_dir: str, role: str = "run", judge_factory=make_judge) -> dict:
    spec = cfg["model"]; precision = cfg.get("precision", "full")
    out = Path(out_dir) / block
    out.mkdir(parents=True, exist_ok=True)
    data = make_block(cfg, block, block_seed(cfg, block, role))
    with gzip.open(out / "stimuli.json.gz", "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    synthetic = str(spec["model_id"]).startswith("synthetic:")
    meter = None if synthetic else g3c.g3b.Meter().start()
    if meter: meter.mark("load")
    J = judge_factory(spec, precision, cfg)
    if meter: meter.mark("loaded")
    result = {"gate": cfg["gate"], "block": block, "seed": data["seed"], "role": role, "model": spec["key"],
              "precision": precision, "model_class": J.model_class, "loaded_revision": J.loaded_revision,
              "budgets": cfg["budgets"], "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "timing": {}}
    rows = []
    for k in cfg["budgets"]:
        if meter: meter.mark(f"k{k}")
        t0 = time.time()
        pr = data["pairs"]
        if synthetic:
            d1 = [J.D_pair(p["interest"], p["other"], k) for p in pr]
            d2 = [J.D_pair(p["other"], p["interest"], k) for p in pr]
            r1 = [{"D": x, "n_reason": 0, "hit_budget": False, "reason": ""} for x in d1]
            r2 = [{"D": x, "n_reason": 0, "hit_budget": False, "reason": ""} for x in d2]
        else:
            texts1 = [prompt(cfg, p["interest"], p["other"], k > 0) for p in pr]
            texts2 = [prompt(cfg, p["other"], p["interest"], k > 0) for p in pr]
            bsz = int(cfg["batch"].get(str(k), cfg["batch"]["default"]))
            both = J.D(texts1 + texts2, k, bsz)
            r1, r2 = both[:len(pr)], both[len(pr):]
        for p, a, b in zip(pr, r1, r2):
            rows.append({"pid": p["pid"], "cell": p["cell"], "k": k, "e_interest": p["e_interest"], "e_other": p["e_other"],
                         "D_interest_first": a["D"], "D_interest_second": b["D"], "L": 0.5 * (a["D"] - b["D"]),
                         "n_reason": [a["n_reason"], b["n_reason"]], "hit_budget": [a["hit_budget"], b["hit_budget"]],
                         "reason": [a["reason"], b["reason"]]})
        result["timing"][str(k)] = round(time.time() - t0, 1)
        print(json.dumps({"k": k, "seconds": result["timing"][str(k)],
                          **{c: round(float(np.mean([r["L"] for r in rows if r["k"] == k and r["cell"] == c])), 3)
                             for c in CELLS[block]}}), flush=True)
    J.close()
    with gzip.open(out / "pairs.jsonl.gz", "wt", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    if meter:
        meter.stop()
        result["meter"] = meter.summary()
    result["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    json.dump(result, open(out / "results.json", "w"), indent=1, default=float)
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "stimuli"])
    ap.add_argument("--config", required=True); ap.add_argument("--block", required=True, choices=list(CELLS))
    ap.add_argument("--out", required=True); ap.add_argument("--role", default="run", choices=["run", "pilot", "smoke"])
    ap.add_argument("--n-pairs", type=int, help="smoke only"); ap.add_argument("--budgets", help="smoke only, comma separated")
    a = ap.parse_args(argv)
    cfg = json.load(open(a.config, encoding="utf-8"))
    if a.n_pairs or a.budgets:
        if a.role != "smoke":
            raise SystemExit("--n-pairs and --budgets change the design and are allowed only with --role smoke")
        cfg["n_pairs"] = a.n_pairs or cfg["n_pairs"]
        cfg["budgets"] = [int(x) for x in a.budgets.split(",")] if a.budgets else cfg["budgets"]
    if a.role == "smoke":
        cfg["seeds"]["smoke_calibration"] = cfg["seeds"]["smoke_test"] = 7
    if a.cmd == "stimuli":
        d = make_block(cfg, a.block, block_seed(cfg, a.block, a.role))
        Path(a.out).mkdir(parents=True, exist_ok=True)
        json.dump(d, open(Path(a.out) / f"stimuli_{a.block}.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print(len(d["pairs"]), "pairs"); return 0
    run_block(cfg, a.block, a.out, a.role)
    return 0


if __name__ == "__main__":
    sys.exit(main())
