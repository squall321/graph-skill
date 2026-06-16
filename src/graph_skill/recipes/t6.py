"""마지막 정형 그래프 2종 — milestone-trend(MTA, 날짜-날짜 이중축) +
reliability-demo-sprt(PRST 축차판정). 둘 다 xy-core 재사용. 엔진 신규작업 0."""

from __future__ import annotations

from ..postprocess import domain_t6 as _t6
from .base import Recipe
from .schedule import _day


def _fmt(v, nd=3):
    return "—" if v is None else f"{v:.{nd}g}"


_PAL = ["#2563eb", "#f59e0b", "#16a34a", "#dc2626", "#7c3aed", "#0891b2"]


class MilestoneTrendRecipe(Recipe):
    """마일스톤 트렌드(MTA) — 보고 시점(x)별 예상 완료일(y). 평탄=일정 유지, 상승=지연.
    완료선 y=x 와 만나면 달성. 날짜는 기준일 경과일수로 환산해 xy-core에 렌더."""

    type_name = "milestone-trend"

    def normalize(self, payload, resolved):
        rdates = [str(d) for d in payload["report_dates"]]
        rdays = [_day(d) for d in rdates]
        ms = payload["milestones"]
        alldays = list(rdays)
        for m in ms:
            alldays += [_day(d) for d in m["forecasts"]]
        d0, d1 = min(alldays), max(alldays)
        rx = [d - d0 for d in rdays]
        series, markers = [], []
        for i, m in enumerate(ms):
            fy = [_day(d) - d0 for d in m["forecasts"]]
            col = _PAL[i % len(_PAL)]
            series.append({"name": str(m.get("name", f"M{i + 1}")), "x": rx, "y": fy,
                           "style": "line+markers", "color": col})
            for j in range(len(rx)):                        # 달성 = 예상완료 ≤ 보고시점 (완료선 도달)
                if fy[j] <= rx[j]:
                    markers.append({"x": rx[j], "y": fy[j], "label": "달성", "color": col})
                    break
        series.append({"name": "완료선 (y=x)", "x": [0, d1 - d0], "y": [0, d1 - d0],
                       "color": "#94a3b8", "dash": [5, 4]})
        opts = {"axes": {"x": {"label": "보고 시점", "unit": "기준일+일"},
                         "y": {"label": "예상 완료", "unit": "기준일+일"}},
                "title": f"{payload.get('title') or '마일스톤 트렌드 (MTA)'} — 기준일 {rdates[0]}"}
        if markers:
            opts["pluginConfig"] = {"named-markers": {"markers": markers}}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        rd = payload.get("report_dates") or []
        ms = payload.get("milestones") or []
        if len(rd) < 2 or not ms:
            miss.append({"field": "report_dates", "why": "보고 시점/마일스톤 예측이 부족",
                         "ask": "report_dates:[ISO날짜…] + milestones:[{name, forecasts:[보고시점별 예상완료 ISO날짜]}] 를 주세요."})
        elif any(len(m.get("forecasts") or []) != len(rd) for m in ms):
            miss.append({"field": "milestones[].forecasts", "why": "예측 개수가 보고 시점 수와 불일치",
                         "ask": "각 마일스톤 forecasts 길이를 report_dates 수와 같게 맞춰주세요."})
        return miss


class ReliabilityDemoSPRTRecipe(Recipe):
    """신뢰성 실증 축차판정(PRST) — 누적 시험시간(x) vs 누적 고장수(y)에 accept/continue/reject
    경계선을 긋고 시험 경로를 계단으로 중첩. MIL-HDBK-781 방식(α/β/판별비)."""

    type_name = "reliability-demo-sprt"

    def normalize(self, payload, resolved):
        alpha, beta = float(payload["alpha"]), float(payload["beta"])
        if payload.get("theta0") is not None and payload.get("theta1") is not None:
            theta0, theta1 = float(payload["theta0"]), float(payload["theta1"])
        else:
            d = float(payload["discrimination_ratio"])
            theta0, theta1 = d, 1.0
        bd = _t6.sprt_bounds(alpha, beta, theta0, theta1)
        traj = [[float(p[0]), float(p[1])] for p in (payload.get("trajectory") or [])]
        tmax = float(payload.get("t_max") or (traj[-1][0] if traj else theta0 * 6))
        tunit = str(payload.get("t_unit", "h"))
        xs = [0.0, tmax]
        rej = [bd["reject_intercept"] + bd["slope"] * t for t in xs]
        acc = [max(0.0, bd["accept_intercept"] + bd["slope"] * t) for t in xs]
        series = [{"name": "기각선 (reject)", "x": xs, "y": rej, "color": "#dc2626", "dash": [6, 4]},
                  {"name": "합격선 (accept)", "x": xs, "y": acc, "color": "#16a34a", "dash": [6, 4]}]
        verdict = {"reject": "기각(불합격)", "accept": "합격", "continue": "계속시험"}[_t6.sprt_decision(traj, bd)]
        if traj:
            series.append({"name": "시험경로", "x": [p[0] for p in traj], "y": [p[1] for p in traj],
                           "style": "step", "color": "#2563eb"})
        opts = {"axes": {"x": {"label": "누적 시험시간", "unit": tunit},
                         "y": {"label": "누적 고장수", "unit": ""}},
                "title": f"{payload.get('title') or 'PRST 축차판정'} — θ0={_fmt(theta0)} θ1={_fmt(theta1)} [{verdict}]"}
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        if payload.get("alpha") is None or payload.get("beta") is None:
            miss.append({"field": "alpha", "why": "생산자/소비자 위험 미상",
                         "ask": "alpha(생산자위험), beta(소비자위험)를 주세요."})
        has_theta = payload.get("theta0") is not None and payload.get("theta1") is not None
        if not has_theta and payload.get("discrimination_ratio") is None:
            miss.append({"field": "theta0", "why": "MTBF 판별 기준 미상",
                         "ask": "theta0(합격 MTBF)·theta1(불합격 MTBF) 또는 discrimination_ratio를 주세요 (+trajectory)."})
        return miss
