"""Statistical post-processing (pure Python): histogram, quartiles, ECDF, normal quantiles
(inverse-normal via Acklam), Pareto cumulative, SPC control limits."""

from __future__ import annotations

import math


def inv_norm(p: float) -> float:
    """Inverse standard-normal CDF (Acklam's rational approximation)."""
    if p <= 0:
        return -1e9
    if p >= 1:
        return 1e9
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def normal_quantiles(n: int) -> list:
    return [inv_norm((i + 0.5) / n) for i in range(n)]


def ecdf(values: list):
    xs = sorted(float(v) for v in values if v is not None)
    n = len(xs) or 1
    return xs, [(i + 1) / n for i in range(len(xs))]


def pareto(categories: list, values: list):
    pairs = sorted(zip(categories, [float(v) for v in values]), key=lambda kv: -kv[1])
    cats = [k for k, _ in pairs]
    vals = [v for _, v in pairs]
    tot = sum(vals) or 1.0
    run, cum = 0.0, []
    for v in vals:
        run += v
        cum.append(run / tot * 100)
    return cats, vals, cum


def capability(values: list, usl=None, lsl=None) -> dict:
    """Process capability: mean, sample sd, Cp, Cpk (None when a spec side is absent)."""
    ys = [float(v) for v in values if v is not None]
    n = len(ys) or 1
    mean = sum(ys) / n
    sd = (sum((v - mean) ** 2 for v in ys) / (n - 1)) ** 0.5 if n > 1 else 0.0
    cp = cpk = None
    if sd > 0:
        if usl is not None and lsl is not None:
            cp = (usl - lsl) / (6 * sd)
            cpk = min((usl - mean) / (3 * sd), (mean - lsl) / (3 * sd))
        elif usl is not None:
            cpk = (usl - mean) / (3 * sd)
        elif lsl is not None:
            cpk = (mean - lsl) / (3 * sd)
    return {"mean": mean, "sd": sd, "cp": cp, "cpk": cpk}


def control_limits(y: list) -> dict:
    ys = [float(v) for v in y if v is not None]
    n = len(ys) or 1
    mean = sum(ys) / n
    var = sum((v - mean) ** 2 for v in ys) / (n - 1) if n > 1 else 0.0
    sd = var ** 0.5
    ucl, lcl = mean + 3 * sd, mean - 3 * sd
    viol = [i for i, v in enumerate(y) if v is not None and (v > ucl or v < lcl)]
    return {"mean": mean, "sd": sd, "ucl": ucl, "lcl": lcl, "violations": viol}


def pearson(a: list, b: list) -> float:
    n = min(len(a), len(b))
    if n < 2:
        return 0.0
    a = [float(x) for x in a[:n]]
    b = [float(x) for x in b[:n]]
    ma, mb = sum(a) / n, sum(b) / n
    num = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    da = sum((x - ma) ** 2 for x in a) ** 0.5
    db = sum((x - mb) ** 2 for x in b) ** 0.5
    return num / (da * db) if da > 0 and db > 0 else 0.0


def pearson_matrix(variables: dict):
    names = list(variables)
    cols = [[float(v) for v in variables[k]] for k in names]
    r = [[pearson(cols[i], cols[j]) for j in range(len(names))] for i in range(len(names))]
    return names, r


def kde(values: list, n: int = 128, bw=None):
    """Gaussian KDE on a regular grid (Silverman bandwidth if bw None). Returns (xs, density)."""
    xs = sorted(float(v) for v in values if v is not None)
    m = len(xs)
    if m == 0:
        return [], []
    lo, hi = xs[0], xs[-1]
    if hi <= lo:
        hi = lo + 1.0
    mean = sum(xs) / m
    sd = (sum((v - mean) ** 2 for v in xs) / m) ** 0.5 or 1.0
    if bw is None:
        q1, q3 = xs[int(0.25 * (m - 1))], xs[int(0.75 * (m - 1))]
        iqr = q3 - q1
        a = min(sd, iqr / 1.349) if iqr > 0 else sd
        bw = 0.9 * a * m ** (-0.2) or sd * 0.1
    bw = bw or 1.0
    pad = 3 * bw
    grid = [lo - pad + (hi - lo + 2 * pad) * i / (n - 1) for i in range(n)]
    inv = 1.0 / (2 * bw * bw)
    norm = 1.0 / (m * bw * math.sqrt(2 * math.pi))
    dens = []
    for x in grid:
        s = 0.0
        for v in xs:
            d = x - v
            s += math.exp(-d * d * inv)
        dens.append(s * norm)
    return grid, dens


def histogram(values: list, bins=None):
    """Return (centers, counts, width). Default bin count = sqrt(n) (clamped 5..50)."""
    vals = sorted(float(v) for v in values if v is not None)
    n = len(vals)
    if n == 0:
        return [], [], 1.0
    lo, hi = vals[0], vals[-1]
    if hi <= lo:
        hi = lo + 1.0
    if not bins or bins < 1:
        bins = max(5, min(50, int(round(n ** 0.5))))
    bins = int(bins)
    w = (hi - lo) / bins
    counts = [0] * bins
    for v in vals:
        b = int((v - lo) / w)
        if b >= bins:
            b = bins - 1
        if b < 0:
            b = 0
        counts[b] += 1
    centers = [lo + w * (i + 0.5) for i in range(bins)]
    return centers, counts, w


def quartiles(values: list):
    """Tukey box-plot stats: q1/med/q3, 1.5·IQR whiskers, outliers."""
    vals = sorted(float(v) for v in values if v is not None)
    n = len(vals)
    if n == 0:
        return None

    def q(p):
        if n == 1:
            return vals[0]
        idx = p * (n - 1)
        lo = int(idx)
        frac = idx - lo
        return vals[lo] + (vals[min(lo + 1, n - 1)] - vals[lo]) * frac

    q1, med, q3 = q(0.25), q(0.5), q(0.75)
    iqr = q3 - q1
    lof, hif = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    inl = [v for v in vals if lof <= v <= hif]
    return {
        "q1": q1, "med": med, "q3": q3,
        "lo": min(inl) if inl else q1,
        "hi": max(inl) if inl else q3,
        "outliers": [v for v in vals if v < lof or v > hif],
        "n": n,
    }
