"""T2 표준 보고 그래프 (배치 A, 11종) — 전부 기존 엔진(xy-core / review-matrix)과 플러그인
(threshold-lines / region-shading / named-markers / area-fill) 재사용. 엔진 신규작업 0.
판정·교차·피팅이 붙는 정형 그림."""

from __future__ import annotations

from ..postprocess import domain_t2 as _t2
from .base import Recipe
from .matrix_compare import MatrixRecipe


def _fmt(v, nd=3):
    return "—" if v is None else f"{v:.{nd}g}"


class EWMAChartRecipe(Recipe):
    type_name = "ewma-chart"

    def normalize(self, payload, resolved):
        vals = [float(v) for v in payload["values"]]
        r = _t2.ewma(vals, float(payload.get("lambda", 0.2)),
                     payload.get("target"), payload.get("sigma"))
        x = list(range(1, len(vals) + 1))
        ax = payload.get("axes") or {}
        unit = str((ax.get("y") or {}).get("unit", ""))
        series = [
            {"name": "원데이터", "x": x, "y": vals, "style": "markers", "color": "#94a3b8"},
            {"name": "EWMA", "x": x, "y": r["z"], "style": "line+markers", "color": "#2563eb"},
            {"name": "UCL", "x": x, "y": r["ucl"], "color": "#dc2626", "dash": [4, 3]},
            {"name": "LCL", "x": x, "y": r["lcl"], "color": "#dc2626", "dash": [4, 3]},
            {"name": "CL", "x": [x[0], x[-1]], "y": [r["center"], r["center"]], "color": "#16a34a", "dash": [6, 4]},
        ]
        opts = {"axes": {"x": {"label": "표본", "unit": ""}, "y": {"label": "측정값", "unit": unit}},
                "title": f"{payload.get('title') or 'EWMA 관리도'} (λ={payload.get('lambda', 0.2)}) — 이탈 {len(r['violations'])}점"}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if len(payload.get("values") or []) < 3:
            miss.append({"field": "values", "why": "관리할 측정값이 없음",
                         "ask": "values:[…] 를 주세요 (lambda 기본 0.2)."})
        if "unit" not in ((payload.get("axes") or {}).get("y") or {}):
            miss.append({"field": "axes.y.unit", "why": "측정량 단위 미상",
                         "ask": "측정량의 단위를 axes.y.unit 으로 주세요 (무차원이면 '')."})
        return miss


class OCCurveRecipe(Recipe):
    type_name = "oc-curve"

    def normalize(self, payload, resolved):
        n, c = int(payload["n"]), int(payload["c"])
        r = _t2.oc_curve(n, c)
        markers = []
        aql, ltpd = payload.get("aql"), payload.get("ltpd")
        if aql is not None:
            markers.append({"x": float(aql), "y": _t2._interp_x_at_y(r["pa"], r["p"], float(aql)) and 0,
                            "label": f"AQL={aql}", "color": "#16a34a"})
        lines = []
        if aql is not None:
            lines.append({"axis": "x", "value": float(aql), "label": f"AQL {aql}", "color": "#16a34a"})
        if ltpd is not None:
            lines.append({"axis": "x", "value": float(ltpd), "label": f"LTPD {ltpd}", "color": "#dc2626"})
        lines += [{"axis": "y", "value": 0.95, "label": "Pa=0.95 (α)", "color": "#16a34a", "dash": [2, 3]},
                  {"axis": "y", "value": 0.10, "label": "Pa=0.10 (β)", "color": "#dc2626", "dash": [2, 3]}]
        opts = {"axes": {"x": {"label": "로트 불량률 p", "unit": ""},
                         "y": {"label": "합격 확률 Pa", "unit": ""}},
                "title": f"{payload.get('title') or 'OC 곡선'} (n={n}, c={c})",
                "pluginConfig": {"threshold-lines": {"lines": lines}}}
        return {"engine": resolved.engine,
                "assets": {"series": [{"name": "Pa(p)", "x": r["p"], "y": r["pa"], "color": "#2563eb"}]},
                "options": opts}

    def structural_requires(self, payload):
        if payload.get("n") is None or payload.get("c") is None:
            return [{"field": "n", "why": "샘플링 플랜 미상",
                     "ask": "샘플 크기 n과 합격판정개수 c를 주세요 (+aql, ltpd 선택)."}]
        return []


