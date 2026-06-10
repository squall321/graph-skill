"""Wave-3 — nichols-chart + parallel-coordinates (xy-core) · wind-rose (polar-core) ·
smith-chart (new smith-core family)."""

from __future__ import annotations

import math

from .base import Recipe
from .base_xy import _num


class SmithChartRecipe(Recipe):
    """RF Smith chart — reflection coefficient Γ trajectory (S11) on the smith-core engine."""

    type_name = "smith-chart"

    def normalize(self, payload, resolved):
        series = []
        for i, s in enumerate(payload.get("series") or []):
            g = []
            if isinstance(s.get("data"), list):
                for pt in s["data"]:
                    if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                        a, b = _num(pt[0]), _num(pt[1])
                        if a is not None and b is not None:
                            g.append([a, b])
            elif s.get("mag") and s.get("phase"):
                for m, ph in zip(s["mag"], s["phase"]):
                    mm, pp = _num(m), _num(ph)
                    if mm is not None and pp is not None:
                        a = math.radians(pp)
                        g.append([mm * math.cos(a), mm * math.sin(a)])
            elif s.get("re") and s.get("im"):
                for re, im in zip(s["re"], s["im"]):
                    rr, ii = _num(re), _num(im)
                    if rr is not None and ii is not None:
                        g.append([rr, ii])
            out = {"name": str(s.get("name", f"S11_{i + 1}")), "gamma": g}
            if s.get("color"):
                out["color"] = str(s["color"])
            series.append(out)
        opts = {}
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        ss = payload.get("series") or []
        has = any((s.get("data") or (s.get("mag") and s.get("phase")) or (s.get("re") and s.get("im"))) for s in ss)
        if not has:
            return [{"field": "series", "why": "S11(반사계수) 데이터가 없음",
                     "ask": "S11을 주세요: series:[{name, data:[[Γre, Γim], ...]}] 또는 {mag:[],phase:[deg]} 또는 {re:[],im:[]}."}]
        return []


class WindRoseRecipe(Recipe):
    """Wind/orientation rose — stacked sector wedges per direction (polar-core)."""

    type_name = "wind-rose"

    def normalize(self, payload, resolved):
        labels = payload.get("dir_labels")
        dirs = [float(d) for d in (payload.get("directions") or [])]
        bins = []
        for b in payload.get("bins") or []:
            nb = {"label": str(b.get("label", "")), "counts": [float(c) for c in (b.get("counts") or [])]}
            if b.get("color"):
                nb["color"] = str(b["color"])
            bins.append(nb)
        if not dirs and labels:
            n = len(labels)
            dirs = [i * 360.0 / n for i in range(n)]
        rad = payload.get("radius") or {}
        opts = {"radius": {"label": str(rad.get("label", "빈도")), "unit": str(rad.get("unit", "%"))}}
        if labels:
            opts["angleLabels"] = [str(x) for x in labels]
        else:
            opts["thetaStep"] = payload.get("thetaStep", 45)
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": [], "rose": {"directions": dirs, "bins": bins}}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("directions") or payload.get("dir_labels")):
            miss.append({"field": "directions", "why": "방향(섹터)이 없음",
                         "ask": "방향을 주세요 (directions:[deg...] 또는 dir_labels:['N','NE',...])."})
        if not (payload.get("bins") or []):
            miss.append({"field": "bins", "why": "구간(스택)이 없음",
                         "ask": "구간별 빈도를 주세요 (bins:[{label:'0-5 m/s', counts:[방향별 값...]}, ...])."})
        return miss


class NicholsRecipe(Recipe):
    """Open-loop gain[dB] vs phase[deg] (Nichols) + 0 dB / −180° refs + critical point."""

    type_name = "nichols-chart"

    def normalize(self, payload, resolved):
        series = []
        for i, s in enumerate(payload.get("series") or []):
            ph, gn = [], []
            if isinstance(s.get("data"), list):
                for pt in s["data"]:
                    if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                        a, b = _num(pt[0]), _num(pt[1])
                        if a is not None and b is not None:
                            ph.append(a)
                            gn.append(b)
            else:
                ph = [_num(v) for v in (s.get("phase") or [])]
                gn = [_num(v) for v in (s.get("gain") or [])]
            series.append({"name": str(s.get("name", f"L{i + 1}")), "x": ph, "y": gn, "style": "line+markers"})
        opts = {"curve": "straight",
                "axes": {"x": {"label": "Open-loop phase", "unit": "deg", "log": False},
                         "y": {"label": "Open-loop gain", "unit": "dB", "log": False}},
                "pluginConfig": {
                    "threshold-lines": {"lines": [
                        {"axis": "x", "value": -180, "label": "−180°", "color": "#dc2626", "dash": [6, 4]},
                        {"axis": "y", "value": 0, "label": "0 dB", "color": "#059669", "dash": [6, 4]}]},
                    "named-markers": {"markers": [{"x": -180, "y": 0, "label": "crit", "color": "#dc2626"}]}}}
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        ss = payload.get("series") or []
        has = any((s.get("data") or s.get("phase")) for s in ss)
        if not has:
            return [{"field": "series", "why": "Nichols 궤적이 없음",
                     "ask": "개루프 궤적을 주세요 (series:[{name, data:[[phase_deg, gain_dB], ...]}] 또는 {phase:[],gain:[]})."}]
        return []


class ParallelCoordinatesRecipe(Recipe):
    """Parallel coordinates — N normalized vertical axes + one polyline per observation."""

    type_name = "parallel-coordinates"

    def normalize(self, payload, resolved):
        variables = payload.get("variables") or {}
        names = list(variables.keys())
        cols = [[_num(v) for v in variables[n]] for n in names]
        nrows = min((len(c) for c in cols), default=0)
        dims = []
        for c in cols:
            vals = [v for v in c[:nrows] if v is not None]
            mn = min(vals) if vals else 0.0
            mx = max(vals) if vals else 1.0
            if mx <= mn:
                mx = mn + 1.0
            dims.append({"min": mn, "max": mx})
        rows = []
        for r in range(nrows):
            row = []
            for ci, c in enumerate(cols):
                v = c[r]
                row.append((v - dims[ci]["min"]) / (dims[ci]["max"] - dims[ci]["min"]) if v is not None else 0.0)
            rows.append(row)
        pdims = [{"name": names[i], "min": dims[i]["min"], "max": dims[i]["max"]} for i in range(len(names))]
        xa = {"label": "", "unit": "", "categories": names}
        dx, dy = [], []
        for i in range(len(names)):
            dx += [i, i]
            dy += [0.0, 1.0]
        opts = {"axes": {"x": xa, "y": {"label": "정규화 (0–1)", "unit": "", "log": False}},
                "hideAxes": True, "pad": {"left": 28, "right": 28, "bottom": 18},
                "pluginConfig": {"parcoord": {"dims": pdims, "rows": rows}}}
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine,
                "assets": {"series": [{"name": "_pc", "x": dx, "y": dy, "style": "none"}]}, "options": opts}

    def structural_requires(self, payload):
        variables = payload.get("variables") or {}
        if len(variables) < 2:
            return [{"field": "variables", "why": "평행좌표는 변수 2개 이상 필요",
                     "ask": "변수별 값을 주세요 (variables:{이름:[값...], ...}, 2개 이상, 같은 길이)."}]
        return []
