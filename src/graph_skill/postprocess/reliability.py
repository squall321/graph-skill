"""Reliability post-processing (pure Python): Kaplan-Meier survival + median ranks
(plotting positions for probability paper). No external dependencies."""

from __future__ import annotations

import math


def weibull_fit(values: list):
    """Median-rank-regression Weibull fit on failure data (>0). Returns the linearized
    plotting coords + shape β / scale η / R², or None if <2 points.

    Linearizes via Y=ln(-ln(1-F)) vs X=ln(t); slope=β, η=exp(-intercept/β)."""
    xs = sorted(float(v) for v in values if v is not None and float(v) > 0)
    n = len(xs)
    if n < 2:
        return None
    f = median_ranks(n)
    X = [math.log(x) for x in xs]
    Y = [math.log(-math.log(1 - fi)) for fi in f]
    sx, sy = sum(X), sum(Y)
    sxx = sum(x * x for x in X)
    sxy = sum(X[i] * Y[i] for i in range(n))
    d = n * sxx - sx * sx
    beta = (n * sxy - sx * sy) / d if d else 1.0
    a = (sy - beta * sx) / n
    eta = math.exp(-a / beta) if beta else float("nan")
    ybar = sy / n
    sstot = sum((y - ybar) ** 2 for y in Y)
    ssres = sum((Y[i] - (beta * X[i] + a)) ** 2 for i in range(n))
    r2 = 1 - ssres / sstot if sstot > 0 else 1.0
    return {"x": xs, "Y": Y, "beta": beta, "eta": eta, "intercept": a, "r2": r2}


def kaplan_meier(durations: list, events: list):
    """Kaplan-Meier estimator. events: 1=failure, 0=right-censored.

    Returns (t[], S(t)[], censored[]) where the step starts at (0, 1.0) and S drops only at
    failure times; ``censored`` is a list of (time, S_at_time) to mark censoring ticks.
    """
    data = sorted(zip([float(d) for d in durations], [int(e) for e in events]))
    ts, surv, cens = [0.0], [1.0], []
    s = 1.0
    for t in sorted({d for d, _ in data}):
        at_risk = sum(1 for d, _ in data if d >= t)
        deaths = sum(1 for d, e in data if d == t and e == 1)
        ncens = sum(1 for d, e in data if d == t and e == 0)
        if deaths > 0 and at_risk > 0:
            s *= 1 - deaths / at_risk
            ts.append(t)
            surv.append(s)
        if ncens > 0:
            cens.append((t, s))
    return ts, surv, cens


def median_ranks(n: int) -> list:
    """Bernard's approximation (i-0.3)/(n+0.4) — plotting positions for prob/Weibull paper."""
    return [(i - 0.3) / (n + 0.4) for i in range(1, n + 1)]
