"""확장 6종 — 디스플레이·음향·민감도·액추에이터·RF·재료 (문헌/표준 근거):
cie-chromaticity(CIE 1931 색역도, 공식 궤적 내장) · octave-band(IEC 61260 1/3옥타브) ·
tornado-chart(민감도) · motor-tn-curve(T-N+효율 이중축) · vswr-curve(S11→VSWR 변환 지원) ·
dma-curve(E'/E''/tanδ, Tg 자동 마커)."""

from __future__ import annotations

import math

from ..postprocess import photometry as _ph
from .base import Recipe


class CIEChromaticityRecipe(Recipe):
    type_name = "cie-chromaticity"

    def normalize(self, payload, resolved):
        locus = _ph.spectral_locus()
        lx = [p[0] for p in locus] + [locus[0][0]]         # close with the purple line
        ly = [p[1] for p in locus] + [locus[0][1]]
        series = [{"name": "스펙트럼 궤적 (CIE 1931)", "x": lx, "y": ly, "color": "#6b7280"}]
        pal = {"srgb": "#0072B2", "dci_p3": "#E69F00", "bt2020": "#009E73"}
        for g in payload.get("gamuts") or ["srgb", "dci_p3"]:
            spec = _ph.GAMUTS.get(str(g))
            if not spec:
                continue
            tri = [spec["r"], spec["g"], spec["b"], spec["r"]]
            series.append({"name": spec["name"], "x": [p[0] for p in tri], "y": [p[1] for p in tri],
                           "color": pal.get(str(g), "#9333ea"), "dash": [5, 4]})
        pts = payload.get("points") or []
        if pts:
            series.append({"name": "측정점", "x": [float(p["x"]) for p in pts],
                           "y": [float(p["y"]) for p in pts], "style": "markers", "color": "#dc2626"})
        wp = payload.get("white") or {"x": _ph.WHITE_D65[0], "y": _ph.WHITE_D65[1]}
        series.append({"name": "백색점", "x": [float(wp["x"])], "y": [float(wp["y"])],
                       "style": "markers", "color": "#111827"})
        title = str(payload.get("title") or "CIE 1931 색도도")
        meas = payload.get("measured_gamut")               # {r:{x,y}, g:{...}, b:{...}} → 커버리지
        if isinstance(meas, dict) and all(k in meas for k in ("r", "g", "b")):
            tri_m = [(float(meas[k]["x"]), float(meas[k]["y"])) for k in ("r", "g", "b")]
            series.append({"name": "측정 색역", "x": [p[0] for p in tri_m] + [tri_m[0][0]],
                           "y": [p[1] for p in tri_m] + [tri_m[0][1]], "color": "#dc2626"})
            ref = payload.get("coverage_ref", "dci_p3")
            rs = _ph.GAMUTS.get(str(ref))
            if rs:
                ratio = _ph.gamut_area_ratio(tri_m, (rs["r"], rs["g"], rs["b"]))
                title += f" — 면적비 {ratio * 100:.1f}% vs {rs['name']}"
        options = {
            "axes": {"x": {"label": "x", "unit": ""}, "y": {"label": "y", "unit": ""}},
            "equalAspect": True, "title": title,
        }
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        bad = [g for g in (payload.get("gamuts") or []) if str(g) not in _ph.GAMUTS]
        if bad:
            return [{"field": "gamuts", "why": f"알 수 없는 색역 {bad}",
                     "ask": f"gamuts는 {list(_ph.GAMUTS)} 중에서. 다른 색역이면 measured_gamut으로 직접 좌표를 주세요."}]
        return []


