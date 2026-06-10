"""Control-system loci (xy-core, complex plane) — nyquist-plot + root-locus.

Both need equal aspect (so circles/distances read true) + the unit-circle plugin (origin axes,
unit circle). Nyquist marks the −1 critical point; root-locus marks open-loop poles/zeros.
"""

from __future__ import annotations

from .base import Recipe
from .base_xy import _num


def _reim(s: dict):
    """Extract (Re[], Im[]) from a series given as data=[[Re,Im],...] or {real:[],imag:[]}."""
    if isinstance(s.get("data"), list):
        re_, im = [], []
        for pt in s["data"]:
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                a, b = _num(pt[0]), _num(pt[1])
                if a is not None and b is not None:
                    re_.append(a)
                    im.append(b)
        return re_, im
    re_ = [_num(v) for v in (s.get("real") or [])]
    im = [_num(v) for v in (s.get("imag") or [])]
    return re_, im


class NyquistRecipe(Recipe):
    """Open-loop frequency response in the complex plane + unit circle + −1 critical point."""

    type_name = "nyquist-plot"

    def normalize(self, payload, resolved):
        series = []
        for i, s in enumerate(payload.get("series") or []):
            re_, im = _reim(s)
            out = {"name": str(s.get("name", f"G{i+1}")), "x": re_, "y": im, "style": "line+markers"}
            if s.get("color"):
                out["color"] = str(s["color"])
            series.append(out)
        opts = {
            "curve": "straight", "equalAspect": True,
            "axes": {"x": {"label": "Real axis", "unit": "", "log": False},
                     "y": {"label": "Imaginary axis", "unit": "", "log": False}},
            "pluginConfig": {
                "unit-circle": {"circle": True, "radius": 1, "showAxes": True},
                "named-markers": {"markers": [{"x": -1, "y": 0, "label": "−1", "color": "#dc2626"}]},
            },
        }
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        ss = payload.get("series") or []
        ok = any(_reim(s)[0] for s in ss)
        if not ok:
            return [{"field": "series", "why": "Nyquist 궤적이 없음",
                     "ask": "개루프 주파수응답 궤적을 주세요 (series:[{name, data:[[Re,Im],...]}] 또는 {real:[],imag:[]})."}]
        return []


class RootLocusRecipe(Recipe):
    """Closed-loop pole loci vs gain K + open-loop poles(×)/zeros(○); imag axis = stability bound."""

    type_name = "root-locus"

    def normalize(self, payload, resolved):
        series = []
        for i, s in enumerate(payload.get("series") or payload.get("branches") or []):
            re_, im = _reim(s)
            series.append({"name": str(s.get("name", f"branch{i+1}")), "x": re_, "y": im, "style": "markers"})
        markers = []
        for p in payload.get("poles") or []:
            a, b = _num(p[0]), _num(p[1])
            if a is not None and b is not None:
                markers.append({"x": a, "y": b, "label": "× pole", "color": "#dc2626"})
        for z in payload.get("zeros") or []:
            a, b = _num(z[0]), _num(z[1])
            if a is not None and b is not None:
                markers.append({"x": a, "y": b, "label": "○ zero", "color": "#2563eb"})
        opts = {
            "curve": "straight", "equalAspect": True,
            "axes": {"x": {"label": "Real (σ)", "unit": "", "log": False},
                     "y": {"label": "Imaginary (jω)", "unit": "", "log": False}},
            "pluginConfig": {
                "unit-circle": {"circle": False, "showAxes": True},
                "named-markers": {"markers": markers},
            },
        }
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        has_branch = any(_reim(s)[0] for s in (payload.get("series") or payload.get("branches") or []))
        if not has_branch and not (payload.get("poles") or []):
            return [{"field": "series/poles", "why": "근궤적 데이터가 없음",
                     "ask": "근궤적 가지(series:[{name,data:[[Re,Im],...]}])와 개루프 poles/zeros([[Re,Im],...])를 주세요."}]
        return []
