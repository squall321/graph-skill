"""Shock Response Spectrum — Smallwood ramp-invariant digital filter (absolute-acceleration
model). Standard drop/shock reporting: SDOF maximax response vs natural frequency, log-log.
Deterministic pure-python (no scipy)."""

from __future__ import annotations

import math


def srs_maximax(accel, fs, fn_lo=10.0, fn_hi=10000.0, per_octave=6, q=10.0):
    """accel: acceleration samples [g], fs [Hz]. Returns (fn[], srs[]) maximax |response| [g].
    fn grid is 1/per_octave-octave spaced over [fn_lo, fn_hi] (capped at fs/2)."""
    fs = float(fs)
    if fn_lo <= 0 or fs <= 0:
        raise ValueError(f"srs: fn_lo({fn_lo})와 fs({fs})는 양수여야 합니다.")
    zeta = 1.0 / (2.0 * q)
    dt = 1.0 / fs
    fn_hi = min(float(fn_hi), fs / 2.0)
    if fn_hi <= fn_lo:  # Nyquist 캡 후 상한<=하한이면 비단조/초과-Nyquist 그리드 — 조용히 반환 금지
        raise ValueError(f"srs: 분석 상한 {fn_hi:.1f}Hz <= 하한 {fn_lo:.1f}Hz "
                         f"(Nyquist={fs / 2:.1f}Hz). fs를 높이거나 fn_lo를 낮추세요.")
    n_oct = math.log(fn_hi / fn_lo, 2)
    npts = max(2, int(round(n_oct * per_octave)) + 1)
    fns = [fn_lo * (2 ** (i * n_oct / (npts - 1))) for i in range(npts)]

    out = []
    x = [float(v) for v in accel]
    for fn in fns:
        wn = 2.0 * math.pi * fn
        wd = wn * math.sqrt(1.0 - zeta * zeta)
        e = math.exp(-zeta * wn * dt)
        k = wd * dt
        c = e * math.cos(k)
        s = e * math.sin(k)
        sp = s / k
        b0 = 1.0 - sp
        b1 = 2.0 * (sp - c)
        b2 = e * e - sp
        a1 = -2.0 * c
        a2 = e * e
        y1 = y0 = 0.0
        x1 = x2 = 0.0
        peak = 0.0
        for xi in x:
            y = b0 * xi + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y0
            x2, x1 = x1, xi
            y0, y1 = y1, y
            a = abs(y)
            if a > peak:
                peak = a
        out.append(peak)
    return fns, out


def half_sine(peak_g, duration_ms, fs, pre_ms=2.0, post_ms=15.0):
    """Reference half-sine shock pulse (e.g. 1500 g / 0.5 ms) with zero padding."""
    dt = 1.0 / float(fs)
    n_pulse = int(round(duration_ms * 1e-3 * fs))
    if n_pulse < 4:  # 언더샘플 시 sin 그리드가 0으로 붕괴(1500g→~0) — 조용히 0 반환 금지
        raise ValueError(f"half_sine: 펄스가 {n_pulse} 샘플로 언더샘플 "
                         f"({duration_ms}ms @ {fs}Hz). fs를 높이세요 (펄스당 ≥4 샘플 필요).")
    n_pre = int(round(pre_ms * 1e-3 * fs))
    n_post = int(round(post_ms * 1e-3 * fs))
    sig = [0.0] * n_pre
    for i in range(n_pulse):
        sig.append(peak_g * math.sin(math.pi * i / (n_pulse - 1)))
    sig += [0.0] * n_post
    t = [i * dt for i in range(len(sig))]
    return t, sig
