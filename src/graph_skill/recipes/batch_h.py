"""Batch H (no-new-plugin subset) — reliability / SPC / fatigue / controls / modal-correlation.

process-capability-hist · paris-crack-growth · campbell-diagram (xy-core) ·
mac-matrix-heatmap (field-core) · kaplan-meier-survival (xy-core).
Reuses existing engines + plugins (histogram/threshold-lines/named-markers/step/heatmap-grid)
plus postprocess (stats.capability, reliability.kaplan_meier). No new engine, no new plugin.
"""

from __future__ import annotations

import math

from ..postprocess import reliability, stats
from .base import Recipe
from .base_xy import BaseXYRecipe, _num


def _axis(a, dlabel="", dunit=""):
    a = a or {}
    return {"label": str(a.get("label", dlabel)), "unit": str(a.get("unit", dunit)),
            "log": a.get("scale", "linear") == "log"}


def _vals(payload):
    return [v for v in (_num(x) for x in (payload.get("values") or [])) if v is not None]


class ProcessCapabilityRecipe(Recipe):
    """Histogram + USL/LSL/Target spec lines + normal fit overlay; Cp/Cpk in the title."""

    type_name = "process-capability-hist"

    def normalize(self, payload, resolved):
        vals = _vals(payload)
        params = payload.get("params") or {}
        usl, lsl, tgt = _num(params.get("USL")), _num(params.get("LSL")), _num(params.get("target"))
        centers, counts, w = stats.histogram(vals, params.get("bins"))
        cap = stats.capability(vals, usl, lsl)
        mean, sd = cap["mean"], cap["sd"]
        series = [{"name": "count", "x": centers, "y": counts, "style": "bar", "color": "#2563eb"}]
        if sd > 0 and centers and w > 0:
            lo, hi, tot = centers[0] - w / 2, centers[-1] + w / 2, len(vals) * w
            fx, fy = [], []
            for k in range(81):
                xx = lo + (hi - lo) * k / 80
                fy.append(math.exp(-((xx - mean) ** 2) / (2 * sd * sd)) / (sd * math.sqrt(2 * math.pi)) * tot)
                fx.append(xx)
            series.append({"name": "normal fit", "x": fx, "y": fy, "style": "line", "color": "#dc2626"})
        lines = []
        if usl is not None:
            lines.append({"axis": "x", "value": usl, "label": "USL", "color": "#dc2626", "dash": [6, 4]})
        if lsl is not None:
            lines.append({"axis": "x", "value": lsl, "label": "LSL", "color": "#dc2626", "dash": [6, 4]})
        if tgt is not None:
            lines.append({"axis": "x", "value": tgt, "label": "Target", "color": "#059669", "dash": [4, 4]})
        title = str(payload.get("title") or "Process capability")
        if cap["cp"] is not None and cap["cpk"] is not None:
            title += f"  (Cp={cap['cp']:.2f}, Cpk={cap['cpk']:.2f})"
        elif cap["cpk"] is not None:
            title += f"  (Cpk={cap['cpk']:.2f})"
        opts = {"axes": {"x": _axis((payload.get("axes") or {}).get("x")),
                         "y": {"label": "Frequency", "unit": "", "log": False}},
                "title": title, "pluginConfig": {"threshold-lines": {"lines": lines}}}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if not _vals(payload):
            miss.append({"field": "values", "why": "측정값이 없음",
                         "ask": "공정능력을 볼 측정값들을 주세요 (values:[...])."})
        params = payload.get("params") or {}
        if params.get("USL") is None and params.get("LSL") is None:
            miss.append({"field": "params.USL/LSL", "why": "규격한계가 없음 → Cp/Cpk 계산 불가",
                         "ask": "규격상한/하한을 주세요 (params.USL, params.LSL; 한쪽만 있어도 됨)."})
        xa = (payload.get("axes") or {}).get("x") or {}
        if not xa.get("label") or "unit" not in xa:
            miss.append({"field": "axes.x", "why": "측정 특성(x) 의미/단위 미상",
                         "ask": "측정 특성과 단위는? (axes.x={label,unit})"})
        return miss