class OctaveBandRecipe(Recipe):
    type_name = "octave-band"

    def normalize(self, payload, resolved):
        if payload.get("bands"):
            bands = [(float(b[0]), float(b[1])) for b in payload["bands"]]
        else:
            spec = payload.get("spectrum") or []
            bands = _ph.spectrum_to_third_octave([float(p[0]) for p in spec],
                                                 [float(p[1]) for p in spec])
        cats = [(f"{fc:g}" if fc < 1000 else f"{fc / 1000:g}k") for fc, _ in bands]
        series = [{"name": "밴드 레벨", "x": list(range(len(bands))),
                   "y": [round(lv, 2) for _, lv in bands], "style": "bar"}]
        lim = payload.get("limit") or []
        if lim:
            lm = {float(p[0]): float(p[1]) for p in lim}
            series.append({"name": "한계", "x": list(range(len(bands))),
                           "y": [lm.get(fc) for fc, _ in bands], "color": "#dc2626", "dash": [5, 4]})
        yu = str(payload.get("level_unit", "dB"))
        options = {"axes": {"x": {"label": "1/3 옥타브 중심주파수", "unit": "Hz", "categories": cats},
                            "y": {"label": "레벨", "unit": yu}},
                   "title": str(payload.get("title") or "1/3 옥타브 밴드 스펙트럼")}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("bands") or payload.get("spectrum")):
            miss.append({"field": "bands", "why": "밴드/스펙트럼 데이터가 없음",
                         "ask": "bands:[[fc_Hz, level], …](IEC 61260 공칭 fc) 또는 협대역 spectrum:[[Hz, dB], …]를 주세요."})
        if "level_unit" not in payload:
            miss.append({"field": "level_unit", "why": "레벨 단위/기준 미상 (dB SPL? dBA? dB re 1V?)",
                         "ask": "레벨 단위를 알려주세요 (예: 'dB SPL', 'dBA', 'dB re 20µPa')."})
        return miss


class TornadoRecipe(Recipe):
    type_name = "tornado-chart"

    def normalize(self, payload, resolved):
        base = float(payload["baseline"])
        rows = [{"name": str(f.get("name", "")), "low": float(f["low"]), "high": float(f["high"])}
                for f in payload.get("factors") or []]
        rows.sort(key=lambda r: -abs(r["high"] - r["low"]))   # 토네이도: 스팬 큰 순
        unit = str(payload.get("unit", ""))
        vals = [base] + [r["low"] for r in rows] + [r["high"] for r in rows]
        pad = (max(vals) - min(vals)) * 0.18 or 1.0
        n = len(rows)
        name_w = min(190, 24 + max(len(r["name"]) for r in rows) * 11)
        options = {
            "hideAxes": True,
            "pad": {"left": name_w, "right": 56, "bottom": 26},
            "axes": {"x": {"label": "응답", "unit": unit}, "y": {"label": "", "unit": ""}},
            "pluginConfig": {"tornado": {"rows": rows, "baseline": base, "unit": unit}},
            "title": str(payload.get("title") or "민감도 토네이도 차트"),
        }
        series = [{"name": "_tn", "style": "none",
                   "x": [min(vals) - pad, max(vals) + pad], "y": [-0.5, n - 0.5]}]
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        miss = []
        if len(payload.get("factors") or []) < 2:
            miss.append({"field": "factors", "why": "민감도 인자 부족",
                         "ask": "factors:[{name, low:인자하한일때 응답, high:상한일때 응답}, …] (2개 이상)."})
        if payload.get("baseline") is None:
            miss.append({"field": "baseline", "why": "기준 응답값 미상",
                         "ask": "baseline(모든 인자 공칭일 때 응답값)을 알려주세요."})
        if "unit" not in payload:
            miss.append({"field": "unit", "why": "응답량 단위 미상",
                         "ask": "응답량 단위를 알려주세요 (무차원이면 '')."})
        return miss


class MotorTNRecipe(Recipe):
    type_name = "motor-tn-curve"

    def normalize(self, payload, resolved):
        series = []
        for s in payload.get("curves") or []:
            d = s.get("data") or []
            series.append({"name": str(s.get("name", "T-N")),
                           "x": [float(p[0]) for p in d], "y": [float(p[1]) for p in d],
                           **({"color": s["color"]} if s.get("color") else {})})
        eff = payload.get("efficiency") or []
        if eff:
            series.append({"name": "효율", "x": [float(p[0]) for p in eff],
                           "y": [float(p[1]) for p in eff], "axis": "right",
                           "color": "#009E73", "dash": [5, 4]})
        ops = payload.get("points") or []
        if ops:
            series.append({"name": "동작점", "x": [float(p[0]) for p in ops],
                           "y": [float(p[1]) for p in ops], "style": "markers", "color": "#dc2626"})
        tu = str(((payload.get("axes") or {}).get("y") or {}).get("unit", "mN·m"))
        options = {"axes": {"x": {"label": "회전수", "unit": "rpm"},
                            "y": {"label": "토크", "unit": tu},
                            "y2": {"label": "효율", "unit": "%"}},
                   "title": str(payload.get("title") or "모터 T-N 특성")}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("curves") or []):
            miss.append({"field": "curves", "why": "T-N 곡선이 없음",
                         "ask": "T-N 곡선을 주세요: curves:[{name, data:[[rpm, 토크], …]}] "
                                "(+efficiency:[[rpm, %]], points:[[rpm, 토크]] 동작점)."})
        ay = ((payload.get("axes") or {}).get("y")) or {}
        if "unit" not in ay:
            miss.append({"field": "axes.y.unit", "why": "토크 단위 미상 (mN·m? N·m? gf·cm?)",
                         "ask": "토크 단위를 알려주세요 (예: 'mN·m')."})
        return miss


