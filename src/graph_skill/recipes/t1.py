"""T1 표준 보고 그래프 10종 — 전부 기존 엔진(xy-core / review-matrix)과 플러그인
(threshold-lines / region-shading / named-markers / waterfall) 재사용. 엔진 신규작업 0.
판정(교차점 보간·마진·룩업)이 붙는 정형 그림: 곡선만 그리던 기존 타입과의 차별점."""

from __future__ import annotations

from ..postprocess import domain_t1 as _t1
from .base import Recipe
from .matrix_compare import MatrixRecipe


def _fmt(v, nd=1):
    return "—" if v is None else f"{v:.{nd}f}"


def _limit_at(segs, f):
    for s in segs:
        if s["f0"] <= f <= s["f1"]:
            if s["f1"] == s["f0"]:
                return s["level"]
            t = (f - s["f0"]) / (s["f1"] - s["f0"])
            return s["level"] + t * (s.get("level1", s["level"]) - s["level"])
    return None


def _limit_series(segs, name, color):
    x, y = [], []
    for s in segs:
        x += [s["f0"], s["f1"]]
        y += [s["level"], s.get("level1", s["level"])]
    return {"name": name, "x": x, "y": y, "color": color, "dash": [6, 4]}


# CISPR 32 Class B 전도성 방출 한계 (dBμV, 150kHz–30MHz) — QP / AVG
_CISPR32_B = {
    "qp": [{"f0": 0.15e6, "f1": 0.5e6, "level": 66, "level1": 56},
           {"f0": 0.5e6, "f1": 5e6, "level": 56, "level1": 56},
           {"f0": 5e6, "f1": 30e6, "level": 60, "level1": 60}],
    "avg": [{"f0": 0.15e6, "f1": 0.5e6, "level": 56, "level1": 46},
            {"f0": 0.5e6, "f1": 5e6, "level": 46, "level1": 46},
            {"f0": 5e6, "f1": 30e6, "level": 50, "level1": 50}],
}


class LoopGainMarginRecipe(Recipe):
    type_name = "loop-gain-margin"

    def normalize(self, payload, resolved):
        f = [float(x) for x in payload["freq"]]
        g = [float(x) for x in payload["gain_db"]]
        ph = [float(x) for x in payload["phase_deg"]]
        m = _t1.stability_margins(f, g, ph)
        series = [{"name": "이득", "x": f, "y": g, "color": "#2563eb"},
                  {"name": "위상", "x": f, "y": ph, "axis": "right", "color": "#f59e0b"}]
        lines = [{"axis": "y", "value": 0, "label": "0 dB", "color": "#16a34a"},
                 {"axis": "y2", "value": -180, "label": "−180°", "color": "#dc2626"}]
        pcfg = {"threshold-lines": {"lines": lines}}
        if m["f_gc"] is not None:
            pcfg["named-markers"] = {"markers": [{"x": m["f_gc"], "y": 0,
                                     "label": f"PM={_fmt(m['pm_deg'])}°", "color": "#16a34a"}]}
        verdict = "안정" if m["stable"] else "불안정"
        opts = {"axes": {"x": {"label": "주파수", "unit": "Hz", "log": True},
                         "y": {"label": "개루프 이득", "unit": "dB"},
                         "y2": {"label": "위상", "unit": "°"}},
                "title": f"{payload.get('title') or '루프 안정도'} — PM={_fmt(m['pm_deg'])}° "
                         f"GM={_fmt(m['gm_db'])} dB [{verdict}]",
                "pluginConfig": pcfg}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        for k in ("freq", "gain_db", "phase_deg"):
            if len(payload.get(k) or []) < 2:
                return [{"field": k, "why": "개루프 보드 데이터 부족",
                         "ask": "개루프 응답을 주세요: freq:[Hz], gain_db:[dB], phase_deg:[°] (같은 길이, 2점 이상)."}]
        return []


