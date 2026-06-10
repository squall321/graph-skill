"""field-core recipes — normalize a 2D scalar field {x[], y[], z[][]} + axis/z meta.
One recipe serves contour-plot / heatmap-grid / scalar-field-2d / mcae-stress-contour
(they differ only in defaults). z is sanitized to float|None (None = transparent gap)."""

from __future__ import annotations

import math

from ..postprocess import fatigue
from .base import Recipe

_PASS_OPTS = ("colormap", "reverse", "levels", "zdomain", "contours")


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


class FieldRecipe(Recipe):
    type_name = "contour-plot"

    def normalize(self, payload: dict, resolved) -> dict:
        f = payload.get("field") or {}
        x = [float(v) for v in (f.get("x") or [])]
        y = [float(v) for v in (f.get("y") or [])]
        z = [[_num(c) for c in (row or [])] for row in (f.get("z") or [])]

        axes = payload.get("axes") or {}
        zmeta = payload.get("z") or {}
        options = {
            "axes": {"x": self._axis(axes.get("x")), "y": self._axis(axes.get("y"))},
            "z": {"label": str(zmeta.get("label", "")), "unit": str(zmeta.get("unit", ""))},
            "contours": resolved.name != "heatmap-grid",
        }
        opts_in = payload.get("options") or {}
        for k in _PASS_OPTS:
            v = opts_in.get(k, payload.get(k))
            if v is not None:
                options[k] = v
        for k, v in (resolved.options or {}).items():
            options.setdefault(k, v)
        if payload.get("title"):
            options["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"field": {"x": x, "y": y, "z": z}}, "options": options}

    @staticmethod
    def _axis(a) -> dict:
        a = a or {}
        return {"label": str(a.get("label", "")), "unit": str(a.get("unit", ""))}

    def structural_requires(self, payload: dict) -> list:
        miss = []
        f = payload.get("field") or {}
        x, y, z = f.get("x"), f.get("y"), f.get("z")
        if not (isinstance(x, list) and x and isinstance(y, list) and y and isinstance(z, list) and z):
            miss.append({"field": "field", "why": "2D 필드 데이터가 없음",
                         "ask": "필드 데이터를 주세요: field={x:[열좌표 nx], y:[행좌표 ny], z:[[ny×nx 값]]}."})
            return miss
        if len(z) != len(y) or any(not isinstance(r, list) or len(r) != len(x) for r in z):
            miss.append({"field": "field.z", "why": "z 격자 차원이 x/y와 불일치",
                         "ask": f"z 는 {len(y)}행 × {len(x)}열 (y×x) 2D 배열이어야 합니다. 차원을 확인해 주세요."})
        zmeta = payload.get("z") or {}
        if not zmeta.get("label") or ("unit" not in zmeta):
            miss.append({"field": "z", "why": "z(색) 물리량/단위 미상 → colorbar 의미 불명",
                         "ask": "z(색으로 표시할 양)의 물리량과 단위는? (예: '응력 σ', 'MPa'; 무차원이면 unit:'')"})
        return miss


class VectorQuiverRecipe(Recipe):
    """2D vector field as arrows (length+color = magnitude); reuses field-core (colorbar/axes/
    probe) with the new arrow overlay. Magnitude grid backs the colorbar; arrows on top."""

    type_name = "vector-quiver-2d"

    def normalize(self, payload, resolved):
        f = payload.get("field") or {}
        x = [float(v) for v in (f.get("x") or [])]
        y = [float(v) for v in (f.get("y") or [])]
        u = [[_num(c) for c in (row or [])] for row in (f.get("u") or [])]
        v = [[_num(c) for c in (row or [])] for row in (f.get("v") or [])]
        z = []
        for j in range(len(u)):
            row = []
            for i in range(len(u[j])):
                uu = u[j][i]
                vv = v[j][i] if (j < len(v) and i < len(v[j])) else None
                row.append(math.sqrt(uu * uu + vv * vv) if (uu is not None and vv is not None) else None)
            z.append(row)
        axes = payload.get("axes") or {}
        zmeta = payload.get("z") or {}
        options = {
            "axes": {"x": FieldRecipe._axis(axes.get("x")), "y": FieldRecipe._axis(axes.get("y"))},
            "z": {"label": str(zmeta.get("label", "|V|")), "unit": str(zmeta.get("unit", ""))},
            "arrowsOnly": not bool(payload.get("show_magnitude")),
            "contours": False,
            "colormap": payload.get("colormap", "viridis"),
        }
        if payload.get("arrowDensity") is not None:
            options["arrowDensity"] = payload["arrowDensity"]
        if payload.get("zdomain") is not None:
            options["zdomain"] = payload["zdomain"]
        if payload.get("title"):
            options["title"] = str(payload["title"])
        return {"engine": resolved.engine,
                "assets": {"field": {"x": x, "y": y, "z": z, "vectors": {"x": x, "y": y, "u": u, "v": v}}},
                "options": options}

    def structural_requires(self, payload):
        miss = []
        f = payload.get("field") or {}
        x, y, u, v = f.get("x"), f.get("y"), f.get("u"), f.get("v")
        if not (isinstance(x, list) and x and isinstance(y, list) and y
                and isinstance(u, list) and u and isinstance(v, list) and v):
            miss.append({"field": "field", "why": "벡터장 데이터가 없음",
                         "ask": "벡터장을 주세요: field={x:[nx], y:[ny], u:[[ny×nx]], v:[[ny×nx]]}."})
            return miss
        if len(u) != len(y) or len(v) != len(y) or any(len(r) != len(x) for r in u) or any(len(r) != len(x) for r in v):
            miss.append({"field": "field.u/v", "why": "u/v 격자 차원이 x/y와 불일치",
                         "ask": f"u, v 는 각각 {len(y)}행 × {len(x)}열 (y×x) 2D 배열이어야 합니다."})
        for kk in ("x", "y"):
            a = (payload.get("axes") or {}).get(kk) or {}
            if not a.get("label") or "unit" not in a:
                miss.append({"field": f"axes.{kk}", "why": f"{kk}축 위치/단위 미상",
                             "ask": f"{kk}축 위치 좌표와 단위는? (axes.{kk}={{label,unit}}; 무차원이면 unit:'')"})
        return miss


def _signal(payload):
    """Ordered load sequence from signal:[...] or the first series' y / data values."""
    if isinstance(payload.get("signal"), list):
        return [_num(v) for v in payload["signal"]]
    s = (payload.get("series") or [{}])[0]
    if isinstance(s.get("data"), list):
        return [_num(pt[-1] if isinstance(pt, (list, tuple)) else pt) for pt in s["data"]]
    if isinstance(s.get("y"), list):
        return [_num(v) for v in s["y"]]
    return []


class RainflowRecipe(Recipe):
    """Rainflow cycle-count histogram (mean × range) as a field-core heatmap."""

    type_name = "rainflow-cycle-histogram"

    def normalize(self, payload, resolved):
        sig = [v for v in _signal(payload) if v is not None]
        params = payload.get("params") or {}
        mc, rc, Z = fatigue.rainflow_matrix(sig, int(params.get("mean_bins", 12)),
                                            int(params.get("range_bins", 12)))
        load = payload.get("load") or {}
        lbl = str(load.get("label", "Load"))
        unit = str(load.get("unit", ""))
        options = {
            "axes": {"x": {"label": f"Mean {lbl}", "unit": unit},
                     "y": {"label": f"{lbl} range", "unit": unit}},
            "z": {"label": "Cycles", "unit": ""},
            "colormap": payload.get("colormap", "turbo"),
            "contours": False,
        }
        if payload.get("title"):
            options["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"field": {"x": mc, "y": rc, "z": Z}}, "options": options}

    def structural_requires(self, payload):
        miss = []
        if len([v for v in _signal(payload) if v is not None]) < 3:
            miss.append({"field": "signal", "why": "하중 이력이 부족(>=3)",
                         "ask": "하중 시계열을 주세요 (signal:[하중값...] 순서대로, 또는 series:[{data:[[t,load],...]}])."})
        load = payload.get("load") or {}
        if not load.get("label") or "unit" not in load:
            miss.append({"field": "load", "why": "하중 물리량/단위 미상",
                         "ask": "하중(응력/하중) 종류와 단위는? (load={label:'Stress', unit:'MPa'})"})
        return miss
