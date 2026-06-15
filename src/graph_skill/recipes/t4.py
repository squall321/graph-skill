"""T2 표준 보고 그래프 (배치 C, 9종) — risk-matrix/friction-wear/fan-pump/tq-pinch/
jr-curve/load-transient/mott-schottky/compressor-map/harmonic-spur.
전부 기존 엔진(xy-core / review-matrix)·플러그인 재사용. 엔진 신규작업 0."""

from __future__ import annotations

from ..postprocess import domain_t2 as _t2
from ..postprocess import domain_t3 as _t3
from ..postprocess import domain_t4 as _t4
from .base import Recipe
from .matrix_compare import MatrixRecipe


def _fmt(v, nd=3):
    return "—" if v is None else f"{v:.{nd}g}"


_ZONE_COL = {"low": "#16a34a", "medium": "#eab308", "high": "#f97316", "extreme": "#dc2626"}


class RiskMatrixRecipe(Recipe):
    type_name = "risk-matrix"

    def normalize(self, payload, resolved):
        risks = payload["risks"]
        groups = {z: {"x": [], "y": []} for z in _ZONE_COL}
        markers = []
        for r in risks:
            p, i = int(r["probability"]), int(r["impact"])
            z = _t3.risk_zone(p, i)
            groups[z]["x"].append(p)
            groups[z]["y"].append(i)
            markers.append({"x": p, "y": i, "label": str(r.get("id", r.get("name", ""))), "color": _ZONE_COL[z]})
            res = r.get("residual")
            if res:
                markers.append({"x": int(res["p"]), "y": int(res["i"]), "label": "(완화)", "color": "#94a3b8"})
        series = [{"name": z, "x": g["x"], "y": g["y"], "style": "markers", "color": _ZONE_COL[z]}
                  for z, g in groups.items() if g["x"]]
        opts = {"axes": {"x": {"label": "발생확률", "unit": ""}, "y": {"label": "영향", "unit": ""}},
                "title": str(payload.get("title") or "리스크 매트릭스 (5×5)"),
                "pluginConfig": {"named-markers": {"markers": markers}}}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        if not (payload.get("risks") or []):
            return [{"field": "risks", "why": "리스크가 없음",
                     "ask": "risks:[{id|name, probability:1~5, impact:1~5, residual?:{p,i}}] 를 주세요."}]
        return []


class FrictionWearRecipe(Recipe):
    type_name = "friction-wear-curve"

    def normalize(self, payload, resolved):
        series, ss = [], None
        for si, s in enumerate(payload["series"]):
            data = [[float(p[0]), float(p[1])] for p in s["data"]]
            xs = [p[0] for p in data]
            ys = [p[1] for p in data]
            series.append({"name": str(s.get("name", f"시편 {si + 1}")), "x": xs, "y": ys})
            if ss is None:
                ss = _t2.steady_state(xs, ys, float(payload.get("steady_frac", 0.5)))
                ss["xmax"] = xs[-1]
        pcfg = {}
        if ss:
            series.append({"name": f"정상상태 평균 {_fmt(ss['mean'])}", "x": [ss["x0"], ss["x1"]],
                           "y": [ss["mean"], ss["mean"]], "color": "#16a34a", "dash": [6, 4]})
            pcfg["region-shading"] = {"regions": [{"x0": 0, "x1": ss["x0"], "label": "런인"}]}
        ax = payload.get("axes") or {}
        opts = {"axes": {"x": {"label": str((ax.get("x") or {}).get("label", "미끄럼거리")),
                               "unit": str((ax.get("x") or {}).get("unit", "m"))},
                         "y": {"label": "마찰계수 COF", "unit": ""}},
                "title": str(payload.get("title") or "마찰계수-거리 곡선")}
        if pcfg:
            opts["pluginConfig"] = pcfg
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        if not (payload.get("series") or []):
            return [{"field": "series", "why": "마찰 데이터가 없음",
                     "ask": "series:[{name, data:[[거리(m), COF],…]}] 를 주세요."}]
        return []