class ParisCrackRecipe(Recipe):
    """da/dN vs ΔK on log-log + power-law (Paris) fit line + ΔKth/KIC vertical lines."""

    type_name = "paris-crack-growth"
    _base = BaseXYRecipe()

    def normalize(self, payload, resolved):
        norm = self._base.normalize(payload, resolved)
        ax = norm["options"]["axes"]
        ax["x"]["log"] = True
        ax["y"]["log"] = True
        if not ax["x"].get("label"):
            ax["x"]["label"] = "ΔK"
        if not ax["y"].get("label"):
            ax["y"]["label"] = "da/dN"
        # power-law fit (linear in log-log) on series 0 → Paris exponent m
        s0 = (norm["assets"]["series"] or [{}])[0]
        pts = [(x, y) for x, y in zip(s0.get("x", []), s0.get("y", [])) if x and y and x > 0 and y > 0]
        if len(pts) >= 2:
            lx = [math.log10(x) for x, _ in pts]
            ly = [math.log10(y) for _, y in pts]
            n = len(lx)
            sx, sy = sum(lx), sum(ly)
            sxx = sum(v * v for v in lx)
            sxy = sum(lx[i] * ly[i] for i in range(n))
            d = n * sxx - sx * sx
            if d != 0:
                m = (n * sxy - sx * sy) / d
                b = (sy - m * sx) / n
                xs = sorted(x for x, _ in pts)
                fx = [xs[0], xs[-1]]
                fy = [10 ** (b + m * math.log10(x)) for x in fx]
                norm["assets"]["series"].append(
                    {"name": f"Paris fit (m={m:.2f})", "x": fx, "y": fy, "style": "line",
                     "color": "#dc2626", "dash": [5, 4]})
        lines = []
        dkth, kic = _num(payload.get("dKth")), _num(payload.get("KIC"))
        if dkth is not None:
            lines.append({"axis": "x", "value": dkth, "label": "ΔKth", "color": "#059669", "dash": [6, 4]})
        if kic is not None:
            lines.append({"axis": "x", "value": kic, "label": "KIC", "color": "#dc2626", "dash": [6, 4]})
        if lines:
            norm["options"].setdefault("pluginConfig", {})["threshold-lines"] = {"lines": lines}
        return norm

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("series") or []):
            miss.append({"field": "series", "why": "균열성장 데이터가 없음",
                         "ask": "균열성장을 주세요 (series:[{name, data:[[ΔK, da/dN], ...]}]); x=ΔK, y=da/dN."})
        ya = (payload.get("axes") or {}).get("y") or {}
        if not ya.get("label") or "unit" not in ya:
            miss.append({"field": "axes.y", "why": "da/dN(y) 단위 미상",
                         "ask": "da/dN의 단위는? (axes.y={label:'da/dN', unit:'mm/cycle'}); axes.x=ΔK{unit:'MPa√m'}"})
        return miss


class CampbellRecipe(Recipe):
    """Rotor Campbell diagram: natural-frequency lines vs speed + engine-order rays (k·rpm/60)."""

    type_name = "campbell-diagram"

    def normalize(self, payload, resolved):
        modes = payload.get("modes") or []
        series = []
        for mo in modes:
            xs, ys = [], []
            for pt in mo.get("data") or []:
                xs.append(float(pt[0]))
                ys.append(_num(pt[1]))
            series.append({"name": str(mo.get("name", "mode")), "x": xs, "y": ys, "style": "line+markers"})
        rr = payload.get("rpm_range")
        if not rr:
            allr = [x for s in series for x in s["x"]]
            rr = [min(allr), max(allr)] if allr else [0.0, 1000.0]
        for o in payload.get("orders") or []:
            o = float(o)
            tag = str(int(o)) if o == int(o) else str(o)
            series.append({"name": f"{tag}X", "x": [rr[0], rr[1]],
                           "y": [o * rr[0] / 60.0, o * rr[1] / 60.0], "style": "line",
                           "dash": [5, 4], "color": "#888"})
        ax = payload.get("axes") or {}
        opts = {"curve": "straight",
                "axes": {"x": _axis(ax.get("x"), "Rotational speed", "rpm"),
                         "y": _axis(ax.get("y"), "Frequency", "Hz")}}
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        if not (payload.get("modes") or []):
            return [{"field": "modes", "why": "고유진동수 곡선이 없음",
                     "ask": "모드별 곡선을 주세요 (modes:[{name, data:[[rpm, freq_Hz], ...]}]); orders:[1,2,..] 선택."}]
        return []


