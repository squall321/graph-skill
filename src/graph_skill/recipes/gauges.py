"""gauge-core KPI indicators — gauge / radial-progress / bullet-chart. Accepts a single
indicator (flat payload) or items[]. min/max default to a 0..100 dial when omitted
(a conventional gauge scale, not an invented physical unit). Values animate on load."""

from __future__ import annotations

from .base import Recipe

_ITEM_KEYS = ("label", "value", "min", "max", "target", "unit", "bands", "goal", "color", "delta", "spark")


def _items(payload):
    if payload.get("items"):
        src = payload["items"]
    else:
        single = {k: payload[k] for k in _ITEM_KEYS if k in payload}
        src = [single] if "value" in single else []
    out = []
    for it in src:
        if not isinstance(it, dict) or it.get("value") is None:
            continue
        d = {"label": str(it.get("label", "")), "value": float(it["value"]),
             "min": float(it.get("min", 0)), "max": float(it.get("max", 100))}
        for k in ("target", "unit", "bands", "goal", "color"):
            if it.get(k) is not None:
                d[k] = float(it[k]) if k == "target" else it[k]
        if it.get("delta") is not None:
            d["delta"] = float(it["delta"])
        if isinstance(it.get("spark"), list):
            d["spark"] = [float(s) for s in it["spark"]]
        out.append(d)
    return out


class _GaugeBase(Recipe):
    _kind = "gauge"

    def normalize(self, payload: dict, resolved) -> dict:
        options = {"title": payload.get("title") or "", "theme": (payload.get("options") or {}).get("theme", "auto")}
        return {"engine": resolved.engine,
                "assets": {"kind": self._kind, "items": _items(payload)}, "options": options}

    def structural_requires(self, payload: dict) -> list:
        if not _items(payload):
            return [{"field": "value", "why": "지표 값이 없음",
                     "ask": "지표 값을 주세요: value (+min,max,target,unit,label). 여러 개면 items:[{…}, …]."}]
        return []


class GaugeRecipe(_GaugeBase):
    type_name = "gauge"
    _kind = "gauge"


class RadialProgressRecipe(_GaugeBase):
    type_name = "radial-progress"
    _kind = "radial-progress"


class BulletChartRecipe(_GaugeBase):
    type_name = "bullet-chart"
    _kind = "bullet"


class StatCardRecipe(_GaugeBase):
    """Big-number KPI cards (value count-up + trend delta + sparkline) in a grid."""

    type_name = "stat-card"
    _kind = "card"