class FanPumpRecipe(Recipe):
    type_name = "fan-pump-operating-point"

    def normalize(self, payload, resolved):
        series = []
        curves = payload["curves"]
        pump = None
        for i, c in enumerate(curves):
            data = [[float(p[0]), float(p[1])] for p in c["data"]]
            series.append({"name": str(c.get("name", f"성능 {i + 1}")), "x": [p[0] for p in data], "y": [p[1] for p in data]})
            if pump is None:
                pump = data
        sysc = payload.get("system")
        markers = []
        if sysc and pump:
            sd = [[float(p[0]), float(p[1])] for p in sysc]
            series.append({"name": "시스템 곡선", "x": [p[0] for p in sd], "y": [p[1] for p in sd],
                           "color": "#dc2626", "dash": [5, 4]})
            op = _t4.curve_intersection(pump, sd)
            if op:
                markers.append({"x": op[0], "y": op[1], "label": f"운전점 ({_fmt(op[0])}, {_fmt(op[1])})", "color": "#16a34a"})
        ax = payload.get("axes") or {}
        opts = {"axes": {"x": {"label": "유량 Q", "unit": str((ax.get("x") or {}).get("unit", "m³/h"))},
                         "y": {"label": "양정/압력", "unit": str((ax.get("y") or {}).get("unit", "m"))}},
                "title": str(payload.get("title") or "팬/펌프 운전점")}
        if markers:
            opts["pluginConfig"] = {"named-markers": {"markers": markers}}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("curves") or []):
            miss.append({"field": "curves", "why": "성능 곡선이 없음",
                         "ask": "curves:[{name, data:[[Q, ΔP/H],…]}] 를 주세요 (+system:[[Q,ΔP],…])."})
        if "unit" not in ((payload.get("axes") or {}).get("y") or {}):
            miss.append({"field": "axes.y.unit", "why": "양정/압력 단위 미상",
                         "ask": "axes.y={label,unit} 을 주세요 (예: 'm' 또는 'kPa')."})
        return miss


class TQPinchRecipe(Recipe):
    type_name = "tq-pinch-diagram"

    def normalize(self, payload, resolved):
        streams = payload["streams"]
        dtmin = float(payload.get("dtmin", 10))
        hot = _t4.composite_curve(streams, "hot")
        cold = _t4.composite_curve(streams, "cold")
        # cold 곡선을 ΔTmin 만족하도록 x(엔탈피) 이동 — 여기선 표시용 단순 정렬
        series = []
        if hot:
            series.append({"name": "고온 복합곡선", "x": [p[0] for p in hot], "y": [p[1] for p in hot], "color": "#dc2626"})
        if cold:
            shift = (hot[-1][0] - cold[-1][0]) if hot else 0
            series.append({"name": "저온 복합곡선", "x": [p[0] + shift for p in cold], "y": [p[1] + dtmin for p in cold], "color": "#2563eb"})
        ax = payload.get("axes") or {}
        opts = {"axes": {"x": {"label": "엔탈피 Q", "unit": str((ax.get("x") or {}).get("unit", "kW"))},
                         "y": {"label": "온도 T", "unit": "°C"}},
                "title": f"{payload.get('title') or 'T-Q 핀치 선도'} — ΔTmin {dtmin:g}°C"}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        streams = payload.get("streams") or []
        if not streams or not any(s.get("side") == "hot" for s in streams) or not any(s.get("side") == "cold" for s in streams):
            return [{"field": "streams", "why": "고온/저온 스트림이 필요",
                     "ask": "streams:[{side:'hot'|'cold', T_in, T_out, mcp(kW/°C)}] 를 고온·저온 각각 주세요 (+dtmin)."}]
        return []


class JRCurveRecipe(Recipe):
    type_name = "jr-curve"

    def normalize(self, payload, resolved):
        data = [[float(p[0]), float(p[1])] for p in payload["data"]]
        da = [p[0] for p in data]
        j = [p[1] for p in data]
        sy = float(payload["sigma_y"])
        fit = _t4.jr_curve_fit(da, j, sy)
        dmax = max(da)
        xs = [dmax * k / 40 for k in range(1, 41)]
        series = [{"name": "J-Δa 데이터", "x": da, "y": j, "style": "markers", "color": "#2563eb"},
                  {"name": f"멱법칙 (m={_fmt(fit['m'])})", "x": xs, "y": [fit["C"] * (x ** fit["m"]) for x in xs], "color": "#16a34a"},
                  {"name": "블런팅선", "x": [0, dmax], "y": [0, fit["blunting_slope"] * dmax], "color": "#94a3b8", "dash": [5, 4]}]
        opts = {"axes": {"x": {"label": "균열성장 Δa", "unit": "mm"},
                         "y": {"label": "J-적분", "unit": str(payload.get("j_unit", "kJ/m²"))}},
                "title": str(payload.get("title") or "J-R 파괴저항 곡선")}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if len(payload.get("data") or []) < 3:
            miss.append({"field": "data", "why": "J-Δa 데이터 부족",
                         "ask": "data:[[Δa(mm), J(kJ/m²)],…] 를 주세요 (3점 이상)."})
        if payload.get("sigma_y") is None:
            miss.append({"field": "sigma_y", "why": "항복강도 미상(블런팅선 산출용)",
                         "ask": "sigma_y(항복강도, J 단위계와 일관)를 주세요."})
        return miss


