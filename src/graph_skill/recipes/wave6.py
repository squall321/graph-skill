"""Wave-6 breadth — eye-diagram (field-core fold histogram) + gauge-r-r (AIAG bar)."""

from __future__ import annotations

from ..postprocess import eye, gaugerr
from .base import Recipe
from .base_xy import _num
from .field2d import _signal


class EyeDiagramRecipe(Recipe):
    """Eye diagram — serial waveform folded into a UI-phase × amplitude persistence heatmap."""

    type_name = "eye-diagram"

    def normalize(self, payload, resolved):
        sig = [v for v in _signal(payload) if v is not None]
        params = payload.get("params") or {}
        sps = int(params.get("sps") or params.get("samples_per_symbol") or 0)
        ui = int(params.get("ui", 2))
        ph, amp, z = eye.eye_histogram(sig, sps, ui)
        unit = str((payload.get("axes") or {}).get("y", {}).get("unit", "V"))
        opts = {"axes": {"x": {"label": "Time", "unit": "UI"}, "y": {"label": "Amplitude", "unit": unit}},
                "z": {"label": "Hits", "unit": ""},
                "colormap": payload.get("colormap", "turbo"), "contours": False}
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"field": {"x": ph, "y": amp, "z": z}}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if len([v for v in _signal(payload) if v is not None]) < 8:
            miss.append({"field": "signal", "why": "아이다이어그램용 신호가 부족",
                         "ask": "직렬 파형을 주세요 (signal:[...] 또는 series:[{data:[[t,v]]}])."})
        if not ((payload.get("params") or {}).get("sps") or (payload.get("params") or {}).get("samples_per_symbol")):
            miss.append({"field": "params.sps", "why": "UI당 샘플수(sps)가 필요 → 폴딩 불가",
                         "ask": "심볼(UI)당 샘플 수 sps를 주세요 (예: 32)."})
        return miss


class GaugeRRRecipe(Recipe):
    """Gauge R&R — variance components (EV/AV/GRR/PV) as % study variation, 30% acceptance line."""

    type_name = "gauge-r-r"

    def normalize(self, payload, resolved):
        data = payload.get("measurements")
        res = gaugerr.gauge_rr(data)
        pct = res["pct"]
        cats = ["EV (반복)", "AV (재현)", "GRR", "PV (부품)"]
        vals = [pct["EV"], pct["AV"], pct["GRR"], pct["PV"]]
        title = str(payload.get("title") or "Gauge R&R")
        title += f"  (%GRR={pct['GRR']:.1f}, ndc={res['ndc']:.1f})"
        opts = {"axes": {"x": {"label": "", "unit": "", "log": False, "categories": cats},
                         "y": {"label": "% study variation", "unit": "%", "log": False}},
                "title": title,
                "pluginConfig": {"threshold-lines": {"lines": [
                    {"axis": "y", "value": 30, "label": "30% (한계)", "color": "#dc2626", "dash": [6, 4]},
                    {"axis": "y", "value": 10, "label": "10% (양호)", "color": "#059669", "dash": [4, 4]}]}}}
        colors = ["#2563eb", "#0891b2", "#dc2626", "#059669"]
        series = [{"name": "%SV", "x": list(range(4)), "y": vals, "style": "bar", "color": "#2563eb"}]
        # per-bar color via separate none? keep single color bar for simplicity
        series[0]["color"] = colors[2] if pct["GRR"] > 30 else "#2563eb"
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        m = payload.get("measurements")
        ok = isinstance(m, list) and len(m) >= 2 and isinstance(m[0], list) and m[0] and isinstance(m[0][0], list)
        if not ok:
            return [{"field": "measurements", "why": "부품×작업자×반복 데이터가 없음",
                     "ask": "측정을 주세요 (measurements[part][operator]=[반복 측정값...], 부품>=2·반복>=2)."}]
        return []
