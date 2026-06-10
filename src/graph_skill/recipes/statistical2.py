"""Pareto / Q-Q / ECDF / SPC control-chart recipes.

All xy-core, reusing existing engine features only — bar + secondary (right) axis +
threshold-lines (now incl. axis:"y2") + named-markers + regression-fit + curve:"step".
No new engine or plugin code.
"""

from __future__ import annotations

from ..postprocess import stats
from .base import Recipe
from .base_xy import BaseXYRecipe, _num


def _values(payload: dict) -> list:
    """Flat finite values from values:[...] or the first series' data/y."""
    if isinstance(payload.get("values"), list):
        return [v for v in (_num(x) for x in payload["values"]) if v is not None]
    s = (payload.get("series") or [{}])[0]
    if isinstance(s.get("data"), list):
        out = (_num(pt[-1] if isinstance(pt, (list, tuple)) else pt) for pt in s["data"])
        return [v for v in out if v is not None]
    if isinstance(s.get("y"), list):
        return [v for v in (_num(x) for x in s["y"]) if v is not None]
    return []


def _axis(a, dlabel="value"):
    a = a or {}
    return {"label": str(a.get("label", dlabel)), "unit": str(a.get("unit", "")), "log": False}


class ParetoRecipe(Recipe):
    """Sorted bars (left) + cumulative % line (right axis) + 80% reference line."""

    type_name = "pareto"

    def normalize(self, payload, resolved):
        cats = [str(c) for c in (payload.get("categories") or [])]
        vals = [float(_num(v) or 0.0) for v in (payload.get("values") or [])]
        cats2, vals2, cum = stats.pareto(cats, vals)
        idx = list(range(len(vals2)))
        ax = payload.get("axes") or {}
        xa = _axis(ax.get("x"), "")
        xa["categories"] = cats2
        series = [
            {"name": "value", "x": idx, "y": vals2, "style": "bar", "axis": "left", "color": "#2563eb"},
            {"name": "cumulative", "x": idx, "y": cum, "style": "line+markers", "axis": "right", "color": "#dc2626"},
        ]
        options = {
            "curve": "straight",
            "axes": {"x": xa, "y": _axis(ax.get("y")),
                     "y2": {"label": "Cumulative", "unit": "%", "log": False}},
            "pluginConfig": {"threshold-lines": {"lines": [
                {"axis": "y2", "value": 80, "label": "80%", "color": "#888", "dash": [4, 4]}]}},
        }
        if payload.get("title"):
            options["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        miss = []
        cats = payload.get("categories") or []
        vals = payload.get("values") or []
        if not cats:
            miss.append({"field": "categories", "why": "파레토 범주가 없음",
                         "ask": "파레토 범주(라벨)들을 알려주세요 (categories:[...])."})
        if not vals:
            miss.append({"field": "values", "why": "범주별 값이 없음",
                         "ask": "각 범주의 값(빈도/비용/결함수 등)을 주세요 (values:[...], categories와 동일 길이)."})
        if cats and vals and len(cats) != len(vals):
            miss.append({"field": "values", "why": "categories와 values 길이 불일치",
                         "ask": "categories와 values의 개수를 동일하게 맞춰주세요."})
        ya = (payload.get("axes") or {}).get("y") or {}
        if not ya.get("label") or "unit" not in ya:
            miss.append({"field": "axes.y", "why": "값(y)의 의미/단위 미상",
                         "ask": "막대 값이 무엇이고 단위는? (axes.y={label,unit}; 결함 건수면 unit:'건' 등)"})
        return miss


class QQRecipe(Recipe):
    """Normal Q-Q plot — sample quantiles vs theoretical normal quantiles + LS fit line."""

    type_name = "qq-plot"

    def normalize(self, payload, resolved):
        vals = sorted(_values(payload))
        tq = stats.normal_quantiles(len(vals))
        ax = payload.get("axes") or {}
        ya = ax.get("y") or {}
        series = [{"name": "Q-Q", "x": tq, "y": vals, "style": "markers", "color": "#2563eb"}]
        options = {
            "curve": "straight",
            "axes": {"x": {"label": "Theoretical quantiles", "unit": "", "log": False},
                     "y": {"label": str(ya.get("label", "Sample quantiles")),
                           "unit": str(ya.get("unit", "")), "log": False}},
            "pluginConfig": {"regression-fit": {"model": "linear", "showR2": True}},
        }
        if payload.get("title"):
            options["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        if len(_values(payload)) < 3:
            return [{"field": "values", "why": "정규성 점검용 표본이 부족(>=3)",
                     "ask": "Q-Q 플롯으로 정규성을 볼 표본 값들을 주세요 (values:[...], 3개 이상)."}]
        return []


class ECDFRecipe(Recipe):
    """Empirical CDF — sorted x vs F(x)=i/n, drawn as a step line."""

    type_name = "ecdf-plot"

    def normalize(self, payload, resolved):
        xs, F = stats.ecdf(_values(payload))
        ax = payload.get("axes") or {}
        series = [{"name": "ECDF", "x": xs, "y": F, "style": "line", "color": "#2563eb"}]
        options = {
            "curve": "step",
            "axes": {"x": _axis(ax.get("x")), "y": {"label": "F(x)", "unit": "", "log": False}},
        }
        if payload.get("title"):
            options["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        miss = []
        if not _values(payload):
            miss.append({"field": "values", "why": "누적분포를 그릴 값이 없음",
                         "ask": "ECDF로 그릴 표본 값들을 주세요 (values:[...])."})
        xa = (payload.get("axes") or {}).get("x") or {}
        if not xa.get("label") or "unit" not in xa:
            miss.append({"field": "axes.x", "why": "변수(x)의 의미/단위 미상",
                         "ask": "분포를 그릴 변수와 단위는? (axes.x={label,unit}; 무차원이면 unit:'')"})
        return miss


class SPCRecipe(Recipe):
    """Shewhart control chart — measurement series + CL/UCL/LCL (mean ± 3σ) + OOC markers."""

    type_name = "spc-control-chart"
    _base = BaseXYRecipe()

    def normalize(self, payload, resolved):
        norm = self._base.normalize(payload, resolved)
        s0 = (norm["assets"]["series"] or [{}])[0]
        xs, ys = s0.get("x", []), s0.get("y", [])
        cl = stats.control_limits(ys)
        lines = [
            {"axis": "y", "value": cl["mean"], "label": "CL", "color": "#059669", "dash": [6, 4]},
            {"axis": "y", "value": cl["ucl"], "label": "UCL", "color": "#dc2626", "dash": [6, 4]},
            {"axis": "y", "value": cl["lcl"], "label": "LCL", "color": "#dc2626", "dash": [6, 4]},
        ]
        markers = [{"x": xs[i], "y": ys[i], "label": "OOC", "color": "#dc2626"}
                   for i in cl["violations"] if i < len(xs) and ys[i] is not None]
        pc = norm["options"].setdefault("pluginConfig", {})
        pc["threshold-lines"] = {"lines": lines}
        pc["named-markers"] = {"markers": markers}
        for s in norm["assets"]["series"]:
            s.setdefault("style", "line+markers")
        return norm

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("series") or []):
            miss.append({"field": "series", "why": "관리도 측정 시계열이 없음",
                         "ask": "관리도용 측정 시퀀스를 주세요 (series:[{name, data:[[sample, value], ...]}])."})
        ya = (payload.get("axes") or {}).get("y") or {}
        if not ya.get("label") or "unit" not in ya:
            miss.append({"field": "axes.y", "why": "측정량(y)의 의미/단위 미상",
                         "ask": "관리 대상 측정량과 단위는? (axes.y={label,unit})"})
        return miss
