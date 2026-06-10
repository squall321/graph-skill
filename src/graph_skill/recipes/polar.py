"""polar-core recipes — polar-plot / radar-chart / rf-radiation-pattern."""

from __future__ import annotations

from .base import Recipe
from .base_xy import _num


class PolarRecipe(Recipe):
    type_name = "polar-plot"

    def normalize(self, payload, resolved):
        series = []
        for i, s in enumerate(payload.get("series") or []):
            th, rr = [], []
            if isinstance(s.get("theta"), list) and isinstance(s.get("r"), list):
                for t, v in zip(s["theta"], s["r"]):
                    th.append(float(t))
                    rr.append(_num(v))
            else:
                for pt in (s.get("data") or []):
                    if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                        th.append(float(pt[0]))
                        rr.append(_num(pt[1]))
            out = {"name": s.get("name") or f"series {i + 1}", "theta": th, "r": rr,
                   "closed": bool(s.get("closed", payload.get("closed", False)))}
            if s.get("color"):
                out["color"] = str(s["color"])
            series.append(out)
        rad = payload.get("radius") or (payload.get("axes") or {}).get("r") or {}
        options = {"radius": {"label": str(rad.get("label", "")), "unit": str(rad.get("unit", ""))}}
        for k in ("thetaStep", "rmin", "rmax"):
            v = (payload.get("options") or {}).get(k, payload.get(k))
            if v is not None:
                options[k] = v
        if payload.get("title"):
            options["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        miss = []
        if not payload.get("series"):
            miss.append({"field": "series", "why": "극좌표 데이터 없음", "ask": "series:[{theta:[deg], r:[값]}] 형태로 데이터를 주세요."})
        rad = payload.get("radius") or (payload.get("axes") or {}).get("r") or {}
        if not rad.get("label") or "unit" not in rad:
            miss.append({"field": "radius", "why": "반경(값) 의미/단위 미상", "ask": "반경으로 표시할 양과 단위는? (radius={label,unit})"})
        return miss


class RadarRecipe(Recipe):
    type_name = "radar-chart"

    def normalize(self, payload, resolved):
        axes = [str(a) for a in (payload.get("axes_labels") or payload.get("categories") or [])]
        n = max(1, len(axes))
        series = []
        for i, s in enumerate(payload.get("series") or []):
            vals = [_num(v) for v in (s.get("values") or [])]
            out = {"name": s.get("name") or f"series {i + 1}",
                   "theta": [k * 360.0 / n for k in range(len(vals))], "r": vals, "closed": True}
            if s.get("color"):
                out["color"] = str(s["color"])
            series.append(out)
        rad = payload.get("radius") or {}
        options = {"radius": {"label": str(rad.get("label", "")), "unit": str(rad.get("unit", ""))}, "angleLabels": axes}
        if payload.get("rmax") is not None:
            options["rmax"] = payload["rmax"]
        if payload.get("rmin") is not None:
            options["rmin"] = payload["rmin"]
        if payload.get("title"):
            options["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("axes_labels") or payload.get("categories")):
            miss.append({"field": "axes_labels", "why": "레이더 축(항목)이 없음", "ask": "레이더 축(항목 라벨)들을 알려주세요 (axes_labels:[...])."})
        if not payload.get("series"):
            miss.append({"field": "series", "why": "레이더 시리즈가 없음", "ask": "series:[{name, values:[축별 값]}]을 주세요."})
        return miss


class RadiationPatternRecipe(PolarRecipe):
    type_name = "rf-radiation-pattern"

    def normalize(self, payload, resolved):
        p = dict(payload)
        if not p.get("radius"):
            p["radius"] = {"label": "Gain", "unit": "dBi"}
        p.setdefault("closed", True)
        return super().normalize(p, resolved)

    def structural_requires(self, payload):
        if not payload.get("series"):
            return [{"field": "series", "why": "방사패턴 데이터 없음", "ask": "series:[{theta:[deg], r:[gain dBi]}]를 주세요."}]
        return []
