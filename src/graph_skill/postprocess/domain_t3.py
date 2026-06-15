"""Pure-python domain math for T2 batch B report figures. Self-verified in tests/test_t3.py."""

from __future__ import annotations

import math


def _slope(xs, ys):
    n = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(xs[i] * ys[i] for i in range(n))
    det = n * sxx - sx * sx
    return (n * sxy - sx * sy) / det if abs(det) > 1e-15 else 0.0


# ── phase-noise → RMS jitter ─────────────────────────────────────────────────
def phase_jitter(offsets, lf_dbc, f1=None, f2=None, carrier=None):
    """Integrate L(f) [dBc/Hz] over [f1,f2] (trapezoid in linear f, power domain).
    RMS phase jitter = √(2·∫ 10^(L/10) df). time jitter = φ/(2π·carrier)."""
    f1 = float(f1) if f1 is not None else offsets[0]
    f2 = float(f2) if f2 is not None else offsets[-1]
    total = 0.0
    for i in range(1, len(offsets)):
        fa, fb = offsets[i - 1], offsets[i]
        if fb < f1 or fa > f2:
            continue
        pa = 10 ** (lf_dbc[i - 1] / 10.0)
        pb = 10 ** (lf_dbc[i] / 10.0)
        total += (pa + pb) / 2.0 * (fb - fa)
    rms_rad = math.sqrt(2.0 * total)
    out = {"rms_rad": rms_rad, "rms_deg": math.degrees(rms_rad)}
    if carrier:
        out["jitter_s"] = rms_rad / (2.0 * math.pi * float(carrier))
    return out


# ── soa boundary from device params ──────────────────────────────────────────
def soa_boundary(rds_on, id_max, pd_max, vds_max, v_min=0.1):
    """DC SOA upper boundary (log-log Vds–Id): Rds_on(slope1) → Id_max(flat) →
    Pd_max(slope −1) → Vds_max(vertical). Returns boundary polyline points (Vds, Id)."""
    v_rds = id_max * rds_on              # Rds line reaches Id_max here
    v_pd = pd_max / id_max               # Id_max meets Pd line here
    v_pdmax = vds_max                    # Pd line reaches Vds_max
    i_at_vmax = pd_max / vds_max
    return [(v_min, v_min / rds_on), (v_rds, id_max), (v_pd, id_max),
            (v_pdmax, i_at_vmax), (vds_max, min(i_at_vmax, v_min / rds_on))]


def point_in_soa(v, i, rds_on, id_max, pd_max, vds_max):
    return (i <= v / rds_on) and (i <= id_max) and (v * i <= pd_max) and (v <= vds_max)


# ── GUM uncertainty budget ───────────────────────────────────────────────────
def uncertainty_budget(components, k=2):
    """components:[{name,u,c?}]. variance_i=(c·u)², %contribution, combined uc=√Σ, U=k·uc."""
    var = [(float(c.get("c", 1)) * float(c["u"])) ** 2 for c in components]
    total = sum(var)
    uc = math.sqrt(total)
    return {"variances": var, "percent": [v / total * 100 if total else 0 for v in var],
            "uc": uc, "U": k * uc, "k": k}


# ── tolerance stackup ────────────────────────────────────────────────────────
def tolerance_stackup(links):
    """links:[{nominal,tol_plus,tol_minus,sense?}]. Worst-case (Σ|tol|) and RSS (√Σtol²)."""
    nom = sum(float(l["nominal"]) * float(l.get("sense", 1)) for l in links)
    tols = [max(abs(float(l.get("tol_plus", 0))), abs(float(l.get("tol_minus", 0)))) for l in links]
    wc = sum(tols)
    rss = math.sqrt(sum(t * t for t in tols))
    return {"nominal": nom, "wc": wc, "rss": rss, "tols": tols}


# ── earned value (EVM) ───────────────────────────────────────────────────────
def evm_metrics(pv, ev, ac, bac):
    """Schedule/cost variance & indices + EAC. SV=EV−PV, CV=EV−AC, SPI=EV/PV, CPI=EV/AC."""
    spi = ev / pv if pv else 0.0
    cpi = ev / ac if ac else 0.0
    return {"sv": ev - pv, "cv": ev - ac, "spi": spi, "cpi": cpi,
            "eac": bac / cpi if cpi else float(bac)}


# ── risk matrix zone ─────────────────────────────────────────────────────────
def risk_zone(p, i):
    """5×5 risk score = P·I → zone (low/medium/high/extreme)."""
    s = int(p) * int(i)
    if s >= 15:
        return "extreme"
    if s >= 10:
        return "high"
    if s >= 5:
        return "medium"
    return "low"


# ── dQ/dV (battery incremental capacity) ─────────────────────────────────────
def dqdv(v, q, window=5):
    """dQ/dV vs V (incremental capacity). Sorts by V, finite-difference, optional smoothing."""
    pairs = sorted(zip([float(x) for x in v], [float(x) for x in q]))
    vs = [p[0] for p in pairs]
    qs = [p[1] for p in pairs]
    vm, d = [], []
    for i in range(len(vs) - 1):
        dv = vs[i + 1] - vs[i]
        if dv == 0:
            continue
        vm.append((vs[i + 1] + vs[i]) / 2.0)
        d.append((qs[i + 1] - qs[i]) / dv)
    if window and len(d) >= window:
        try:
            from .smoothing import savgol
            d = savgol(d, window if window % 2 else window + 1, 2)
        except Exception:
            pass
    return {"v": vm, "dqdv": d}


# ── torque-angle yield ───────────────────────────────────────────────────────
def torque_yield(angle, torque, elastic_frac=0.3, drop=0.5):
    """Elastic slope from the first `elastic_frac`; yield = first point whose local slope
    falls below `drop`×elastic slope (gradient method)."""
    n = len(angle)
    ne = max(2, int(n * elastic_frac))
    k = _slope(angle[:ne], torque[:ne])
    for i in range(ne, n - 1):
        s = (torque[i + 1] - torque[i]) / (angle[i + 1] - angle[i] + 1e-12)
        if s < drop * k:
            return {"k_elastic": k, "yield_angle": angle[i], "yield_torque": torque[i]}
    return {"k_elastic": k, "yield_angle": None, "yield_torque": None}


# ── creep min rate ───────────────────────────────────────────────────────────
def min_creep_rate(t, strain):
    """Minimum (secondary-stage) creep rate = min local slope of strain–time."""
    slopes = [(strain[i + 1] - strain[i]) / (t[i + 1] - t[i] + 1e-12) for i in range(len(t) - 1)]
    mi = min(range(len(slopes)), key=lambda k: slopes[k])
    return {"min_rate": slopes[mi], "t_at_min": t[mi], "strain_at_min": strain[mi]}
