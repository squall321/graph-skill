"""Pure-python domain math for T2 standardized report figures (deterministic, no deps).
Self-verified in tests/test_t2.py against closed-form anchors."""

from __future__ import annotations

import math


# ── ewma-chart ───────────────────────────────────────────────────────────────
def ewma(values, lam=0.2, target=None, sigma=None):
    """EWMA control chart. z_t = λ·x_t + (1−λ)·z_{t−1}; time-varying 3σ limits
    σ_z(t) = σ·√(λ/(2−λ)·[1−(1−λ)^{2t}]). σ from moving range if not given."""
    vals = [float(v) for v in values]
    n = len(vals)
    mu = float(target) if target is not None else sum(vals) / n
    if sigma is None:
        mrs = [abs(vals[i] - vals[i - 1]) for i in range(1, n)]
        sigma = (sum(mrs) / len(mrs)) / 1.128 if mrs else 0.0
    sigma = float(sigma)
    z, ucl, lcl, zi = [], [], [], mu
    for t in range(n):
        zi = lam * vals[t] + (1 - lam) * zi
        z.append(zi)
        s = sigma * math.sqrt((lam / (2 - lam)) * (1 - (1 - lam) ** (2 * (t + 1))))
        ucl.append(mu + 3 * s)
        lcl.append(mu - 3 * s)
    viol = [i for i in range(n) if z[i] > ucl[i] or z[i] < lcl[i]]
    return {"z": z, "ucl": ucl, "lcl": lcl, "center": mu, "sigma": sigma, "violations": viol}


# ── oc-curve (sampling) ──────────────────────────────────────────────────────
def oc_curve(n, c, p_max=0.2, npts=101):
    """Operating characteristic: P(accept) vs lot fraction defective p (binomial)."""
    ps, pa = [], []
    for i in range(npts):
        p = p_max * i / (npts - 1)
        ps.append(p)
        pa.append(sum(math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k)) for k in range(0, c + 1)))
    return {"p": ps, "pa": pa}


def _interp_x_at_y(xs, ys, target):
    for i in range(1, len(xs)):
        if (ys[i - 1] - target) * (ys[i] - target) <= 0 and ys[i] != ys[i - 1]:
            t = (target - ys[i - 1]) / (ys[i] - ys[i - 1])
            return xs[i - 1] + t * (xs[i] - xs[i - 1])
    return None


# ── roc / pr curve ───────────────────────────────────────────────────────────
def roc_pr(y_true, y_score, mode="roc"):
    """ROC (FPR,TPR) or PR (recall,precision) from labels+scores. AUC by trapezoid;
    best threshold by Youden's J (ROC). Sorts by descending score."""
    pairs = sorted(zip([float(s) for s in y_score], [int(y) for y in y_true]), key=lambda t: -t[0])
    pos = sum(1 for _s, y in pairs if y)
    neg = len(pairs) - pos
    tp = fp = 0
    xs, ys = [0.0], [0.0 if mode == "roc" else 1.0]
    best = None
    for s, y in pairs:
        if y:
            tp += 1
        else:
            fp += 1
        tpr = tp / pos if pos else 0.0
        fpr = fp / neg if neg else 0.0
        if mode == "roc":
            xs.append(fpr)
            ys.append(tpr)
            j = tpr - fpr
            if best is None or j > best[0]:
                best = (j, fpr, tpr, s)
        else:
            xs.append(tpr)                                  # recall
            ys.append(tp / (tp + fp) if (tp + fp) else 1.0)  # precision
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    sx = [xs[i] for i in order]
    sy = [ys[i] for i in order]
    auc = sum((sx[i] - sx[i - 1]) * (sy[i] + sy[i - 1]) / 2 for i in range(1, len(sx)))
    return {"x": xs, "y": ys, "auc": auc, "best": best, "mode": mode}


