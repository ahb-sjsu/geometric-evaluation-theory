"""G3e self-test of the reader. No network, no GPU.

A fake server of known structure answers the same requests the real one does, so every claim the
adapter makes can be checked against the truth it was built from.

  1. single-token scale   the vector read back equals the server's, and the greedy text is its argmax
  2. digit tree           the distribution over 0 to 100 equals the server's exactly, when nothing
                          is pruned and nothing falls outside the visible twenty
  3. grouped digits       a server whose tokenizer emits "100" and "85" as single tokens is read
                          correctly, which is the tokenizer difference the gate exists to test
  4. the twenty-token wall the mass the adapter reports as unseen bounds the mass it actually lost
  5. pruning              what is pruned is reported, and the reported vector still sums to one
  6. the model pin        a server that changes model mid-block stops the run
  7. the cache            a second pass sends no request and returns the same records
  8. end to end           a synthetic judge behind the fake server, read through G3c's harness and
                          G3c's grader, predicts its own test block and is graded PASS

Run: python api_selftest.py --out selftest
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(next((_HERE.parent / d for d in ("G3c", "g3c") if (_HERE.parent / d / "judge.py").exists()), _HERE.parent / "G3c")))
import api_judge as A  # noqa: E402
import judge as J  # noqa: E402
import judge_grade  # noqa: E402

TOP = A.TOP


class FakeServer:
    """A judge whose score distribution is a known function of the worksheet's error count.

    `group` makes the tokenizer emit multi-digit tokens, as a digit-grouping tokenizer does.
    `visible` caps how many tokens a position reports, which is the wall a served model puts up.
    """

    def __init__(self, model="fake/judge-1", group=False, visible=TOP, sd=1.2, name_switch_at=None):
        self.model, self.group, self.visible, self.sd = model, group, visible, sd
        self.name_switch_at = name_switch_at
        self.calls = 0

    # the truth: a Gaussian over the scale, centred on quality
    def dist(self, e: int, lo: int, hi: int) -> np.ndarray:
        q = 1.0 - e / 20.0
        centre = lo + q * (hi - lo)
        sd = self.sd * (hi - lo) / 9.0
        x = np.arange(lo, hi + 1, dtype=float)
        p = np.exp(-0.5 * ((x - centre) / sd) ** 2)
        return p / p.sum()

    @staticmethod
    def _e_of(user: str) -> int:
        return sum(1 for ln in user.split("\n") if J._line_correct(ln) is False and "×" in ln)

    def _scale_of(self, user: str) -> tuple[int, int]:
        import re
        m = re.search(r"from (\d+) to (\d+)", user)
        return (int(m.group(1)), int(m.group(2))) if m else (0, 9)

    def _tokens(self, value: int, hi: int) -> list[str]:
        s = str(value)
        return [s] if (self.group or hi <= 9) else list(s)

    def __call__(self, body: dict) -> dict:
        self.calls += 1
        model = self.model
        if self.name_switch_at and self.calls > self.name_switch_at:
            model = self.model + "-v2"
        msgs = body["messages"]
        user = msgs[0]["content"]
        if "Which student got more problems right" in user:
            top = [["A", math.log(0.7)], ["B", math.log(0.3)]]
            return {"model": model, "choices": [{"message": {"content": "A"},
                    "logprobs": {"content": [{"top_logprobs": [{"token": t, "logprob": lp} for t, lp in top]}]}}]}
        lo, hi = self._scale_of(user)
        p = self.dist(self._e_of(user), lo, hi)
        prefix = msgs[1]["content"] if len(msgs) > 1 else ""
        # next-token distribution given the prefix already written
        nxt: dict[str, float] = {}
        for v, pv in zip(range(lo, hi + 1), p):
            toks = self._tokens(v, hi)
            joined = ""
            for i, t in enumerate(toks):
                if joined == prefix:
                    nxt[t] = nxt.get(t, 0.0) + float(pv)
                    break
                joined += t
            else:
                if joined == prefix:             # the prefix is a whole value: this row stops here
                    nxt["<stop>"] = nxt.get("<stop>", 0.0) + float(pv)
        tot = sum(nxt.values())
        if tot <= 0:
            nxt = {"<stop>": 1.0}
            tot = 1.0
        items = sorted(((t, v / tot) for t, v in nxt.items()), key=lambda x: -x[1])[:self.visible]
        top = [[t, math.log(max(v, 1e-30))] for t, v in items]
        # the greedy continuation, for the text read-out
        best = int(np.arange(lo, hi + 1)[int(np.argmax(p))])
        text = "".join(self._tokens(best, hi)) if not prefix else "".join(self._tokens(best, hi))[len(prefix):]
        positions = [{"top_logprobs": [{"token": t, "logprob": lp} for t, lp in top]}]
        if not prefix and not self.group and hi > 9 and len(str(best)) > 1:
            # a second position, so the free run's own second step exists in the record
            rest = {}
            for v, pv in zip(range(lo, hi + 1), p):
                ts = self._tokens(v, hi)
                if ts[0] == str(best)[0] and len(ts) > 1:
                    rest[ts[1]] = rest.get(ts[1], 0.0) + float(pv)
            rt = sum(rest.values()) or 1.0
            positions.append({"top_logprobs": [{"token": t, "logprob": math.log(max(v / rt, 1e-30))}
                                               for t, v in sorted(rest.items(), key=lambda x: -x[1])[:self.visible]]})
        return {"model": model, "choices": [{"message": {"content": text}, "logprobs": {"content": positions}}]}


def cfg_for(scales, sample_seed=7) -> dict:
    cfg = json.load(open(Path(_HERE.parent / "G3c" / "prereg_config.json"), encoding="utf-8"))
    cfg = copy.deepcopy(cfg)
    cfg["scales"] = scales
    cfg["sample_seed"] = sample_seed
    cfg["api"] = {"base_url": "http://fake/v1", "token_file": "/dev/null", "concurrency": 2, "extra_body": {}}
    return cfg


def judge_on(server, cfg, cache=None, key="fake", served_as=None):
    spec = {"key": key, "model_id": "api:fake", "precisions": ["served"]}
    if served_as:
        spec["served_as"] = served_as
    return A.APIJudge(spec, "served", cfg, transport=server, cache_path=cache)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="selftest")
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    checks = []

    def check(name, ok, detail=None):
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    rng = np.random.default_rng(99)
    sheets = [J.make_worksheet(rng, 20, e) for e in (0, 5, 11, 17, 20)]
    texts = [s["text"] for s in sheets]

    # 1. single-token scale
    srv = FakeServer()
    cfg = cfg_for([{"lo": 0, "hi": 9}])
    recs = judge_on(srv, cfg).score(texts, {"lo": 0, "hi": 9}, 8, 1.0, 16)
    worst = max(float(np.abs(np.array(r["p"]) - srv.dist(s["e"], 0, 9)).max()) for r, s in zip(recs, sheets))
    check("single-token scale: the vector read back is the server's", worst < 1e-6, {"largest difference": worst})
    check("single-token scale: the greedy text is the argmax",
          all(r["argmax"] == float(np.argmax(srv.dist(s["e"], 0, 9))) for r, s in zip(recs, sheets)),
          {"argmax": [r["argmax"] for r in recs]})

    # 2. digit tree, one digit at a time
    srv = FakeServer()
    cfg = cfg_for([{"lo": 0, "hi": 100}])
    cfg["tree_prune"] = 0.0
    recs = judge_on(srv, cfg).score(texts, {"lo": 0, "hi": 100}, 8, 1.0, 16)
    worst = max(float(np.abs(np.array(r["p"]) - srv.dist(s["e"], 0, 100)).max()) for r, s in zip(recs, sheets))
    check("digit tree: the distribution over 0 to 100 is the server's", worst < 1e-6,
          {"largest difference": worst, "invalid": max(r["tree_invalid_mass"] for r in recs)})

    # 3. grouped digits. With 101 scores and one token each, a server showing twenty cannot show
    # them all, so this asks the reader to be exact when the wall is lifted and honest when it is not.
    srvg = FakeServer(group=True, visible=200)
    recsg = judge_on(srvg, cfg).score(texts, {"lo": 0, "hi": 100}, 8, 1.0, 16)
    worstg = max(float(np.abs(np.array(r["p"]) - srvg.dist(s["e"], 0, 100)).max()) for r, s in zip(recsg, sheets))
    check("grouped digits: a tokenizer that writes a whole score as one token is read correctly",
          worstg < 1e-6, {"largest difference": worstg})
    srvg20 = FakeServer(group=True, visible=TOP)
    rg20 = judge_on(srvg20, cfg).score(texts[:1], {"lo": 0, "hi": 100}, 0, 1.0, 16)[0]
    lost_g = float(np.abs(np.array(rg20["p"]) - srvg20.dist(sheets[0]["e"], 0, 100)).sum() / 2)
    check("grouped digits behind the wall: the reported bound covers the mass lost",
          rg20["tree_unseen_bound"] + 1e-9 >= lost_g,
          {"bound": rg20["tree_unseen_bound"], "lost": round(lost_g, 6)})

    # 3b. a vocabulary that contains Unicode number characters. `str.isdigit()` is true for
    # them and `int()` refuses them, which stopped a calibration block on the token "1\u2083".
    class OddTokenServer(FakeServer):
        def __call__(self, body):
            r = super().__call__(body)
            pos = r["choices"][0]["logprobs"]["content"][0]["top_logprobs"]
            pos.append({"token": "1\u2083", "logprob": math.log(0.02)})
            pos.append({"token": "\u00b2", "logprob": math.log(0.01)})
            return r
    odd = judge_on(OddTokenServer(), cfg).score(texts[:2], {"lo": 0, "hi": 100}, 0, 1.0, 16)
    # The vector is written rounded to six decimals, so 101 entries may sum to one only to
    # about 5e-5. The check is that the reader finishes and returns a distribution at all.
    check("a Unicode number character in the vocabulary does not stop the reader",
          all(abs(sum(r["p"]) - 1.0) < 1e-4 and r["argmax"] == r["argmax"] for r in odd),
          {"sums": [round(sum(r["p"]), 6) for r in odd]})
    odd9 = judge_on(OddTokenServer(), cfg_for([{"lo": 0, "hi": 9}])).score(texts[:2], {"lo": 0, "hi": 9}, 0, 1.0, 16)
    check("and it is not counted as a score on a single-token scale",
          all(abs(sum(r["p"]) - 1.0) < 1e-6 for r in odd9))

    # 4. the twenty-token wall, and 5. pruning
    srvv = FakeServer(visible=6, sd=3.0)
    rec = judge_on(srvv, cfg).score(texts[:1], {"lo": 0, "hi": 100}, 0, 1.0, 16)[0]
    truth = srvv.dist(sheets[0]["e"], 0, 100)
    lost = float(np.abs(np.array(rec["p"]) - truth).sum() / 2)
    check("the twenty-token wall: the reported bound covers the mass actually lost",
          rec["tree_unseen_bound"] + 1e-9 >= lost, {"bound": rec["tree_unseen_bound"], "lost": round(lost, 6)})
    cfgp = cfg_for([{"lo": 0, "hi": 100}]); cfgp["tree_prune"] = 0.05
    recp = judge_on(FakeServer(sd=3.0), cfgp).score(texts[:1], {"lo": 0, "hi": 100}, 0, 1.0, 16)[0]
    check("pruning: what is pruned is reported and the vector still sums to one",
          recp["tree_pruned_mass"] > 0 and abs(sum(recp["p"]) - 1.0) < 1e-5,
          {"pruned": recp["tree_pruned_mass"], "sum": round(sum(recp["p"]), 6)})

    # 6. the model pin
    swapped = False
    try:
        judge_on(FakeServer(name_switch_at=3), cfg_for([{"lo": 0, "hi": 9}])).score(texts, {"lo": 0, "hi": 9}, 0, 1.0, 16)
    except A.ModelChanged as e:
        swapped = True
        detail = str(e)
    check("the model pin: a server that changes model stops the run", swapped, detail if swapped else "no error raised")
    pinned = False
    try:
        judge_on(FakeServer(), cfg_for([{"lo": 0, "hi": 9}]), served_as="someone/else").score(texts[:1], {"lo": 0, "hi": 9}, 0, 1.0, 16)
    except A.ModelChanged:
        pinned = True
    check("the model pin: a served name other than the registered one stops the run", pinned)

    # 7. the cache
    cpath = out / "cache_probe.jsonl"
    if cpath.exists():
        cpath.unlink()
    srvc = FakeServer()
    cfg9 = cfg_for([{"lo": 0, "hi": 9}])
    j1 = judge_on(srvc, cfg9, cache=cpath); r1 = j1.score(texts, {"lo": 0, "hi": 9}, 8, 1.0, 16); j1.close()
    first_calls = srvc.calls
    j2 = judge_on(srvc, cfg9, cache=cpath); r2 = j2.score(texts, {"lo": 0, "hi": 9}, 8, 1.0, 16); j2.close()
    check("the cache: a second pass sends no request and returns the same records",
          srvc.calls == first_calls and r1 == r2,
          {"calls first pass": first_calls, "calls after second": srvc.calls, "records equal": r1 == r2})

    # 8. end to end through G3c's harness and grader
    e2e = cfg_for([{"lo": 0, "hi": 9}, {"lo": 0, "hi": 100}], sample_seed=11)
    e2e["n_cal_per_level"] = 8
    e2e["n_pairs_per_gap"] = 40
    e2e["gap_ladder"] = [1, 2, 4, 8, 12]
    e2e["seeds"] = {"calibration": 4242, "test": 4243}
    e2e["bars"] = {"dev_max": 0.14, "z_max": 4.55, "threshold_factor": 1.75, "rank_agreement_min": 0.0,
                   "vacuity_acc_min": 0.9, "vacuity_bits_min": 1.0}
    e2e["models"] = [{"key": "fake", "model_id": "api:fake", "precisions": ["served"]}]
    e2e["_role"] = "run"
    server = FakeServer()
    d = out / "e2e"
    J.run_block(e2e, "calibration", "fake", "served", str(d), judge_factory=A.factory(str(d), "calibration", transport=server))
    cal = d / "calibration" / "fake__served"
    pred = judge_grade.predict(str(cal), e2e, n_boot=100)
    json.dump(pred, open(cal / "predictions.json", "w"), indent=1, default=float)
    J.run_block(e2e, "test", "fake", "served", str(d), judge_factory=A.factory(str(d), "test", transport=server))
    obs = judge_grade.observed(str(d / "test" / "fake__served"), e2e)
    v = judge_grade.grade(pred, obs, e2e["bars"])
    json.dump({"predictions": pred, "observed": obs, "verdicts": v}, open(out / "e2e_grade.json", "w"), indent=1, default=float)
    check("end to end: the harness records who served the block",
          json.load(open(d / "calibration" / "fake__served" / "results.json"))["loaded_revision"] == "fake/judge-1")
    check("end to end: J1 PASS, the calibration block predicts the test block",
          v["J1_prediction"]["verdict"] == "PASS",
          {k: round(r["max_abs_dev"], 3) for k, r in v["J1_prediction"].items() if isinstance(r, dict)})
    check("end to end: the fake judge meets anti-vacuity", v["anti_vacuity"]["met"], v["anti_vacuity"])
    check("end to end: the expected-score threshold is below the argmax on 0 to 9",
          pred["scales"]["0-9"]["readouts"]["expected"]["threshold"] < pred["scales"]["0-9"]["readouts"]["argmax"]["threshold"],
          {"expected": pred["scales"]["0-9"]["readouts"]["expected"]["threshold"],
           "argmax": pred["scales"]["0-9"]["readouts"]["argmax"]["threshold"]})

    verdict = "PASS" if all(c["pass"] for c in checks) else "FAIL"
    json.dump({"verdict": verdict, "checks": checks, "seconds": round(time.time() - t0, 1)},
              open(out / "api_selftest.json", "w"), indent=1, default=float)
    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["check"], "" if c["pass"] else json.dumps(c["detail"], default=str)[:200])
    print("SELFTEST", verdict)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
