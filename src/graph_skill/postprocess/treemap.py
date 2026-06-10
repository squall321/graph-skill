"""Squarified treemap layout (Bruls/Huizing/van Wijk) — pure Python, deterministic.
Returns rectangles in a unit square; the engine plugin just draws them."""

from __future__ import annotations


def _layout_row(sizes, x, y, dy):
    w = sum(sizes) / dy if dy else 0
    out, yy = [], y
    for s in sizes:
        h = s / w if w else 0
        out.append({"x": x, "y": yy, "w": w, "h": h})
        yy += h
    return out


def _layout_col(sizes, x, y, dx):
    h = sum(sizes) / dx if dx else 0
    out, xx = [], x
    for s in sizes:
        w = s / h if h else 0
        out.append({"x": xx, "y": y, "w": w, "h": h})
        xx += w
    return out


def _layout(sizes, x, y, dx, dy):
    return _layout_row(sizes, x, y, dy) if dx >= dy else _layout_col(sizes, x, y, dx)


def _worst(sizes, x, y, dx, dy):
    rects = _layout(sizes, x, y, dx, dy)
    w = 0.0
    for r in rects:
        if r["w"] <= 0 or r["h"] <= 0:
            return float("inf")
        w = max(w, r["w"] / r["h"], r["h"] / r["w"])
    return w


def _leftover(sizes, x, y, dx, dy):
    if dx >= dy:
        w = sum(sizes) / dy if dy else 0
        return (x + w, y, dx - w, dy)
    h = sum(sizes) / dx if dx else 0
    return (x, y + h, dx, dy - h)


def _squarify(sizes, x, y, dx, dy, out):
    if not sizes:
        return
    if len(sizes) == 1:
        out.append({"x": x, "y": y, "w": dx, "h": dy})
        return
    i = 1
    while i < len(sizes) and _worst(sizes[:i], x, y, dx, dy) >= _worst(sizes[:i + 1], x, y, dx, dy):
        i += 1
    out.extend(_layout(sizes[:i], x, y, dx, dy))
    _squarify(sizes[i:], *_leftover(sizes[:i], x, y, dx, dy), out)


def squarify(values, dx=1.0, dy=1.0):
    """Layout positive ``values`` into rectangles of a dx×dy area (origin 0,0), largest first."""
    vals = [float(v) for v in values if v is not None and float(v) > 0]
    if not vals:
        return []
    order = sorted(range(len(vals)), key=lambda k: -vals[k])
    total = sum(vals)
    sizes = [vals[k] * dx * dy / total for k in order]
    rects = []
    _squarify(sizes, 0.0, 0.0, dx, dy, rects)
    # map back to original order
    out = [None] * len(vals)
    for pos, k in enumerate(order):
        out[k] = rects[pos]
    return out