# ── bathtub-curve (Weibull hazard) ───────────────────────────────────────────
def weibull_hazard(beta, eta, t):
    return (beta / eta) * ((t / eta) ** (beta - 1)) if t > 0 else 0.0


def bathtub(phases, tmax, npts=120):
    """Composite hazard from 3 Weibull phases [{beta,eta}] (infant β<1, useful β≈1,
    wearout β>1). Returns t[], hazard[] (sum of phase hazards)."""
    ts = [tmax * i / (npts - 1) for i in range(npts)]
    h = []
    for t in ts:
        h.append(sum(weibull_hazard(float(p["beta"]), float(p["eta"]), t) for p in phases))
    return {"t": ts, "hazard": h}


# ── crow-amsaa / Duane reliability growth ────────────────────────────────────
def crow_amsaa(failure_times):
    """NHPP power-law MLE from cumulative failure times. β=n/Σln(T/t_i), λ=n/T^β.
    β<1 ⇒ reliability growing. Returns β, λ, cumulative & instantaneous MTBF series."""
    ts = sorted(float(t) for t in failure_times if t > 0)
    n = len(ts)
    big_t = ts[-1]
    beta = n / sum(math.log(big_t / t) for t in ts)
    lam = n / (big_t ** beta)
    cum_mtbf = [(t / (lam * t ** beta)) for t in ts]           # T/N(T) = 1/(λ T^{β-1})
    inst_mtbf = [1.0 / (lam * beta * t ** (beta - 1)) for t in ts]
    return {"times": ts, "n": n, "beta": beta, "lam": lam,
            "cum_mtbf": cum_mtbf, "inst_mtbf": inst_mtbf, "growing": beta < 1}


# ── mohr-circle ──────────────────────────────────────────────────────────────
def mohr_circle(s1, s3, npts=73):
    """Mohr's circle for a 2D stress state (σ1 ≥ σ3). center=(σ1+σ3)/2, R=(σ1−σ3)/2."""
    c = (s1 + s3) / 2.0
    r = abs(s1 - s3) / 2.0
    pts = [(c + r * math.cos(2 * math.pi * i / (npts - 1)),
            r * math.sin(2 * math.pi * i / (npts - 1))) for i in range(npts)]
    return {"center": c, "radius": r, "points": pts}


# ── boiling-curve CHF detection ──────────────────────────────────────────────
def detect_chf(dt, q):
    """Critical Heat Flux = the peak q″ (Nukiyama). Returns (dT, q) at the max."""
    i = max(range(len(q)), key=lambda k: q[k])
    return {"index": i, "dt": dt[i], "q": q[i]}


# ── friction/wear steady-state window ────────────────────────────────────────
def steady_state(x, y, frac=0.5):
    """Steady-state = last `frac` of the run. Returns mean ± sd + the window x-range."""
    n = len(y)
    i0 = int(n * (1 - frac))
    win = [float(v) for v in y[i0:]]
    m = sum(win) / len(win)
    sd = (sum((v - m) ** 2 for v in win) / (len(win) - 1)) ** 0.5 if len(win) > 1 else 0.0
    return {"mean": m, "sd": sd, "x0": x[i0], "x1": x[-1], "i0": i0}


# ── gate-charge Miller plateau ───────────────────────────────────────────────
def miller_plateau(qg, vgs):
    """Detect the Miller plateau (flattest Vgs segment) → split Qgs / Qgd / Qg."""
    n = len(qg)
    if n < 4:
        return None
    slopes = [(vgs[i + 1] - vgs[i]) / (qg[i + 1] - qg[i] + 1e-12) for i in range(n - 1)]
    smin = min(abs(s) for s in slopes)
    flat = [i for i, s in enumerate(slopes) if abs(s) <= smin * 1.5]
    i0, i1 = flat[0], flat[-1] + 1
    return {"q_start": qg[i0], "q_end": qg[i1], "v_plateau": vgs[i0],
            "qgs": qg[i0], "qgd": qg[i1] - qg[i0], "qg_total": qg[-1]}
