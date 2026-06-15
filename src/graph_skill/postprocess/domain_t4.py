"""Pure-python domain math for T2 batch C report figures. Self-verified in tests/test_t4.py."""

from __future__ import annotations

import math


def _interp(pts, x):
    """Linear interp of a [(x,y)] polyline at x (None if out of range)."""
    for i in range(1, len(pts)):
        x0, x1 = pts[i - 1][0], pts[i][0]
        if (x0 - x) * (x1 - x) <= 0 and x1 != x0:
            t = (x - x0) / (x1 - x0)
            return pts[i - 1][1] + t * (pts[i][1] - pts[i - 1][1])
    return None


# ── curve–curve intersection (fan/pump operating point) ──────────────────────
def curve_intersection(c1, c2):
    """First intersection of two polylines [(x,y)] (interp c2 onto c1's x, sign change)."""
    prev = None
    for x, y in c1:
        y2 = _interp(c2, x)
        if y2 is None:
            prev = None
            continue
        d = y - y2
        if prev is not None and prev[1] * d < 0:
            x0, d0 = prev
            t = d0 / (d0 - d)
            xi = x0 + t * (x - x0)
            return (xi, _interp(c2, xi))
        prev = (x, d)
    return None


# ── J-R fracture resistance fit ──────────────────────────────────────────────
def jr_curve_fit(delta_a, j, sigma_y):
    """Power-law J = C·Δa^m (log-log linear fit) + blunting line J = 2·σY·Δa."""
    la, lj = [], []
    for i, da in enumerate(delta_a):
        if da > 0 and j[i] > 0:
            la.append(math.log(da))
            lj.append(math.log(j[i]))
    n = len(la)
    sx, sy = sum(la), sum(lj)
    sxx = sum(v * v for v in la)
    sxy = sum(la[i] * lj[i] for i in range(n))
    m = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    c = math.exp((sy - m * sx) / n)
    return {"C": c, "m": m, "blunting_slope": 2 * sigma_y}


# ── load transient metrics ───────────────────────────────────────────────────
def transient_metrics(t, v, v_nom, tol_pct):
    """Over/undershoot %, recovery time (last instant outside the ±tol band)."""
    band = v_nom * tol_pct / 100.0
    peak, trough = max(v), min(v)
    rec = None
    for i in range(len(t) - 1, -1, -1):
        if abs(v[i] - v_nom) > band:
            rec = t[i]
            break
    return {"overshoot_pct": (peak - v_nom) / v_nom * 100.0,
            "undershoot_pct": (v_nom - trough) / v_nom * 100.0,
            "recovery_t": rec, "band": band, "peak": peak, "trough": trough}


# ── Mott-Schottky (1/C² → N_D, V_fb) ─────────────────────────────────────────
def mott_schottky(v, c, area_cm2, eps_r):
    """1/C² vs V linear fit → flat-band V_fb (x-intercept) and doping N_D (from slope).
    ε0=8.854e-14 F/cm, q=1.602e-19 C → N_D in cm⁻³ (area in cm²)."""
    eps0 = 8.854e-14
    q = 1.602e-19
    inv = [1.0 / (cc * cc) for cc in c]
    n = len(v)
    sx, sy = sum(v), sum(inv)
    sxx = sum(x * x for x in v)
    sxy = sum(v[i] * inv[i] for i in range(n))
    slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    b = (sy - slope * sx) / n
    v_fb = -b / slope if slope else None
    n_d = 2.0 / (q * eps0 * eps_r * area_cm2 * area_cm2 * slope) if slope else None
    return {"inv_c2": inv, "slope": slope, "v_fb": v_fb, "n_d": n_d}


# ── harmonic / spur peak detection ───────────────────────────────────────────
def harmonic_peaks(freqs, amps, f0, n_max, tol=0.05):
    """Peaks near n·f0 (n=1..n_max). dbc = amp − fundamental amp."""
    def near(target):
        best = None
        for i, f in enumerate(freqs):
            if abs(f - target) <= tol * f0 and (best is None or amps[i] > amps[best]):
                best = i
        return best

    out, fund = [], None
    for nn in range(1, n_max + 1):
        idx = near(nn * f0)
        if idx is not None:
            if nn == 1:
                fund = amps[idx]
            out.append({"n": nn, "freq": freqs[idx], "amp": amps[idx],
                        "dbc": amps[idx] - (fund if fund is not None else amps[idx])})
    return out


# ── pinch composite curve ────────────────────────────────────────────────────
def composite_curve(streams, side):
    """Temperature-interval composite curve (cumulative enthalpy H vs T) for hot|cold
    streams [{side,T_in,T_out,mcp}]. Returns [(H, T)] polyline (ascending T)."""
    sel = [s for s in streams if s.get("side") == side]
    if not sel:
        return []
    temps = sorted({float(s["T_in"]) for s in sel} | {float(s["T_out"]) for s in sel})
    pts = [(0.0, temps[0])]
    h = 0.0
    for i in range(1, len(temps)):
        tlo, thi = temps[i - 1], temps[i]
        mcp = sum(float(s["mcp"]) for s in sel
                  if min(float(s["T_in"]), float(s["T_out"])) <= tlo
                  and max(float(s["T_in"]), float(s["T_out"])) >= thi)
        h += mcp * (thi - tlo)
        pts.append((h, thi))
    return pts
