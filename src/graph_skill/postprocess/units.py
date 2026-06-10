"""Unit conversions for mechanical curves. Pure Python (no numpy needed)."""

from __future__ import annotations

import math


def eng_stress_strain(force_n: list, disp_mm: list, A0_mm2: float, L0_mm: float):
    """Engineering stress/strain from raw force[N] / displacement[mm].

    σ = F / A0  (N/mm² = MPa),  ε = ΔL / L0  (dimensionless).
    None values pass through as gaps. Raises if A0/L0 non-positive (N6 guard).
    """
    if not (A0_mm2 > 0):
        raise ValueError("A0 must be positive [mm^2]")
    if not (L0_mm > 0):
        raise ValueError("L0 must be positive [mm]")
    strain = [(d / L0_mm) if d is not None else None for d in disp_mm]
    stress = [(f / A0_mm2) if f is not None else None for f in force_n]
    return strain, stress


def eng_to_true(eps: list, sig: list):
    """Engineering -> true: ε_t = ln(1+ε), σ_t = σ(1+ε). Valid up to necking (uniform strain)."""
    te: list = []
    ts: list = []
    for e, s in zip(eps, sig):
        if e is None or s is None or (1.0 + e) <= 0:
            te.append(None)
            ts.append(None)
        else:
            te.append(math.log(1.0 + e))
            ts.append(s * (1.0 + e))
    return te, ts
