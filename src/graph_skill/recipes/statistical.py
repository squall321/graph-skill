"""Statistical & bar recipes — histogram / bar-plot / box-plot / error-bar (all xy-core,
using the new bar / categorical-axis / none-style engine support + box-plot/error-bars
plugins + stats postprocess)."""

from __future__ import annotations

import math

from ..postprocess import stats
from .base import Recipe
from .base_xy import BaseXYRecipe, _num


def _values(payload: dict) -> list:
    if isinstance(payload.get("values"), list):
        return [_num(v) for v in payload["values"]]
    s = (payload.get("series") or [{}])[0]
    if isinstance(s.get("data"), list):
        return [_num(pt[-1] if isinstance(pt, (list, tuple)) else pt) for pt in s["data"]]
    if isinstance(s.get("y"), list):
        return [_num(v) for v in s["y"]]
    return []


def _axis(a, dlabel="value"):
    a = a or {}
    return {"label": str(a.get("label", dlabel)), "unit": str(a.get("unit", "")), "log": False}


class HistogramRecipe(Recipe):
    type_name = "histogram"

    def normalize(self, payload, resolved):
        vals = [v for v in _values(payload) if v is not None]
        params = payload.get("params") or {}
        centers, counts, w = stats.histogram(vals, params.get("bins"))
        if params.get("density") and vals and w > 0:
            tot = len(vals) * w
            counts = [c / tot for c in counts]
        ax = payload.get("axes") or {}
        options = {"axes": {"x": _axis(ax.get("x")),
                            "y": {"label": "Density" if params.get("density") else "Frequency", "unit": "", "log": False}}}
        if payload.get("title"):
            options["title"] = str(payload["title"])
        return {"engine": resolved.engine,
                "assets": {"series": [{"name": "count", "x": centers, "y": counts, "style": "bar", "color": "#2563eb"}]},
                "options": options}

    def structural_requires(self, payload):
        miss = []
        if not [v for v in _values(payload) if v is not None]:
            miss.append({"field": "values", "why": "분포를 그릴 값이 없음",
                         "ask": "히스토그램으로 그릴 값들을 알려주세요 (values:[...] 또는 series data)."})
        xa = (payload.get("axes") or {}).get("x") or {}
        if not xa.get("label") or "unit" not in xa:
            miss.append({"field": "axes.x", "why": "분포 변수(x)의 의미/단위 미상",
                         "ask": "분포를 그릴 변수가 무엇이고 단위는? (axes.x={label,unit}; 무차원이면 unit:'')"})
        return miss


class BarPlotRecipe(Recipe):
    type_name = "bar-plot"

    def normalize(self, payload, resolved):
        cats = [str(c) for c in (payload.get("categories") or [])]
        vals = payload.get("values")
        if vals is None:
            s = (payload.get("series") or [{}])[0]
            vals = [(pt[-1] if isinstance(pt, (list, tuple)) else pt) for pt in (s.get("data") or [])]
        ys = [_num(v) for v in (vals or [])]
        ax = payload.get("axes") or {}
        xa = _axis(ax.get("x"), "")
        xa["categories"] = cats
        options = {"axes": {"x": xa, "y": _axis(ax.get("y"))}}
        if payload.get("title"):
            options["title"] = str(payload["title"])
        return {"engine": resolved.engine,
                "assets": {"series": [{"name": "value", "x": list(range(len(ys))), "y": ys, "style": "bar", "color": "#2563eb"}]},
                "options": options}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("categories") or []):
            miss.append({"field": "categories", "why": "막대 범주가 없음", "ask": "막대 범주(라벨)들을 알려주세요 (categories:[...])."})
        ya = (payload.get("axes") or {}).get("y") or {}
        if not ya.get("label") or "unit" not in ya:
            miss.append({"field": "axes.y", "why": "막대 값(y)의 의미/단위 미상", "ask": "막대로 표시할 양과 단위는? (axes.y={label,unit})"})
        return miss


class BoxPlotRecipe(Recipe):
    type_name = "box-plot"

    def normalize(self, payload, resolved):
        groups = payload.get("groups") or []
        cats, gstats, lo, hi = [], [], math.inf, -math.inf
        for i, g in enumerate(groups):
            cats.append(str(g.get("label", f"g{i + 1}")))
            q = stats.quartiles([_num(v) for v in (g.get("values") or [])]) or {"q1": 0, "med": 0, "q3": 0, "lo": 0, "hi": 0, "outliers": []}
            gstats.append({"x": i, "q1": q["q1"], "med": q["med"], "q3": q["q3"], "lo": q["lo"], "hi": q["hi"], "outliers": q["outliers"]})
            for v in [q["lo"], q["hi"]] + q["outliers"]:
                lo, hi = min(lo, v), max(hi, v)
        dx, dy = [], []
        ylo = lo if math.isfinite(lo) else 0.0
        yhi = hi if math.isfinite(hi) else 1.0
        for gs in gstats:
            dx += [gs["x"], gs["x"]]
            dy += [ylo, yhi]
        ax = payload.get("axes") or {}
        xa = _axis(ax.get("x"), "")
        xa["categories"] = cats
        options = {"axes": {"x": xa, "y": _axis(ax.get("y"))}, "pluginConfig": {"box-plot": {"groups": gstats}}}
        if payload.get("title"):
            options["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": [{"name": "_range", "x": dx, "y": dy, "style": "none"}]}, "options": options}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("groups") or []):
            miss.append({"field": "groups", "why": "박스플롯 그룹이 없음", "ask": "그룹들을 알려주세요 (groups:[{label, values:[...]}, ...])."})
        ya = (payload.get("axes") or {}).get("y") or {}
        if not ya.get("label") or "unit" not in ya:
            miss.append({"field": "axes.y", "why": "측정값(y)의 의미/단위 미상", "ask": "분포를 볼 측정량과 단위는? (axes.y={label,unit})"})
        return miss


class ErrorBarRecipe(Recipe):
    type_name = "error-bar"
    _base = BaseXYRecipe()

    def normalize(self, payload, resolved):
        norm = self._base.normalize(payload, resolved)
        bars = []
        for s in payload.get("series") or []:
            data = s.get("data") or []
            errs = s.get("err")
            for j, pt in enumerate(data):
                if isinstance(pt, (list, tuple)) and len(pt) >= 3:
                    x, y, e = pt[0], pt[1], pt[2]
                elif isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    x, y = pt[0], pt[1]
                    e = errs[j] if (errs and j < len(errs)) else None
                else:
                    continue
                if e is not None:
                    bars.append({"x": float(x), "y": float(y), "err": float(e)})
        norm["options"].setdefault("pluginConfig", {})["error-bars"] = {"bars": bars}
        for s in norm["assets"]["series"]:
            s.setdefault("style", "line+markers")
        return norm
