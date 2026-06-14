"""구조해석·열전달·측정/시험 정형 플롯 8종 (문헌 근거):
mesh-convergence(격자수렴 Richardson/GCI) · stress-linearization(ASME 경로 선형화) ·
hysteresis-loop(반복하중 + 소산에너지) · thermal-response(1차 RC 적합 τ/T∞) ·
nusselt-correlation(Nu-Re 멱법칙 적합) · frf-coherence(FRF+coherence 이중축) ·
allan-deviation(σ(τ) log-log + 기울기 가이드) · calibration-curve(교정 적합+잔차)."""

from __future__ import annotations

from ..postprocess import experiment as _ex
from .base import Recipe


def _ax_need(payload, axis, what):
    a = ((payload.get("axes") or {}).get(axis)) or {}
    if not a.get("label") or a.get("unit") is None:
        return {"field": f"axes.{axis}", "why": f"{what} 물리량/단위 미상",
                "ask": f"{axis}축({what})의 label과 unit을 알려주세요."}
    return None


class MeshConvergenceRecipe(Recipe):
    type_name = "mesh-convergence"

    def normalize(self, payload, resolved):
        cases = payload.get("cases") or []
        hs = [float(c["h"]) for c in cases]
        phis = [float(c["value"]) for c in cases]
        order = sorted(range(len(hs)), key=lambda i: hs[i])
        xs = [hs[i] for i in order]
        ys = [phis[i] for i in order]
        series = [{"name": "격자별 결과", "x": xs, "y": ys, "style": "line+markers"}]
        rich = _ex.richardson(hs, phis)
        title = str(payload.get("title") or "격자 수렴성 (grid independence)")
        plug = {}
        if rich and rich.get("monotonic"):
            series.append({"name": f"Richardson 외삽 (p={rich['p']:.2f})",
                           "x": [xs[0], xs[-1]], "y": [rich["phi_ext"], rich["phi_ext"]],
                           "color": "#dc2626", "dash": [6, 4]})
            title += f" — φ_ext={rich['phi_ext']:.4g}, GCI_fine={rich['gci_fine_pct']:.2f}%"
        ay = (payload.get("axes") or {}).get("y") or {}
        options = {"axes": {"x": {"label": "격자 대표 크기 h", "unit": str(payload.get("h_unit", "")), "log": True},
                            "y": {"label": str(ay.get("label", "결과량")), "unit": str(ay.get("unit", ""))}},
                   "title": title, **plug}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        miss = []
        cases = payload.get("cases") or []
        if len(cases) < 3:
            miss.append({"field": "cases", "why": "격자 케이스 3개 미만 (Richardson에 3개 필요)",
                         "ask": "격자 수렴 케이스를 주세요: cases:[{h:격자크기, value:결과값}, …] 3개 이상."})
        m = _ax_need(payload, "y", "수렴 판정 결과량")
        if m:
            miss.append(m)
        return miss


class StressLinearizationRecipe(Recipe):
    type_name = "stress-linearization"

    def normalize(self, payload, resolved):
        path = [[float(p[0]), float(p[1])] for p in (payload.get("path") or [])]
        xs = [p[0] for p in path]
        ys = [p[1] for p in path]
        lin = _ex.stress_linearize(xs, ys)
        series = [{"name": "경로 응력 (raw)", "x": xs, "y": ys}]
        title = str(payload.get("title") or "응력 선형화 (through-thickness)")
        if lin:
            series.append({"name": f"membrane σm={lin['membrane']:.4g}",
                           "x": [xs[0], xs[-1]], "y": [lin["membrane"], lin["membrane"]],
                           "color": "#16a34a", "dash": [6, 4]})
            series.append({"name": f"m+b (σb=±{abs(lin['bending']):.4g})",
                           "x": [q[0] for q in lin["mb_line"]], "y": [q[1] for q in lin["mb_line"]],
                           "color": "#dc2626", "dash": [3, 3]})
        s_unit = str(((payload.get("axes") or {}).get("y") or {}).get("unit", "MPa"))
        options = {"axes": {"x": {"label": "두께 방향 위치", "unit": str(payload.get("x_unit", "mm"))},
                            "y": {"label": "응력", "unit": s_unit}}, "title": title}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        miss = []
        if len(payload.get("path") or []) < 3:
            miss.append({"field": "path", "why": "두께 경로 응력 분포가 없음",
                         "ask": "선형화 경로를 주세요: path:[[두께방향 위치, 응력], …] (SCL 시작→끝, 3점 이상)."})
        # NEVER-invent: 응력 단위를 묵묵히 'MPa'로 채우지 않는다 (ksi/psi 오라벨링 차단)
        if (((payload.get("axes") or {}).get("y") or {}).get("unit")) is None:
            miss.append({"field": "axes.y.unit", "why": "응력 단위 미상 (MPa? ksi? psi?)",
                         "ask": "응력 단위를 axes.y.unit 으로 주세요 (예: 'MPa'). 무차원일 수 없어 추측하지 않습니다."})
        return miss