class VSWRRecipe(Recipe):
    type_name = "vswr-curve"

    def normalize(self, payload, resolved):
        if payload.get("vswr"):
            d = [[float(p[0]), float(p[1])] for p in payload["vswr"]]
        else:                                            # s11_db → VSWR 변환
            d = []
            for p in payload.get("s11_db") or []:
                f, db = float(p[0]), float(p[1])
                g = min(0.9999, 10 ** (db / 20.0)) if db < 0 else 0.9999
                d.append([f, (1 + g) / (1 - g)])
        series = [{"name": "VSWR", "x": [p[0] for p in d], "y": [round(p[1], 4) for p in d]}]
        lim = payload.get("limit")
        plug = {}
        if lim is not None:
            plug = {"pluginConfig": {"threshold-lines": {"lines": [
                {"axis": "y", "value": float(lim), "label": f"한계 {float(lim):g}",
                 "color": "#dc2626", "dash": [6, 4]}]}}}
        worst = max(d, key=lambda p: p[1]) if d else None
        title = str(payload.get("title") or "VSWR")
        if worst and lim is not None:
            ok = worst[1] <= float(lim)
            title += f" — 최대 {worst[1]:.2f} @ {worst[0]:g} ({'적합' if ok else '한계 초과'})"
        fu = str(payload.get("f_unit", "MHz"))
        options = {"axes": {"x": {"label": "주파수", "unit": fu},
                            "y": {"label": "VSWR", "unit": ""}}, "title": title, **plug}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        if not (payload.get("vswr") or payload.get("s11_db")):
            return [{"field": "vswr", "why": "VSWR/S11 데이터가 없음",
                     "ask": "vswr:[[주파수, VSWR], …] 또는 s11_db:[[주파수, S11 dB], …](자동 변환)를 주세요. "
                            "f_unit 기본 MHz, limit로 한계선(예: 2.0)."}]
        return []


class DMARecipe(Recipe):
    type_name = "dma-curve"

    def normalize(self, payload, resolved):
        t = [float(v) for v in (payload.get("temp") or [])]
        series = []
        for key, name, col in (("e_storage", "E' (저장 탄성률)", "#0072B2"),
                               ("e_loss", "E'' (손실 탄성률)", "#E69F00")):
            ys = payload.get(key)
            if ys:
                series.append({"name": name, "x": t, "y": [float(v) for v in ys], "color": col})
        td = payload.get("tan_delta")
        title = str(payload.get("title") or "DMA 곡선")
        if td:
            tdv = [float(v) for v in td]
            series.append({"name": "tanδ", "x": t, "y": tdv, "axis": "right", "color": "#009E73"})
            i = max(range(len(tdv)), key=lambda k: tdv[k])
            series.append({"name": f"Tg≈{t[i]:g}°C (tanδ peak)", "x": [t[i]], "y": [tdv[i]],
                           "style": "markers", "axis": "right", "color": "#dc2626"})
            title += f" — Tg(tanδ peak) ≈ {t[i]:g}°C"
        eu = str(payload.get("e_unit", "MPa"))
        options = {"axes": {"x": {"label": "온도", "unit": "°C"},
                            "y": {"label": "탄성률", "unit": eu, "log": True},
                            "y2": {"label": "tanδ", "unit": ""}}, "title": title}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("temp") and payload.get("e_storage")):
            miss.append({"field": "temp/e_storage", "why": "DMA 데이터가 없음",
                         "ask": "DMA 결과를 주세요: temp:[°C…], e_storage:[E'…] (+e_loss, tan_delta 권장)."})
        if "e_unit" not in payload:
            miss.append({"field": "e_unit", "why": "탄성률 단위 미상 (MPa? GPa?)",
                         "ask": "탄성률 단위를 알려주세요 (예: 'MPa')."})
        return miss


def _vswr_self_check():
    """-9.54 dB → |Γ|=1/3 → VSWR=2.0 (모듈 로드 시 자가검증)."""
    g = 10 ** (-9.542425094393249 / 20)
    assert abs((1 + g) / (1 - g) - 2.0) < 1e-9


_vswr_self_check()
