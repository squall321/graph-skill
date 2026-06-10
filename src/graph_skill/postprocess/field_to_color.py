"""field_to_color — scalar field → per-vertex RGB for cad3d-core (FE result coloring).

Pure Python, zero dependencies. Anchored colormaps (viridis / turbo / coolwarm / gray)
linearly interpolated to a 256-entry LUT, matching field-core's color space closely so a
3D result map and its 2D contour read consistently. Deterministic.
"""

from __future__ import annotations

# Anchor control points (pos in [0,1] -> RGB 0..255). Linear interp between anchors.
_ANCHORS = {
    "viridis": [
        (0.00, (68, 1, 84)), (0.25, (59, 82, 139)), (0.50, (33, 144, 140)),
        (0.75, (93, 201, 99)), (1.00, (253, 231, 37)),
    ],
    "turbo": [
        (0.000, (48, 18, 59)), (0.125, (70, 107, 227)), (0.250, (40, 168, 254)),
        (0.375, (24, 229, 194)), (0.500, (60, 253, 118)), (0.625, (163, 252, 60)),
        (0.750, (231, 228, 49)), (0.875, (254, 150, 40)), (1.000, (122, 4, 3)),
    ],
    "coolwarm": [
        (0.00, (59, 76, 192)), (0.50, (221, 221, 221)), (1.00, (180, 4, 38)),
    ],
    "gray": [(0.00, (0, 0, 0)), (1.00, (255, 255, 255))],
}


def lut(cmap: str = "viridis", n: int = 256) -> list:
    """Return an n-entry [[r,g,b], ...] LUT (uint8) for the named colormap."""
    anchors = _ANCHORS.get(cmap) or _ANCHORS["viridis"]
    out = []
    for i in range(n):
        t = i / (n - 1) if n > 1 else 0.0
        # locate segment
        for k in range(len(anchors) - 1):
            p0, c0 = anchors[k]
            p1, c1 = anchors[k + 1]
            if t <= p1 or k == len(anchors) - 2:
                f = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
                f = max(0.0, min(1.0, f))
                out.append([int(round(c0[j] + (c1[j] - c0[j]) * f)) for j in range(3)])
                break
    return out


def _percentile(sorted_vals: list, q: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = q * (len(sorted_vals) - 1)
    lo = int(idx)
    frac = idx - lo
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac


def scalar_to_rgb(values, vmin=None, vmax=None, cmap="viridis", clip_percentile=None):
    """Map a scalar list to per-value [r,g,b] (uint8).

    vmin/vmax fix the color range (e.g. yield strength); if None they default to the data
    range, or to the [p, 100-p] percentile window when clip_percentile=p (outlier-robust).
    Returns (rgb_list, (vmin, vmax)).
    """
    vals = [float(v) for v in values]
    if vmin is None or vmax is None:
        finite = sorted(v for v in vals if v == v)  # drop NaN
        if clip_percentile:
            p = clip_percentile / 100.0
            lo, hi = _percentile(finite, p), _percentile(finite, 1 - p)
        else:
            lo, hi = (finite[0], finite[-1]) if finite else (0.0, 1.0)
        vmin = lo if vmin is None else vmin
        vmax = hi if vmax is None else vmax
    if vmax <= vmin:
        vmax = vmin + 1.0
    table = lut(cmap, 256)
    span = vmax - vmin
    rgb = []
    for v in vals:
        t = (v - vmin) / span
        t = 0.0 if t < 0 else (1.0 if t > 1 else t)
        rgb.append(table[int(round(t * 255))])
    return rgb, (vmin, vmax)
