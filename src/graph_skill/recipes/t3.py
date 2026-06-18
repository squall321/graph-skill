"""T2 표준 보고 그래프 (배치 B, 10종) — phase-noise/soa/uncertainty-budget/tolerance-stackup/
evm-s-curve/burndown-burnup/dqdv/torque-angle/creep/equivalence-tost.
전부 기존 엔진(xy-core)·플러그인 재사용. 엔진 신규작업 0."""

from __future__ import annotations

from ..postprocess import domain_t3 as _t3
from .base import Recipe


def _fmt(v, nd=3):
    return "—" if v is None else f"{v:.{nd}g}"


class PhaseNoiseRecipe(Recipe):
    type_name = "phase-noise"

    def normalize(self, payload, resolved):
        offs = [float(x) for x in payload["offsets"]]
        lf = [float(x) for x in payload["lf"]]
        series = [{"name": "L(f)", "x": offs, "y": lf, "color": "#2563eb"}]
        markers = [{"x": float(s[0]), "y": float(s[1]), "label": "spur", "color": "#dc2626"}
                   for s in (payload.get("spurs") or [])]
        title = str(payload.get("title") or "위상잡음 L(f)")
        integ = payload.get("integ")
        if integ:
            j = _t3.phase_jitter(offs, lf, integ[0], integ[1], payload.get("carrier"))
            tail = f"RMS 위상지터 {_fmt(j['rms_deg'])}°"
            if "jitter_s" in j:
                tail += f" ({_fmt(j['jitter_s'] * 1e15)} fs)"
            title += f" — {tail}"
        opts = {"axes": {"x": {"label": "오프셋 주파수", "unit": "Hz", "log": True},
                         "y": {"label": "위상잡음", "unit": "dBc/Hz"}}, "title": title}
        if markers:
            opts["pluginConfig"] = {"named-markers": {"markers": markers}}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        if len(payload.get("offsets") or []) < 2 or len(payload.get("lf") or []) < 2:
            return [{"field": "offsets", "why": "위상잡음 데이터 부족",
                     "ask": "offsets:[Hz], lf:[dBc/Hz] 를 같은 길이로 주세요 (+spurs, integ:[f1,f2], carrier 선택)."}]
        return []


class SOAChartRecipe(Recipe):
    type_name = "soa-chart"

    def normalize(self, payload, resolved):
        series = []
        dev = payload.get("device")
        bound = None
        if dev:
            b = _t3.soa_boundary(float(dev["rds_on"]), float(dev["id_max"]),
                                 float(dev["pd_max"]), float(dev["vds_max"]))
            bound = (dev, b)
            series.append({"name": "DC SOA", "x": [p[0] for p in b], "y": [p[1] for p in b], "color": "#dc2626"})
        for lim in (payload.get("limits") or []):
            d = [[float(p[0]), float(p[1])] for p in lim["data"]]
            series.append({"name": str(lim.get("pulse", "한계")), "x": [p[0] for p in d], "y": [p[1] for p in d]})
        markers = []
        for pt in (payload.get("points") or []):
            v, i = float(pt["vds"]), float(pt["id"])
            ok = _t3.point_in_soa(v, i, float(dev["rds_on"]), float(dev["id_max"]),
                                  float(dev["pd_max"]), float(dev["vds_max"])) if dev else True
            markers.append({"x": v, "y": i, "label": str(pt.get("label", "")),
                            "color": "#16a34a" if ok else "#dc2626"})
        opts = {"axes": {"x": {"label": "Vds", "unit": "V", "log": True},
                         "y": {"label": "Id", "unit": "A", "log": True}},
                "title": str(payload.get("title") or "안전동작영역 (SOA)")}
        if markers:
            opts["pluginConfig"] = {"named-markers": {"markers": markers}}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        if not payload.get("device") and not (payload.get("limits") or []):
            return [{"field": "device", "why": "SOA 한계 정의가 없음",
                     "ask": "device:{rds_on,id_max,pd_max,vds_max} 또는 limits:[{pulse,data:[[Vds,Id]]}] 를 주세요."}]
        return []