class ROCPRCurveRecipe(Recipe):
    type_name = "roc-pr-curve"

    def normalize(self, payload, resolved):
        mode = str(payload.get("mode", "roc"))
        if payload.get("y_true") and payload.get("y_score"):
            r = _t2.roc_pr(payload["y_true"], payload["y_score"], mode)
            xs, ys = r["x"], r["y"]
            auc, best = r["auc"], r.get("best")
        else:
            pts = payload["points"]
            xs = [float(p[0]) for p in pts]
            ys = [float(p[1]) for p in pts]
            auc = sum((xs[i] - xs[i - 1]) * (ys[i] + ys[i - 1]) / 2 for i in range(1, len(xs)))
            best = None
        series = [{"name": ("ROC" if mode == "roc" else "PR"), "x": xs, "y": ys, "color": "#2563eb"}]
        pcfg = {}
        if mode == "roc":
            series.append({"name": "무작위", "x": [0, 1], "y": [0, 1], "color": "#94a3b8", "dash": [4, 4]})
            if best:
                pcfg["named-markers"] = {"markers": [{"x": best[1], "y": best[2],
                                         "label": "Youden 최적", "color": "#16a34a"}]}
        xa = {"label": "FPR (1−특이도)" if mode == "roc" else "Recall", "unit": ""}
        ya = {"label": "TPR (민감도)" if mode == "roc" else "Precision", "unit": ""}
        opts = {"axes": {"x": xa, "y": ya},
                "title": f"{payload.get('title') or (mode.upper() + ' 곡선')} — AUC={_fmt(auc)}"}
        if pcfg:
            opts["pluginConfig"] = pcfg
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        ok = (payload.get("y_true") and payload.get("y_score")) or (len(payload.get("points") or []) >= 2)
        if not ok:
            return [{"field": "y_true", "why": "ROC/PR 입력 부족",
                     "ask": "y_true:[0/1], y_score:[점수] 를 주거나 points:[[fpr,tpr],…] 를 주세요."}]
        return []


class BathtubCurveRecipe(Recipe):
    type_name = "bathtub-curve"

    def normalize(self, payload, resolved):
        if payload.get("phases"):
            r = _t2.bathtub(payload["phases"], float(payload.get("tmax", 100)))
            xs, ys = r["t"], r["hazard"]
        else:
            data = [[float(p[0]), float(p[1])] for p in payload["data"]]
            xs = [p[0] for p in data]
            ys = [p[1] for p in data]
        tmax = xs[-1] if xs else 1
        regs = [{"x0": 0, "x1": tmax * 0.2, "label": "초기고장 (감소)"},
                {"x0": tmax * 0.2, "x1": tmax * 0.75, "label": "우발고장 (일정)"},
                {"x0": tmax * 0.75, "x1": tmax, "label": "마모고장 (증가)"}]
        pcfg = {"region-shading": {"regions": regs}}
        bi = payload.get("burn_in_time")
        if bi is not None:
            pcfg["threshold-lines"] = {"lines": [{"axis": "x", "value": float(bi),
                                       "label": f"번인 {bi:g}", "color": "#dc2626"}]}
        opts = {"axes": {"x": {"label": "시간", "unit": str(payload.get("t_unit", "h"))},
                         "y": {"label": "고장률 λ(t)", "unit": "1/" + str(payload.get("t_unit", "h"))}},
                "title": str(payload.get("title") or "욕조곡선 (고장률)"), "pluginConfig": pcfg}
        return {"engine": resolved.engine,
                "assets": {"series": [{"name": "λ(t)", "x": xs, "y": ys, "color": "#2563eb"}]},
                "options": opts}

    def structural_requires(self, payload):
        if not payload.get("phases") and len(payload.get("data") or []) < 2:
            return [{"field": "phases", "why": "욕조곡선 정의가 없음",
                     "ask": "phases:[{beta,eta}×3] (+tmax) 또는 data:[[t,λ(t)],…] 를 주세요."}]
        return []


