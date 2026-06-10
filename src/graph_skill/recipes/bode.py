"""dual-axis + bode recipes (xy-core secondary-y). dual-axis = generic left/right y; bode =
log-frequency Magnitude[dB] (left) + Phase[deg] (right)."""

from __future__ import annotations

from .base import Recipe
from .base_xy import BaseXYRecipe, _num


class DualAxisRecipe(Recipe):
    type_name = "dual-axis"
    _base = BaseXYRecipe()

    def normalize(self, payload, resolved):
        norm = self._base.normalize(payload, resolved)
        y2 = (payload.get("axes") or {}).get("y2")
        if y2:
            norm["options"]["axes"]["y2"] = {
                "label": str(y2.get("label", "")), "unit": str(y2.get("unit", "")), "log": False
            }
        return norm

    def structural_requires(self, payload):
        y2 = (payload.get("axes") or {}).get("y2") or {}
        if not y2.get("label") or "unit" not in y2:
            return [{"field": "axes.y2", "why": "우측 축(2nd y)의 의미/단위 미상",
                     "ask": "우측 y축 물리량과 단위는? (axes.y2={label,unit}; 우측 시리즈에는 axis:'right')"}]
        return []


class BodeRecipe(Recipe):
    type_name = "bode"

    def normalize(self, payload, resolved):
        freqs = [float(f) for f in (payload.get("freqs") or [])]
        mag = [_num(v) for v in (payload.get("mag") or [])]
        phase = [_num(v) for v in (payload.get("phase") or [])]
        series = [
            {"name": "Magnitude", "x": freqs, "y": mag, "axis": "left", "color": "#2563eb"},
            {"name": "Phase", "x": freqs, "y": phase, "axis": "right", "color": "#dc2626", "dash": [5, 4]},
        ]
        options = {
            "curve": "straight",
            "axes": {
                "x": {"label": "Frequency", "unit": "Hz", "log": True},
                "y": {"label": "Magnitude", "unit": "dB", "log": False},
                "y2": {"label": "Phase", "unit": "deg", "log": False},
            },
        }
        if payload.get("title"):
            options["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        if not (payload.get("freqs") and payload.get("mag") and payload.get("phase")):
            return [{"field": "bode", "why": "Bode 데이터 부족",
                     "ask": "Bode 데이터를 주세요: freqs:[Hz], mag:[dB], phase:[deg] (동일 길이)."}]
        return []
