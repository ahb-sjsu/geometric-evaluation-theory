"""Feasibility probe, not a registered stage: can Qwen2.5-7B-Instruct, answering immediately,
tell worksheets with different numbers of wrong answers apart, in pointwise scoring and in
pairwise comparison? Worksheets of N single-digit multiplications with e wrong answers."""
import json, random, sys, time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MID = "Qwen/Qwen2.5-7B-Instruct"; REV = "a09a35458c702b33eeacc393d103063234e8bc28"
tok = AutoTokenizer.from_pretrained(MID, revision=REV)
model = AutoModelForCausalLM.from_pretrained(MID, revision=REV, torch_dtype=torch.bfloat16, device_map={"": 0}).eval()
tok.padding_side = "left"
rng = random.Random(7)


def worksheet(N, e):
    items = [(rng.randint(2, 9), rng.randint(2, 9)) for _ in range(N)]
    wrong = set(rng.sample(range(N), e))
    lines = []
    for i, (a, b) in enumerate(items):
        c = a * b
        if i in wrong:
            c = c + rng.choice([-a, a, -b, b, -1, 1, -2, 2, 10, -10])
            c = c if c > 0 and c != a * b else a * b + 1
        lines.append(f"{i + 1}. {a} × {b} = {c}")
    return "\n".join(lines)


def chat(u):
    return tok.apply_chat_template([{"role": "user", "content": u}], tokenize=False, add_generation_prompt=True)


def generate(prompts, k=4):
    outs = []
    for i in range(0, len(prompts), 16):
        enc = tok(prompts[i:i + 16], return_tensors="pt", padding=True).to(model.device)
        with torch.no_grad():
            g = model.generate(**enc, max_new_tokens=k, do_sample=False, pad_token_id=tok.eos_token_id)
        outs += [tok.decode(r, skip_special_tokens=True) for r in g[:, enc["input_ids"].shape[1]:]]
    return outs


t0 = time.time()
out = {}
for N in (10, 20):
    rows = []
    for e in range(0, N + 1, max(1, N // 10)):
        for _ in range(6):
            rows.append((e, worksheet(N, e)))
    for lo, hi in ((1, 5), (1, 10), (0, 100)):
        prompts = [chat(f"Below is a worksheet of {N} multiplication problems with a student's answers.\n\n{ws}\n\n"
                        f"Rate the student's answers on a scale from {lo} to {hi}, where {hi} means every answer is correct "
                        f"and {lo} means none is. Reply with a single integer and nothing else.") for _, ws in rows]
        texts = generate(prompts)
        by_e = {}
        for (e, _), t in zip(rows, texts):
            by_e.setdefault(e, []).append(t.strip())
        out[f"N{N}_scale{lo}-{hi}"] = by_e
        print(f"N={N} scale {lo}-{hi}:", {e: v for e, v in by_e.items()}, flush=True)
    # pairwise: which of two worksheets (same N) has more correct answers, both orders, letter logits
    ids = [tok.encode(L, add_special_tokens=False) for L in ("A", "B")]
    assert all(len(i) == 1 for i in ids)
    la, lb = ids[0][0], ids[1][0]
    res = {}
    for gap in (1, 2, 4):
        correct = 0; first = []
        trials = 24
        for _ in range(trials):
            e1 = rng.randint(0, N - gap); e2 = e1 + gap
            w1, w2 = worksheet(N, e1), worksheet(N, e2)
            ps = [chat(f"Below are two students' answers to worksheets of {N} multiplication problems.\n\nStudent A:\n{x}\n\n"
                       f"Student B:\n{y}\n\nWhich student got more problems right? Answer with the single letter A or B.")
                  for x, y in ((w1, w2), (w2, w1))]
            enc = tok(ps, return_tensors="pt", padding=True).to(model.device)
            with torch.no_grad():
                lg = model(**enc).logits[:, -1, :].float()
            p = torch.sigmoid(lg[:, la] - lg[:, lb]).cpu().tolist()
            pref = 0.5 * (p[0] + (1 - p[1]))
            correct += pref > 0.5; first += [p[0], p[1]]
        res[gap] = {"accuracy": correct / trials, "mean_P_first": sum(first) / len(first)}
    out[f"N{N}_pairwise"] = res
    print(f"N={N} pairwise:", res, flush=True)
out["seconds"] = round(time.time() - t0, 1)
json.dump(out, open("feasibility_scoring.json", "w"), indent=1, ensure_ascii=False)
print("done", out["seconds"], "s")
