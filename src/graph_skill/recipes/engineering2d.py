"""Batch G — engineering 2D quick-wins. All xy-core, reusing base-xy / force-displacement +
existing plugins (threshold-lines, named-markers, error-bars, live-tangent). No new engine,
no new plugin. Each recipe only normalizes free input + wires the right plugin config.
"""

from __future__ import annotations

from .base import Recipe
from .base_xy import BaseXYRecipe, _num
from .force_displacement import ForceDisplacementRecipe


def _axis(a, dlabel=""):
    a = a or {}
    return {"label": str(a.get("label", dlabel)), "unit": str(a.get("unit", "")),
            "log": a.get("scale", "linear") == "log"}


def _ay_ok(payload):
    ya = (payload.get("axes") or {}).get("y") or {}
    return bool(ya.get("label")) and "unit" in ya


class MainEffectsRecipe(Recipe):
    """DOE main-effects: each factor's level-means as a series on a shared categorical x,
    plus a grand-mean reference line."""

    type_name = "main-effects-plot"

    def normalize(self, payload, resolved):
        factors = payload.get("factors") or []
        cats, series, allm, idx = [], [], [], 0
        for f in factors:
            levels = [str(l) for l in (f.get("levels") or [])]
            means = [_num(v) for v in (f.get("means") or [])]
            xs = []
            for lv, m in zip(levels, means):
                cats.append(f"{f.get('name', '')}:{lv}")
                xs.append(idx)
                idx += 1
                if m is not None:
                    allm.append(m)
            series.append({"name": str(f.get("name", f"factor{len(series)+1}")),
                           "x": xs, "y": means, "style": "line+markers"})
        grand = _num(payload.get("grand_mean"))
        if grand is None and allm:
            grand = sum(allm) / len(allm)
        ax = payload.get("axes") or {}
        xa = _axis(ax.get("x"), "")
        xa["categories"] = cats
        opts = {"curve": "straight", "axes": {"x": xa, "y": _axis(ax.get("y"), "response")}}
        if grand is not None:
            opts["pluginConfig"] = {"threshold-lines": {"lines": [
                {"axis": "y", "value": grand, "label": "전체평균", "color": "#888", "dash": [5, 4]}]}}
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        factors = payload.get("factors") or []
        if not factors:
            miss.append({"field": "factors", "why": "주효과 인자가 없음",
                         "ask": "인자별 수준과 평균을 주세요 (factors:[{name, levels:[...], means:[...]}, ...])."})
        for i, f in enumerate(factors):
            if len(f.get("levels") or []) != len(f.get("means") or []):
                miss.append({"field": f"factors[{i}]", "why": "levels와 means 길이 불일치",
                             "ask": f"인자 '{f.get('name', i)}'의 levels와 means 개수를 맞춰주세요."})
        if not _ay_ok(payload):
            miss.append({"field": "axes.y", "why": "반응변수(y)의 의미/단위 미상",
                         "ask": "반응(응답) 변수와 단위는? (axes.y={label,unit}; 수율%면 unit:'%')"})
        return miss


class InteractionRecipe(Recipe):
    """DOE interaction: factor_x levels on x; one line per factor_series level (crossing = interaction)."""

    type_name = "interaction-plot"

    def normalize(self, payload, resolved):
        fx = payload.get("factor_x") or {}
        fs = payload.get("factor_series") or {}
        xl = [str(l) for l in (fx.get("levels") or [])]
        sl = [str(l) for l in (fs.get("levels") or [])]
        means = payload.get("means") or []
        series = []
        for si, slv in enumerate(sl):
            row = means[si] if si < len(means) else []
            series.append({"name": f"{fs.get('name', '')}={slv}",
                           "x": list(range(len(xl))), "y": [_num(v) for v in row], "style": "line+markers"})
        ax = payload.get("axes") or {}
        xa = _axis(ax.get("x"), str(fx.get("name", "")))
        xa["categories"] = xl
        opts = {"curve": "straight", "axes": {"x": xa, "y": _axis(ax.get("y"), "response")}}
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        fx = (payload.get("factor_x") or {}).get("levels") or []
        fs = (payload.get("factor_series") or {}).get("levels") or []
        means = payload.get("means") or []
        if not fx or not fs or not means:
            miss.append({"field": "interaction", "why": "교호작용 데이터 부족",
                         "ask": "factor_x:{name,levels}, factor_series:{name,levels}, means:[[행=series수준 × 열=x수준]] 를 주세요."})
        elif len(means) != len(fs) or any(len(r) != len(fx) for r in means):
            miss.append({"field": "means", "why": "means 차원이 levels와 불일치",
                         "ask": "means는 (factor_series 수준 수) × (factor_x 수준 수) 행렬이어야 합니다."})
        if not _ay_ok(payload):
            miss.append({"field": "axes.y", "why": "반응변수(y) 단위 미상",
                         "ask": "반응 변수와 단위는? (axes.y={label,unit})"})
        return miss