class HysteresisRecipe(Recipe):
    type_name = "hysteresis-loop"

    def normalize(self, payload, resolved):
        series = []
        total_e = 0.0
        for i, lp in enumerate(payload.get("loops") or []):
            pts = [[float(p[0]), float(p[1])] for p in (lp.get("data") or [])]
            e = _ex.loop_energy(pts)
            total_e += e
            series.append({"name": f"{lp.get('name', f'cycle {i+1}')} (E={e:.4g})",
                           "x": [p[0] for p in pts], "y": [p[1] for p in pts],
                           **({"color": lp["color"]} if lp.get("color") else {})})
        ax = payload.get("axes") or {}
        options = {"axes": {
            "x": {"label": str((ax.get("x") or {}).get("label", "변위")), "unit": str((ax.get("x") or {}).get("unit", "mm"))},
            "y": {"label": str((ax.get("y") or {}).get("label", "하중")), "unit": str((ax.get("y") or {}).get("unit", "N"))}},
            "title": str(payload.get("title") or "반복하중 이력곡선") + f" — 총 소산에너지 {total_e:.4g}"}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        miss = []
        loops = payload.get("loops") or []
        if not loops or any(len(lp.get("data") or []) < 4 for lp in loops):
            miss.append({"field": "loops", "why": "이력 루프 데이터가 없음/불충분",
                         "ask": "사이클별 루프를 주세요: loops:[{name?, data:[[변위, 하중], …]}, …]."})
        for axk, what in (("x", "변위"), ("y", "하중")):
            m = _ax_need(payload, axk, what)
            if m:
                miss.append(m)
        return miss


class ThermalResponseRecipe(Recipe):
    type_name = "thermal-response"

    def normalize(self, payload, resolved):
        d = [[float(p[0]), float(p[1])] for p in (payload.get("data") or [])]
        ts = [p[0] for p in d]
        ys = [p[1] for p in d]
        series = [{"name": "측정", "x": ts, "y": ys, "style": "line+markers"}]
        fit = _ex.thermal_rc_fit(ts, ys)
        title = str(payload.get("title") or "열 응답 (1차 RC 적합)")
        if fit:
            import math
            fx = [ts[0] + (ts[-1] - ts[0]) * i / 120 for i in range(121)]
            fy = [fit["t_inf"] + (fit["t0"] - fit["t_inf"]) * math.exp(-(x - ts[0]) / fit["tau"]) for x in fx]
            series.append({"name": f"적합: τ={fit['tau']:.4g}, T∞={fit['t_inf']:.4g}",
                           "x": fx, "y": fy, "color": "#dc2626", "dash": [6, 4]})
            title += f" — τ={fit['tau']:.4g} {payload.get('t_unit', 's')}, T∞={fit['t_inf']:.4g}°C"
        options = {"axes": {"x": {"label": "시간", "unit": str(payload.get("t_unit", "s"))},
                            "y": {"label": "온도", "unit": "°C"}}, "title": title}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        if len(payload.get("data") or []) < 5:
            return [{"field": "data", "why": "가열/냉각 곡선 데이터 부족",
                     "ask": "온도 응답을 주세요: data:[[시간, 온도°C], …] (5점 이상; t_unit 기본 s)."}]
        return []


class NusseltRecipe(Recipe):
    type_name = "nusselt-correlation"

    def normalize(self, payload, resolved):
        d = [[float(p[0]), float(p[1])] for p in (payload.get("data") or [])]
        xs = [p[0] for p in d]
        ys = [p[1] for p in d]
        series = [{"name": "데이터", "x": xs, "y": ys, "style": "markers"}]
        fit = _ex.power_fit(xs, ys)
        title = str(payload.get("title") or "Nu–Re 상관")
        if fit:
            fx = [min(xs) * (max(xs) / min(xs)) ** (i / 60) for i in range(61)]
            fy = [fit["C"] * x ** fit["m"] for x in fx]
            series.append({"name": f"적합 Nu={fit['C']:.3g}·Re^{fit['m']:.3g} (R²={fit['r2']:.4f})",
                           "x": fx, "y": fy, "color": "#dc2626"})
        for ref in payload.get("references") or []:    # 문헌 상관식 오버레이 {name, C, m}
            fx = [min(xs) * (max(xs) / min(xs)) ** (i / 60) for i in range(61)]
            series.append({"name": str(ref.get("name", "ref")),
                           "x": fx, "y": [float(ref["C"]) * x ** float(ref["m"]) for x in fx],
                           "dash": [4, 4]})
        ax = payload.get("axes") or {}
        options = {"axes": {
            "x": {"label": str((ax.get("x") or {}).get("label", "Re")), "unit": str((ax.get("x") or {}).get("unit", "")), "log": True},
            "y": {"label": str((ax.get("y") or {}).get("label", "Nu")), "unit": str((ax.get("y") or {}).get("unit", "")), "log": True}},
            "title": title}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        d = payload.get("data") or []
        if len(d) < 4:
            return [{"field": "data", "why": "상관 데이터 부족",
                     "ask": "무차원수 쌍을 주세요: data:[[Re, Nu], …] (4점 이상, 양수)."}]
        if any(float(p[0]) <= 0 or float(p[1]) <= 0 for p in d):
            return [{"field": "data", "why": "log-log 적합에 0/음수 불가",
                     "ask": "Re/Nu 값은 모두 양수여야 합니다."}]
        return []


