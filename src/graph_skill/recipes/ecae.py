"""E-CAE 검증·시험 보고 정형 플롯 8종 — 문헌/표준 근거:
srs-spectrum(JESD22-B111 낙하충격 SRS, Smallwood maximax) · emi-spectrum(CISPR 한계선+마진)
· zth-transient(JESD51-14 과도 열임피던스) · pdn-impedance(Power Integrity target impedance)
· temp-cycle-profile(JESD22-A104 온도 사이클) · spec-margin-chart(검증 마진 요약)
· derating-curve(부품 derating + 동작점 합부) · battery-discharge(방전곡선 + cutoff)."""

from __future__ import annotations

from .base import Recipe

# CISPR 32 radiated emission limits at 3 m, dBμV/m (public standard constants)
_EMI_PRESETS = {
    "cispr32_b_3m": [(30.0, 230.0, 40.0), (230.0, 1000.0, 47.0)],
    "cispr32_a_3m": [(30.0, 230.0, 50.0), (230.0, 1000.0, 57.0)],
}


def _limit_at(segments, f):
    for f0, f1, lv in segments:
        if f0 <= f <= f1:
            return lv
    return None


def _limit_step_series(segments, name="한계선", color="#dc2626"):
    """Step polyline through limit segments (vertical jumps at boundaries)."""
    xs, ys = [], []
    for f0, f1, lv in segments:
        xs += [f0, f1]
        ys += [lv, lv]
    return {"name": name, "x": xs, "y": ys, "color": color, "dash": [6, 4]}


class SRSRecipe(Recipe):
    type_name = "srs-spectrum"

    def normalize(self, payload, resolved):
        from ..postprocess import srs as _srs

        params = payload.get("params") or {}
        fs = float(params["fs"])
        q = float(params.get("q", 10))
        per_oct = int(params.get("per_octave", 6))
        accel = [float(v) for v in (payload.get("accel") or [])]
        fns, vals = _srs.srs_maximax(accel, fs, q=q, per_octave=per_oct)
        series = [{"name": f"SRS (Q={q:g})", "x": fns, "y": vals}]
        ref = params.get("ref_half_sine")            # {peak_g, duration_ms} 기준 펄스 SRS 비교
        if isinstance(ref, dict) and ref.get("peak_g") and ref.get("duration_ms"):
            _, pulse = _srs.half_sine(float(ref["peak_g"]), float(ref["duration_ms"]), fs)
            rf, rv = _srs.srs_maximax(pulse, fs, q=q, per_octave=per_oct)
            series.append({"name": f"규격 half-sine {ref['peak_g']:g}g/{ref['duration_ms']:g}ms",
                           "x": rf, "y": rv, "color": "#dc2626", "dash": [6, 4]})
        options = {
            "axes": {"x": {"label": "고유진동수", "unit": "Hz", "log": True},
                     "y": {"label": "SRS maximax", "unit": "g", "log": True}},
        }
        if payload.get("title"):
            options["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("accel") or []):
            miss.append({"field": "accel", "why": "충격 가속도 시계열이 없음",
                         "ask": "낙하/충격 가속도 샘플을 주세요: accel:[g 값…] + params.fs[Hz]."})
        if not ((payload.get("params") or {}).get("fs")):
            miss.append({"field": "params.fs", "why": "샘플링 주파수 미상 (SRS 필터 계수에 필요)",
                         "ask": "가속도 데이터의 샘플링 주파수 fs를 Hz로 알려주세요 (예: 50000)."})
        return miss


class EMIRecipe(Recipe):
    type_name = "emi-spectrum"

    def _segments(self, payload):
        if payload.get("limit"):
            return [(float(s["f0"]), float(s["f1"]), float(s["level"])) for s in payload["limit"]]
        preset = payload.get("preset")
        return _EMI_PRESETS.get(str(preset)) if preset else None

    def normalize(self, payload, resolved):
        spec = [[float(p[0]), float(p[1])] for p in (payload.get("spectrum") or [])]
        segs = self._segments(payload) or []
        xs = [p[0] for p in spec]
        ys = [p[1] for p in spec]
        series = [{"name": "측정", "x": xs, "y": ys, "color": "#0072B2"}]
        if segs:
            series.append(_limit_step_series(segs))
        # violations + worst margin
        worst, vx, vy = None, [], []
        for f, lv in spec:
            lim = _limit_at(segs, f)
            if lim is None:
                continue
            m = lim - lv
            if worst is None or m < worst[0]:
                worst = (m, f)
            if m < 0:
                vx.append(f)
                vy.append(lv)
        if vx:
            series.append({"name": f"위반 ({len(vx)}점)", "x": vx, "y": vy,
                           "style": "markers", "color": "#dc2626"})
        title = str(payload.get("title") or "EMI 방사 스펙트럼")
        if worst is not None:
            title += f" — 최소 마진 {worst[0]:+.1f} dB @ {worst[1]:g} MHz"
        options = {
            "axes": {"x": {"label": "주파수", "unit": "MHz", "log": True},
                     "y": {"label": "전계강도", "unit": "dBμV/m"}},
            "title": title,
        }
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("spectrum") or []):
            miss.append({"field": "spectrum", "why": "측정 스펙트럼이 없음",
                         "ask": "EMI 측정점을 주세요: spectrum:[[주파수 MHz, 레벨 dBμV/m], …]."})
        if self._segments(payload) is None:
            miss.append({"field": "limit", "why": "규격 한계선이 없음",
                         "ask": "한계선을 주세요: limit:[{f0,f1,level}] (MHz, dBμV/m) 또는 "
                                "preset:'cispr32_b_3m'|'cispr32_a_3m'(CISPR 32, 3m)."})
        return miss


