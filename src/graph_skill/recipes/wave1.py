"""Wave-1 expansion (no engine/plugin change) — pdf-kde / ridgeline (xy-core) ·
spectrogram (field-core heatmap, STFT) · scatter-matrix (review-matrix SPLOM embed).
All reuse existing engines + postprocess (stats.kde, spectral.spectrogram)."""

from __future__ import annotations

from ..postprocess import spectral, stats
from .base import Recipe
from .base_xy import _num
from .field2d import _signal
from .matrix_compare import MatrixRecipe, inject_plugin as _inject_plugin


def _axis(a, dlabel=""):
    a = a or {}
    return {"label": str(a.get("label", dlabel)), "unit": str(a.get("unit", "")),
            "log": a.get("scale", "linear") == "log"}


class PdfKdeRecipe(Recipe):
    """Kernel-density (smooth PDF) of one variable, or several overlaid groups."""

    type_name = "pdf-kde"

    def normalize(self, payload, resolved):
        groups = payload.get("groups")
        series = []
        if groups:
            for g in groups:
                xs, dens = stats.kde([_num(v) for v in (g.get("values") or []) if _num(v) is not None])
                series.append({"name": str(g.get("label", "group")), "x": xs, "y": dens, "style": "line"})
        else:
            xs, dens = stats.kde([_num(v) for v in (payload.get("values") or []) if _num(v) is not None])
            series.append({"name": "density", "x": xs, "y": dens, "style": "line", "color": "#2563eb"})
        ax = payload.get("axes") or {}
        opts = {"curve": "smooth",
                "axes": {"x": _axis(ax.get("x")), "y": {"label": "Density", "unit": "", "log": False}}}
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        has = bool(payload.get("groups")) or bool(payload.get("values"))
        if not has:
            miss.append({"field": "values", "why": "분포를 추정할 값이 없음",
                         "ask": "KDE로 추정할 값들을 주세요 (values:[...] 또는 groups:[{label,values}])."})
        xa = (payload.get("axes") or {}).get("x") or {}
        if not xa.get("label") or "unit" not in xa:
            miss.append({"field": "axes.x", "why": "변수(x)의 의미/단위 미상",
                         "ask": "분포 변수와 단위는? (axes.x={label,unit}; 무차원이면 unit:'')"})
        return miss


class RidgelineRecipe(Recipe):
    """Stacked density ridges — one KDE per group, vertically offset (joyplot)."""

    type_name = "ridgeline"

    def normalize(self, payload, resolved):
        groups = payload.get("groups") or []
        kdes = []
        for g in groups:
            xs, dens = stats.kde([_num(v) for v in (g.get("values") or []) if _num(v) is not None])
            kdes.append((str(g.get("label", "")), xs, dens))
        gmax = max((max(d) if d else 0.0) for _, _, d in kdes) or 1.0
        amp, spacing = 0.9, 1.0
        series = []
        for i, (lbl, xs, dens) in enumerate(kdes):
            base = i * spacing
            series.append({"name": lbl, "x": xs, "y": [base + d / gmax * amp for d in dens], "style": "line"})
        ax = payload.get("axes") or {}
        opts = {"curve": "smooth",
                "axes": {"x": _axis(ax.get("x")), "y": {"label": "그룹 (오프셋)", "unit": "", "log": False}}}
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if len(payload.get("groups") or []) < 2:
            miss.append({"field": "groups", "why": "능선도는 그룹(>=2)이 필요",
                         "ask": "그룹들을 주세요 (groups:[{label, values:[...]}, ...], 2개 이상)."})
        xa = (payload.get("axes") or {}).get("x") or {}
        if not xa.get("label") or "unit" not in xa:
            miss.append({"field": "axes.x", "why": "변수(x) 의미/단위 미상",
                         "ask": "분포 변수와 단위는? (axes.x={label,unit})"})
        return miss


class SpectrogramRecipe(Recipe):
    """Time-frequency STFT magnitude as a field-core heatmap (time × freq)."""

    type_name = "spectrogram"

    def normalize(self, payload, resolved):
        sig = [v for v in _signal(payload) if v is not None]
        params = payload.get("params") or {}
        fs = float(params.get("fs") or payload.get("fs") or 0)
        times, freqs, z = spectral.spectrogram(sig, fs, params.get("nperseg"),
                                               float(params.get("overlap", 0.5)))
        ax = payload.get("axes") or {}
        amp_unit = str((payload.get("z") or {}).get("unit", ""))
        opts = {"axes": {"x": {"label": str((ax.get("x") or {}).get("label", "Time")), "unit": "s"},
                         "y": {"label": "Frequency", "unit": "Hz"}},
                "z": {"label": "Amplitude", "unit": amp_unit},
                "colormap": payload.get("colormap", "turbo"), "contours": False}
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"field": {"x": times, "y": freqs, "z": z}}, "options": opts}

    def structural_requires(self, payload):
        if len([v for v in _signal(payload) if v is not None]) < 4:
            return [{"field": "signal", "why": "STFT용 신호가 부족(>=4)",
                     "ask": "시간신호를 주세요 (signal:[...] 또는 series:[{data:[[t,v]]}]) + params.fs[Hz]."}]
        return []


class ScatterMatrixRecipe(Recipe):
    """Scatter-plot matrix (SPLOM) — pairwise scatters embedded as review-matrix graph cells."""

    type_name = "scatter-matrix"
    _matrix = MatrixRecipe()

    def normalize(self, payload, resolved):
        variables = payload.get("variables") or {}
        names = list(variables.keys())
        states = [{"id": n, "label": n} for n in names]
        items = []
        for yi in names:
            cells = {}
            for xi in names:
                if xi == yi:
                    cells[xi] = {"kind": "text", "value": yi}
                else:
                    xv, yv = variables[xi], variables[yi]
                    m = min(len(xv), len(yv))
                    gp = {"axes": {"x": {"label": xi, "unit": ""}, "y": {"label": yi, "unit": ""}},
                          "series": [{"name": f"{xi}~{yi}",
                                      "data": [[_num(xv[k]), _num(yv[k])] for k in range(m)], "style": "markers"}]}
                    cells[xi] = {"kind": "graph", "graph_ref": {"type": "correlation-scatter", "payload": gp}}
            items.append({"id": yi, "label": yi, "type": "graph", "cells": cells})
        mp = {"title": str(payload.get("title") or "Scatter matrix (SPLOM)"),
              "states": states, "items": items, "options": {"diff": False}}
        out = self._matrix.normalize(mp, resolved)
        _inject_plugin(out, "brushlink", {"group": "splom"})   # linked brushing across cells
        return out

    def structural_requires(self, payload):
        variables = payload.get("variables") or {}
        if len(variables) < 2:
            return [{"field": "variables", "why": "SPLOM은 변수 2개 이상 필요",
                     "ask": "변수별 값을 주세요 (variables:{이름:[값...], ...}, 2개 이상, 같은 길이)."}]
        lens = {len(v) for v in variables.values()}
        if len(lens) > 1:
            return [{"field": "variables", "why": "변수 길이 불일치",
                     "ask": "모든 변수의 관측 개수를 동일하게 맞춰주세요."}]
        return []