class CrowAMSAARecipe(Recipe):
    type_name = "crow-amsaa-growth"

    def normalize(self, payload, resolved):
        r = _t2.crow_amsaa(payload["failure_times"])
        series = [{"name": "누적 MTBF", "x": r["times"], "y": r["cum_mtbf"], "color": "#2563eb"},
                  {"name": "순간 MTBF", "x": r["times"], "y": r["inst_mtbf"], "color": "#f59e0b"}]
        pcfg = {}
        tgt = payload.get("target_mtbf")
        if tgt is not None:
            pcfg["threshold-lines"] = {"lines": [{"axis": "y", "value": float(tgt),
                                       "label": f"목표 MTBF {tgt:g}", "color": "#16a34a"}]}
        verdict = "성장중" if r["growing"] else "성장정체/악화"
        opts = {"axes": {"x": {"label": "누적 시험시간", "unit": str(payload.get("t_unit", "h")), "log": True},
                         "y": {"label": "MTBF", "unit": str(payload.get("t_unit", "h")), "log": True}},
                "title": f"{payload.get('title') or '신뢰도 성장'} — β={_fmt(r['beta'])} [{verdict}]"}
        if pcfg:
            opts["pluginConfig"] = pcfg
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        if len(payload.get("failure_times") or []) < 3:
            return [{"field": "failure_times", "why": "누적 고장시점이 부족",
                     "ask": "failure_times:[누적 고장시점…] 를 주세요 (3개 이상, +target_mtbf 선택)."}]
        return []


class MohrCircleRecipe(Recipe):
    type_name = "mohr-circle"

    def normalize(self, payload, resolved):
        unit = str(((payload.get("axes") or {}).get("unit", payload.get("unit", ""))))
        states = payload["states"]
        series, markers = [], []
        palette = ["#2563eb", "#f59e0b", "#16a34a", "#dc2626"]
        for i, st in enumerate(states):
            if "s1" in st and "s3" in st:
                s1, s3 = float(st["s1"]), float(st["s3"])
            else:
                sx, sy, txy = float(st["sx"]), float(st["sy"]), float(st.get("txy", 0))
                c = (sx + sy) / 2
                r = ((sx - sy) / 2) ** 2 + txy ** 2
                r = r ** 0.5
                s1, s3 = c + r, c - r
            m = _t2.mohr_circle(s1, s3)
            col = palette[i % len(palette)]
            series.append({"name": str(st.get("name", f"상태 {i + 1}")),
                           "x": [p[0] for p in m["points"]], "y": [p[1] for p in m["points"]], "color": col})
            markers.append({"x": m["center"], "y": 0, "label": f"c={_fmt(m['center'])}", "color": col})
        opts = {"axes": {"x": {"label": "수직응력 σ", "unit": unit}, "y": {"label": "전단응력 τ", "unit": unit}},
                "title": str(payload.get("title") or "모어 원"),
                "equalAspect": True, "pluginConfig": {"named-markers": {"markers": markers}}}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("states") or []):
            miss.append({"field": "states", "why": "응력상태가 없음",
                         "ask": "states:[{s1,s3} 또는 {sx,sy,txy}] 를 주세요."})
        if "unit" not in (payload.get("axes") or {}) and not payload.get("unit"):
            miss.append({"field": "unit", "why": "응력 단위 미상",
                         "ask": "응력 단위를 unit(또는 axes.unit)으로 주세요 (예: 'MPa')."})
        return miss