class TransientRecipe(Recipe):
    """Transient time-history: multi-channel time series + auto peak markers + optional limit lines."""

    type_name = "transient-time-history"
    _base = BaseXYRecipe()

    def normalize(self, payload, resolved):
        norm = self._base.normalize(payload, resolved)
        markers = []
        for s in norm["assets"]["series"]:
            best, bi = None, -1
            for i, v in enumerate(s["y"]):
                if v is None:
                    continue
                if best is None or abs(v) > abs(best):
                    best, bi = v, i
            if bi >= 0:
                markers.append({"x": s["x"][bi], "y": best, "label": f"{s['name']} peak", "color": "#dc2626"})
        pc = norm["options"].setdefault("pluginConfig", {})
        pc["named-markers"] = {"markers": markers}
        limits = payload.get("limits") or []
        if limits:
            pc["threshold-lines"] = {"lines": [
                {"axis": "y", "value": _num(l.get("value")), "label": str(l.get("label", "")),
                 "color": "#b45309", "dash": [6, 4]} for l in limits if _num(l.get("value")) is not None]}
        return norm

    def structural_requires(self, payload):
        if not (payload.get("series") or []):
            return [{"field": "series", "why": "시간이력 채널이 없음",
                     "ask": "시간이력을 주세요 (series:[{name, data:[[time, value], ...]}]) + axes.x(time)/y."}]
        return []


class ConvergenceRecipe(Recipe):
    """Solver convergence: residual (log-y) vs iteration, multi-equation + convergence tolerance line."""

    type_name = "convergence-residual-plot"
    _base = BaseXYRecipe()

    def normalize(self, payload, resolved):
        norm = self._base.normalize(payload, resolved)
        axes = norm["options"]["axes"]
        axes["y"]["log"] = True
        if not axes["x"].get("label"):
            axes["x"]["label"] = "Iteration"
        if not axes["y"].get("label"):
            axes["y"]["label"] = "Residual"
        tol = _num(payload.get("tolerance"))
        if tol is not None:
            norm["options"].setdefault("pluginConfig", {})["threshold-lines"] = {"lines": [
                {"axis": "y", "value": tol, "label": "수렴기준", "color": "#059669", "dash": [6, 4]}]}
        return norm

    def structural_requires(self, payload):
        if not (payload.get("series") or []):
            return [{"field": "series", "why": "잔차 이력이 없음",
                     "ask": "잔차 이력을 주세요 (series:[{name:'continuity', data:[[iter, residual], ...]}, ...])."}]
        return []