class ZthRecipe(Recipe):
    type_name = "zth-transient"

    def normalize(self, payload, resolved):
        series = []
        for c in payload.get("curves") or []:
            d = c.get("data") or []
            series.append({"name": str(c.get("name", "Zth")),
                           "x": [float(p[0]) for p in d], "y": [float(p[1]) for p in d],
                           **({"color": c["color"]} if c.get("color") else {})})
        options = {
            "axes": {"x": {"label": "시간", "unit": "s", "log": True},
                     "y": {"label": "Zth(t)", "unit": "K/W", "log": True}},
        }
        if payload.get("title"):
            options["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        if not (payload.get("curves") or []):
            return [{"field": "curves", "why": "Zth 곡선이 없음",
                     "ask": "과도 열임피던스 곡선을 주세요: curves:[{name, data:[[t_s, Zth_K/W], …]}] "
                            "(JESD51-14 TDI면 두 곡선 — 분기점이 RthJC)."}]
        return []


class PDNRecipe(Recipe):
    type_name = "pdn-impedance"

    def normalize(self, payload, resolved):
        series = []
        for s in payload.get("series") or []:
            d = s.get("data") or []
            series.append({"name": str(s.get("name", "Z")),
                           "x": [float(p[0]) for p in d], "y": [float(p[1]) for p in d],
                           **({"color": s["color"]} if s.get("color") else {})})
        tgt = payload.get("target")
        segs = None
        if isinstance(tgt, (int, float)):
            f_all = [x for s in series for x in s["x"]]
            segs = [(min(f_all), max(f_all), float(tgt))] if f_all else None
        elif isinstance(tgt, list):
            segs = [(float(s["f0"]), float(s["f1"]), float(s["z"])) for s in tgt]
        worst = None
        if segs:
            series.append(_limit_step_series(segs, name="target impedance"))
            for s in series[:-1]:
                for f, z in zip(s["x"], s["y"]):
                    lim = _limit_at(segs, f)
                    if lim and (worst is None or z / lim > worst[0]):
                        worst = (z / lim, f)
        title = str(payload.get("title") or "PDN 임피던스")
        if worst is not None and worst[0] > 1:
            title += f" — target {worst[0]:.2f}× 초과 @ {worst[1]:g} Hz"
        options = {
            "axes": {"x": {"label": "주파수", "unit": "Hz", "log": True},
                     "y": {"label": "임피던스", "unit": "Ω", "log": True}},
            "title": title,
        }
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("series") or []):
            miss.append({"field": "series", "why": "임피던스 곡선이 없음",
                         "ask": "PDN 임피던스를 주세요: series:[{name, data:[[Hz, Ω], …]}]."})
        if payload.get("target") is None:
            miss.append({"field": "target", "why": "target impedance 미상 (위반 판정 불가)",
                         "ask": "target impedance를 주세요: target: 0.05 (Ω 평탄) 또는 "
                                "target:[{f0,f1,z}] 구간형."})
        return miss


