"""Why does the threshold reader's constant drift, and which reader does not?

The two-alternative reader fails its self-test in a clean monotone way. The
ratio of reported threshold to true resolution falls from 0.975 to 0.762 as the
resolution coarsens twenty-fold, and the recovered exponent is -0.466 against a
true -0.5. A bias of that shape would corrupt exactly the law under test.

Two candidate causes, which predict different things.

  (a) Selection. Keeping only positions where the player chose one of the top
      two conditions on those two beating the other four. When noise is large
      against the spacing of the others, that favours the better of the two.
      If this is the cause, the drift vanishes in a world with only two moves.

  (b) Misspecification. The truth is a Gaussian curve in the linear gap, and
      the reader fits a logistic in the log gap. A wrong family puts its
      midpoint in a place that depends on where the data mass sits relative to
      the transition, and that moves with the resolution because the gap
      distribution is fixed. If this is the cause, the drift survives in the
      two-move world and goes away under a family with the right shape, or
      under a reader that uses no family at all.

Three readers are compared in both worlds.

  logistic   logistic in log gap, slope free         (the failing reader)
  weibull    Weibull in linear gap, shape free       (the psychophysics standard)
  isotonic   monotone regression, 75 percent crossing (no family)
"""
import json

import numpy as np
from scipy.optimize import minimize
from sklearn.isotonic import IsotonicRegression

SDS = [0.01, 0.02, 0.05, 0.10, 0.20]
N = 80000


def simulate(rng, n_pos, sd, k_moves, lapse=0.03):
    gap = np.clip(np.exp(rng.normal(np.log(0.03), 1.1, size=n_pos)), 1e-4, 0.6)
    vals = np.zeros((n_pos, k_moves))
    vals[:, 1] = -gap
    if k_moves > 2:
        extra = rng.exponential(0.05, size=(n_pos, k_moves - 2))
        vals[:, 2:] = -gap[:, None] - np.cumsum(extra, axis=1)
    choice = np.argmax(vals + rng.normal(0, sd, size=vals.shape), axis=1)
    slip = rng.random(n_pos) < lapse
    choice[slip] = rng.integers(0, k_moves, size=slip.sum())
    keep = choice <= 1
    return gap[keep], (choice[keep] == 0).astype(float)


def fit_logistic(g, y):
    lg = np.log(g)

    def nll(th):
        mu, ls, b = th
        lam = 0.25 / (1 + np.exp(-b))
        p = 0.5 + (0.5 - lam) / (1 + np.exp(-(lg - mu) / np.exp(ls)))
        p = np.clip(p, 1e-9, 1 - 1e-9)
        return -np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))
    best = min((minimize(nll, [m, 0.0, -2.0], method="Nelder-Mead",
                         options={"maxiter": 4000}) for m in np.quantile(lg, [0.3, 0.5, 0.7])),
               key=lambda r: r.fun)
    return float(np.exp(best.x[0]))


def fit_weibull(g, y):
    def nll(th):
        le, lk, b = th
        lam = 0.25 / (1 + np.exp(-b))
        p = 0.5 + (0.5 - lam) * (1 - np.exp(-(g / np.exp(le)) ** np.exp(lk)))
        p = np.clip(p, 1e-9, 1 - 1e-9)
        return -np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))
    best = min((minimize(nll, [np.log(q), 0.3, -2.0], method="Nelder-Mead",
                         options={"maxiter": 4000}) for q in np.quantile(g, [0.3, 0.5, 0.8])),
               key=lambda r: r.fun)
    e, k = np.exp(best.x[0]), np.exp(best.x[1])
    # Report the gap at which the lapse-free curve reaches 75 percent, so the
    # three readers are reporting the same point of the curve.
    return float(e * (np.log(2.0)) ** (1.0 / k))


def fit_isotonic(g, y):
    order = np.argsort(g)
    lg, yy = np.log(g[order]), y[order]
    iso = IsotonicRegression(y_min=0.0, y_max=1.0, increasing=True).fit(lg, yy)
    grid = np.linspace(lg.min(), lg.max(), 4000)
    p = iso.predict(grid)
    idx = np.searchsorted(p, 0.75)
    idx = min(max(idx, 1), len(grid) - 1)
    return float(np.exp(grid[idx]))


READERS = {"logistic": fit_logistic, "weibull": fit_weibull, "isotonic": fit_isotonic}


def main():
    rng = np.random.default_rng(424242)
    out = {}
    for world, k in (("two_moves", 2), ("six_moves", 6)):
        out[world] = {}
        data = [simulate(rng, N, sd, k) for sd in SDS]
        for name, fn in READERS.items():
            eps = [fn(g, y) for g, y in data]
            const = [e / sd for e, sd in zip(eps, SDS)]
            slope = float(np.polyfit(np.log(SDS), np.log(eps), 1)[0])
            out[world][name] = {"eps_over_sd": const, "spread": max(const) / min(const),
                                "loglog_slope_should_be_1": slope}
            print("%-10s %-9s eps/sd %s  spread %.3f  slope %.4f"
                  % (world, name, ["%.3f" % c for c in const], max(const) / min(const), slope),
                  flush=True)
    with open("/home/claude/deploy/g7a_reader_diagnosis.json", "w") as f:
        json.dump(out, f, indent=1)
    print("wrote /home/claude/deploy/g7a_reader_diagnosis.json", flush=True)


if __name__ == "__main__":
    main()
