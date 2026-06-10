"""residual-diagnostic-panel — regression diagnostics (Q-Q / Residual-vs-Fitted /
Scale-Location / Residual-vs-Leverage) embedded as four graph cells in a review-matrix.
Reuses review-matrix's graph-cell embedding + xy-core; no new engine. Computes a simple
least-squares fit + standardized residuals + leverage in pure Python.
"""

from __future__ import annotations

import math

from ..postprocess import stats
from .base import Recipe
from .base_xy import _num
from .matrix_compare import MatrixRecipe


def _xy(payload):
    if isinstance(payload.get("x"), list) and isinstance(payload.get("y"), list):
        out = []
        for a, b in zip(payload["x"], payload["y"]):
            na, nb = _num(a), _num(b)
            if na is not None and nb is not None:
                out.append((na, nb))
        return out
    s = (payload.get("series") or [{}])[0]
    out = []
    for pt in (s.get("data") or []):
        if isinstance(pt, (list, tuple)) and len(pt) >= 2:
            na, nb = _num(pt[0]), _num(pt[1])
            if na is not None and nb is not None:
                out.append((na, nb))
    return out


def _scatter(xl, yl, pairs):
    return {"axes": {"x": {"label": xl, "unit": ""}, "y": {"label": yl, "unit": ""}},
            "series": [{"name": yl, "data": [[a, b] for a, b in pairs], "style": "markers"}]}


class ResidualPanelRecipe(Recipe):
    type_name = "residual-diagnostic-panel"
    _matrix = MatrixRecipe()

    def normalize(self, payload, resolved):
        pairs = _xy(payload)
        n = len(pairs)
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        xbar = sum(xs) / n
        ybar = sum(ys) / n
        sxx = sum((x - xbar) ** 2 for x in xs) or 1e-9
        sxy = sum((xs[i] - xbar) * (ys[i] - ybar) for i in range(n))
        a = sxy / sxx
        b = ybar - a * xbar
        fitted = [a * x + b for x in xs]
        resid = [ys[i] - fitted[i] for i in range(n)]
        sse = sum(e * e for e in resid)
        s = math.sqrt(sse / (n - 2)) if n > 2 and sse > 0 else (math.sqrt(sse / n) if sse > 0 else 1.0)
        lev = [1.0 / n + (x - xbar) ** 2 / sxx for x in xs]
        sr = [resid[i] / (s * math.sqrt(max(1e-9, 1 - lev[i]))) for i in range(n)]
        order = sorted(range(n), key=lambda i: sr[i])
        sr_sorted = [sr[i] for i in order]
        tq = stats.normal_quantiles(n)

        qq = _scatter("Theoretical quantiles", "Std. residual", list(zip(tq, sr_sorted)))
        rf = _scatter("Fitted value", "Residual", list(zip(fitted, resid)))
        sl = _scatter("Fitted value", "√|std. residual|", [(fitted[i], math.sqrt(abs(sr[i]))) for i in range(n)])
        lv = _scatter("Leverage", "Std. residual", list(zip(lev, sr)))

        def cell(gp):
            return {"kind": "graph", "graph_ref": {"type": "base-xy", "payload": gp}}

        items = [
            {"id": "qq", "label": "Normal Q-Q", "type": "graph", "cells": {"d": cell(qq)}},
            {"id": "rf", "label": "Residual vs Fitted", "type": "graph", "cells": {"d": cell(rf)}},
            {"id": "sl", "label": "Scale-Location", "type": "graph", "cells": {"d": cell(sl)}},
            {"id": "lv", "label": "Residual vs Leverage", "type": "graph", "cells": {"d": cell(lv)}},
        ]
        mpayload = {
            "title": str(payload.get("title") or f"Regression diagnostics (slope={a:.3g}, n={n})"),
            "states": [{"id": "d", "label": "Diagnostic"}],
            "items": items,
            "options": {"diff": False},
        }
        return self._matrix.normalize(mpayload, resolved)

    def structural_requires(self, payload):
        pairs = _xy(payload)
        if len(pairs) < 3:
            return [{"field": "x/y", "why": "회귀 진단에 (x,y) 표본 부족(>=3)",
                     "ask": "회귀할 (x,y) 데이터를 주세요 (x:[...], y:[...] 또는 series:[{data:[[x,y],...]}])."}]
        if len({p[0] for p in pairs}) < 2:
            return [{"field": "x", "why": "x 변화가 없어 회귀 불가",
                     "ask": "x 값이 서로 달라야 회귀가 가능합니다 (현재 모두 동일)."}]
        return []