class BoilingCurveRecipe(Recipe):
    type_name = "boiling-curve"

    def normalize(self, payload, resolved):
        series, chf = [], None
        for i, s in enumerate(payload["series"]):
            data = [[float(p[0]), float(p[1])] for p in s["data"]]
            xs = [p[0] for p in data]
            ys = [p[1] for p in data]
            series.append({"name": str(s.get("name", f"곡선 {i + 1}")), "x": xs, "y": ys})
            if chf is None:
                c = _t2.detect_chf(xs, ys)
                chf = c
        pcfg = {}
        if chf:
            pcfg["named-markers"] = {"markers": [{"x": chf["dt"], "y": chf["q"],
                                     "label": f"CHF q″={_fmt(chf['q'])}", "color": "#dc2626"}]}
        regs = [{"x0": float(r["from_dT"]), "x1": float(r["to_dT"]), "label": str(r.get("name", ""))}
                for r in (payload.get("regimes") or [])]
        if regs:
            pcfg["region-shading"] = {"regions": regs}
        opts = {"axes": {"x": {"label": "벽면 과열도 ΔT_sat", "unit": "K", "log": True},
                         "y": {"label": "열유속 q″", "unit": "W/cm²", "log": True}},
                "title": str(payload.get("title") or "비등곡선 (Nukiyama)")}
        if pcfg:
            opts["pluginConfig"] = pcfg
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        if not (payload.get("series") or []):
            return [{"field": "series", "why": "비등곡선 데이터가 없음",
                     "ask": "series:[{name, data:[[ΔTsat(K), q″(W/cm²)],…]}] 를 주세요."}]
        return []


class GateChargeRecipe(Recipe):
    type_name = "gate-charge-curve"

    def normalize(self, payload, resolved):
        data = [[float(p[0]), float(p[1])] for p in payload["data"]]
        qg = [p[0] for p in data]
        vgs = [p[1] for p in data]
        pl = _t2.miller_plateau(qg, vgs)
        series = [{"name": "Vgs", "x": qg, "y": vgs, "color": "#2563eb"}]
        pcfg = {}
        title_tail = ""
        if pl:
            pcfg["named-markers"] = {"markers": [
                {"x": pl["q_start"], "y": pl["v_plateau"], "label": f"Qgs={_fmt(pl['qgs'])}", "color": "#16a34a"},
                {"x": pl["q_end"], "y": pl["v_plateau"], "label": f"Qgd={_fmt(pl['qgd'])}", "color": "#dc2626"}]}
            pcfg["region-shading"] = {"regions": [{"x0": pl["q_start"], "x1": pl["q_end"], "label": "Miller plateau"}]}
            title_tail = f" — Qg={_fmt(pl['qg_total'])}"
        opts = {"axes": {"x": {"label": "게이트 차지 Qg", "unit": "nC"}, "y": {"label": "Vgs", "unit": "V"}},
                "title": f"{payload.get('title') or '게이트 차지 곡선'}{title_tail}"}
        if pcfg:
            opts["pluginConfig"] = pcfg
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        if len(payload.get("data") or []) < 4:
            return [{"field": "data", "why": "게이트 차지 곡선 데이터가 부족",
                     "ask": "data:[[Qg(nC), Vgs(V)],…] 를 주세요 (4점 이상)."}]
        return []


class ImmunityProfileRecipe(Recipe):
    type_name = "immunity-level-profile"

    def normalize(self, payload, resolved):
        pts = payload["points"]
        verdict_col = {"A": "#16a34a", "B": "#f59e0b", "C": "#dc2626", "F": "#dc2626"}
        markers = [{"x": float(p[0]), "y": float(p[1]),
                    "label": str(p[2]) if len(p) > 2 else "", "color": verdict_col.get(str(p[2]) if len(p) > 2 else "", "#2563eb")}
                   for p in pts]
        series = [{"name": "측정 레벨", "x": [float(p[0]) for p in pts], "y": [float(p[1]) for p in pts],
                   "style": "markers", "color": "#94a3b8"}]
        req = payload.get("required") or []
        if req:
            rx, ry = [], []
            for r in req:
                rx += [float(r["f0"]), float(r["f1"])]
                ry += [float(r["level"]), float(r["level"])]
            series.append({"name": "요구 내성", "x": rx, "y": ry, "style": "step", "color": "#dc2626", "dash": [5, 4]})
        bad = [str(p[2]) for p in pts if len(p) > 2 and str(p[2]) in ("C", "F")]
        opts = {"axes": {"x": {"label": "주파수", "unit": "MHz", "log": True},
                         "y": {"label": "내성 레벨", "unit": "V/m"}},
                "title": f"{payload.get('title') or '내성 시험 프로파일'} — 부적합 {len(bad)}건",
                "pluginConfig": {"named-markers": {"markers": markers}}}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        if not (payload.get("points") or []):
            return [{"field": "points", "why": "내성 측정점이 없음",
                     "ask": "points:[[MHz, level, 'A'|'B'|'C'|'F'],…] 를 주세요 (+required 구간 선택)."}]
        return []