class TempCycleRecipe(Recipe):
    type_name = "temp-cycle-profile"

    def normalize(self, payload, resolved):
        p = payload.get("params") or {}
        t_lo, t_hi = float(p["t_min"]), float(p["t_max"])
        ramp, dwell = float(p["ramp_min"]), float(p["dwell_min"])
        cycles = int(p.get("cycles", 3))
        xs, ys, t = [0.0], [t_lo], 0.0
        for _ in range(cycles):
            for dt_, temp in ((dwell, t_lo), (ramp, t_hi), (dwell, t_hi), (ramp, t_lo)):
                t += dt_
                xs.append(t)
                ys.append(temp)
        series = [{"name": f"규격 프로파일 ({t_lo:g}↔{t_hi:g}°C)", "x": xs, "y": ys, "color": "#0072B2"}]
        for m in payload.get("measured") or []:
            d = m.get("data") or []
            series.append({"name": str(m.get("name", "측정")), "x": [float(q[0]) for q in d],
                           "y": [float(q[1]) for q in d], "color": m.get("color") or "#E69F00"})
        options = {
            "axes": {"x": {"label": "시간", "unit": "min"}, "y": {"label": "온도", "unit": "°C"}},
            "pluginConfig": {"threshold-lines": {"lines": [
                {"axis": "y", "value": t_lo, "label": f"{t_lo:g}°C", "color": "#94a3b8", "dash": [4, 4]},
                {"axis": "y", "value": t_hi, "label": f"{t_hi:g}°C", "color": "#94a3b8", "dash": [4, 4]}]}},
        }
        if payload.get("title"):
            options["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        p = payload.get("params") or {}
        need = [k for k in ("t_min", "t_max", "ramp_min", "dwell_min") if p.get(k) is None]
        if need:
            return [{"field": f"params.{need[0]}", "why": f"사이클 조건 {need} 미상",
                     "ask": "온도 사이클 조건을 주세요: params={t_min, t_max(°C), ramp_min, dwell_min(분), "
                            "cycles?}. 예: JESD22-A104 -40↔125°C."}]
        return []


class SpecMarginRecipe(Recipe):
    type_name = "spec-margin-chart"

    def normalize(self, payload, resolved):
        items = []
        for it in payload.get("items") or []:
            d = {"label": str(it.get("label", "")), "value": float(it["value"])}
            for k in ("min", "max", "unit"):
                if it.get(k) is not None:
                    d[k] = float(it[k]) if k != "unit" else str(it[k])
            items.append(d)
        options = {"title": str(payload.get("title") or "규격 마진"), "theme": "auto"}
        return {"engine": resolved.engine, "assets": {"kind": "margin", "items": items}, "options": options}

    def structural_requires(self, payload):
        items = payload.get("items") or []
        if not items:
            return [{"field": "items", "why": "검증 항목이 없음",
                     "ask": "items:[{label, value, min?|max?(둘 중 1+), unit?}]를 주세요."}]
        bad = [it.get("label", "?") for it in items
               if it.get("value") is None or (it.get("min") is None and it.get("max") is None)]
        if bad:
            return [{"field": "items", "why": f"value 또는 규격 한계 누락: {bad[:3]}",
                     "ask": "각 항목에 value와 min/max 중 최소 하나가 필요합니다."}]
        return []


class DeratingRecipe(Recipe):
    type_name = "derating-curve"

    def normalize(self, payload, resolved):
        curve = [[float(p[0]), float(p[1])] for p in (payload.get("curve") or [])]
        series = [{"name": "derating 한계", "x": [p[0] for p in curve], "y": [p[1] for p in curve],
                   "color": "#dc2626"}]

        def allow_at(x):
            if not curve:
                return None
            if x <= curve[0][0]:
                return curve[0][1]
            for (x0, y0), (x1, y1) in zip(curve, curve[1:]):
                if x0 <= x <= x1:
                    return y0 + (y1 - y0) * (x - x0) / ((x1 - x0) or 1)
            return curve[-1][1]

        ok_x, ok_y, ng_x, ng_y = [], [], [], []
        for pt in payload.get("points") or []:
            x, v = float(pt["temp" if "temp" in pt else "x"]), float(pt["value"])
            (ng_x if v > (allow_at(x) or v) else ok_x).append(x)
            (ng_y if v > (allow_at(x) or v) else ok_y).append(v)
        if ok_x:
            series.append({"name": "동작점 (적합)", "x": ok_x, "y": ok_y, "style": "markers", "color": "#16a34a"})
        if ng_x:
            series.append({"name": "동작점 (위반)", "x": ng_x, "y": ng_y, "style": "markers", "color": "#dc2626"})
        ax = payload.get("axes") or {}
        options = {"axes": {
            "x": {"label": str((ax.get("x") or {}).get("label", "온도")), "unit": str((ax.get("x") or {}).get("unit", "°C"))},
            "y": {"label": str((ax.get("y") or {}).get("label", "")), "unit": str((ax.get("y") or {}).get("unit", ""))},
        }}
        if payload.get("title"):
            options["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        miss = []
        if len(payload.get("curve") or []) < 2:
            miss.append({"field": "curve", "why": "derating 한계곡선이 없음",
                         "ask": "한계곡선을 주세요: curve:[[온도, 허용치], …] (예: [[25,100],[85,100],[125,40]])."})
        ay = ((payload.get("axes") or {}).get("y")) or {}
        if not ay.get("label") or ay.get("unit") is None:
            miss.append({"field": "axes.y", "why": "허용치(y)의 물리량/단위 미상",
                         "ask": "y축이 무엇인가요? (예: 허용 전력 [W], 정격 전류 [%], unit 포함)."})
        return miss


class BatteryDischargeRecipe(Recipe):
    type_name = "battery-discharge"

    def normalize(self, payload, resolved):
        series = []
        for s in payload.get("series") or []:
            d = s.get("data") or []
            series.append({"name": str(s.get("name", "방전")),
                           "x": [float(p[0]) for p in d], "y": [float(p[1]) for p in d],
                           **({"color": s["color"]} if s.get("color") else {})})
        params = payload.get("params") or {}
        options = {
            "axes": {"x": {"label": "방전 용량", "unit": str(params.get("cap_unit", "mAh"))},
                     "y": {"label": "전압", "unit": "V"}},
        }
        if params.get("v_cutoff") is not None:
            options["pluginConfig"] = {"threshold-lines": {"lines": [
                {"axis": "y", "value": float(params["v_cutoff"]), "label": f"cutoff {params['v_cutoff']:g}V",
                 "color": "#dc2626", "dash": [6, 4]}]}}
        if payload.get("title"):
            options["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        if not (payload.get("series") or []):
            return [{"field": "series", "why": "방전 곡선이 없음",
                     "ask": "방전 곡선을 주세요: series:[{name:'0.5C', data:[[용량 mAh, 전압 V], …]}, …] "
                            "(+params.v_cutoff 선택)."}]
        return []
