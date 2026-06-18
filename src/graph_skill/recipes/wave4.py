"""Wave-4 breadth (xy-core reuse, on the now visually-verified base) —
pole-zero-map · cusum-chart · goodman-haigh · psd-welch."""

from __future__ import annotations

import math

from ..postprocess import spectral
from .base import Recipe
from .base_xy import _num
from .field2d import _signal


def _axis(a, dlabel="", dunit=""):
    a = a or {}
    return {"label": str(a.get("label", dlabel)), "unit": str(a.get("unit", dunit)),
            "log": a.get("scale", "linear") == "log"}


def _pairs(items):
    out = []
    for p in items or []:
        if isinstance(p, (list, tuple)) and len(p) >= 2:
            a, b = _num(p[0]), _num(p[1])
            if a is not None and b is not None:
                out.append([a, b])
    return out


class PoleZeroRecipe(Recipe):
    """Pole-zero map on the complex plane (equal aspect) — poles ×, zeros ○; s- or z-domain."""

    type_name = "pole-zero-map"

    def normalize(self, payload, resolved):
        poles, zeros = _pairs(payload.get("poles")), _pairs(payload.get("zeros"))
        domain = payload.get("domain", "s")
        markers = [{"x": p[0], "y": p[1], "label": "× pole", "color": "#dc2626"} for p in poles]
        markers += [{"x": z[0], "y": z[1], "label": "○ zero", "color": "#2563eb"} for z in zeros]
        uc = {"circle": domain == "z", "showAxes": True}    # z-domain: unit circle = stability boundary
        opts = {"curve": "straight", "equalAspect": True,
                "axes": {"x": {"label": "Real (σ)" if domain == "s" else "Re", "unit": "", "log": False},
                         "y": {"label": "Imag (jω)" if domain == "s" else "Im", "unit": "", "log": False}},
                "pluginConfig": {"unit-circle": uc, "named-markers": {"markers": markers}}}
        # invisible series to seed the domain so the markers are framed
        xs = [m["x"] for m in markers] or [-1, 1]
        ys = [m["y"] for m in markers] or [-1, 1]
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine,
                "assets": {"series": [{"name": "_pz", "x": xs + [0], "y": ys + [0], "style": "none"}]}, "options": opts}

    def structural_requires(self, payload):
        if not (_pairs(payload.get("poles")) or _pairs(payload.get("zeros"))):
            return [{"field": "poles/zeros", "why": "극점/영점이 없음",
                     "ask": "극점/영점을 주세요 (poles:[[Re,Im],...], zeros:[[Re,Im],...]); domain:'s'|'z'."}]
        return []


class CusumRecipe(Recipe):
    """CUSUM control chart — cumulative deviation from target with ±H decision interval."""

    type_name = "cusum-chart"

    def normalize(self, payload, resolved):
        vals = [_num(v) for v in (payload.get("values") or [])]
        params = payload.get("params") or {}
        target = _num(params.get("target"))
        if target is None:
            fin = [v for v in vals if v is not None]
            target = sum(fin) / len(fin) if fin else 0.0
        sd = _num(params.get("sd")) or 1.0
        k = _num(params.get("k", 0.5)) * sd          # slack
        h = _num(params.get("h", 4)) * sd            # decision interval
        sh, sl, xs, hi, lo = 0.0, 0.0, [], [], []
        for i, v in enumerate(vals):
            d = (v - target) if v is not None else 0.0
            sh = max(0.0, sh + d - k)
            sl = min(0.0, sl + d + k)
            xs.append(i + 1)
            hi.append(sh)
            lo.append(sl)
        ax = payload.get("axes") or {}
        opts = {"curve": "straight",
                "axes": {"x": _axis(ax.get("x"), "Sample #"), "y": _axis(ax.get("y"), "CUSUM")},
                "pluginConfig": {"threshold-lines": {"lines": [
                    {"axis": "y", "value": h, "label": "+H", "color": "#dc2626", "dash": [6, 4]},
                    {"axis": "y", "value": -h, "label": "−H", "color": "#dc2626", "dash": [6, 4]}]}}}
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        series = [{"name": "C+", "x": xs, "y": hi, "style": "line+markers", "color": "#2563eb"},
                  {"name": "C−", "x": xs, "y": lo, "style": "line+markers", "color": "#059669"}]
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("values") or []):
            miss.append({"field": "values", "why": "측정 시퀀스가 없음",
                         "ask": "측정값 시퀀스를 주세요 (values:[...] 순서대로); params.target/sd 권장."})
        ya = (payload.get("axes") or {}).get("y") or {}
        if not ya.get("label"):
            pass  # CUSUM y label defaults; measurement unit optional here
        return miss