class ConductedEmissionRecipe(Recipe):
    type_name = "conducted-emission"

    def normalize(self, payload, resolved):
        spec = [[float(p[0]), float(p[1])] for p in payload["spectrum"]]
        xs = [p[0] for p in spec]
        ys = [p[1] for p in spec]
        preset = payload.get("preset")
        qp = payload.get("qp_limit") or (_CISPR32_B["qp"] if preset == "cispr32_b" else None)
        avg = payload.get("avg_limit") or (_CISPR32_B["avg"] if preset == "cispr32_b" else None)
        series = [{"name": "측정", "x": xs, "y": ys, "color": "#2563eb"}]
        worst = None
        for segs, nm, col in ((qp, "QP 한계", "#dc2626"), (avg, "AVG 한계", "#f59e0b")):
            if segs:
                series.append(_limit_series(segs, nm, col))
                for p in spec:
                    lim = _limit_at(segs, p[0])
                    if lim is not None:
                        mar = lim - p[1]
                        worst = mar if worst is None else min(worst, mar)
        verdict = "PASS" if (worst is None or worst >= 0) else "FAIL"
        opts = {"axes": {"x": {"label": "주파수", "unit": "Hz", "log": True},
                         "y": {"label": "전도 방출", "unit": "dBμV"}},
                "title": f"{payload.get('title') or '전도성 방출'} — worst margin {_fmt(worst)} dB [{verdict}]"}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if len(payload.get("spectrum") or []) < 2:
            miss.append({"field": "spectrum", "why": "전도 스펙트럼이 없음",
                         "ask": "spectrum:[[Hz, dBμV], …] 를 주세요."})
        if not (payload.get("qp_limit") or payload.get("avg_limit") or payload.get("preset")):
            miss.append({"field": "qp_limit", "why": "한계선 미상",
                         "ask": "한계선을 주세요: preset:'cispr32_b' 또는 qp_limit/avg_limit:[{f0,f1,level,level1?}]."})
        return miss