class LoadTransientRecipe(Recipe):
    type_name = "load-transient-response"
    _matrix = MatrixRecipe()

    def normalize(self, payload, resolved):
        ch = payload["channels"]
        il = [[float(p[0]), float(p[1])] for p in ch["i_load"]]
        vo = [[float(p[0]), float(p[1])] for p in ch["v_out"]]
        params = payload.get("params") or {}
        v_nom = float(params.get("v_nom", vo[0][1]))
        tol = float(params.get("tol_pct", 5))
        m = _t4.transient_metrics([p[0] for p in vo], [p[1] for p in vo], v_nom, tol)
        band_hi, band_lo = v_nom + m["band"], v_nom - m["band"]
        tx = [vo[0][0], vo[-1][0]]

        def cell(name, data, ylab, unit, extra=None):
            series = [{"name": name, "x": [p[0] for p in data], "y": [p[1] for p in data], "color": "#2563eb"}]
            if extra:
                series += extra
            gp = {"axes": {"x": {"label": "시간", "unit": "s"}, "y": {"label": ylab, "unit": unit}}, "series": series}
            return {"kind": "graph", "graph_ref": {"type": "base-xy", "payload": gp}}

        vband = [{"name": "+tol", "x": tx, "y": [band_hi, band_hi], "color": "#dc2626", "dash": [4, 3]},
                 {"name": "−tol", "x": tx, "y": [band_lo, band_lo], "color": "#dc2626", "dash": [4, 3]}]
        items = [{"id": "i", "label": "부하 전류", "type": "graph", "cells": {"t": cell("I_load", il, "전류", "A")}},
                 {"id": "v", "label": f"출력 전압 (오버 {_fmt(m['overshoot_pct'])}% 회복 {_fmt(m['recovery_t'])}s)",
                  "type": "graph", "cells": {"t": cell("V_out", vo, "전압", "V", vband)}}]
        mp = {"title": str(payload.get("title") or "부하 과도응답"),
              "states": [{"id": "t", "label": ""}], "items": items, "options": {"diff": False}}
        out = self._matrix.normalize(mp, resolved)
        return out

    def structural_requires(self, payload):
        ch = payload.get("channels") or {}
        if not ch.get("i_load") or not ch.get("v_out"):
            return [{"field": "channels", "why": "전류/전압 채널이 필요",
                     "ask": "channels:{i_load:[[t,A]], v_out:[[t,V]]} + params:{v_nom, tol_pct} 를 주세요."}]
        return []


class MottSchottkyRecipe(Recipe):
    type_name = "mott-schottky-cv"

    def normalize(self, payload, resolved):
        data = [[float(p[0]), float(p[1])] for p in payload["data"]]
        v = [p[0] for p in data]
        c = [p[1] for p in data]
        params = payload["params"]
        r = _t4.mott_schottky(v, c, float(params["area_cm2"]), float(params["eps_r"]))
        fit_y = [r["slope"] * x + (r["inv_c2"][0] - r["slope"] * v[0]) for x in v]
        series = [{"name": "1/C²", "x": v, "y": r["inv_c2"], "style": "markers", "color": "#2563eb"},
                  {"name": "선형적합", "x": v, "y": fit_y, "color": "#16a34a", "dash": [5, 4]}]
        pcfg = {}
        if r["v_fb"] is not None:
            pcfg["threshold-lines"] = {"lines": [{"axis": "x", "value": r["v_fb"],
                                       "label": f"V_fb {_fmt(r['v_fb'])}V", "color": "#dc2626"}]}
        opts = {"axes": {"x": {"label": "전압 V", "unit": "V"}, "y": {"label": "1/C²", "unit": "F⁻²"}},
                "title": f"{payload.get('title') or 'Mott-Schottky'} — N_D={_fmt(r['n_d'])} cm⁻³ V_fb={_fmt(r['v_fb'])}V"}
        if pcfg:
            opts["pluginConfig"] = pcfg
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if len(payload.get("data") or []) < 3:
            miss.append({"field": "data", "why": "C-V 데이터 부족",
                         "ask": "data:[[V(V), C(F)],…] 를 주세요 (3점 이상)."})
        p = payload.get("params") or {}
        if p.get("area_cm2") is None or p.get("eps_r") is None:
            miss.append({"field": "params", "why": "면적·유전율 미상(도핑농도 환산용)",
                         "ask": "params:{area_cm2(소자 면적 cm²), eps_r(비유전율)} 를 주세요."})
        return miss


