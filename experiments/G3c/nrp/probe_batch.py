"""Size a judge's batches to the GPU it actually got, with batch-probe, and record what was chosen.

The sealed batch sizes were fitted on Atlas (Quadro GV100), where bfloat16 runs on the slow path.
On a card with native bfloat16 the same batch leaves the GPU idle between Python steps, and NRP
deletes a pod whose GPU sits under 40 percent. batch-probe binary-searches the largest batch whose
forward pass fits, with headroom, so the device is actually saturated.

    python probe_batch.py --config prereg_config.json --model qwen7b --precision full \\
        --out /data/runs/run/calibration/qwen7b__full/batch_probe.json --write-config

Two shapes are probed under no_grad, both the ones the run performs: a scoring prompt of about 400
tokens, which is also the digit tree's first pass, and a pairwise prompt of about 800 tokens. The
scoring batch is used for `batch` and `batch_tree`, the pairwise one for `batch_pairwise`, and
`tree_rows` is left as the registration sets it. With --write-config the pod's own copy of the
config is updated in place; the sealed file in the repository and the ConfigMap are untouched, and
the JSON written beside the run's data records what the pod used.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, "/work/g3c")
import judge  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True); ap.add_argument("--model", required=True)
    ap.add_argument("--precision", default="full"); ap.add_argument("--out", required=True)
    ap.add_argument("--write-config", action="store_true")
    ap.add_argument("--score-tokens", type=int, default=420); ap.add_argument("--pair-tokens", type=int, default=820)
    a = ap.parse_args()
    import torch
    from batch_probe import probe_batch_size

    cfg = json.load(open(a.config, encoding="utf-8"))
    spec = {m["key"]: m for m in cfg["models"]}[a.model]
    merged = {**cfg, **{k: spec[k] for k in ("batch", "batch_tree", "batch_pairwise", "tree_rows") if k in spec}}
    J = judge.LMJudge(spec, a.precision, merged)
    dev = J.model.device
    name = torch.cuda.get_device_name(0)

    def probe(length: int) -> int:
        def input_fn(b: int):
            ids = torch.randint(1000, 2000, (b, length), device=dev)
            return {"input_ids": ids, "attention_mask": torch.ones_like(ids)}
        return int(probe_batch_size(J.model, input_fn, mode="infer", low=1, high=256, headroom=0.25,
                                    device=dev, verbose=False))

    score_b, pair_b = probe(a.score_tokens), probe(a.pair_tokens)
    rec = {"gpu": name, "model": a.model, "precision": a.precision,
           "sealed": {k: merged.get(k) for k in ("batch", "batch_tree", "batch_pairwise", "tree_rows")},
           "probed": {"score_tokens": a.score_tokens, "score_batch": score_b,
                      "pair_tokens": a.pair_tokens, "pair_batch": pair_b},
           "chosen": {"batch": max(1, score_b), "batch_tree": max(1, score_b), "batch_pairwise": max(1, pair_b),
                      "tree_rows": merged.get("tree_rows")},
           "total_gib": round(torch.cuda.get_device_properties(0).total_memory / 2**30, 2)}
    J.close()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(rec, open(a.out, "w"), indent=1)
    if a.write_config:
        for m in cfg["models"]:
            if m["key"] == a.model:
                m.update({k: v for k, v in rec["chosen"].items() if v is not None})
        cfg["batch_probe"] = {a.model: rec["chosen"], "gpu": name}
        json.dump(cfg, open(a.config, "w"), indent=1)
    print(json.dumps(rec))
    print("PROBE_DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