class FRFCoherenceRecipe(Recipe):
    type_name = "frf-coherence"

    def normalize(self, payload, resolved):
        f = [float(v) for v in (payload.get("freq") or [])]
        mag = [float(v) for v in (payload.get("frf") or [])]
        coh = [float(v) for v in (payload.get("coherence") or [])]
        series = [{"name": "FRF |H(f)|", "x": f, "y": mag}]
        if coh:
            series.append({"name": "coherence", "x": f, "y": coh, "axis": "right", "color": "#999999"})
        # 공진 피크 마커 (단순 국소최대 상위 N)
        peaks = []
        for i in range(1, len(mag) - 1):
            if mag[i] > mag[i - 1] and mag[i] > mag[i + 1]:
                peaks.append((mag[i], f[i]))
        peaks.sort(reverse=True)
        if peaks:
            top = peaks[:int(payload.get("n_peaks", 3))]
            series.append({"name": "공진", "x": [p[1] for p in top], "y": [p[0] for p in top],
                           "style": "markers", "color": "#dc2626"})
        au = str(((payload.get("axes") or {}).get("y") or {}).get("unit", "m/s²/N"))
        options = {"axes": {
            "x": {"label": "주파수", "unit": "Hz"},
            "y": {"label": "|H(f)|", "unit": au, "log": True},
            "y2": {"label": "coherence", "unit": ""}},
            "title": str(payload.get("title") or "FRF + coherence (모달 시험)")}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("freq") and payload.get("frf")):
            miss.append({"field": "freq/frf", "why": "FRF 데이터가 없음",
                         "ask": "FRF를 주세요: freq:[Hz…], frf:[|H| 값…] (+coherence:[0~1…] 권장)."})
        ay = ((payload.get("axes") or {}).get("y")) or {}
        if "unit" not in ay:
            miss.append({"field": "axes.y.unit", "why": "FRF 단위 미상(가속도/힘? 변위/힘?)",
                         "ask": "FRF 단위를 알려주세요 (예: 'm/s²/N'(accelerance), 'm/N'(compliance))."})
        return miss


class AllanRecipe(Recipe):
    type_name = "allan-deviation"

    def normalize(self, payload, resolved):
        params = payload.get("params") or {}
        fs = float(params["fs"])
        samples = [float(v) for v in (payload.get("samples") or [])]
        taus, sig = _ex.allan_deviation(samples, fs)
        series = [{"name": "Allan σ(τ)", "x": taus, "y": sig, "style": "line+markers"}]
        # 기울기 가이드선 (백색노이즈 -1/2, RRW +1/2) — 첫 점 기준 통과선
        if taus:
            t0, s0 = taus[0], sig[0]
            tspan = [t0, taus[-1]]
            series.append({"name": "기울기 -1/2 (white/ARW)", "x": tspan,
                           "y": [s0, s0 * (tspan[1] / t0) ** -0.5], "color": "#999999", "dash": [4, 4]})
        yu = str(params.get("unit", ""))
        options = {"axes": {"x": {"label": "평균화 시간 τ", "unit": "s", "log": True},
                            "y": {"label": "Allan deviation", "unit": yu, "log": True}},
                   "title": str(payload.get("title") or "Allan deviation (노이즈 특성)")}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        miss = []
        if len(payload.get("samples") or []) < 100:
            miss.append({"field": "samples", "why": "정적 샘플 부족(τ 그리드에 최소 수백 점 필요)",
                         "ask": "정지 상태 센서 출력 샘플을 주세요: samples:[…] (수천 점 권장) + params.fs[Hz]."})
        p = payload.get("params") or {}
        if not p.get("fs"):
            miss.append({"field": "params.fs", "why": "샘플레이트 미상(τ 환산 불가)",
                         "ask": "샘플링 주파수 fs[Hz]를 알려주세요."})
        if "unit" not in p:
            miss.append({"field": "params.unit", "why": "센서 출력 단위 미상",
                         "ask": "출력 단위를 알려주세요 (예: 'deg/s', 'm/s²', 무차원이면 '')."})
        return miss