class GoodmanRecipe(Recipe):
    """Goodman–Haigh fatigue diagram — mean vs alternating stress + Goodman failure line."""

    type_name = "goodman-haigh"

    def normalize(self, payload, resolved):
        su = _num(payload.get("Su"))
        se = _num(payload.get("Se"))
        pts = _pairs([[p.get("mean"), p.get("alt")] if isinstance(p, dict) else p
                      for p in (payload.get("points") or [])])
        series = []
        if su and se:
            series.append({"name": f"Goodman (Su={su:g}, Se={se:g})", "x": [0, su], "y": [se, 0],
                           "style": "line", "color": "#dc2626", "dash": [6, 4]})
        if pts:
            series.append({"name": "operating", "x": [p[0] for p in pts], "y": [p[1] for p in pts],
                           "style": "markers", "color": "#2563eb"})
        unit = str((payload.get("axes") or {}).get("unit", "MPa"))
        opts = {"curve": "straight",
                "axes": {"x": {"label": "Mean stress σm", "unit": unit, "log": False},
                         "y": {"label": "Alternating stress σa", "unit": unit, "log": False}}}
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("Su") and payload.get("Se")):
            miss.append({"field": "Su/Se", "why": "Goodman 선에 극한강도 Su·피로한도 Se 필요",
                         "ask": "Su(극한강도)와 Se(피로한도)를 주세요. points:[{mean,alt}] 동작점도 함께."})
        # NEVER-invent: 응력 단위를 묵묵히 'MPa'로 채우지 않는다 (Su/Se가 ksi인데 MPa로 오라벨링 차단,
        # stress-linearization 게이트와 동일 정책)
        if "unit" not in (payload.get("axes") or {}):
            miss.append({"field": "axes.unit", "why": "응력 단위 미상 (MPa? ksi?)",
                         "ask": "응력 단위를 axes.unit 으로 주세요 (예: 'MPa'). Su/Se·동작점과 같은 단위계여야 합니다."})
        return miss


class PsdWelchRecipe(Recipe):
    """Power spectral density (Welch) — averaged periodogram, log-log."""

    type_name = "psd-welch"

    def normalize(self, payload, resolved):
        sig = [v for v in _signal(payload) if v is not None]
        params = payload.get("params") or {}
        fs = float(params.get("fs") or payload.get("fs") or 0)
        freqs, psd = spectral.welch(sig, fs, params.get("nperseg"), float(params.get("overlap", 0.5)))
        # drop DC for log-x
        f2 = [f for f in freqs if f > 0]
        p2 = [psd[i] for i in range(len(freqs)) if freqs[i] > 0]
        unit = str((payload.get("z") or {}).get("unit", ""))
        yl = "PSD" + (f" [{unit}²/Hz]" if unit else "")
        opts = {"curve": "straight",
                "axes": {"x": {"label": "Frequency", "unit": "Hz", "log": True},
                         "y": {"label": yl, "unit": "", "log": True}}}
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine,
                "assets": {"series": [{"name": "PSD", "x": f2, "y": p2, "style": "line", "color": "#2563eb"}]},
                "options": opts}

    def structural_requires(self, payload):
        if len([v for v in _signal(payload) if v is not None]) < 4:
            return [{"field": "signal", "why": "PSD 추정용 신호가 부족(>=4)",
                     "ask": "시간신호를 주세요 (signal:[...] 또는 series:[{data:[[t,v]]}]) + params.fs[Hz]."}]
        return []
