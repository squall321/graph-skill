"""stress-strain recipe — converts raw force[N]/displacement[mm] series + A0/L0 into an
engineering (or true) stress-strain curve, with auto UTS/Fracture markers and Et tangent.
extends base-xy; axes are derived (require_axes=false)."""

from __future__ import annotations

from ..postprocess import units
from .base import Recipe
from .base_xy import BaseXYRecipe


class StressStrainRecipe(Recipe):
    type_name = "stress-strain"
    _base = BaseXYRecipe()

    def normalize(self, payload: dict, resolved) -> dict:
        params = payload.get("params") or {}
        A0 = float(params["A0"])
        L0 = float(params["L0"])
        true_stress = bool(params.get("true_stress"))

        out_series = []
        for i, s in enumerate(payload.get("series") or []):
            ns = self._base._series(s, i)  # x=displacement[mm], y=force[N]
            strain, stress = units.eng_stress_strain(ns["y"], ns["x"], A0, L0)
            if true_stress:
                strain, stress = units.eng_to_true(strain, stress)
            out_series.append({"name": ns["name"], "x": strain, "y": stress})

        options = {
            "axes": {
                "x": {"label": "Strain ε", "unit": "", "log": False},
                "y": {"label": "True stress σₜ" if true_stress else "Stress σ", "unit": "MPa", "log": False},
            },
            "curve": "monotone",
            "pluginConfig": {
                "named-markers": {"markers": self._markers(out_series)},
                "live-tangent": {"label": "Et", "unit": "GPa", "scale": 1e-3, "seriesIndex": 0, "colorByMag": True},
            },
        }
        regions = params.get("regions") or (payload.get("options") or {}).get("regions")
        if regions:
            options["pluginConfig"]["region-shading"] = {"regions": regions}
        if payload.get("title"):
            options["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": out_series}, "options": options}

    @staticmethod
    def _markers(series: list) -> list:
        if not series:
            return []
        s0 = series[0]
        markers = []
        # UTS = max stress
        mi, mv = None, float("-inf")
        for j, y in enumerate(s0["y"]):
            if y is not None and y > mv:
                mv, mi = y, j
        if mi is not None:
            markers.append({"x": s0["x"][mi], "y": s0["y"][mi], "label": "UTS", "color": "#059669"})
        # Fracture = last finite point
        for j in range(len(s0["y"]) - 1, -1, -1):
            if s0["y"][j] is not None:
                markers.append({"x": s0["x"][j], "y": s0["y"][j], "label": "Fracture", "color": "#dc2626"})
                break
        return markers
