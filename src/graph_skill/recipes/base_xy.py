"""base-xy recipe — normalize multi-series X-Y input into canonical Series[].

Tolerates: list of [x, y] pairs, list of {x, y} dicts, or parallel x[]/y[] arrays.
Non-finite y becomes ``None`` (a gap / broken line); points with non-finite x are dropped.
"""

from __future__ import annotations

import math

from .base import Recipe

_ALLOWED_OPTS = {
    "curve",
    "palette",
    "theme",
    "grid",
    "legend",
    "responsive",
    "interactions",
    "exportButtons",
}
_STYLES = {"line", "markers", "line+markers", "step"}


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


class BaseXYRecipe(Recipe):
    type_name = "base-xy"

    def normalize(self, payload: dict, resolved) -> dict:
        series = [self._series(s, i) for i, s in enumerate(payload.get("series") or [])]
        return {
            "engine": resolved.engine,
            "assets": {"series": series},
            "options": self._options(payload, resolved),
        }

    # ----- series -----------------------------------------------------------
    def _series(self, s: dict, i: int) -> dict:
        if not isinstance(s, dict):
            raise ValueError(f"series[{i}] must be an object")
        name = str(s.get("name") or f"series {i + 1}")
        xs: list = []
        ys: list = []
        if isinstance(s.get("x"), list) and isinstance(s.get("y"), list):
            for xv, yv in zip(s["x"], s["y"]):
                self._push(xs, ys, xv, yv)
        else:
            data = s.get("data")
            if not isinstance(data, list):
                raise ValueError(f"series[{i}] '{name}' has no 'data' array or x/y arrays")
            for pt in data:
                if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    self._push(xs, ys, pt[0], pt[1])
                elif isinstance(pt, dict):
                    self._push(xs, ys, pt.get("x"), pt.get("y"))
                else:
                    raise ValueError(f"series[{i}] '{name}' point must be [x,y] or {{x,y}}")
        if not xs:
            raise ValueError(f"series[{i}] '{name}' has no finite points")
        out = {"name": name, "x": xs, "y": ys}
        if s.get("color"):
            out["color"] = str(s["color"])
        if s.get("style") in _STYLES:
            out["style"] = s["style"]
        if s.get("axis") in ("left", "right"):
            out["axis"] = s["axis"]
        if isinstance(s.get("dash"), list):
            out["dash"] = [float(d) for d in s["dash"]]
        return out

    @staticmethod
    def _push(xs: list, ys: list, xv, yv) -> None:
        x = _num(xv)
        if x is None:
            return  # x must be finite to position the point
        xs.append(x)
        ys.append(_num(yv))  # y None -> gap

    # ----- options ----------------------------------------------------------
    def _options(self, payload: dict, resolved) -> dict:
        opts = dict(resolved.options)  # options_defaults (curve, grid, ...)
        axes = payload.get("axes") or {}
        opts["axes"] = {"x": self._axis(axes.get("x")), "y": self._axis(axes.get("y"))}
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        for k, v in (payload.get("options") or {}).items():
            if k in _ALLOWED_OPTS:
                opts[k] = v
        return opts

    @staticmethod
    def _axis(a) -> dict:
        a = a or {}
        return {
            "label": str(a.get("label", "")),
            "unit": str(a.get("unit", "")),
            "log": a.get("scale", "linear") == "log",
        }
