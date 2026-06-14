"""구조해석·열전달·측정 보고용 수치 계산 — Richardson 외삽/GCI(격자수렴), ASME식 응력
선형화(membrane/bending), 이력곡선 소산에너지, 1차 열응답(τ,T∞) 적합, 멱법칙 적합(Nu-Re),
Allan deviation, 선형 교정 적합(R²·잔차). 전부 결정적 pure python."""

from __future__ import annotations

import math


# ── 격자 수렴 (Roache GCI / Richardson) ──────────────────────────────────────
def richardson(h, phi, fs=1.25):
    """h: 격자 대표 크기(내림차순 아님 무방, 정렬함), phi: 대응 결과값.
    최세밀 3개 격자로 관측 수렴차수 p, 외삽값 phi_ext, GCI_fine[%] 반환."""
    pairs = sorted(zip(h, phi), key=lambda t: t[0])      # fine -> coarse
    if len(pairs) < 3:
        return None
    (h1, f1), (h2, f2), (h3, f3) = pairs[0], pairs[1], pairs[2]
    r21, r32 = h2 / h1, h3 / h2
    e21, e32 = f2 - f1, f3 - f2
    if e21 == 0 or e32 == 0 or (e32 / e21) <= 0:
        return {"p": None, "phi_ext": f1, "gci_fine_pct": None, "monotonic": False}
    # fixed-point iteration for observed order p (Celik et al. ASME procedure):
    # p = |ln|e32/e21| + q(p)| / ln r21,  q = ln((r21^p - s)/(r32^p - s))
    s = 1.0 if (e32 / e21) > 0 else -1.0
    p = abs(math.log(abs(e32 / e21)) / math.log(r21))
    for _ in range(50):
        q = math.log((r21 ** p - s) / (r32 ** p - s)) if (r32 ** p - s) != 0 else 0.0
        p_new = abs(math.log(abs(e32 / e21)) + q) / math.log(r21)
        if abs(p_new - p) < 1e-10:
            p = p_new
            break
        p = p_new
    phi_ext = f1 + (f1 - f2) / (r21 ** p - 1)
    ea = abs((f1 - f2) / f1) if f1 != 0 else abs(f1 - f2)
    gci = 100.0 * fs * ea / (r21 ** p - 1)
    return {"p": p, "phi_ext": phi_ext, "gci_fine_pct": gci, "monotonic": True}


# ── 응력 선형화 (ASME Sec VIII Div 2 Part 5 관행) ────────────────────────────
def stress_linearize(x, sigma):
    """x: 두께 방향 경로 좌표(0..t), sigma: 경로 응력. membrane(σm), bending(±σb),
    그리고 경로 양 끝에서의 m+b 선형분포 좌표를 반환. 사다리꼴 적분."""
    t = x[-1] - x[0]
    if t <= 0:
        return None

    def trapz(f):
        s = 0.0
        for i in range(1, len(x)):
            s += 0.5 * (f[i] + f[i - 1]) * (x[i] - x[i - 1])
        return s

    xm = x[0] + t / 2.0
    sm = trapz(sigma) / t
    mom = trapz([sig * (xm - xi) for xi, sig in zip(x, sigma)])
    sb = 6.0 * mom / (t * t)
    line = [[x[0], sm + sb], [x[-1], sm - sb]]          # m+b linear distribution
    return {"membrane": sm, "bending": sb, "mb_line": line, "t": t}


# ── 이력곡선 소산 에너지 (shoelace) ─────────────────────────────────────────
def loop_energy(points):
    """닫힌(또는 거의 닫힌) 하중-변위 루프의 면적 = 사이클 소산 에너지."""
    a = 0.0
    n = len(points)
    for i in range(n):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % n]
        a += x0 * y1 - x1 * y0
    return abs(a) / 2.0