class UncertaintyBudgetRecipe(Recipe):
    type_name = "uncertainty-budget-chart"

    def normalize(self, payload, resolved):
        comps = payload["components"]
        k = float(payload.get("k", 2))
        r = _t3.uncertainty_budget(comps, k)
        cats = [str(c.get("name", f"u{i + 1}")) for i, c in enumerate(comps)]
        meas = payload.get("measurand") or {}
        xa = {"label": "성분", "unit": "", "categories": cats}
        opts = {"axes": {"x": xa, "y": {"label": "분산 기여율", "unit": "%"}},
                "title": f"{payload.get('title') or '측정 불확도 버짓'} — "
                         f"uc={_fmt(r['uc'])} U(k={r['k']:g})={_fmt(r['U'])} {str(meas.get('unit', ''))}"}
        return {"engine": resolved.engine,
                "assets": {"series": [{"name": "기여율", "x": list(range(len(cats))), "y": r["percent"],
                                       "style": "bar", "color": "#2563eb"}]}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("components") or []):
            miss.append({"field": "components", "why": "불확도 성분이 없음",
                         "ask": "components:[{name,u,c?(감도)}] 를 주세요."})
        if "unit" not in (payload.get("measurand") or {}):
            miss.append({"field": "measurand.unit", "why": "측정량 단위 미상",
                         "ask": "measurand:{label,unit} 을 주세요 (불확도 단위 표기용; 무차원이면 '')."})
        return miss


class ToleranceStackupRecipe(Recipe):
    type_name = "tolerance-stackup-chart"

    def normalize(self, payload, resolved):
        links = payload["links"]
        r = _t3.tolerance_stackup(links)
        cats = [str(l.get("name", f"L{i + 1}")) for i, l in enumerate(links)]
        ax = payload.get("axes") or {}
        unit = str((ax.get("y") or {}).get("unit", ""))
        spec = payload.get("spec") or {}
        lines = []
        if spec.get("min") is not None:
            lines.append({"axis": "y", "value": float(spec["min"]), "label": f"min {spec['min']}", "color": "#dc2626"})
        if spec.get("max") is not None:
            lines.append({"axis": "y", "value": float(spec["max"]), "label": f"max {spec['max']}", "color": "#dc2626"})
        opts = {"axes": {"x": {"label": "링크", "unit": "", "categories": cats},
                         "y": {"label": "공차 기여", "unit": unit}},
                "title": f"{payload.get('title') or '공차 스택업'} — 공칭 {_fmt(r['nominal'])} "
                         f"WC ±{_fmt(r['wc'])} RSS ±{_fmt(r['rss'])} {unit}"}
        if lines:
            opts["pluginConfig"] = {"threshold-lines": {"lines": lines}}
        return {"engine": resolved.engine,
                "assets": {"series": [{"name": "공차 ±", "x": list(range(len(cats))), "y": r["tols"],
                                       "style": "bar", "color": "#f59e0b"}]}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("links") or []):
            miss.append({"field": "links", "why": "스택업 링크가 없음",
                         "ask": "links:[{name,nominal,tol_plus,tol_minus,sense?}] 를 주세요."})
        if "unit" not in ((payload.get("axes") or {}).get("y") or {}):
            miss.append({"field": "axes.y.unit", "why": "치수 단위 미상",
                         "ask": "치수 단위를 axes.y.unit 으로 주세요 (예: 'mm')."})
        return miss


class EVMSCurveRecipe(Recipe):
    type_name = "evm-s-curve"

    def normalize(self, payload, resolved):
        dates = [str(d) for d in payload["dates"]]
        x = list(range(len(dates)))
        pv = [float(v) for v in payload["pv"]]
        ev = [float(v) for v in payload["ev"]]
        ac = [float(v) for v in payload["ac"]]
        bac = float(payload["bac"])
        i = len(ev) - 1
        m = _t3.evm_metrics(pv[i], ev[i], ac[i], bac)
        series = [{"name": "PV (계획가치)", "x": x, "y": pv, "color": "#94a3b8"},
                  {"name": "EV (획득가치)", "x": x, "y": ev, "color": "#2563eb"},
                  {"name": "AC (실제원가)", "x": x, "y": ac, "color": "#f59e0b"}]
        pcfg = {"threshold-lines": {"lines": [{"axis": "y", "value": bac, "label": f"BAC {bac:g}", "color": "#16a34a"}]},
                "named-markers": {"markers": [{"x": x[i], "y": m["eac"], "label": f"EAC {_fmt(m['eac'])}", "color": "#dc2626"}]}}
        series.append({"name": "_lim", "x": [x[i], x[i]], "y": [bac, m["eac"]], "style": "none"})  # BAC/EAC 자동스케일 포함
        unit = str((payload.get("axes") or {}).get("unit", ""))
        opts = {"axes": {"x": {"label": "기간", "unit": "", "categories": dates},
                         "y": {"label": "누적 가치", "unit": unit}},
                "title": f"{payload.get('title') or 'EVM 성과 S-커브'} — SPI={_fmt(m['spi'])} CPI={_fmt(m['cpi'])}",
                "pluginConfig": pcfg}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        for k in ("dates", "pv", "ev", "ac"):
            if not (payload.get(k) or []):
                return [{"field": k, "why": "EVM 데이터 부족",
                         "ask": "dates:[], pv:[], ev:[], ac:[] (같은 길이) + bac 를 주세요."}]
        if payload.get("bac") is None:
            return [{"field": "bac", "why": "BAC(완료시예산) 미상", "ask": "bac(완료시점 총예산)를 주세요."}]
        return []


