"""Pure-python domain math for the T1 standardized report figures (deterministic, no deps).
Each function is self-verified in tests/test_t1.py against a known closed-form anchor."""

from __future__ import annotations

import math


def interp_crossing(xs, ys, target):
    """First x where ys crosses `target` (linear interp in y), incl. exact endpoint hits.
    None if it never reaches `target`."""
    for i in range(1, len(xs)):
        y0, y1 = ys[i - 1], ys[i]
        if y0 == target:
            return xs[i - 1]
        if y1 == target:
            return xs[i]
        if (y0 - target) * (y1 - target) < 0 and y1 != y0:
            t = (target - y0) / (y1 - y0)
            return xs[i - 1] + t * (xs[i] - xs[i - 1])
    return None


def val_at(xs, ys, x):
    """Linear-interpolated y at x (None if out of range or x is None)."""
    if x is None:
        return None
    for i in range(1, len(xs)):
        if (xs[i - 1] - x) * (xs[i] - x) <= 0 and xs[i] != xs[i - 1]:
            t = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
            return ys[i - 1] + t * (ys[i] - ys[i - 1])
    return None


def _log_crossing(xs, ys, target):
    lt = math.log10(target)
    for i in range(1, len(xs)):
        a, b = ys[i - 1], ys[i]
        if a <= 0 or b <= 0:
            continue
        la, lb = math.log10(a), math.log10(b)
        if (la - lt) * (lb - lt) <= 0 and la != lb:
            t = (lt - la) / (lb - la)
            return xs[i - 1] + t * (xs[i] - xs[i - 1])
    return None


# ── loop-gain-margin ─────────────────────────────────────────────────────────
def stability_margins(freq, gain_db, phase_deg):
    """Open-loop Bode -> gain margin / phase margin. Gain crossover (0 dB) gives PM=180+φ;
    phase crossover (-180°) gives GM=-gain. stable iff both > 0."""
    f_gc = interp_crossing(freq, gain_db, 0.0)
    ph = val_at(freq, phase_deg, f_gc)
    pm = (180.0 + ph) if ph is not None else None
    f_pc = interp_crossing(freq, phase_deg, -180.0)
    g = val_at(freq, gain_db, f_pc)
    gm = (-g) if g is not None else None
    stable = bool(pm is not None and pm > 0 and gm is not None and gm > 0)
    return {"f_gc": f_gc, "pm_deg": pm, "f_pc": f_pc, "gm_db": gm, "stable": stable}


# ── jitter-bathtub (dual-Dirac) ──────────────────────────────────────────────
def dual_dirac_bathtub(rj, dj, target_ber=1e-12, npts=101):
    """Left/right BER bathtub curves over UI offset 0..1 from RJ(σ, UI) + DJ(pk-pk, UI),
    dual-Dirac (erfc closed form). Returns curves + eye opening @ target_ber (log-interp)."""
    sx = rj * math.sqrt(2.0)
    ui = [i / (npts - 1) for i in range(npts)]
    bl, br = [], []
    for x in ui:
        bl.append(0.5 * math.erfc((x - dj / 2.0) / sx) if x > dj / 2.0 else 0.5)
        br.append(0.5 * math.erfc(((1.0 - dj / 2.0) - x) / sx) if x < 1.0 - dj / 2.0 else 0.5)
    xl = _log_crossing(ui, bl, target_ber)
    xr = _log_crossing(ui, br, target_ber)
    opening = (xr - xl) if (xl is not None and xr is not None) else None
    return {"ui": ui, "ber_left": bl, "ber_right": br, "xl": xl, "xr": xr, "eye_opening": opening}


# ── thermal-resistance-stack ─────────────────────────────────────────────────
def thermal_stack(power, nodes, ambient=25.0):
    """θ-stack ladder: ΔT_i = P·R_i; node temps accumulate from ambient up to junction.
    nodes: [{name, r}] ordered ambient->junction direction is reversed internally so the
    last node temp is the junction temp. Returns deltas, node temps, t_junction."""
    deltas = [power * float(n["r"]) for n in nodes]
    temps, t = [], float(ambient)
    for d in reversed(deltas):  # build up from ambient
        t += d
        temps.append(t)
    temps.reverse()  # align with node order (junction first)
    return {"deltas": deltas, "node_temps": temps, "t_junction": (temps[0] if temps else ambient),
            "total_dt": sum(deltas)}


# ── xbar-R control chart constants (ASTM/AIAG, n=2..10) ───────────────────────
_XBAR_R = {
    2: (1.880, 0.0, 3.267, 1.128), 3: (1.023, 0.0, 2.574, 1.693),
    4: (0.729, 0.0, 2.282, 2.059), 5: (0.577, 0.0, 2.114, 2.326),
    6: (0.483, 0.0, 2.004, 2.534), 7: (0.419, 0.076, 1.924, 2.704),
    8: (0.373, 0.136, 1.864, 2.847), 9: (0.337, 0.184, 1.816, 2.970),
    10: (0.308, 0.223, 1.777, 3.078),
}


def xbar_r(subgroups):
    """Variables control chart from equal-size subgroups. Xbar/R limits via A2,D3,D4."""
    n = len(subgroups[0])
    a2, d3, d4, _d2 = _XBAR_R.get(n) or _XBAR_R[5]
    means = [sum(g) / len(g) for g in subgroups]
    ranges = [max(g) - min(g) for g in subgroups]
    xbb = sum(means) / len(means)
    rb = sum(ranges) / len(ranges)
    return {"means": means, "ranges": ranges, "xbb": xbb, "rb": rb, "n": n,
            "x_ucl": xbb + a2 * rb, "x_lcl": xbb - a2 * rb, "r_ucl": d4 * rb, "r_lcl": d3 * rb}


# ── FMEA RPN + AIAG-VDA Action Priority ──────────────────────────────────────
def rpn(s, o, d):
    return int(s) * int(o) * int(d)


def action_priority(s, o, d):
    """AIAG-VDA Action Priority (H/M/L) from S,O,D (1-10). Faithful to the published
    decision logic banded by severity then occurrence then detection."""
    s, o, d = int(s), int(o), int(d)
    if s >= 9:                                   # safety / regulatory severity
        if o >= 4:
            return "H"
        if o >= 2:
            return "H" if d >= 5 else "M"
        return "H" if d >= 7 else ("M" if d >= 5 else "L")
    if s >= 7:                                   # major / significant
        if o >= 6:
            return "H"
        if o >= 4:
            return "H" if d >= 5 else "M"
        if o >= 2:
            return "M" if d >= 5 else "L"
        return "L"
    if s >= 4:                                   # moderate
        if o >= 8:
            return "H" if d >= 6 else "M"
        if o >= 6:
            return "M" if d >= 5 else "L"
        if o >= 4:
            return "M" if d >= 7 else "L"
        return "L"
    return "L"                                   # minor severity (1-3)