# ── 1차 열응답 적합: T(t) = Tinf - (Tinf - T0)·exp(-t/τ) ────────────────────
def thermal_rc_fit(t, temp):
    """τ를 로그 그리드로 탐색, 각 τ에서 (T0, Tinf)는 선형 최소제곱 → 최소 SSE 선택."""
    span = max(t) - min(t)
    best = None
    for k in range(120):
        tau = span * (10 ** (-2 + 2.6 * k / 119))        # span/100 .. ~4*span
        # model: T = Tinf + (T0 - Tinf) e^{-t/τ} = a + b·e^{-t/τ}
        e = [math.exp(-(ti - t[0]) / tau) for ti in t]
        n = len(t)
        se, see = sum(e), sum(v * v for v in e)
        sy, sye = sum(temp), sum(y * v for y, v in zip(temp, e))
        det = n * see - se * se
        if abs(det) < 1e-12:
            continue
        b = (n * sye - se * sy) / det
        a = (sy - b * se) / n
        sse = sum((a + b * ei - yi) ** 2 for ei, yi in zip(e, temp))
        if best is None or sse < best[0]:
            best = (sse, tau, a, a + b)
    if best is None:
        return None
    _, tau, t_inf, t0 = best
    return {"tau": tau, "t_inf": t_inf, "t0": t0}


# ── 멱법칙 적합 y = C·x^m (Nu-Re 등) ────────────────────────────────────────
def power_fit(x, y):
    lx = [math.log(v) for v in x]
    ly = [math.log(v) for v in y]
    n = len(lx)
    sx, sy = sum(lx), sum(ly)
    sxx = sum(v * v for v in lx)
    sxy = sum(a * b for a, b in zip(lx, ly))
    det = n * sxx - sx * sx
    if abs(det) < 1e-12:
        return None
    m = (n * sxy - sx * sy) / det
    c = math.exp((sy - m * sx) / n)
    ym = sy / n
    ss_res = sum((lyi - (math.log(c) + m * lxi)) ** 2 for lxi, lyi in zip(lx, ly))
    ss_tot = sum((lyi - ym) ** 2 for lyi in ly) or 1e-12
    return {"C": c, "m": m, "r2": 1 - ss_res / ss_tot}


# ── Allan deviation ─────────────────────────────────────────────────────────
def allan_deviation(samples, fs, points_per_decade=6):
    """비중첩 Allan: σ(τ) = sqrt(0.5·mean((ȳ_{i+1}-ȳ_i)²)). τ는 로그 그리드."""
    n = len(samples)
    t0 = 1.0 / fs
    max_m = n // 3
    taus, sigmas = [], []
    k = 0
    while True:
        m = int(round(10 ** (k / points_per_decade)))
        k += 1
        if m < 1:
            continue
        if m > max_m:
            break
        nclus = n // m
        means = [sum(samples[i * m:(i + 1) * m]) / m for i in range(nclus)]
        if len(means) < 2:
            break
        diffs = [(means[i + 1] - means[i]) ** 2 for i in range(len(means) - 1)]
        av = 0.5 * sum(diffs) / len(diffs)
        if taus and abs(m * t0 - taus[-1]) < 1e-12:
            continue
        taus.append(m * t0)
        sigmas.append(math.sqrt(av))
    return taus, sigmas


# ── 선형 교정 적합 (slope/intercept/R² + 잔차) ──────────────────────────────
def linear_fit(x, y):
    n = len(x)
    sx, sy = sum(x), sum(y)
    sxx = sum(v * v for v in x)
    sxy = sum(a * b for a, b in zip(x, y))
    det = n * sxx - sx * sx
    if abs(det) < 1e-12:
        return None
    slope = (n * sxy - sx * sy) / det
    intercept = (sy - slope * sx) / n
    ym = sy / n
    resid = [yi - (slope * xi + intercept) for xi, yi in zip(x, y)]
    ss_res = sum(r * r for r in resid)
    ss_tot = sum((yi - ym) ** 2 for yi in y) or 1e-12
    return {"slope": slope, "intercept": intercept, "r2": 1 - ss_res / ss_tot, "residuals": resid}


def bland_altman(a, b):
    """Paired method comparison (Bland & Altman 1986). Per pair: mean=(a+b)/2, diff=a-b.
    Returns means/diffs + bias(평균 차이) + sd + ±1.96·SD limits of agreement."""
    n = min(len(a), len(b))
    if n < 2:
        return None
    a = [float(x) for x in a[:n]]
    b = [float(x) for x in b[:n]]
    means = [(a[i] + b[i]) / 2.0 for i in range(n)]
    diffs = [a[i] - b[i] for i in range(n)]
    bias = sum(diffs) / n
    sd = (sum((d - bias) ** 2 for d in diffs) / (n - 1)) ** 0.5
    return {"means": means, "diffs": diffs, "bias": bias, "sd": sd,
            "loa_hi": bias + 1.96 * sd, "loa_lo": bias - 1.96 * sd, "n": n}