class CompressorMapRecipe(Recipe):
    type_name = "compressor-map"

    def normalize(self, payload, resolved):
        series = []
        for sl in payload["speed_lines"]:
            d = [[float(p[0]), float(p[1])] for p in sl["data"]]
            series.append({"name": f"{sl.get('rpm', '')} rpm", "x": [p[0] for p in d], "y": [p[1] for p in d]})
        surge = payload.get("surge")
        if surge:
            sd = [[float(p[0]), float(p[1])] for p in surge]
            series.append({"name": "서지선", "x": [p[0] for p in sd], "y": [p[1] for p in sd], "color": "#dc2626", "dash": [5, 4]})
        markers = []
        op = payload.get("operating_point")
        if op:
            markers.append({"x": float(op["mdot"]), "y": float(op["pr"]), "label": "운전점", "color": "#16a34a"})
        ax = payload.get("axes") or {}
        opts = {"axes": {"x": {"label": "보정 유량", "unit": str((ax.get("x") or {}).get("unit", "kg/s"))},
                         "y": {"label": "압력비 PR", "unit": ""}},
                "title": str(payload.get("title") or "압축기 성능 맵")}
        if markers:
            opts["pluginConfig"] = {"named-markers": {"markers": markers}}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        if not (payload.get("speed_lines") or []):
            return [{"field": "speed_lines", "why": "속도선이 없음",
                     "ask": "speed_lines:[{rpm, data:[[mdot, PR],…]}] 를 주세요 (+surge:[[mdot,PR]], operating_point:{mdot,pr})."}]
        return []


class HarmonicSpurRecipe(Recipe):
    type_name = "harmonic-spur-table"

    def normalize(self, payload, resolved):
        spec = [[float(p[0]), float(p[1])] for p in payload["spectrum"]]
        xs = [p[0] for p in spec]
        ys = [p[1] for p in spec]
        f0 = float(payload["f0"])
        n_max = int(payload.get("n_max", 10))
        peaks = _t4.harmonic_peaks(xs, ys, f0, n_max)
        markers = [{"x": p["freq"], "y": p["amp"], "label": f"{p['n']}f0 ({_fmt(p['dbc'])}dBc)",
                    "color": "#dc2626" if p["n"] > 1 else "#16a34a"} for p in peaks]
        worst = max((p["dbc"] for p in peaks if p["n"] > 1), default=None)
        opts = {"axes": {"x": {"label": "주파수", "unit": str(payload.get("f_unit", "MHz")), "log": False},
                         "y": {"label": "전력", "unit": "dBm"}},
                "title": f"{payload.get('title') or '고조파/스퓨리어스'} — 최악 고조파 {_fmt(worst)} dBc",
                "pluginConfig": {"named-markers": {"markers": markers}}}
        return {"engine": resolved.engine,
                "assets": {"series": [{"name": "스펙트럼", "x": xs, "y": ys, "color": "#2563eb"}]}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if len(payload.get("spectrum") or []) < 2:
            miss.append({"field": "spectrum", "why": "스펙트럼이 없음",
                         "ask": "spectrum:[[주파수, dBm],…] 를 주세요."})
        if payload.get("f0") is None:
            miss.append({"field": "f0", "why": "기본 주파수 미상",
                         "ask": "f0(기본 주파수)를 주세요 (n_max 기본 10)."})
        return miss