class CalibrationRecipe(Recipe):
    type_name = "calibration-curve"

    def normalize(self, payload, resolved):
        d = [[float(p[0]), float(p[1])] for p in (payload.get("data") or [])]
        xs = [p[0] for p in d]
        ys = [p[1] for p in d]
        fit = _ex.linear_fit(xs, ys)
        series = [{"name": "측정점", "x": xs, "y": ys, "style": "markers"}]
        title = str(payload.get("title") or "교정 곡선")
        if fit:
            series.append({"name": f"적합 y={fit['slope']:.5g}x+{fit['intercept']:+.4g} (R²={fit['r2']:.5f})",
                           "x": [min(xs), max(xs)],
                           "y": [fit["slope"] * min(xs) + fit["intercept"], fit["slope"] * max(xs) + fit["intercept"]],
                           "color": "#dc2626"})
            series.append({"name": "잔차", "x": xs, "y": fit["residuals"],
                           "style": "markers", "axis": "right", "color": "#999999"})
        tol = payload.get("tolerance")
        if tol is not None and fit:
            series.append({"name": f"허용오차 ±{float(tol):g}", "x": [min(xs), max(xs), None, min(xs), max(xs)],
                           "y": [float(tol), float(tol), None, -float(tol), -float(tol)],
                           "axis": "right", "color": "#d97706", "dash": [4, 4]})
        ax = payload.get("axes") or {}
        xu = str((ax.get("x") or {}).get("unit", ""))
        yu = str((ax.get("y") or {}).get("unit", ""))
        options = {"axes": {
            "x": {"label": str((ax.get("x") or {}).get("label", "기준값")), "unit": xu},
            "y": {"label": str((ax.get("y") or {}).get("label", "측정값")), "unit": yu},
            "y2": {"label": "잔차", "unit": yu}},
            "title": title}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        miss = []
        if len(payload.get("data") or []) < 3:
            miss.append({"field": "data", "why": "교정점 부족",
                         "ask": "교정 데이터를 주세요: data:[[기준값, 측정값], …] (3점 이상)."})
        for axk, what in (("x", "기준값"), ("y", "측정값")):
            m = _ax_need(payload, axk, what)
            if m:
                miss.append(m)
        return miss


class BlandAltmanRecipe(Recipe):
    """측정-시뮬/장비간 일치도(Bland-Altman) — 차이 vs 평균 산점 + bias·±1.96SD LoA 기준선.
    correlation-scatter(동일성 y=x)로 대체 불가한 방법비교 표준(측정-CAE 상관 업무)."""
    type_name = "bland-altman"

    def normalize(self, payload, resolved):
        ba = _ex.bland_altman(payload.get("method1") or [], payload.get("method2") or [])
        ax = payload.get("axes") or {}
        unit = str(((ax.get("y") or ax.get("x") or {}).get("unit", "")))
        names = payload.get("names") or ["방법1", "방법2"]
        series = [{"name": "쌍", "x": ba["means"], "y": ba["diffs"], "style": "markers", "color": "#2563eb"}]
        if ba["means"]:
            xlo, xhi = min(ba["means"]), max(ba["means"])
            for lbl, yv, col, dash in (
                (f"bias={ba['bias']:.4g}", ba["bias"], "#16a34a", [6, 4]),
                (f"+1.96SD={ba['loa_hi']:.4g}", ba["loa_hi"], "#dc2626", [3, 3]),
                (f"-1.96SD={ba['loa_lo']:.4g}", ba["loa_lo"], "#dc2626", [3, 3]),
            ):
                series.append({"name": lbl, "x": [xlo, xhi], "y": [yv, yv], "color": col, "dash": dash})
        title = str(payload.get("title") or f"Bland-Altman ({names[0]} vs {names[1]})")
        options = {"axes": {"x": {"label": f"평균 ({names[0]}, {names[1]})", "unit": unit},
                            "y": {"label": f"차이 ({names[0]} - {names[1]})", "unit": unit}},
                   "title": title}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        miss = []
        a, b = payload.get("method1") or [], payload.get("method2") or []
        if len(a) < 2 or len(b) < 2 or len(a) != len(b):
            miss.append({"field": "method1", "why": "쌍을 이룬 측정 2조(같은 길이, 2개 이상) 필요",
                         "ask": "두 방법의 쌍 측정값을 주세요: method1:[...], method2:[...] (같은 대상·순서, 길이 동일)."})
        ay = (payload.get("axes") or {}).get("y") or (payload.get("axes") or {}).get("x") or {}
        if "unit" not in ay:
            miss.append({"field": "axes.y.unit", "why": "측정 단위 미상",
                         "ask": "측정량의 단위를 axes.y.unit 으로 주세요 (두 방법 공통; 무차원이면 \"\")."})
        return miss
