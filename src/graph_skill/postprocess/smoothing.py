"""Smoothing — centered moving average + Savitzky-Golay (pure Python, normal-equations)."""

from __future__ import annotations


def moving_average(y: list, window: int) -> list:
    w = max(1, int(window))
    if w <= 1:
        return list(y)
    half, n, out = w // 2, len(y), []
    for i in range(n):
        seg = [v for v in y[max(0, i - half):min(n, i + half + 1)] if v is not None]
        out.append(sum(seg) / len(seg) if seg else None)
    return out


def _inv(M: list) -> list:
    n = len(M)
    A = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(M)]
    for col in range(n):
        if abs(A[col][col]) < 1e-12:
            for r in range(col + 1, n):
                if abs(A[r][col]) > 1e-12:
                    A[col], A[r] = A[r], A[col]
                    break
        piv = A[col][col] or 1e-12
        for j in range(2 * n):
            A[col][j] /= piv
        for r in range(n):
            if r == col:
                continue
            f = A[r][col]
            for j in range(2 * n):
                A[r][j] -= f * A[col][j]
    return [row[n:] for row in A]


def savgol(y: list, window: int, polyorder: int = 2) -> list:
    """Savitzky-Golay smoothing. window is forced odd; polyorder < window. Edge points where
    the window doesn't fit (or hits a gap) fall back to the raw value."""
    w = int(window)
    if w % 2 == 0:
        w += 1
    p = int(polyorder)
    if w <= p + 1:
        return list(y)
    half = w // 2
    xs = list(range(-half, half + 1))
    M = [[sum(x ** (a + b) for x in xs) for b in range(p + 1)] for a in range(p + 1)]
    minv = _inv(M)
    h = [sum(minv[0][j] * (xs[k] ** j) for j in range(p + 1)) for k in range(w)]  # central-point weights
    n, out = len(y), []
    for i in range(n):
        acc, ok = 0.0, True
        for k in range(w):
            idx = i - half + k
            if idx < 0 or idx >= n or y[idx] is None:
                ok = False
                break
            acc += h[k] * y[idx]
        out.append(acc if ok else y[i])
    return out
