"""correlation-scatter recipe — base-xy scatter + regression line + R² + y=x identity.
For CAE-vs-Test correlation and DOE relations."""

from __future__ import annotations

from .base import Recipe
from .base_xy import BaseXYRecipe


class CorrelationScatterRecipe(Recipe):
    type_name = "correlation-scatter"
    _base = BaseXYRecipe()

    def normalize(self, payload: dict, resolved) -> dict:
        norm = self._base.normalize(payload, resolved)
        for s in norm["assets"]["series"]:
            s.setdefault("style", "markers")
        opts = payload.get("options") or {}
        params = payload.get("params") or {}
        rf = {"model": "linear", "showR2": True, "identityLine": True}
        if opts.get("identity") is False or params.get("identity") is False:
            rf["identityLine"] = False
        norm["options"].setdefault("pluginConfig", {}).setdefault("regression-fit", rf)
        return norm
