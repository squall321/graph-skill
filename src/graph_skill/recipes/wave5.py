"""Wave-5 breadth (engine reuse) — multitrack-stack (review-matrix graph-cell stack) +
response-surface-2d (quadratic RSM fit → field-core contour)."""

from __future__ import annotations

from ..postprocess import treemap as _tm
from .base import Recipe
from .base_xy import _num
from .matrix_compare import MatrixRecipe, inject_plugin as _inject_plugin


class TreemapRecipe(Recipe):
    """Squarified treemap — category composition by area (layout pre-computed, plugin draws)."""

    type_name = "treemap"
    _pal = ["#2563eb", "#0891b2", "#059669", "#ca8a04", "#dc2626", "#9333ea", "#0ea5e9", "#65a30d"]

    def normalize(self, payload, resolved):
        items = payload.get("items") or []
        labels = [str(it.get("label", "")) for it in items]
        values = [_num(it.get("value")) or 0.0 for it in items]
        colors = [it.get("color") for it in items]
        rects = _tm.squarify(values, 1.0, 1.0)
        cfg_rects = []
        for i, r in enumerate(rects):
            if r is None:
                continue
            cfg_rects.append({"label": labels[i], "value": values[i], "x": r["x"], "y": r["y"],
                              "w": r["w"], "h": r["h"], "color": colors[i] or self._pal[i % len(self._pal)]})
        opts = {"axes": {"x": {"label": "", "unit": "", "log": False}, "y": {"label": "", "unit": "", "log": False}},
                "hideAxes": True, "pad": {"left": 12, "right": 12, "bottom": 12},
                "pluginConfig": {"treemap": {"rects": cfg_rects}}}
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine,
                "assets": {"series": [{"name": "_tm", "x": [0, 1], "y": [0, 1], "style": "none"}]}, "options": opts}

    def structural_requires(self, payload):
        items = payload.get("items") or []
        vals = [it for it in items if _num(it.get("value")) and _num(it.get("value")) > 0]
        if len(vals) < 1:
            return [{"field": "items", "why": "구성 항목/값이 없음",
                     "ask": "구성 항목을 주세요 (items:[{label, value(>0), color?}, ...])."}]
        return []


def _solve(a, b):
    """Gaussian elimination for small dense a·x=b. Returns x or None if singular."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-12:
            return None
        m[col], m[piv] = m[piv], m[col]
        pv = m[col][col]
        for j in range(col, n + 1):
            m[col][j] /= pv
        for r in range(n):
            if r != col and m[r][col]:
                f = m[r][col]
                for j in range(col, n + 1):
                    m[r][j] -= f * m[col][j]
    return [m[i][n] for i in range(n)]


class MultitrackRecipe(Recipe):
    """N channels stacked as aligned time panels (drop/vibration multi-signal)."""

    type_name = "multitrack-stack"
    _matrix = MatrixRecipe()

    def normalize(self, payload, resolved):
        channels = payload.get("channels") or []
        xm = payload.get("x") or {}
        xlab, xunit = str(xm.get("label", "Time")), str(xm.get("unit", "s"))

        def cell(ch, i):
            gp = {"axes": {"x": {"label": xlab, "unit": xunit},
                           "y": {"label": str(ch.get("name", f"ch{i+1}")), "unit": str(ch.get("unit", ""))}},
                  "series": [{"name": str(ch.get("name", f"ch{i+1}")), "data": ch.get("data") or [],
                              "color": ch.get("color")}]}
            return {"kind": "graph", "graph_ref": {"type": "base-xy", "payload": gp}}

        items = [{"id": f"ch{i}", "label": str(ch.get("name", f"ch{i+1}")), "type": "graph",
                  "cells": {"t": cell(ch, i)}} for i, ch in enumerate(channels)]
        mp = {"title": str(payload.get("title") or "Multitrack"),
              "states": [{"id": "t", "label": xlab}], "items": items, "options": {"diff": False}}
        out = self._matrix.normalize(mp, resolved)
        _inject_plugin(out, "xsync", {"group": "mt"})    # shared crosshair across panels
        return out

    def structural_requires(self, payload):
        chs = payload.get("channels") or []
        if len(chs) < 2:
            return [{"field": "channels", "why": "멀티트랙은 채널 2개 이상",
                     "ask": "채널들을 주세요 (channels:[{name, unit, data:[[t,v],...]}, ...], 2개 이상)."}]
        if any(not (c.get("data")) for c in chs):
            return [{"field": "channels[].data", "why": "채널 데이터 누락",
                     "ask": "각 채널에 data=[[time, value], ...] 를 주세요."}]
        return []


class ResponseSurfaceRecipe(Recipe):
    """Response surface (RSM) — quadratic least-squares fit over 2 factors → contour map."""

    type_name = "response-surface-2d"

    def normalize(self, payload, resolved):
        x1 = [_num(v) for v in (payload.get("x1") or [])]
        x2 = [_num(v) for v in (payload.get("x2") or [])]
        yy = [_num(v) for v in (payload.get("y") or [])]
        pts = [(x1[i], x2[i], yy[i]) for i in range(min(len(x1), len(x2), len(yy)))
               if None not in (x1[i], x2[i], yy[i])]
        # fit y = b0 + b1 x1 + b2 x2 + b3 x1^2 + b4 x2^2 + b5 x1 x2
        ata = [[0.0] * 6 for _ in range(6)]
        atb = [0.0] * 6
        for a, b, y in pts:
            row = [1.0, a, b, a * a, b * b, a * b]
            for r in range(6):
                atb[r] += row[r] * y
                for c in range(6):
                    ata[r][c] += row[r] * row[c]
        beta = _solve(ata, atb) or [0, 0, 0, 0, 0, 0]
        a0, a1 = min(p[0] for p in pts), max(p[0] for p in pts)
        b0, b1 = min(p[1] for p in pts), max(p[1] for p in pts)
        nx = int((payload.get("params") or {}).get("grid", 30))
        gx = [a0 + (a1 - a0) * i / (nx - 1) for i in range(nx)]
        gy = [b0 + (b1 - b0) * j / (nx - 1) for j in range(nx)]
        z = [[beta[0] + beta[1] * a + beta[2] * b + beta[3] * a * a + beta[4] * b * b + beta[5] * a * b
              for a in gx] for b in gy]
        fac = payload.get("factors") or {}
        zmeta = payload.get("z") or {}
        opts = {"axes": {"x": {"label": str((fac.get("x1") or {}).get("label", "x1")), "unit": str((fac.get("x1") or {}).get("unit", ""))},
                         "y": {"label": str((fac.get("x2") or {}).get("label", "x2")), "unit": str((fac.get("x2") or {}).get("unit", ""))}},
                "z": {"label": str(zmeta.get("label", "Response")), "unit": str(zmeta.get("unit", ""))},
                "colormap": payload.get("colormap", "viridis"), "contours": True}
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"field": {"x": gx, "y": gy, "z": z}}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        n = min(len(payload.get("x1") or []), len(payload.get("x2") or []), len(payload.get("y") or []))
        if n < 6:
            miss.append({"field": "x1/x2/y", "why": "2차 RSM 적합에 점 6개 이상 필요",
                         "ask": "두 인자와 응답을 주세요 (x1:[...], x2:[...], y:[...], 6점 이상)."})
        zmeta = payload.get("z") or {}
        if not zmeta.get("label") or "unit" not in zmeta:
            miss.append({"field": "z", "why": "응답(z) 의미/단위 미상",
                         "ask": "응답량과 단위는? (z={label:'수율', unit:'%'})"})
        return miss
