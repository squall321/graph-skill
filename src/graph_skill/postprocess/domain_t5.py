"""Pure-python domain math for the engine-overlay report figures (eye-mask, psychrometric,
distribution-fit). Self-verified in tests/test_t5.py."""

from __future__ import annotations

import math


# ── point-in-polygon (eye-mask hit counting) ─────────────────────────────────
def point_in_polygon(x, y, poly):
    """Ray-casting even-odd test. poly = [[x,y],…]."""
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i][0], poly[i][1]
        xj, yj = poly[j][0], poly[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-30) + xi):
            inside = not inside
        j = i
    return inside


def eye_mask_hits(ph, amp, z, polygons):
    """Count eye-histogram hits (Σz over cells) that fall inside any mask polygon."""
    hits, total = 0.0, 0.0
    for jy, yv in enumerate(amp):
        row = z[jy] if jy < len(z) else []
        for ix, xv in enumerate(ph):
            v = row[ix] if ix < len(row) else 0
            if not v:
                continue
            total += v
            if any(point_in_polygon(xv, yv, p) for p in polygons):
                hits += v
    return {"hits": hits, "total": total, "ratio": (hits / total) if total else 0.0}


# ── psychrometrics (ASHRAE / Magnus) ─────────────────────────────────────────
def p_ws(t_c):
    """Saturation vapor pressure over water [Pa] (Magnus)."""
    return 610.94 * math.exp(17.625 * t_c / (t_c + 243.04))


def humidity_ratio(t_c, rh, p=101325.0):
    """Humidity ratio W [kg/kg dry air] at dry-bulb t_c and RH (0–1)."""
    pw = max(0.0, min(rh, 1.0)) * p_ws(t_c)
    return 0.62198 * pw / (p - pw)


def saturation_curve(t_lo, t_hi, p=101325.0, n=40):
    return [[t_lo + (t_hi - t_lo) * i / (n - 1), humidity_ratio(t_lo + (t_hi - t_lo) * i / (n - 1), 1.0, p) * 1000.0]
            for i in range(n)]


def rh_curve(rh, t_lo, t_hi, p=101325.0, n=40):
    return [[t_lo + (t_hi - t_lo) * i / (n - 1), humidity_ratio(t_lo + (t_hi - t_lo) * i / (n - 1), rh, p) * 1000.0]
            for i in range(n)]


# ── inverse normal CDF (Acklam) ──────────────────────────────────────────────
def norm_ppf(p):
    """Inverse standard-normal CDF (Acklam's rational approximation)."""
    if p <= 0:
        return -8.0
    if p >= 1:
        return 8.0
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


def _linfit(xs, ys):
    n = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(xs[i] * ys[i] for i in range(n))
    det = n * sxx - sx * sx
    m = (n * sxy - sx * sy) / det if det else 0.0
    b = (sy - m * sx) / n
    ym = sy / n
    ss_res = sum((ys[i] - (m * xs[i] + b)) ** 2 for i in range(n))
    ss_tot = sum((y - ym) ** 2 for y in ys) or 1e-30
    return {"slope": m, "intercept": b, "r2": 1 - ss_res / ss_tot}


# ── probability-plot linearization per distribution ──────────────────────────
def prob_plot(values, dist):
    """Median-rank probability plot for a distribution. Returns plotted (x,y) + fit r².
    dist ∈ weibull|lognormal|normal|exponential. x/y are the linearizing transforms."""
    vs = sorted(float(v) for v in values)
    n = len(vs)
    fi = [(i + 1 - 0.3) / (n + 0.4) for i in range(n)]   # median rank
    pts = []
    for i, v in enumerate(vs):
        f = fi[i]
        if dist == "weibull":
            if v <= 0:
                continue
            pts.append((math.log(v), math.log(-math.log(1 - f))))
        elif dist == "lognormal":
            if v <= 0:
                continue
            pts.append((math.log(v), norm_ppf(f)))
        elif dist == "exponential":
            pts.append((v, -math.log(1 - f)))
        else:  # normal
            pts.append((v, norm_ppf(f)))
    fit = _linfit([p[0] for p in pts], [p[1] for p in pts])
    return {"x": [p[0] for p in pts], "y": [p[1] for p in pts], "r2": fit["r2"], "fit": fit}
