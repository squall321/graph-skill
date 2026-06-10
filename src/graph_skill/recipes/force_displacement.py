"""force-displacement recipe — base-xy + live-tangent re-labelled as local stiffness dF/dd."""

from __future__ import annotations

from .base import Recipe
from .base_xy import BaseXYRecipe


class ForceDisplacementRecipe(Recipe):
    type_name = "force-displacement"
    _base = BaseXYRecipe()

    def normalize(self, payload: dict, resolved) -> dict:
        norm = self._base.normalize(payload, resolved)
        pc = norm["options"].setdefault("pluginConfig", {})
        pc.setdefault("live-tangent", {"label": "k", "unit": "N/mm", "scale": 1, "seriesIndex": 0, "colorByMag": False})
        return norm
