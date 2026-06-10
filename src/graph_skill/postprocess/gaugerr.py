"""Gauge R&R (AIAG range method) — variance components from parts × operators × trials.
Pure Python. Returns EV/AV/GRR/PV as % of total study variation + ndc."""

from __future__ import annotations

_K1 = {2: 0.8862, 3: 0.5908, 4: 0.4857, 5: 0.4299}                  # trials (repeatability)
_K2 = {2: 0.7071, 3: 0.5231, 4: 0.4467}                             # operators (reproducibility)
_K3 = {2: 0.7071, 3: 0.5231, 4: 0.4467, 5: 0.4030, 6: 0.3742,
       7: 0.3534, 8: 0.3375, 9: 0.3249, 10: 0.3146}                 # parts


def gauge_rr(measurements):
    """measurements[part][operator] = [trial values]. Returns dict of components (% study var)."""
    nparts = len(measurements)
    nops = len(measurements[0]) if nparts else 0
    ntrials = len(measurements[0][0]) if (nparts and nops) else 0
    if nparts < 2 or nops < 1 or ntrials < 2:
        raise ValueError("need >= 2 parts, >= 1 operator, >= 2 trials")
    ranges = []
    for p in range(nparts):
        for o in range(nops):
            t = [float(v) for v in measurements[p][o]]
            ranges.append(max(t) - min(t))
    rbar = sum(ranges) / len(ranges)
    ev = rbar * _K1.get(ntrials, _K1[3])

    op_means = []
    for o in range(nops):
        flat = [float(v) for p in range(nparts) for v in measurements[p][o]]
        op_means.append(sum(flat) / len(flat))
    xdiff = (max(op_means) - min(op_means)) if nops > 1 else 0.0
    av2 = (xdiff * _K2.get(nops, _K2[2])) ** 2 - ev * ev / (nparts * ntrials) if nops > 1 else 0.0
    av = av2 ** 0.5 if av2 > 0 else 0.0

    part_means = []
    for p in range(nparts):
        flat = [float(v) for o in range(nops) for v in measurements[p][o]]
        part_means.append(sum(flat) / len(flat))
    rp = max(part_means) - min(part_means)
    pv = rp * _K3.get(nparts, _K3[10])

    grr = (ev * ev + av * av) ** 0.5
    tv = (grr * grr + pv * pv) ** 0.5 or 1.0
    ndc = 1.41 * pv / grr if grr > 0 else float("inf")
    pct = lambda v: 100.0 * v / tv
    return {"EV": ev, "AV": av, "GRR": grr, "PV": pv, "TV": tv,
            "pct": {"EV": pct(ev), "AV": pct(av), "GRR": pct(grr), "PV": pct(pv)},
            "ndc": ndc, "n_parts": nparts, "n_ops": nops, "n_trials": ntrials}