class BurndownRecipe(Recipe):
    type_name = "burndown-burnup"

    def normalize(self, payload, resolved):
        periods = [str(p) for p in payload["periods"]]
        x = list(range(len(periods)))
        total = float(payload["total_scope"])
        actual = [float(v) for v in payload["actual"]]
        mode = str(payload.get("mode", "down"))
        n = len(periods)
        ideal = [total - total * i / (n - 1) for i in range(n)] if mode == "down" else [total * i / (n - 1) for i in range(n)]
        series = [{"name": "이상선", "x": x, "y": ideal, "color": "#94a3b8", "dash": [6, 4]},
                  {"name": "실제", "x": x, "y": actual, "style": "step", "color": "#2563eb"}]
        scope = payload.get("scope")
        if scope:
            series.append({"name": "범위", "x": x, "y": [float(v) for v in scope], "style": "step", "color": "#dc2626", "dash": [3, 3]})
        ax = payload.get("axes") or {}
        opts = {"axes": {"x": {"label": "기간", "unit": "", "categories": periods},
                         "y": {"label": str((ax.get("y") or {}).get("label", "잔여")),
                               "unit": str((ax.get("y") or {}).get("unit", "SP"))}},
                "title": f"{payload.get('title') or ('번다운' if mode == 'down' else '번업')} 차트"}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("periods") or []):
            miss.append({"field": "periods", "why": "기간이 없음", "ask": "periods:[…] 를 주세요."})
        if payload.get("total_scope") is None or not (payload.get("actual") or []):
            miss.append({"field": "total_scope", "why": "범위/실적 미상",
                         "ask": "total_scope + actual:[기간별 잔여(또는 누적)] 를 주세요 (mode:'down'|'up')."})
        return miss


class DQDVRecipe(Recipe):
    type_name = "dqdv-curve"

    def normalize(self, payload, resolved):
        win = int(payload.get("smooth_window", 5))
        series, markers = [], []
        palette = ["#2563eb", "#f59e0b", "#16a34a", "#dc2626"]
        for ci, cyc in enumerate(payload["cycles"]):
            data = [[float(p[0]), float(p[1])] for p in cyc["data"]]
            r = _t3.dqdv([p[0] for p in data], [p[1] for p in data], win)
            series.append({"name": str(cyc.get("name", f"cycle {ci + 1}")), "x": r["v"], "y": r["dqdv"],
                           "color": palette[ci % len(palette)]})
        opts = {"axes": {"x": {"label": "전압 V", "unit": "V"}, "y": {"label": "dQ/dV", "unit": "Ah/V"}},
                "title": str(payload.get("title") or "dQ/dV 미분용량 곡선 (ICA)")}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        if not (payload.get("cycles") or []):
            return [{"field": "cycles", "why": "사이클 데이터가 없음",
                     "ask": "cycles:[{name, data:[[V(V), Q(Ah)],…]}] 를 주세요 (+smooth_window)."}]
        return []


class TorqueAngleRecipe(Recipe):
    type_name = "torque-angle-curve"

    def normalize(self, payload, resolved):
        data = [[float(p[0]), float(p[1])] for p in payload["data"]]
        ang = [p[0] for p in data]
        tq = [p[1] for p in data]
        y = _t3.torque_yield(ang, tq)
        series = [{"name": "토크", "x": ang, "y": tq, "color": "#2563eb"}]
        pcfg = {}
        markers = []
        if y["yield_angle"] is not None:
            markers.append({"x": y["yield_angle"], "y": y["yield_torque"],
                            "label": f"항복 {_fmt(y['yield_torque'])}", "color": "#dc2626"})
        snug = payload.get("snug_torque")
        lines = []
        if snug is not None:
            lines.append({"axis": "y", "value": float(snug), "label": f"스너그 {snug:g}", "color": "#16a34a"})
        if markers:
            pcfg["named-markers"] = {"markers": markers}
        if lines:
            pcfg["threshold-lines"] = {"lines": lines}
        opts = {"axes": {"x": {"label": "회전각", "unit": "°"}, "y": {"label": "토크", "unit": "N·m"}},
                "title": str(payload.get("title") or "토크-각도 체결 곡선")}
        if pcfg:
            opts["pluginConfig"] = pcfg
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        if len(payload.get("data") or []) < 4:
            return [{"field": "data", "why": "토크-각도 데이터 부족",
                     "ask": "data:[[회전각(°), 토크(N·m)],…] 를 주세요 (4점 이상, +snug_torque)."}]
        return []


