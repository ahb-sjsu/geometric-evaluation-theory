"""Second diagnosis: two ways out of the selection bias, tested against each other.

The first diagnosis settled the cause. Every reader, including the one that
fits no curve family, holds its constant in a two-move world and drifts in a
six-move world. Keeping only positions where the player chose one of the top
two conditions on those two beating the rest, and that favours the better of
them more as noise grows against the spacing of the alternatives. The bias is
in the conditioning, so no cleverer curve removes it.

Two ways out.

  cutoff   Keep the two-alternative reader, and keep only positions that really
           are two-alternative: the engine's third move far below its second. No
           model of the other moves is needed because they are out of reach.
           The cutoff has to be in fixed win-probability units, since the
           threshold is what is being measured and cannot be used to set it.

  menu     Stop conditioning. Fit one noise scale to the player's choice over
           the engine's whole menu at once, a multinomial choice model in the
           line of Regan and Haworth. Nothing is dropped, so nothing is selected.
           The risk moves to the noise family: a logit menu model is exact for
           Gumbel noise and an approximation for Gaussian, so it is tested in
           both worlds, the one it assumes and the one it does not.

The bar is the one the law needs. Reported scale over true scale must be
constant across a twenty-fold range, and the log-log slope must be one.
"""
import json

import numpy as np
from scipy.optimize import minimize, minimize_scalar

SDS = [0.01, 0.02, 0.05, 0.10, 0.20]
N = 80000
K = 6


def world(rng, n, sd, noise, lapse=0.03):
    gap = np.clip(np.exp(rng.normal(np.log(0.03), 1.1, size=n)), 1e-4, 0.6)
    extra = rng.exponential(0.05, size=(n, K - 2))
    vals = np.zeros((n, K))
    vals[:, 1] = -gap
    vals[:, 2:] = -gap[:, None] - np.cumsum(extra, axis=1)
    if noise == "gaussian":
        eps = rng.normal(0, sd, size=vals.shape)
    else:                                   # Gumbel with the same standard deviation
        beta = sd * np.sqrt(6) / np.pi
        eps = rng.gumbel(0, beta, size=vals.shape)
    choice = np.argmax(vals + eps, axis=1)
    slip = rng.random(n) < lapse
    choice[slip] = rng.integers(0, K, size=slip.sum())
    return vals, choice


def weibull_top2(g, y):
    def nll(th):
        le, lk, b = th
        lam = 0.25 / (1 + np.exp(-b))
        p = 0.5 + (0.5 - lam) * (1 - np.exp(-(g / np.exp(le)) ** np.exp(lk)))
        p = np.clip(p, 1e-9, 1 - 1e-9)
        return -np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))
    best = min((minimize(nll, [np.log(q), 0.3, -2.0], method="Nelder-Mead",
                         options={"maxiter": 4000}) for q in np.quantile(g, [0.3, 0.5, 0.8])),
               key=lambda r: r.fun)
    return float(np.exp(best.x[0]) * np.log(2.0) ** (1.0 / np.exp(best.x[1])))


def read_top2(vals, choice, third_cutoff=None):
    g = -vals[:, 1]
    keep = choice <= 1
    if third_cutoff is not None:
        keep &= (vals[:, 1] - vals[:, 2]) >= third_cutoff
    if keep.sum() < 800:
        return None, int(keep.sum())
    return weibull_top2(g[keep], (choice[keep] == 0).astype(float)), int(keep.sum())


def read_menu(vals, choice):
    """One temperature over the whole menu, with a uniform lapse component."""
    def nll(th):
        lt, b = th
        tau = np.exp(lt)
        lam = 0.25 / (1 + np.exp(-b))
        z = vals / tau
        z = z - z.max(axis=1, keepdims=True)
        p = np.exp(z)
        p = p / p.sum(axis=1, keepdims=True)
        pc = (1 - lam) * p[np.arange(len(choice)), choice] + lam / K
        return -np.sum(np.log(np.clip(pc, 1e-12, None)))
    best = min((minimize(nll, [np.log(t0), -2.0], method="Nelder-Mead",
                         options={"maxiter": 3000}) for t0 in (0.01, 0.05, 0.2)),
               key=lambda r: r.fun)
    return float(np.exp(best.x[0]))


def main():
    rng = np.random.default_rng(90210)
    out = {}
    for noise in ("gaussian", "gumbel"):
        data = [world(rng, N, sd, noise) for sd in SDS]
        rows = {}

        e0 = [read_top2(v, c)[0] for v, c in data]
        rows["top2_no_cutoff"] = e0
        for cut in (0.10, 0.20, 0.30):
            r = [read_top2(v, c, cut) for v, c in data]
            rows["top2_third_below_%.2f" % cut] = [x[0] for x in r]
            rows["n_kept_%.2f" % cut] = [x[1] for x in r]
        rows["menu"] = [read_menu(v, c) for v, c in data]

        out[noise] = {}
        for name, eps in rows.items():
            if name.startswith("n_kept"):
                print("%-9s %-24s %s" % (noise, name, eps), flush=True)
                out[noise][name] = eps
                continue
            ok = [(e, sd) for e, sd in zip(eps, SDS) if e is not None]
            if len(ok) < 3:
                # Too few positions survive this cutoff to read a slope. That is
                # itself the cost of the cutoff and is printed, not hidden.
                print("%-9s %-24s too few positions survive, %d of %d conditions readable"
                      % (noise, name, len(ok), len(SDS)), flush=True)
                out[noise][name] = {"readable_conditions": len(ok)}
                continue
            const = [e / sd for e, sd in ok]
            slope = float(np.polyfit(np.log([sd for _, sd in ok]), np.log([e for e, _ in ok]), 1)[0])
            out[noise][name] = {"scale_over_sd": const, "spread": max(const) / min(const),
                                "slope_should_be_1": slope}
            print("%-9s %-24s scale/sd %s  spread %.3f  slope %.4f"
                  % (noise, name, ["%.3f" % c for c in const], max(const) / min(const), slope),
                  flush=True)
    with open("/home/claude/deploy/g7a_reader_diagnosis2.json", "w") as f:
        json.dump(out, f, indent=1)
    print("wrote /home/claude/deploy/g7a_reader_diagnosis2.json", flush=True)


if __name__ == "__main__":
    main()
