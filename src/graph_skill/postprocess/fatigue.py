"""Fatigue post-processing (pure Python): rainflow cycle counting (ASTM E1049-85) +
mean×range 2D histogram for the cycle-count heatmap."""

from __future__ import annotations


def reversals(series: list):
    """Yield turning points (peaks/valleys), including the first and last points."""
    s = [float(v) for v in series if v is not None]
    if len(s) < 2:
        yield from s
        return
    it = iter(s)
    x_last = next(it)
    x = next(it)
    d_last = x - x_last
    yield x_last
    for x_next in it:
        d_next = x_next - x
        if d_last * d_next < 0:
            yield x
        x_last, x = x, x_next
        if d_next != 0:
            d_last = d_next
    yield x


def extract_cycles(series: list):
    """Rainflow cycles as (range, mean, count) where count is 1.0 (full) or 0.5 (half)."""
    points = []
    out = []
    for x in reversals(series):
        points.append(x)
        while len(points) >= 3:
            x1, x2, x3 = points[-3], points[-2], points[-1]
            rng_x = abs(x3 - x2)
            rng_y = abs(x2 - x1)
            if rng_x < rng_y:
                break
            if len(points) == 3:
                out.append((rng_y, (x1 + x2) / 2.0, 0.5))   # contains start → half
                points.pop(0)
            else:
                out.append((rng_y, (x1 + x2) / 2.0, 1.0))
                last = points.pop()
                points.pop()
                points.pop()
                points.append(last)
    for i in range(len(points) - 1):
        out.append((abs(points[i + 1] - points[i]), (points[i] + points[i + 1]) / 2.0, 0.5))
    return out


def rainflow_matrix(series: list, mean_bins: int = 12, range_bins: int = 12):
    """Bin rainflow cycles into a mean×range count grid.
    Returns (mean_centers[nm], range_centers[nr], Z[nr][nm]) of summed counts."""
    cycles = extract_cycles(series)
    if not cycles:
        return [0.0], [0.0], [[0.0]]
    means = [c[1] for c in cycles]
    ranges = [c[0] for c in cycles]
    m0, m1 = min(means), max(means)
    r0, r1 = 0.0, max(ranges)
    if m1 <= m0:
        m1 = m0 + 1.0
    if r1 <= r0:
        r1 = r0 + 1.0
    mw = (m1 - m0) / mean_bins
    rw = (r1 - r0) / range_bins
    Z = [[0.0] * mean_bins for _ in range(range_bins)]
    for rng, mean, cnt in cycles:
        mi = min(mean_bins - 1, max(0, int((mean - m0) / mw))) if mw > 0 else 0
        ri = min(range_bins - 1, max(0, int((rng - r0) / rw))) if rw > 0 else 0
        Z[ri][mi] += cnt
    mean_centers = [m0 + mw * (i + 0.5) for i in range(mean_bins)]
    range_centers = [r0 + rw * (j + 0.5) for j in range(range_bins)]
    return mean_centers, range_centers, Z