class CreepCurveRecipe(Recipe):
    type_name = "creep-curve"

    def normalize(self, payload, resolved):
        series, mn = [], None
        for si, s in enumerate(payload["series"]):
            data = [[float(p[0]), float(p[1])] for p in s["data"]]
            xs = [p[0] for p in data]
            ys = [p[1] for p in data]
            series.append({"name": str(s.get("name", f"조건 {si + 1}")), "x": xs, "y": ys})
            if mn is None:
                mn = _t3.min_creep_rate(xs, ys)
                mn["xmax"] = xs[-1]
        pcfg = {}
        if mn:
            pcfg["named-markers"] = {"markers": [{"x": mn["t_at_min"], "y": mn["strain_at_min"],
                                     "label": f"최소 크리프율 {_fmt(mn['min_rate'])}/h", "color": "#dc2626"}]}
            tm = mn["xmax"]
            pcfg["region-shading"] = {"regions": [
                {"x0": 0, "x1": tm * 0.15, "label": "1차(천이)"},
                {"x0": tm * 0.15, "x1": tm * 0.8, "label": "2차(정상)"},
                {"x0": tm * 0.8, "x1": tm, "label": "3차(가속)"}]}
        ax = payload.get("axes") or {}
        opts = {"axes": {"x": {"label": "시간", "unit": str((ax.get("x") or {}).get("unit", "h"))},
                         "y": {"label": "변형률", "unit": str((ax.get("y") or {}).get("unit", ""))}},
                "title": str(payload.get("title") or "크리프 곡선")}
        if pcfg:
            opts["pluginConfig"] = pcfg
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("series") or []):
            miss.append({"field": "series", "why": "크리프 데이터가 없음",
                         "ask": "series:[{name, data:[[시간(h), 변형률],…]}] 를 주세요."})
        if "unit" not in ((payload.get("axes") or {}).get("y") or {}):
            miss.append({"field": "axes.y.unit", "why": "변형률 단위 미상",
                         "ask": "변형률 단위를 axes.y.unit 으로 주세요 (무차원이면 '')."})
        return miss


class EquivalenceTOSTRecipe(Recipe):
    type_name = "equivalence-tost-plot"

    def normalize(self, payload, resolved):
        ests = payload["estimates"]
        b = payload["bounds"]
        lo, hi = float(b["lower"]), float(b["upper"])
        cats = [str(e.get("name", f"E{i + 1}")) for i, e in enumerate(ests)]
        unit = str(payload.get("unit", ""))
        series, markers = [], []
        for i, e in enumerate(ests):
            cl, ch = float(e["ci_low"]), float(e["ci_high"])
            equiv = (cl >= lo and ch <= hi)
            col = "#16a34a" if equiv else "#dc2626"
            series.append({"name": str(e.get("name", f"E{i + 1}")), "x": [i, i], "y": [cl, ch], "color": col})
            markers.append({"x": i, "y": float(e["point"]), "label": "등가" if equiv else "비등가", "color": col})
        lines = [{"axis": "y", "value": lo, "label": f"하한 {lo:g}", "color": "#dc2626", "dash": [4, 3]},
                 {"axis": "y", "value": hi, "label": f"상한 {hi:g}", "color": "#dc2626", "dash": [4, 3]}]
        opts = {"axes": {"x": {"label": "추정치", "unit": "", "categories": cats},
                         "y": {"label": "효과", "unit": unit}},
                "title": str(payload.get("title") or "등가성(TOST) 플롯"),
                "pluginConfig": {"threshold-lines": {"lines": lines}, "named-markers": {"markers": markers}}}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("estimates") or []):
            miss.append({"field": "estimates", "why": "추정치가 없음",
                         "ask": "estimates:[{name,point,ci_low,ci_high}] 를 주세요."})
        b = payload.get("bounds") or {}
        if b.get("lower") is None or b.get("upper") is None:
            miss.append({"field": "bounds", "why": "등가한계 미상",
                         "ask": "bounds:{lower,upper}(등가한계 ±Δ)와 unit 을 주세요."})
        return miss
