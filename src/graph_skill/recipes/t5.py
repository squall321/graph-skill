"""엔진-오버레이 정형 그래프 5종 — eye-mask-compliance/efficiency-map/rpm-order-map
(field-core 오버레이 레이어 재사용) + psychrometric-chart/distribution-fit-compare(순수 레시피).
field-core에 추가한 범용 overlays(curves/markers/polygons) 레이어를 쓴다."""

from __future__ import annotations

from ..postprocess import domain_t5 as _t5
from ..postprocess import eye
from .base import Recipe
from .field2d import _signal
from .matrix_compare import MatrixRecipe


def _fmt(v, nd=3):
    return "—" if v is None else f"{v:.{nd}g}"


def _hex_mask(w, h, cx=0.5):
    """육각 아이마스크 (아이 개구부 중심 cx, UI ±w/2, 진폭 ±h/2)."""
    return [[cx - w / 2, 0], [cx - w / 4, h / 2], [cx + w / 4, h / 2],
            [cx + w / 2, 0], [cx + w / 4, -h / 2], [cx - w / 4, -h / 2]]


class EyeMaskComplianceRecipe(Recipe):
    type_name = "eye-mask-compliance"

    def normalize(self, payload, resolved):
        sig = [v for v in _signal(payload) if v is not None]
        params = payload.get("params") or {}
        sps = int(params.get("sps") or params.get("samples_per_symbol") or 0)
        ui = int(params.get("ui", 2))
        ph, amp, z = eye.eye_histogram(sig, sps, ui)
        mask = payload.get("mask") or {}
        polys = mask.get("polygons")
        if not polys:
            polys = [_hex_mask(float(mask.get("width", 0.5)), float(mask.get("height", 0.5)))]
        hit = _t5.eye_mask_hits(ph, amp, z, polys)
        verdict = "PASS" if hit["hits"] == 0 else "FAIL"
        overlays = {"polygons": [{"points": p, "color": "#dc2626"} for p in polys]}
        unit = str((payload.get("axes") or {}).get("y", {}).get("unit", "V"))
        opts = {"axes": {"x": {"label": "Time", "unit": "UI"}, "y": {"label": "Amplitude", "unit": unit}},
                "z": {"label": "Hits", "unit": ""}, "colormap": payload.get("colormap", "turbo"), "contours": False,
                "title": f"{payload.get('title') or '아이 마스크 판정'} — 마스크 히트 {int(hit['hits'])} [{verdict}]"}
        return {"engine": resolved.engine,
                "assets": {"field": {"x": ph, "y": amp, "z": z, "overlays": overlays}}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if len([v for v in _signal(payload) if v is not None]) < 8:
            miss.append({"field": "signal", "why": "아이다이어그램용 신호가 부족",
                         "ask": "직렬 파형을 주세요 (signal:[...] 또는 series:[{data:[[t,v]]}])."})
        if not ((payload.get("params") or {}).get("sps") or (payload.get("params") or {}).get("samples_per_symbol")):
            miss.append({"field": "params.sps", "why": "UI당 샘플수(sps) 필요",
                         "ask": "심볼(UI)당 샘플 수 sps를 주세요 (예: 32)."})
        return miss


class EfficiencyMapRecipe(Recipe):
    type_name = "efficiency-map"

    def normalize(self, payload, resolved):
        field = payload["field"]
        overlays = {}
        env = payload.get("envelope")
        if env:
            overlays["curves"] = [{"name": "최대토크 외곽선", "points": [[float(p[0]), float(p[1])] for p in env],
                                   "color": "#dc2626", "width": 2.4}]
        pts = payload.get("points") or []
        if pts:
            overlays["markers"] = [{"x": float(p["rpm"]), "y": float(p["torque"]),
                                    "label": str(p.get("label", "")), "color": "#111827"} for p in pts]
        ax = payload.get("axes") or {}
        opts = {"axes": {"x": {"label": "회전수", "unit": str((ax.get("x") or {}).get("unit", "rpm"))},
                         "y": {"label": "토크", "unit": str((ax.get("y") or {}).get("unit", "Nm"))}},
                "z": {"label": "효율", "unit": "%"}, "colormap": payload.get("colormap", "viridis"), "contours": True,
                "title": str(payload.get("title") or "효율 맵 (등효율 컨투어)")}
        fld = {"x": [float(v) for v in field["x"]], "y": [float(v) for v in field["y"]],
               "z": [[float(c) for c in row] for row in field["z"]]}
        if overlays:
            fld["overlays"] = overlays
        return {"engine": resolved.engine, "assets": {"field": fld}, "options": opts}

    def structural_requires(self, payload):
        f = payload.get("field") or {}
        if not f.get("x") or not f.get("y") or not f.get("z"):
            return [{"field": "field", "why": "효율 격자가 없음",
                     "ask": "field:{x:[rpm], y:[Nm], z:[[효율%]]} 를 주세요 (+envelope:[[rpm,Nm]], points:[{rpm,torque,label}])."}]
        return []


class RPMOrderMapRecipe(Recipe):
    type_name = "rpm-order-map"

    def normalize(self, payload, resolved):
        field = payload["field"]
        rpm = [float(v) for v in field["x"]]
        orders = payload.get("orders") or [1, 2, 4]
        curves = []
        pal = ["#ffffff", "#fde047", "#f97316", "#ef4444", "#a855f7"]
        for k, o in enumerate(orders):
            pts = [[r, o * r / 60.0] for r in rpm]
            curves.append({"name": f"{o}차", "points": pts, "color": pal[k % len(pal)], "width": 1.6, "dash": [5, 4]})
        ax = payload.get("axes") or {}
        opts = {"axes": {"x": {"label": "회전수", "unit": str((ax.get("x") or {}).get("unit", "rpm"))},
                         "y": {"label": "주파수", "unit": "Hz"}},
                "z": {"label": "진폭", "unit": str((payload.get("z") or {}).get("unit", "dB"))},
                "colormap": payload.get("colormap", "turbo"), "contours": False,
                "title": str(payload.get("title") or "RPM 오더 맵")}
        fld = {"x": rpm, "y": [float(v) for v in field["y"]],
               "z": [[float(c) for c in row] for row in field["z"]], "overlays": {"curves": curves}}
        return {"engine": resolved.engine, "assets": {"field": fld}, "options": opts}

    def structural_requires(self, payload):
        f = payload.get("field") or {}
        if not f.get("x") or not f.get("y") or not f.get("z"):
            return [{"field": "field", "why": "스펙트럼 행렬이 없음",
                     "ask": "field:{x:[rpm], y:[Hz], z:[[진폭]]} 를 주세요 (+orders:[1,2,4])."}]
        return []


class PsychrometricRecipe(Recipe):
    type_name = "psychrometric-chart"

    def normalize(self, payload, resolved):
        t_lo, t_hi = float(payload.get("t_lo", 0)), float(payload.get("t_hi", 45))
        p = float(payload.get("pressure", 101325))
        series = [{"name": "포화선 (100%)", "x": [r[0] for r in _t5.saturation_curve(t_lo, t_hi, p)],
                   "y": [r[1] for r in _t5.saturation_curve(t_lo, t_hi, p)], "color": "#2563eb"}]
        for rh in (0.2, 0.4, 0.6, 0.8):
            cv = _t5.rh_curve(rh, t_lo, t_hi, p)
            series.append({"name": f"{int(rh * 100)}% RH", "x": [r[0] for r in cv], "y": [r[1] for r in cv],
                           "color": "#94a3b8", "dash": [4, 4]})
        pts = payload.get("points") or []
        if pts:
            px, py = [], []
            for pt in pts:
                tdb = float(pt["tdb"])
                w = float(pt["w"]) if pt.get("w") is not None else _t5.humidity_ratio(tdb, float(pt.get("rh", 0.5)), p) * 1000.0
                px.append(tdb)
                py.append(w)
            series.append({"name": "상태점", "x": px, "y": py, "style": "markers", "color": "#dc2626"})
        opts = {"axes": {"x": {"label": "건구온도 Tdb", "unit": "°C"}, "y": {"label": "절대습도 W", "unit": "g/kg"}},
                "title": str(payload.get("title") or "습공기선도 (ASHRAE)")}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        return []


class DistributionFitRecipe(Recipe):
    type_name = "distribution-fit-compare"
    _matrix = MatrixRecipe()

    _LAB = {"weibull": ("Weibull", "ln(t)", "ln(−ln(1−F))"), "lognormal": ("Lognormal", "ln(t)", "Φ⁻¹(F)"),
            "normal": ("Normal", "t", "Φ⁻¹(F)"), "exponential": ("Exponential", "t", "−ln(1−F)")}

    def normalize(self, payload, resolved):
        vals = [float(v) for v in payload["values"]]
        dists = payload.get("distributions") or ["weibull", "lognormal", "normal", "exponential"]
        ranked = []
        for d in dists:
            pp = _t5.prob_plot(vals, d)
            ranked.append((d, pp))
        best = max(ranked, key=lambda r: r[1]["r2"])[0]
        items = []
        for d, pp in ranked:
            name, xl, yl = self._LAB.get(d, (d, "x", "y"))
            xs = pp["x"]
            fit = pp["fit"]
            line = {"name": "적합", "x": [xs[0], xs[-1]],
                    "y": [fit["slope"] * xs[0] + fit["intercept"], fit["slope"] * xs[-1] + fit["intercept"]],
                    "color": "#16a34a", "dash": [5, 4]}
            gp = {"axes": {"x": {"label": xl, "unit": ""}, "y": {"label": yl, "unit": ""}},
                  "series": [{"name": name, "x": xs, "y": pp["y"], "style": "markers", "color": "#2563eb"}, line]}
            star = " ★최적" if d == best else ""
            items.append({"id": d, "label": f"{name} (R²={_fmt(pp['r2'])}){star}", "type": "graph",
                          "cells": {"t": {"kind": "graph", "graph_ref": {"type": "base-xy", "payload": gp}}}})
        mp = {"title": f"{payload.get('title') or '수명분포 적합 비교'} — 최적: {self._LAB.get(best, (best,))[0]}",
              "states": [{"id": "t", "label": ""}], "items": items, "options": {"diff": False}}
        return self._matrix.normalize(mp, resolved)

    def structural_requires(self, payload):
        if len(payload.get("values") or []) < 3:
            return [{"field": "values", "why": "분포적합용 데이터 부족",
                     "ask": "values:[수명/측정값…] 를 주세요 (3개 이상, +distributions:[…])."}]
        return []