class ResourceHistogramRecipe(Recipe):
    type_name = "resource-histogram"

    def normalize(self, payload, resolved):
        periods = [str(p) for p in payload["periods"]]
        xs = list(range(len(periods)))
        res = payload["resources"]
        cap = payload["capacity"]
        series = []
        palette = ["#2563eb", "#f59e0b", "#16a34a", "#7c3aed", "#0891b2"]
        totals = [0.0] * len(periods)
        for i, r in enumerate(res):
            hrs = [float(v) for v in r["hours"]]
            for k in range(len(periods)):
                totals[k] += hrs[k] if k < len(hrs) else 0
            series.append({"name": str(r.get("name", f"자원{i + 1}")), "x": xs, "y": hrs,
                           "style": "bar", "color": palette[i % len(palette)]})
        cap_arr = cap if isinstance(cap, list) else [float(cap)] * len(periods)
        over = [k for k in range(len(periods)) if totals[k] > cap_arr[k]]
        series.append({"name": "용량", "x": xs, "y": cap_arr, "style": "step", "color": "#dc2626", "dash": [5, 4]})
        ax = payload.get("axes") or {}
        opts = {"axes": {"x": {"label": "기간", "unit": "", "categories": periods},
                         "y": {"label": str((ax.get("y") or {}).get("label", "투입")),
                               "unit": str((ax.get("y") or {}).get("unit", "h"))}},
                "barMode": "stacked",
                "title": f"{payload.get('title') or '자원 히스토그램'} — 초과 {len(over)}기간"}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("periods") or []):
            miss.append({"field": "periods", "why": "기간이 없음", "ask": "periods:[라벨…] 를 주세요."})
        if not (payload.get("resources") or []):
            miss.append({"field": "resources", "why": "자원 투입이 없음",
                         "ask": "resources:[{name, hours:[기간별]}] 를 주세요."})
        if payload.get("capacity") is None:
            miss.append({"field": "capacity", "why": "용량 미상",
                         "ask": "capacity(상수 또는 기간별 배열)를 주세요."})
        return miss


class RACIMatrixRecipe(Recipe):
    type_name = "raci-matrix"
    _matrix = MatrixRecipe()

    def normalize(self, payload, resolved):
        roles = [str(r) for r in payload["roles"]]
        tasks = [str(t) for t in payload["tasks"]]
        amap = {}
        for a in payload.get("assignments") or []:
            amap[(str(a["task"]), str(a["role"]))] = str(a["code"]).upper()
        states = [{"id": f"r{j}", "label": role} for j, role in enumerate(roles)]
        items = []
        for i, task in enumerate(tasks):
            cells = {}
            for j, role in enumerate(roles):
                code = amap.get((task, role))
                cells[f"r{j}"] = {"kind": "badges", "tags": [code]} if code else {"kind": "empty"}
            items.append({"id": f"t{i}", "label": task, "type": "row", "cells": cells})
        mp = {"title": str(payload.get("title") or "RACI 책임할당 매트릭스"),
              "states": states, "items": items, "options": {"diff": False}}
        return self._matrix.normalize(mp, resolved)

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("tasks") or []) or not (payload.get("roles") or []):
            miss.append({"field": "tasks", "why": "작업/역할이 없음",
                         "ask": "tasks:[작업…], roles:[역할…], assignments:[{task,role,code:'R|A|C|I'}] 를 주세요."})
            return miss
        # AIAG/PMBOK: 작업마다 A(Accountable)는 정확히 1명
        a_count = {}
        for a in payload.get("assignments") or []:
            if str(a.get("code", "")).upper() == "A":
                a_count[str(a["task"])] = a_count.get(str(a["task"]), 0) + 1
        bad = [t for t in (str(x) for x in payload["tasks"]) if a_count.get(t, 0) != 1]
        if bad:
            miss.append({"field": "assignments", "why": f"A(책임)가 정확히 1명이 아닌 작업: {', '.join(bad[:5])}",
                         "ask": "각 작업에 Accountable(A)는 정확히 1명이어야 합니다. 할당을 보정해 주세요."})
        return miss
