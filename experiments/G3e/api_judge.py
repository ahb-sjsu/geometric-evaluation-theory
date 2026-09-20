"""G3e: a judge behind an OpenAI-compatible API, read by G3c's harness and graded by G3c's grader.

G3c loads a model and reads its logits. A served model gives less: the text it wrote, and for each
position the twenty most probable tokens with their log probabilities. That is enough, and this
file is the whole difference between the two gates. `APIJudge` has the three methods G3c's
`run_block` asks of a judge, so the worksheets, the blocks, the files written and the grader are
G3c's, unchanged.

  score, single-token scale   one request. The greedy text is the argmax read-out. The first
                              position's top twenty, restricted to the codebook and renormalised,
                              is the probability vector, as in G3c.
  score, 0 to 100             the same request, then G3c's digit tree walked over the API: every
                              live digit prefix is sent back as the start of the assistant's turn
                              and the next position's top twenty give each next digit and, as the
                              remainder, the probability of stopping. A token that is a run of
                              digits extends the prefix by that run, so a tokenizer that groups
                              digits is read correctly.
  pairwise                    one request per order, P(A) / (P(A) + P(B)) at the first position.

What a served model cannot give, and what is recorded instead.
  * Only twenty tokens are visible, and what they leave short of one is the mass the server did
    not show. It is recorded per worksheet as `unseen_mass`, and in the tree a digit outside the
    twenty is booked as stopping, with `tree_unseen_bound` bounding the mass that can move if any
    of it was a digit after all. Both are measured, not guessed.
  * The weights are the operator's. Every response names the model that served it, the first
    response pins that name, and a response that names another stops the run.
  * Every response is written to a cache beside the scores before it is used, so a run that stops
    resumes without asking again and the record holds what the stage saw. A resumed run therefore
    checks the served name against the cache, not against the service, which is the price of not
    asking the same question twice.

    python api_judge.py run --config g3e_config.json --block calibration --model gemma31b --out run_record
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import shutil
import sys
import threading
import time
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(next((_HERE.parent / d for d in ("G3c", "g3c") if (_HERE.parent / d / "judge.py").exists()), _HERE.parent / "G3c")))
import judge as J  # noqa: E402

TOP = 20


class ModelChanged(RuntimeError):
    pass


class HTTPTransport:
    """POST to /chat/completions. Retries what is worth retrying and nothing else."""

    def __init__(self, base_url: str, token: str, timeout: float = 180.0, tries: int = 8):
        import requests
        self._requests = requests
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.headers = {"Authorization": "Bearer " + token}
        self.timeout, self.tries = timeout, tries
        self._local = threading.local()

    def __call__(self, body: dict) -> dict:
        s = getattr(self._local, "s", None)
        if s is None:
            s = self._local.s = self._requests.Session()
        wait = 2.0
        for attempt in range(self.tries):
            try:
                r = s.post(self.url, headers=self.headers, json=body, timeout=self.timeout)
                if r.status_code == 200:
                    return r.json()
                if r.status_code not in (408, 409, 425, 429, 500, 502, 503, 504):
                    raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
            except (self._requests.ConnectionError, self._requests.Timeout):
                pass
            time.sleep(wait)
            wait = min(wait * 2, 120.0)
        raise RuntimeError(f"gave up after {self.tries} tries")


class Cache:
    """Append-only record of every response, keyed by the request. Plain lines while the run is
    live so that a crash loses nothing; gzipped at close."""

    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()
        self.mem: dict[str, dict] = {}
        self.hits = self.misses = 0
        gz = path.with_suffix(path.suffix + ".gz")
        if gz.exists() and not path.exists():
            with gzip.open(gz, "rt", encoding="utf-8") as f, open(path, "w", encoding="utf-8") as g:
                shutil.copyfileobj(f, g)
            gz.unlink()
        if path.exists():
            with open(path, encoding="utf-8") as f:
                for line in f:
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue                # a line cut short by a crash
                    self.mem[rec["k"]] = rec["v"]
        self.fh = open(path, "a", encoding="utf-8")

    @staticmethod
    def key(body: dict) -> str:
        return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def get(self, body: dict):
        v = self.mem.get(self.key(body))
        with self.lock:
            if v is None:
                self.misses += 1
            else:
                self.hits += 1
        return v

    def put(self, body: dict, value: dict):
        k = self.key(body)
        with self.lock:
            self.mem[k] = value
            self.fh.write(json.dumps({"k": k, "v": value}, ensure_ascii=False) + "\n")
            self.fh.flush()

    def close(self):
        self.fh.close()
        gz = self.path.with_suffix(self.path.suffix + ".gz")
        with open(self.path, "rb") as f, gzip.open(gz, "wb") as g:
            shutil.copyfileobj(f, g)
        self.path.unlink()


def reduce_response(j: dict) -> dict:
    """Keep what the gate reads: who served it, what it wrote, and the top tokens per position."""
    ch = j["choices"][0]
    content = (ch.get("logprobs") or {}).get("content") or []
    return {"model": j.get("model"), "text": ch["message"].get("content") or "",
            "top": [[[d["token"], float(d["logprob"])] for d in pos["top_logprobs"]] for pos in content]}


class APIJudge:
    def __init__(self, spec: dict, precision: str, cfg: dict, transport=None, cache_path: Path | None = None):
        api = cfg["api"]
        self.cfg, self.spec = cfg, spec
        self.name = spec["model_id"].split(":", 1)[1]
        self.expect = spec.get("served_as")
        self.extra = dict(api.get("extra_body", {}))
        self.workers = int(api.get("concurrency", 4))
        if transport is None:
            token = open(os.path.expanduser(api["token_file"])).read().strip()
            transport = HTTPTransport(api["base_url"], token)
        self.transport = transport
        self.cache = Cache(Path(cache_path)) if cache_path else None
        self.served = None
        self.lock = threading.Lock()
        self.model_class = "api:" + api["base_url"]
        self.loaded_revision = None
        self.n_requests = 0      # sent to the service
        self.n_asks = 0          # asked for, cache hits included
        # The harness records who served the block before the first worksheet is scored, so ask once now.
        self._ask([{"role": "user", "content": "Reply with the digit 1 and nothing else."}], 1, False)

    # ------------------------------------------------------------------ one request

    def _ask(self, messages: list[dict], max_tokens: int, forced: bool) -> dict:
        body = {"model": self.name, "messages": messages, "max_tokens": max_tokens, "temperature": 0.0,
                "logprobs": True, "top_logprobs": TOP}
        body.update(self.extra)
        if forced:
            body.update({"continue_final_message": True, "add_generation_prompt": False})
        with self.lock:
            self.n_asks += 1
        v = self.cache.get(body) if self.cache else None
        if v is None:
            v = reduce_response(self.transport(body))
            with self.lock:
                self.n_requests += 1
            if self.cache:
                self.cache.put(body, v)
        with self.lock:
            if self.served is None:
                if self.expect and v["model"] != self.expect:
                    raise ModelChanged(f"expected {self.expect!r}, served {v['model']!r}")
                self.served = self.loaded_revision = v["model"]
            elif v["model"] != self.served:
                raise ModelChanged(f"pinned {self.served!r}, served {v['model']!r}")
        if not v["top"]:
            raise RuntimeError("a response carried no log probabilities")
        return v

    @staticmethod
    def _probs(top_pos: list) -> tuple[dict, float]:
        """The visible tokens with their probabilities, and the mass on everything else.

        A served model reports the most probable tokens of a normalised distribution, so what the
        visible ones leave short of one is exactly the mass it did not show. That is measured, not
        guessed from the smallest visible probability."""
        p = {}
        for tok, lp in top_pos:
            p[tok] = p.get(tok, 0.0) + math.exp(lp)
        return p, max(0.0, 1.0 - sum(p.values()))

    def _map(self, fn, items):
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            return list(ex.map(fn, items))

    # ------------------------------------------------------------------ the digit tree, over the API

    def _tree(self, user: str, first: dict, scale: dict, prune: float) -> dict:
        lo, hi = scale["lo"], scale["hi"]
        dist = np.zeros(hi - lo + 1)
        invalid = pruned = 0.0
        digit_mass = sum(v for k, v in first["p"].items() if k.isdigit())
        # Everything here is conditional on the first token being a digit, so the mass the server
        # did not show at the first position enters the bound on that scale.
        unseen = first["missing"] / max(digit_mass, 1e-30)
        frontier = []
        for tok, v in first["p"].items():
            if not tok.isdigit():
                continue
            p = v / max(digit_mass, 1e-30)
            if len(tok) > 3 or int(tok) > hi:
                invalid += p             # appending digits never lowers a value
            elif p > prune:
                frontier.append((tok, p))
            else:
                pruned += p
        while frontier:
            # Worksheets run in parallel and a tree's own requests run in turn, so the number in
            # flight never exceeds the registered concurrency.
            answers = [self._ask([{"role": "user", "content": user}, {"role": "assistant", "content": f[0]}], 1, True)
                       for f in frontier]
            nxt = []
            for (s, p), a in zip(frontier, answers):
                pn, missing = self._probs(a["top"][0])
                digits = {k: v for k, v in pn.items() if k.isdigit()}
                # Whatever is not a visible digit ends the score. The mass the server did not show
                # might have been a digit instead, so it is booked as stopping and bounded here.
                p_stop = max(0.0, 1.0 - sum(digits.values()))
                unseen += p * missing
                if lo <= int(s) <= hi:
                    dist[int(s) - lo] += p * p_stop
                else:
                    invalid += p * p_stop
                for tok, v in digits.items():
                    q, child = p * v, s + tok
                    if len(s) >= 3 or len(child) > 3 or int(child) > hi:
                        invalid += q             # a fourth digit, or a value above the scale
                    elif q > prune:
                        nxt.append((child, q))
                    else:
                        pruned += q
            frontier = nxt
        valid = float(dist.sum())
        return {"p": dist / valid if valid > 0 else dist, "mass_on_codebook": digit_mass, "tree_valid_mass": valid,
                "tree_invalid_mass": invalid, "tree_pruned_mass": pruned, "tree_unseen_bound": unseen}

    # ------------------------------------------------------------------ the three methods of a judge

    def score(self, texts: list[str], scale: dict, n_samples: int, temperature: float, batch: int) -> list[dict]:
        lo, hi = scale["lo"], scale["hi"]
        single = hi <= 9
        if not single and float(temperature) != 1.0:
            raise ValueError("the digit tree gives the distribution at temperature one only")
        prune = float(self.cfg.get("tree_prune", 1e-5))

        def one(text: str) -> dict:
            user = J.score_prompt(self.cfg, text, scale)
            a = self._ask([{"role": "user", "content": user}], 4, False)
            pfirst, missing = self._probs(a["top"][0])
            rec = {"text": a["text"], "argmax": J.parse_int(a["text"], scale), "unseen_mass": round(missing, 8)}
            if single:
                p = np.array([pfirst.get(str(s), 0.0) for s in range(lo, hi + 1)])
                rec["mass_on_codebook"] = round(float(p.sum()), 6)
                rec["codebook_tokens_seen"] = int((p > 0).sum())
                source = "api_first_token"
            else:
                t = self._tree(user, {"p": pfirst, "missing": missing}, scale, prune)
                p = t["p"]
                rec["mass_on_codebook"] = round(float(t["mass_on_codebook"]), 6)
                rec["tree_valid_mass"] = round(float(t["tree_valid_mass"]), 6)
                rec["tree_invalid_mass"] = round(float(t["tree_invalid_mass"]), 6)
                rec["tree_pruned_mass"] = round(float(t["tree_pruned_mass"]), 8)
                rec["tree_unseen_bound"] = round(float(t["tree_unseen_bound"]), 8)
                source = "api_digit_tree"
            if p.sum() <= 0:
                raise RuntimeError("no codebook token among the visible tokens")
            p = p / p.sum()
            rec["p"] = [round(float(x), 6) for x in p]
            if n_samples > 0:
                pt = p ** (1.0 / max(float(temperature), 1e-6)) if single else p
                pt = pt / pt.sum()
                srng = np.random.default_rng([int(self.cfg.get("sample_seed", 0)), zlib.crc32(text.encode()), hi])
                rec["samples"] = [float(x) for x in srng.choice(np.arange(lo, hi + 1), size=int(n_samples), p=pt)]
                rec["samples_source"] = source
            return rec

        return self._map(one, texts)

    def pairwise(self, firsts: list[str], seconds: list[str], batch: int) -> list[float]:
        prefix = self.cfg["prompts"].get("pairwise_prefix", "")
        if prefix:
            raise ValueError("a pairwise prefix needs a forced continuation, which this gate does not register")

        def one(ab) -> float:
            a = self._ask([{"role": "user", "content": J.pair_prompt(self.cfg, ab[0], ab[1])}], 1, False)
            p, _ = self._probs(a["top"][0])
            pa, pb = p.get("A", 0.0), p.get("B", 0.0)
            return float(pa / (pa + pb)) if pa + pb > 0 else float("nan")

        return self._map(one, list(zip(firsts, seconds)))

    def close(self):
        if self.cache:
            self.cache.close()


def factory(out_dir: str, block: str, transport=None):
    def make(spec: dict, precision: str, cfg: dict):
        if not str(spec["model_id"]).startswith("api:"):
            return J.make_judge(spec, precision, cfg)
        d = Path(out_dir) / block / f"{spec['key']}__{precision}"
        d.mkdir(parents=True, exist_ok=True)
        return APIJudge(spec, precision, cfg, transport=transport, cache_path=d / "api_cache.jsonl")
    return make


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run"])
    ap.add_argument("--config", required=True)
    ap.add_argument("--block", choices=["calibration", "test"], required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--precision", default="served")
    ap.add_argument("--out", default="run_record")
    a = ap.parse_args(argv)
    cfg = json.load(open(a.config, encoding="utf-8"))
    cfg["_role"] = "run"
    r = J.run_block(cfg, a.block, a.model, a.precision, a.out, judge_factory=factory(a.out, a.block))
    print(json.dumps({"served": r["loaded_revision"], "files": r["files"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
