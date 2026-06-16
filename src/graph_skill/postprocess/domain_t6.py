"""Math for the final report figures (PRST sequential test). Self-verified in tests/test_t6.py."""

from __future__ import annotations

import math


def sprt_bounds(alpha, beta, theta0, theta1):
    """PRST (Wald SPRT, exponential MTBF) decision boundaries. theta0 = upper test MTBF
    (acceptable), theta1 = lower (unacceptable, theta1 < theta0). For cumulative failures n
    vs cumulative time T the continue region is between two parallel lines n = intercept + s·T:
    accept (lower) intercept = ln(B)/ln(θ0/θ1), reject (upper) = ln(A)/ln(θ0/θ1),
    slope s = (1/θ1 − 1/θ0)/ln(θ0/θ1). A=(1−β)/α, B=β/(1−α)."""
    a_ratio = (1 - beta) / alpha
    b_ratio = beta / (1 - alpha)
    denom = math.log(theta0 / theta1)
    s = (1.0 / theta1 - 1.0 / theta0) / denom
    return {"slope": s, "accept_intercept": math.log(b_ratio) / denom,
            "reject_intercept": math.log(a_ratio) / denom, "A": a_ratio, "B": b_ratio}


def sprt_decision(traj, bounds):
    """Verdict from the test path's last point vs the boundary lines."""
    if not traj:
        return "continue"
    t, n = traj[-1]
    if n >= bounds["reject_intercept"] + bounds["slope"] * t:
        return "reject"
    if n <= bounds["accept_intercept"] + bounds["slope"] * t:
        return "accept"
    return "continue"
