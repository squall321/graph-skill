"""Wave-2 expansion — area-plot / stacked-area / waterfall-chart / violin-plot.
All xy-core; rendering via three new self-contained plugins (area-fill / waterfall / violin)
that draw their own glyphs (box-plot pattern). No engine change."""

from __future__ import annotations

from ..postprocess import stats
from .base import Recipe
from .base_xy import BaseXYRecipe, _num


def _axis(a, dlabel=""):
    a = a or {}
    return {"label": str(a.get("label", dlabel)), "unit": str(a.get("unit", "")),
            "log": a.get("scale", "linear") == "log"}


class AreaPlotRecipe(Recipe):
    """Line + filled area to the baseline."""

    type_name = "area-plot"
    _base = BaseXYRecipe()

    def normalize(self, payload, resolved):
        norm = self._base.normalize(payload, resolved)
        for s in norm["assets"]["series"]:
            s.setdefault("style", "line")
        norm["options"].setdefault("pluginConfig", {})["area-fill"] = {"baseline": 0, "opacity": 0.3}
        return norm

    def structural_requires(self, payload):
        if not (payload.get("series") or []):
            return [{"field": "series", "why": "면적 곡선 데이터가 없음",
                     "ask": "시리즈를 주세요 (series:[{name, data:[[x,y],...]}]) + axes.x/y{label,unit}."}]
        return []


class StackedAreaRecipe(Recipe):
    """Cumulatively stacked filled areas (composition over x). Series share the x grid."""

    type_name = "stacked-area"
    _base = BaseXYRecipe()

    def normalize(self, payload, resolved):
        norm = self._base.normalize(payload, resolved)
        ser = norm["assets"]["series"]
        if ser:
            cum = [0.0] * len(ser[0]["y"])
            for s in ser:
                for k in range(min(len(s["y"]), len(cum))):
                    v = s["y"][k]
                    cum[k] += v if (v is not None) else 0.0
                    s["y"][k] = cum[k]
                s.setdefault("style", "line")
        norm["options"].setdefault("pluginConfig", {})["area-fill"] = {"stacked": True, "opacity": 0.6}
        return norm

    def structural_requires(self, payload):
        if len(payload.get("series") or []) < 1:
            return [{"field": "series", "why": "누적 면적 데이터가 없음",
                     "ask": "공유 x 위 여러 시리즈를 주세요 (series:[{name, data:[[x,y],...]}], 같은 x) + axes.x/y."}]
        return []


class WaterfallRecipe(Recipe):
    """Floating bars: running total decomposition (inc/dec) + optional totals."""

    type_name = "waterfall-chart"

    def normalize(self, payload, resolved):
        cats = [str(c) for c in (payload.get("categories") or [])]
        vals = [_num(v) for v in (payload.get("values") or [])]
        kinds = payload.get("kinds")
        bars, dx, dy, run = [], [], [], 0.0
        for i, v in enumerate(vals):
            kind = kinds[i] if (kinds and i < len(kinds)) else None
            if kind == "total":
                base, top = 0.0, (v if (v is not None and v != 0) else run)
                run = top
            else:
                vv = v or 0.0
                base, top = run, run + vv
                run = top
                kind = kind or ("dec" if vv < 0 else "inc")
            bars.append({"x": i, "base": base, "top": top, "kind": kind})
            dx += [i, i]
            dy += [base, top]
        ax = payload.get("axes") or {}
        xa = _axis(ax.get("x"), "")
        xa["categories"] = cats
        opts = {"axes": {"x": xa, "y": _axis(ax.get("y"))},
                "pluginConfig": {"waterfall": {"bars": bars}}}
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine,
                "assets": {"series": [{"name": "_wf", "x": dx, "y": dy, "style": "none"}]}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("categories") or []) or not (payload.get("values") or []):
            miss.append({"field": "categories/values", "why": "워터폴 단계가 없음",
                         "ask": "단계 라벨과 증감값을 주세요 (categories:[...], values:[+/- 값...]); kinds:['inc'|'dec'|'total'] 선택."})
        ya = (payload.get("axes") or {}).get("y") or {}
        if not ya.get("label") or "unit" not in ya:
            miss.append({"field": "axes.y", "why": "누적량(y) 의미/단위 미상",
                         "ask": "누적되는 양과 단위는? (axes.y={label,unit})"})
        return miss


class ViolinRecipe(Recipe):
    """KDE violins per group (categorical x) + median tick."""

    type_name = "violin-plot"

    def normalize(self, payload, resolved):
        groups = payload.get("groups") or []
        cats, vgroups, dx, dy = [], [], [], []
        for i, g in enumerate(groups):
            cats.append(str(g.get("label", f"g{i + 1}")))
            vals = [_num(v) for v in (g.get("values") or []) if _num(v) is not None]
            ys, dens = stats.kde(vals, n=64)
            med = sorted(vals)[len(vals) // 2] if vals else None
            vgroups.append({"x": i, "ys": ys, "dens": dens, "med": med})
            if ys:
                dx += [i, i]
                dy += [ys[0], ys[-1]]
        ax = payload.get("axes") or {}
        xa = _axis(ax.get("x"), "")
        xa["categories"] = cats
        opts = {"axes": {"x": xa, "y": _axis(ax.get("y"))},
                "pluginConfig": {"violin": {"groups": vgroups}}}
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine,
                "assets": {"series": [{"name": "_v", "x": dx, "y": dy, "style": "none"}]}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("groups") or []):
            miss.append({"field": "groups", "why": "바이올린 그룹이 없음",
                         "ask": "그룹을 주세요 (groups:[{label, values:[...]}, ...])."})
        ya = (payload.get("axes") or {}).get("y") or {}
        if not ya.get("label") or "unit" not in ya:
            miss.append({"field": "axes.y", "why": "측정값(y) 의미/단위 미상",
                         "ask": "분포를 볼 측정량과 단위는? (axes.y={label,unit})"})
        return miss