class CFDLineCompareRecipe(Recipe):
    """CFD/CAE line-extract comparison: multi-case lines + error bars on experimental series."""

    type_name = "cfd-line-extract-compare"
    _base = BaseXYRecipe()

    def normalize(self, payload, resolved):
        norm = self._base.normalize(payload, resolved)
        bars = []
        for s in payload.get("series") or []:
            errs = s.get("err")
            for j, pt in enumerate(s.get("data") or []):
                if isinstance(pt, (list, tuple)) and len(pt) >= 3:
                    x, y, e = pt[0], pt[1], pt[2]
                elif isinstance(pt, (list, tuple)) and len(pt) >= 2 and errs and j < len(errs):
                    x, y, e = pt[0], pt[1], errs[j]
                else:
                    continue
                if _num(e) is not None:
                    bars.append({"x": float(x), "y": float(y), "err": float(e)})
        if bars:
            norm["options"].setdefault("pluginConfig", {})["error-bars"] = {"bars": bars}
        return norm

    def structural_requires(self, payload):
        if not (payload.get("series") or []):
            return [{"field": "series", "why": "비교할 라인 데이터가 없음",
                     "ask": "케이스별 라인을 주세요 (series:[{name, data:[[x,y],...]}]); 실험점은 data=[[x,y,err]] 또는 series.err."}]
        return []


class NonlinearLoadDispRecipe(Recipe):
    """Nonlinear load-displacement / pushover: force-displacement (live-tangent) + yield/ultimate markers."""

    type_name = "nonlinear-load-displacement"
    _fd = ForceDisplacementRecipe()

    def normalize(self, payload, resolved):
        norm = self._fd.normalize(payload, resolved)
        markers = []
        for m in payload.get("markers") or []:
            x, y = _num(m.get("x")), _num(m.get("y"))
            if x is not None and y is not None:
                markers.append({"x": x, "y": y, "label": str(m.get("label", "")), "color": m.get("color", "#dc2626")})
        if not markers:  # auto: peak load = ultimate
            s0 = (norm["assets"]["series"] or [{}])[0]
            ys = s0.get("y", [])
            if ys:
                bi, best = -1, None
                for i, v in enumerate(ys):
                    if v is not None and (best is None or v > best):
                        best, bi = v, i
                if bi >= 0:
                    markers.append({"x": s0["x"][bi], "y": best, "label": "Ultimate", "color": "#dc2626"})
        if markers:
            norm["options"].setdefault("pluginConfig", {})["named-markers"] = {"markers": markers}
        return norm

    def structural_requires(self, payload):
        if not (payload.get("series") or []):
            return [{"field": "series", "why": "하중-변위 데이터가 없음",
                     "ask": "하중-변위를 주세요 (series:[{name, data:[[변위, 하중], ...]}]) + axes.x(변위)/y(하중)."}]
        return []


class SNCurveRecipe(Recipe):
    """S-N (Wöhler) fatigue curve: log cycles vs stress amplitude + fatigue-limit line + design point."""

    type_name = "s-n-fatigue-curve"
    _base = BaseXYRecipe()

    def normalize(self, payload, resolved):
        norm = self._base.normalize(payload, resolved)
        axes = norm["options"]["axes"]
        axes["x"]["log"] = True
        if not axes["x"].get("label"):
            axes["x"]["label"] = "Cycles to failure N"
        if not axes["y"].get("label"):
            axes["y"]["label"] = "Stress amplitude"
        pc = norm["options"].setdefault("pluginConfig", {})
        fl = _num(payload.get("fatigue_limit"))
        if fl is not None:
            pc["threshold-lines"] = {"lines": [
                {"axis": "y", "value": fl, "label": "피로한도", "color": "#059669", "dash": [6, 4]}]}
        dp = payload.get("design_point")
        if isinstance(dp, dict):
            x, y = _num(dp.get("N") or dp.get("x")), _num(dp.get("S") or dp.get("y"))
            if x is not None and y is not None:
                pc["named-markers"] = {"markers": [{"x": x, "y": y, "label": str(dp.get("label", "설계점")), "color": "#dc2626"}]}
        return norm

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("series") or []):
            miss.append({"field": "series", "why": "S-N 데이터가 없음",
                         "ask": "재료별 S-N을 주세요 (series:[{name, data:[[N, S], ...]}]); x=반복수 N, y=응력진폭."})
        ya = (payload.get("axes") or {}).get("y") or {}
        if not ya.get("label") or "unit" not in ya:
            miss.append({"field": "axes.y", "why": "응력진폭(y) 단위 미상",
                         "ask": "응력 진폭의 단위는? (axes.y={label:'Stress amplitude', unit:'MPa'})"})
        return miss
