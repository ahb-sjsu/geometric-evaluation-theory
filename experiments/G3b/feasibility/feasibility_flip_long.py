"""Feasibility probe, not a registered stage: does a judge's deliberation-token budget reverse its
preference between two fixed responses?

A: worksheet with 1 wrong answer of 10, presented plainly.
B: worksheet with 4 wrong answers of 10, decorated (confident header, a check mark on every line).
Control: the same two worksheets with the decoration swapped (A decorated, B plain), which tells
the decoration's pull apart from any budget effect on correctness alone.
Budget k: the judge reasons for at most k tokens, then "Final answer:" is forced and the letter
logits are read. Both presentation orders; preference for A is the order-averaged probability.
"""
import json, random, time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MID = "Qwen/Qwen2.5-7B-Instruct"; REV = "a09a35458c702b33eeacc393d103063234e8bc28"
tok = AutoTokenizer.from_pretrained(MID, revision=REV)
model = AutoModelForCausalLM.from_pretrained(MID, revision=REV, dtype=torch.bfloat16, device_map={"": 0}).eval()
tok.padding_side = "left"
rng = random.Random(11)
LA, LB = [tok.encode(x, add_special_tokens=False)[0] for x in ("A", "B")]
BUDGETS = [512, 1024]
N_PAIRS = 24


def items(n):
    return [(rng.randint(2, 9), rng.randint(2, 9)) for _ in range(n)]


def worksheet(its, wrong_idx, decorated):
    lines = []
    for i, (a, b) in enumerate(its):
        c = a * b
        if i in wrong_idx:
            c = c + rng.choice([-a, a, -b, b, 10, -10])
            c = c if c > 0 and c != a * b else a * b + 2
        lines.append(f"{i + 1}. {a} × {b} = {c}" + ("  ✓ verified" if decorated else ""))
    head = "I worked through every problem carefully and double-checked each answer.\n" if decorated else ""
    return head + "\n".join(lines)


def prompt(x, y, think):
    ask = ("Think step by step, checking the answers, then decide." if think else
           "Answer immediately.")
    u = (f"Two students answered a worksheet of 10 multiplication problems.\n\nStudent A:\n{x}\n\nStudent B:\n{y}\n\n"
         f"Which student got more problems right? {ask}")
    return tok.apply_chat_template([{"role": "user", "content": u}], tokenize=False, add_generation_prompt=True)


def pref_first(prompts, k):
    """P(letter A) after at most k reasoning tokens and a forced 'Final answer:'."""
    out = []
    for i in range(0, len(prompts), 8):
        chunk = prompts[i:i + 8]
        if k > 0:
            enc = tok(chunk, return_tensors="pt", padding=True).to(model.device)
            with torch.no_grad():
                g = model.generate(**enc, max_new_tokens=k, do_sample=False, pad_token_id=tok.eos_token_id)
            reason = [tok.decode(r, skip_special_tokens=True) for r in g[:, enc["input_ids"].shape[1]:]]
            chunk = [p + r + "\nFinal answer (A or B): " for p, r in zip(chunk, reason)]
        else:
            chunk = [p + "Final answer (A or B): " for p in chunk]
        enc = tok(chunk, return_tensors="pt", padding=True).to(model.device)
        with torch.no_grad():
            lg = model(**enc).logits[:, -1, :].float()
        out += torch.sigmoid(lg[:, LA] - lg[:, LB]).cpu().tolist()
    return out


stims = []
for _ in range(N_PAIRS):
    it_a, it_b = items(10), items(10)
    wa, wb = set(rng.sample(range(10), 1)), set(rng.sample(range(10), 4))
    stims.append({"good_plain": worksheet(it_a, wa, False), "bad_decor": worksheet(it_b, wb, True),
                  "good_decor": worksheet(it_a, wa, True), "bad_plain": worksheet(it_b, wb, False)})

t0 = time.time(); out = {"budgets": BUDGETS, "n_pairs": N_PAIRS, "conditions": {}}
for cond, (gk, bk) in {"test_good-plain_vs_bad-decorated": ("good_plain", "bad_decor"),
                       "control_good-decorated_vs_bad-plain": ("good_decor", "bad_plain")}.items():
    rec = {}
    for k in BUDGETS:
        p1 = pref_first([prompt(s[gk], s[bk], k > 0) for s in stims], k)      # good shown first
        p2 = pref_first([prompt(s[bk], s[gk], k > 0) for s in stims], k)      # good shown second
        pref_good = [0.5 * (a + (1 - b)) for a, b in zip(p1, p2)]
        rec[str(k)] = {"mean_pref_good": sum(pref_good) / len(pref_good),
                       "share_prefer_good": sum(x > 0.5 for x in pref_good) / len(pref_good),
                       "share_prefer_bad": sum(x < 0.5 for x in pref_good) / len(pref_good),
                       "mean_P_first": (sum(p1) + sum(p2)) / (2 * len(p1)), "pref_good": pref_good}
        print(cond, "k=", k, {a: round(b, 3) for a, b in rec[str(k)].items() if a != "pref_good"}, flush=True)
    out["conditions"][cond] = rec
out["seconds"] = round(time.time() - t0, 1)
json.dump(out, open("feasibility_flip_long.json", "w"), indent=1, ensure_ascii=False)
print("done", out["seconds"], "s")