class MACMatrixRecipe(Recipe):
    """Modal Assurance Criterion N×N matrix as a [0,1] heatmap (field-core)."""

    type_name = "mac-matrix-heatmap"

    def normalize(self, payload, resolved):
        mat = payload.get("matrix") or []
        ny = len(mat)
        nx = len(mat[0]) if mat else 0
        field = {"x": list(range(nx)), "y": list(range(ny)),
                 "z": [[_num(c) for c in (row or [])] for row in mat]}
        opts = {"axes": {"x": {"label": str(payload.get("axis_x_label", "Mode (test)")), "unit": ""},
                         "y": {"label": str(payload.get("axis_y_label", "Mode (analysis)")), "unit": ""}},
                "z": {"label": "MAC", "unit": ""},
                "colormap": payload.get("colormap", "viridis"), "zdomain": [0, 1], "contours": False}
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"field": field}, "options": opts}

    def structural_requires(self, payload):
        mat = payload.get("matrix") or []
        if not mat or not isinstance(mat[0], list):
            return [{"field": "matrix", "why": "MAC 행렬이 없음",
                     "ask": "MAC 행렬을 주세요 (matrix:[[...], ...], 0~1 값의 N×M 2D 배열)."}]
        nx = len(mat[0])
        if any(not isinstance(r, list) or len(r) != nx for r in mat):
            return [{"field": "matrix", "why": "행 길이 불일치",
                     "ask": "matrix의 모든 행 길이를 동일하게 맞춰주세요."}]
        return []


class WeibullRecipe(Recipe):
    """Weibull probability plot — linearized failure data + median-rank fit line (β, η in title)."""

    type_name = "weibull-prob-paper"

    def normalize(self, payload, resolved):
        vals = _vals(payload)
        fit = reliability.weibull_fit(vals)
        xs, Y = fit["x"], fit["Y"]
        series = [{"name": "data", "x": xs, "y": Y, "style": "markers", "color": "#2563eb"}]
        x0, x1 = xs[0], xs[-1]
        fy = [fit["beta"] * math.log(x0) + fit["intercept"], fit["beta"] * math.log(x1) + fit["intercept"]]
        series.append({"name": f"fit (β={fit['beta']:.2f})", "x": [x0, x1], "y": fy,
                       "style": "line", "color": "#dc2626", "dash": [5, 4]})
        ax = (payload.get("axes") or {}).get("x") or {}
        title = str(payload.get("title") or "Weibull probability plot")
        title += f"  (β={fit['beta']:.2f}, η={fit['eta']:.0f}, R²={fit['r2']:.3f})"
        opts = {"curve": "straight",
                "axes": {"x": {"label": str(ax.get("label", "Life")), "unit": str(ax.get("unit", "")), "log": True},
                         "y": {"label": "ln(−ln(1−F))", "unit": "", "log": False}},
                "title": title}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if len([v for v in _vals(payload) if v is not None and v > 0]) < 2:
            miss.append({"field": "values", "why": "Weibull 적합에 고장 데이터 부족(>=2, 양수)",
                         "ask": "고장(수명) 데이터를 주세요 (values:[...], 양수 2개 이상)."})
        xa = (payload.get("axes") or {}).get("x") or {}
        if not xa.get("label") or "unit" not in xa:
            miss.append({"field": "axes.x", "why": "수명(x) 의미/단위 미상",
                         "ask": "수명 변수와 단위는? (axes.x={label:'Life', unit:'cycles' 또는 'h'})"})
        return miss


class KaplanMeierRecipe(Recipe):
    """Kaplan-Meier survival step curve(s) + censoring tick markers."""

    type_name = "kaplan-meier-survival"

    def normalize(self, payload, resolved):
        markers = []
        series = []
        palette = ["#2563eb", "#dc2626", "#059669", "#9333ea", "#d97706"]

        def add(name, durs, evs, ci):
            ts, surv, cens = reliability.kaplan_meier(durs, evs)
            color = palette[ci % len(palette)]
            series.append({"name": name, "x": ts, "y": surv, "style": "line", "color": color})
            for t, sv in cens:
                markers.append({"x": t, "y": sv, "label": "+censored", "color": color})

        groups = payload.get("groups")
        if groups:
            for i, g in enumerate(groups):
                add(str(g.get("label", f"group{i+1}")), g.get("durations") or [], g.get("events") or [], i)
        else:
            add("survival", payload.get("durations") or [], payload.get("events") or [], 0)
        ax = payload.get("axes") or {}
        opts = {"curve": "step",
                "axes": {"x": _axis(ax.get("x"), "Time"),
                         "y": {"label": "Survival S(t)", "unit": "", "log": False}},
                "pluginConfig": {"named-markers": {"markers": markers}}}
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        groups = payload.get("groups")
        has = bool(groups) or bool(payload.get("durations"))
        miss = []
        if not has:
            miss.append({"field": "durations", "why": "수명/중도절단 데이터가 없음",
                         "ask": "수명 데이터를 주세요 (durations:[...], events:[1=고장,0=중도절단]) 또는 groups:[{label,durations,events}]."})
        xa = (payload.get("axes") or {}).get("x") or {}
        if not xa.get("label") or "unit" not in xa:
            miss.append({"field": "axes.x", "why": "시간(x) 단위 미상",
                         "ask": "수명 시간축 단위는? (axes.x={label:'Time', unit:'h' 또는 'cycles'})"})
        return miss
