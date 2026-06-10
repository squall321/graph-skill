"""Resampling — detect non-uniform dt, interpolate to a uniform grid, decimate."""

from __future__ import annotations


def is_uniform(x: list, tol: float = 1e-6) -> bool:
    if len(x) < 3:
        return True
    d0 = x[1] - x[0]
    if d0 == 0:
        return False
    return all(abs((x[i + 1] - x[i]) - d0) <= tol * abs(d0) for i in range(len(x) - 1))


def resample_uniform(x: list, y: list, n: int | None = None, dt: float | None = None):
    """Linear interpolation onto a uniform grid over [x[0], x[-1]]. None y values propagate."""
    xs, ys = list(x), list(y)
    if len(xs) < 2:
        return xs, ys
    x0, x1 = xs[0], xs[-1]
    if dt:
        m = int(round((x1 - x0) / dt)) + 1
        grid = [x0 + dt * i for i in range(max(2, m))]
    else:
        n = n or len(xs)
        grid = [x0 + (x1 - x0) * i / (n - 1) for i in range(max(2, n))]
    out, j = [], 0
    for g in grid:
        while j < len(xs) - 2 and xs[j + 1] < g:
            j += 1
        xa, xb, ya, yb = xs[j], xs[j + 1], ys[j], ys[j + 1]
        if xb == xa or ya is None or yb is None:
            out.append(ya)
        else:
            out.append(ya + (yb - ya) * (g - xa) / (xb - xa))
    return grid, out


def decimate(x: list, y: list, factor: int):
    factor = max(1, int(factor))
    return list(x)[::factor], list(y)[::factor]