class TDRImpedanceRecipe(Recipe):
    type_name = "tdr-impedance-profile"

    def normalize(self, payload, resolved):
        prof = [[float(p[0]), float(p[1])] for p in payload["profile"]]
        xs = [p[0] for p in prof]
        ys = [p[1] for p in prof]
        z0 = float(payload["z0"])
        tol = float(payload.get("tol_pct", 10)) / 100.0
        hi, lo = z0 * (1 + tol), z0 * (1 - tol)
        viol = [{"x": p[0], "y": p[1], "label": "일탈", "color": "#dc2626"}
                for p in prof if p[1] > hi or p[1] < lo]
        lines = [{"axis": "y", "value": z0, "label": f"Z0={z0:g}Ω", "color": "#16a34a"},
                 {"axis": "y", "value": hi, "label": f"+{tol*100:g}%", "color": "#dc2626"},
                 {"axis": "y", "value": lo, "label": f"−{tol*100:g}%", "color": "#dc2626"}]
        pcfg = {"threshold-lines": {"lines": lines}}
        regs = [{"x0": float(z["x0"]), "x1": float(z["x1"]), "label": str(z.get("label", ""))}
                for z in (payload.get("zones") or [])]
        if regs:
            pcfg["region-shading"] = {"regions": regs}
        if viol:
            pcfg["named-markers"] = {"markers": viol}
        ax = payload.get("axes") or {}
        xu = str((ax.get("x") or {}).get("unit", "mm"))
        opts = {"axes": {"x": {"label": str((ax.get("x") or {}).get("label", "거리")), "unit": xu},
                         "y": {"label": "임피던스", "unit": "Ω"}},
                "title": f"{payload.get('title') or 'TDR 임피던스 프로파일'} — 일탈 {len(viol)}점",
                "pluginConfig": pcfg}
        return {"engine": resolved.engine, "assets": {"series": [
            {"name": "Z(x)", "x": xs, "y": ys, "color": "#2563eb"}]}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if len(payload.get("profile") or []) < 2:
            miss.append({"field": "profile", "why": "임피던스 프로파일이 없음",
                         "ask": "profile:[[거리(또는 ns), Ω], …] 를 주세요."})
        if payload.get("z0") is None:
            miss.append({"field": "z0", "why": "목표 임피던스 미상",
                         "ask": "목표 특성임피던스 z0(Ω)를 주세요 (예: 85). tol_pct 기본 10%."})
        if "unit" not in ((payload.get("axes") or {}).get("x") or {}):
            miss.append({"field": "axes.x.unit", "why": "가로축 단위 미상(거리 mm? 시간 ns?)",
                         "ask": "axes.x={label,unit} 을 주세요 (거리면 'mm', 시간이면 'ns')."})
        return miss


class JitterBathtubRecipe(Recipe):
    type_name = "jitter-bathtub"

    def normalize(self, payload, resolved):
        target = float(payload.get("target_ber", 1e-12))
        if payload.get("rj_sigma") is not None and payload.get("dj") is not None:
            b = _t1.dual_dirac_bathtub(float(payload["rj_sigma"]), float(payload["dj"]), target)
            ui, bl, br = b["ui"], b["ber_left"], b["ber_right"]
            opening, xl, xr = b["eye_opening"], b["xl"], b["xr"]
        else:
            ui = [float(x) for x in payload["ui"]]
            bl = [float(x) for x in payload["ber_left"]]
            br = [float(x) for x in payload["ber_right"]]
            xl = _t1._log_crossing(ui, bl, target)
            xr = _t1._log_crossing(ui, br, target)
            opening = (xr - xl) if (xl is not None and xr is not None) else None
        eps = 1e-30
        series = [{"name": "BER 좌", "x": ui, "y": [max(v, eps) for v in bl], "color": "#2563eb"},
                  {"name": "BER 우", "x": ui, "y": [max(v, eps) for v in br], "color": "#f59e0b"}]
        pcfg = {"threshold-lines": {"lines": [
            {"axis": "y", "value": target, "label": f"target {target:g}", "color": "#dc2626"}]}}
        opts = {"axes": {"x": {"label": "샘플 위치", "unit": "UI"},
                         "y": {"label": "BER", "unit": "", "log": True}},
                "title": f"{payload.get('title') or '지터 배스터브'} — eye opening "
                         f"{_fmt(opening, 3) if opening is None else f'{opening:.3f}'} UI @ {target:g}",
                "pluginConfig": pcfg}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        has_curves = len(payload.get("ui") or []) >= 2 and payload.get("ber_left") and payload.get("ber_right")
        has_dd = payload.get("rj_sigma") is not None and payload.get("dj") is not None
        if not (has_curves or has_dd):
            return [{"field": "ui", "why": "BER 곡선 또는 dual-Dirac 파라미터 필요",
                     "ask": "ui:[UI], ber_left:[], ber_right:[] 를 주거나, rj_sigma(σ, UI)+dj(pk-pk, UI)를 주세요."}]
        return []


class BatteryCycleFadeRecipe(Recipe):
    type_name = "battery-cycle-fade"

    def normalize(self, payload, resolved):
        data = [[float(p[0]), float(p[1])] for p in payload["cycles"]]
        xs = [p[0] for p in data]
        ys = [p[1] for p in data]
        eol = float(payload.get("eol_pct", 80))
        cross = _t1.interp_crossing(xs, ys, eol)
        lines = [{"axis": "y", "value": eol, "label": f"EOL {eol:g}%", "color": "#dc2626"}]
        pcfg = {"threshold-lines": {"lines": lines}}
        if cross is not None:
            pcfg["named-markers"] = {"markers": [{"x": cross, "y": eol,
                                     "label": f"EOL @ {cross:.0f} cyc", "color": "#dc2626"}]}
        series = [{"name": "용량 유지율", "x": xs, "y": ys, "color": "#2563eb"}]
        ce = payload.get("coulombic_eff")
        if ce:
            series.append({"name": "쿨롱효율", "x": xs, "y": [float(v) for v in ce],
                           "axis": "right", "color": "#16a34a"})
        axes = {"x": {"label": "사이클", "unit": "회"}, "y": {"label": "용량 유지율", "unit": "%"}}
        if ce:
            axes["y2"] = {"label": "쿨롱효율", "unit": "%"}
        tail = f"EOL @ {cross:.0f} 사이클" if cross is not None else "EOL 미도달"
        return {"engine": resolved.engine, "assets": {"series": series},
                "options": {"axes": axes, "title": f"{payload.get('title') or '사이클 수명 열화'} — {tail}",
                            "pluginConfig": pcfg}}

    def structural_requires(self, payload):
        if len(payload.get("cycles") or []) < 2:
            return [{"field": "cycles", "why": "사이클 열화 데이터가 없음",
                     "ask": "cycles:[[사이클, 용량유지율%], …] 를 주세요 (EOL 기본 80%)."}]
        return []


class CCCVChargeRecipe(Recipe):
    type_name = "cc-cv-charge-profile"

    def normalize(self, payload, resolved):
        t = [float(x) for x in payload["time"]]
        i = [float(x) for x in payload["current"]]
        v = [float(x) for x in payload["voltage"]]
        series = [{"name": "전류", "x": t, "y": i, "color": "#2563eb"},
                  {"name": "전압", "x": t, "y": v, "axis": "right", "color": "#f59e0b"}]
        pcfg = {}
        vset = payload.get("v_set")
        if vset is not None:
            t_sw = _t1.interp_crossing(t, v, float(vset))  # CC→CV: 전압이 v_set 도달
            if t_sw is not None:
                pcfg["region-shading"] = {"regions": [
                    {"x0": t[0], "x1": t_sw, "label": "CC"},
                    {"x0": t_sw, "x1": t[-1], "label": "CV"}]}
                pcfg["threshold-lines"] = {"lines": [
                    {"axis": "y2", "value": float(vset), "label": f"V_set {vset:g}", "color": "#dc2626"}]}
        ax = payload.get("axes") or {}
        opts = {"axes": {"x": {"label": "시간", "unit": str((ax.get("x") or {}).get("unit", "min"))},
                         "y": {"label": "전류", "unit": "A"},
                         "y2": {"label": "전압", "unit": "V"}},
                "title": str(payload.get("title") or "CC-CV 충전 프로파일")}
        if pcfg:
            opts["pluginConfig"] = pcfg
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        for k in ("time", "current", "voltage"):
            if len(payload.get(k) or []) < 2:
                return [{"field": k, "why": "충전 프로파일 데이터 부족",
                         "ask": "time:[], current:[A], voltage:[V] 를 같은 길이로 주세요 (+ v_set 권장)."}]
        return []


class ThermalStackRecipe(Recipe):
    type_name = "thermal-resistance-stack"

    def normalize(self, payload, resolved):
        power = float(payload["power_w"])
        nodes = payload["nodes"]
        amb = float(payload.get("ambient_temp", 25))
        st = _t1.thermal_stack(power, nodes, amb)
        bars, dx, dy, base = [], [], [], amb
        for i, (n, d) in enumerate(zip(nodes, reversed(st["deltas"]))):  # ambient→junction 누적
            top = base + d
            bars.append({"x": i, "base": base, "top": top, "kind": "inc"})
            dx += [i, i]
            dy += [base, top]
            base = top
        tj = payload.get("tj_max")
        pcfg = {"waterfall": {"bars": bars}}
        title_tail = f"Tj={st['t_junction']:.1f}°C"
        if tj is not None:
            margin = float(tj) - st["t_junction"]
            pcfg["threshold-lines"] = {"lines": [
                {"axis": "y", "value": float(tj), "label": f"Tj_max {tj:g}°C", "color": "#dc2626"}]}
            title_tail += f", margin {margin:+.1f}°C [{'PASS' if margin >= 0 else 'FAIL'}]"
        labels = [str(n.get("name", f"R{i+1}")) for i, n in enumerate(nodes)]
        opts = {"axes": {"x": {"label": "열저항 노드", "unit": "", "categories": list(reversed(labels))},
                         "y": {"label": "온도", "unit": "°C"}},
                "title": f"{payload.get('title') or '열저항 분해 스택'} — {title_tail}",
                "pluginConfig": pcfg}
        return {"engine": resolved.engine,
                "assets": {"series": [{"name": "_wf", "x": dx, "y": dy, "style": "none"}]},
                "options": opts}

    def structural_requires(self, payload):
        miss = []
        if payload.get("power_w") is None:
            miss.append({"field": "power_w", "why": "소비전력 미상",
                         "ask": "소비전력 power_w(W)를 주세요."})
        if len(payload.get("nodes") or []) < 1:
            miss.append({"field": "nodes", "why": "열저항 노드가 없음",
                         "ask": "nodes:[{name, r(°C/W)}, …] 를 junction→ambient 순서로 주세요 (+ ambient_temp, tj_max 권장)."})
        return miss


class HardnessProfileRecipe(Recipe):
    type_name = "hardness-profile"

    def normalize(self, payload, resolved):
        data = [[float(p[0]), float(p[1])] for p in payload["depth"]]
        xs = [p[0] for p in data]
        ys = [p[1] for p in data]
        ax = payload.get("axes") or {}
        hu = str((ax.get("y") or {}).get("unit"))
        pcfg = {}
        lim = payload.get("limit_hardness")
        markers = []
        if lim is not None:
            cross = _t1.interp_crossing(xs, ys, float(lim))
            pcfg["threshold-lines"] = {"lines": [
                {"axis": "y", "value": float(lim), "label": f"한계 {lim:g} {hu}", "color": "#dc2626"}]}
            if cross is not None:
                markers.append({"x": cross, "y": float(lim), "label": f"CHD {cross:.2f}mm", "color": "#dc2626"})
        regs = [{"x0": float(z["x0"]), "x1": float(z["x1"]), "label": str(z.get("label", ""))}
                for z in (payload.get("zones") or [])]
        if regs:
            pcfg["region-shading"] = {"regions": regs}
        if markers:
            pcfg["named-markers"] = {"markers": markers}
        chd = markers[0]["label"] if markers else ""
        opts = {"axes": {"x": {"label": "깊이", "unit": "mm"}, "y": {"label": "경도", "unit": hu}},
                "title": f"{payload.get('title') or '경도 프로파일'}{(' — ' + chd) if chd else ''}",
                "pluginConfig": pcfg}
        return {"engine": resolved.engine, "assets": {"series": [
            {"name": "경도", "x": xs, "y": ys, "color": "#2563eb"}]}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if len(payload.get("depth") or []) < 2:
            miss.append({"field": "depth", "why": "경도 프로파일이 없음",
                         "ask": "depth:[[깊이mm, 경도], …] 를 주세요."})
        if "unit" not in ((payload.get("axes") or {}).get("y") or {}):
            miss.append({"field": "axes.y.unit", "why": "경도 척도 미상(HV? HRC? HB?)",
                         "ask": "경도 척도를 axes.y.unit 으로 주세요 (예: 'HV1'). 한계경도 limit_hardness 권장."})
        return miss


class XbarRChartRecipe(Recipe):
    type_name = "xbar-r-chart"
    _matrix = MatrixRecipe()

    def normalize(self, payload, resolved):
        subs = [[float(v) for v in g] for g in payload["subgroups"]]
        st = _t1.xbar_r(subs)
        ax = payload.get("axes") or {}
        unit = str((ax.get("y") or {}).get("unit", ""))
        idx = list(range(1, len(subs) + 1))

        def panel(name, ys, cl, ucl, lcl, ylab):
            # CL/UCL/LCL as horizontal line series (graph_ref base-xy drops pluginConfig).
            xlo, xhi = idx[0], idx[-1]
            series = [{"name": name, "x": idx, "y": ys, "style": "line+markers", "color": "#2563eb"},
                      {"name": "CL", "x": [xlo, xhi], "y": [cl, cl], "color": "#16a34a", "dash": [6, 4]},
                      {"name": "UCL", "x": [xlo, xhi], "y": [ucl, ucl], "color": "#dc2626", "dash": [3, 3]},
                      {"name": "LCL", "x": [xlo, xhi], "y": [lcl, lcl], "color": "#dc2626", "dash": [3, 3]}]
            gp = {"axes": {"x": {"label": "서브그룹", "unit": ""}, "y": {"label": ylab, "unit": unit}},
                  "series": series}
            return {"kind": "graph", "graph_ref": {"type": "base-xy", "payload": gp}}

        items = [
            {"id": "xbar", "label": f"X̄ (CL={st['xbb']:.4g})", "type": "graph",
             "cells": {"t": panel("X̄", st["means"], st["xbb"], st["x_ucl"], st["x_lcl"], "서브그룹 평균")}},
            {"id": "r", "label": f"R (R̄={st['rb']:.4g})", "type": "graph",
             "cells": {"t": panel("R", st["ranges"], st["rb"], st["r_ucl"], st["r_lcl"], "서브그룹 범위")}},
        ]
        mp = {"title": f"{payload.get('title') or 'X̄-R 관리도'} (n={st['n']})",
              "states": [{"id": "t", "label": ""}], "items": items, "options": {"diff": False}}
        out = self._matrix.normalize(mp, resolved)
        return out

    def structural_requires(self, payload):
        miss = []
        subs = payload.get("subgroups") or []
        if len(subs) < 2 or any(len(g or []) < 2 for g in subs):
            miss.append({"field": "subgroups", "why": "서브그룹(각 2개 이상)이 2개 미만",
                         "ask": "subgroups:[[측정1,측정2,…], …] 를 주세요 (서브그룹 2개↑, 각 크기 동일 2↑)."})
        elif len({len(g) for g in subs}) != 1:
            miss.append({"field": "subgroups", "why": "서브그룹 크기가 불균일",
                         "ask": "모든 서브그룹의 측정 개수(n)를 동일하게 맞춰주세요 (n=2~10)."})
        if "unit" not in ((payload.get("axes") or {}).get("y") or {}):
            miss.append({"field": "axes.y.unit", "why": "측정량 단위 미상",
                         "ask": "측정량의 단위를 axes.y.unit 으로 주세요 (무차원이면 '')."})
        return miss


class FMEAWorksheetRecipe(Recipe):
    type_name = "fmea-worksheet"
    _matrix = MatrixRecipe()

    def normalize(self, payload, resolved):
        rows = payload.get("rows") or []
        mode = str(payload.get("mode", "rpn"))
        states = [{"id": "effect", "label": "영향"}, {"id": "sod", "label": "S·O·D"},
                  {"id": "score", "label": "RPN" if mode == "rpn" else "AP"},
                  {"id": "verdict", "label": "판정"}]
        items = []
        for i, r in enumerate(rows):
            s, o, d = int(r["S"]), int(r["O"]), int(r["D"])
            rpn = _t1.rpn(s, o, d)
            ap = _t1.action_priority(s, o, d)
            if mode == "rpn":
                score_txt = str(rpn)
                st = "fail" if rpn >= 100 else ("warn" if rpn >= 40 else "pass")
            else:
                score_txt = ap
                st = {"H": "fail", "M": "warn", "L": "pass"}[ap]
            label = f"{r.get('item', '')} — {r.get('failure_mode', '')}"
            items.append({"id": f"r{i}", "label": label, "type": "row",
                          "cells": {"effect": {"kind": "text", "value": str(r.get("effect", ""))},
                                    "sod": {"kind": "text", "value": f"{s}·{o}·{d}"},
                                    "score": {"kind": "text", "value": score_txt},
                                    "verdict": {"kind": "status", "status": st}}})
        mp = {"title": str(payload.get("title") or "FMEA 워크시트") + (" (RPN)" if mode == "rpn" else " (AP)"),
              "states": states, "items": items, "options": {"diff": False}}
        return self._matrix.normalize(mp, resolved)

    def structural_requires(self, payload):
        rows = payload.get("rows") or []
        if not rows:
            return [{"field": "rows", "why": "FMEA 행이 없음",
                     "ask": "rows:[{item, failure_mode, effect?, S, O, D}, …] 를 주세요 (S/O/D 1–10)."}]
        for r in rows:
            for k in ("S", "O", "D"):
                v = r.get(k)
                if not isinstance(v, (int, float)) or not (1 <= v <= 10):
                    return [{"field": f"rows[].{k}", "why": "S/O/D 누락 또는 1–10 범위 밖",
                             "ask": "각 행의 S(심각도)·O(발생도)·D(검출도)를 1–10 정수로 주세요."}]
        return []
