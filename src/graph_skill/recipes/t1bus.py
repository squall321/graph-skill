"""T1 business / report-genre charts (all xy-core, glyph plugins):
candlestick-ohlc · slopegraph · dumbbell-plot · diverging-likert-bar · funnel-conversion-chart.

These fill the library's biggest gap — finance / survey / before-after comparison genres that
are standard in real reports but absent from the engineering-heavy catalog. Each pre-computes
its glyph geometry into pluginConfig and emits a style:"none" carrier for autoscale (slopegraph
is the exception — it draws real visible line+marker series, plugin only labels endpoints)."""

from __future__ import annotations

from .base import Recipe
from .base_xy import _num

# colorblind-safe (Okabe-Ito) for slopegraph item lines / dumbbell endpoints
_PAL = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00", "#F0E442", "#999999"]
# diverging ramp (RdBu with neutral gray center) sampled by response count
_DIVERGE = ["#b2182b", "#ef8a62", "#fddbc7", "#bbbbbb", "#d1e5f0", "#67a9cf", "#2166ac"]


def _axis(a, dlabel=""):
    a = a or {}
    return {"label": str(a.get("label", dlabel)), "unit": str(a.get("unit", "")), "log": False}


def _diverge_colors(n: int) -> list:
    if n <= 1:
        return ["#bbbbbb"]
    m = len(_DIVERGE) - 1
    return [_DIVERGE[round(j * m / (n - 1))] for j in range(n)]


class CandlestickRecipe(Recipe):
    type_name = "candlestick-ohlc"

    def normalize(self, payload, resolved):
        periods = [str(p) for p in (payload.get("periods") or [])]
        rows = payload.get("ohlc") or payload.get("candles") or []
        bars, lo, hi = [], None, None
        for i, r in enumerate(rows):
            if isinstance(r, dict):
                o, h, l, c = r.get("open"), r.get("high"), r.get("low"), r.get("close")
            else:
                o, h, l, c = (list(r) + [None] * 4)[:4]
            o, h, l, c = _num(o), _num(h), _num(l), _num(c)
            bars.append({"x": i, "o": o, "h": h, "l": l, "c": c})
            for v in (h, l):
                if v is not None:
                    lo = v if lo is None else min(lo, v)
                    hi = v if hi is None else max(hi, v)
        if not periods:
            periods = [str(i + 1) for i in range(len(bars))]
        pad = ((hi - lo) * 0.06 if (lo is not None and hi is not None and hi > lo) else 1.0)
        ax = payload.get("axes") or {}
        xa = _axis(ax.get("x"), "")
        xa["categories"] = periods
        unit = str((ax.get("y") or {}).get("unit", ""))
        dx, dy = [], []
        for b in bars:
            dx += [b["x"], b["x"]]
            dy += [b["l"], b["h"]]
        opts = {"axes": {"x": xa, "y": _axis(ax.get("y"))},
                "pluginConfig": {"ohlc": {"bars": bars, "unit": unit}}}
        if pad and lo is not None:
            # carrier already spans lo..hi via dy; padding handled by engine nice-ticks
            pass
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine,
                "assets": {"series": [{"name": "_ohlc", "x": dx, "y": dy, "style": "none"}]},
                "options": opts}

    def structural_requires(self, payload):
        miss = []
        rows = payload.get("ohlc") or payload.get("candles") or []
        if not rows:
            miss.append({"field": "ohlc", "why": "캔들(OHLC) 데이터가 없음",
                         "ask": "기간별 시·고·저·종을 주세요: ohlc:[[open,high,low,close], …] (periods 라벨과 정렬)."})
        else:
            for i, r in enumerate(rows):
                vals = ([r.get("open"), r.get("high"), r.get("low"), r.get("close")]
                        if isinstance(r, dict) else list(r))
                if sum(1 for v in vals if v is not None) < 4:
                    miss.append({"field": f"ohlc[{i}]", "why": "OHLC 4개 값이 모두 필요",
                                 "ask": f"{i+1}번째 캔들에 open/high/low/close 4개를 모두 주세요."})
                    break
        ya = (payload.get("axes") or {}).get("y") or {}
        if not ya.get("label") or "unit" not in ya:
            miss.append({"field": "axes.y", "why": "값(가격 등) 의미/단위 미상",
                         "ask": "값 축의 label과 unit을 주세요 (axes.y={label,unit}; 통화/무차원이면 unit 명시)."})
        return miss


class SlopegraphRecipe(Recipe):
    type_name = "slopegraph"

    def normalize(self, payload, resolved):
        positions = [str(p) for p in (payload.get("positions") or [])]
        items = payload.get("items") or []
        series, cfg_items = [], []
        for i, it in enumerate(items):
            name = str(it.get("name", f"항목{i+1}"))
            left, right = _num(it.get("left")), _num(it.get("right"))
            col = it.get("color") or _PAL[i % len(_PAL)]
            series.append({"name": name, "x": [0, 1], "y": [left, right],
                           "style": "line+markers", "color": col})
            cfg_items.append({"name": name, "left": left, "right": right, "color": col})
        ax = payload.get("axes") or {}
        xa = _axis(ax.get("x"), "")
        xa["categories"] = positions or ["전", "후"]
        # right pad so endpoint name labels fit
        name_w = min(220, 40 + (max((len(i["name"]) for i in cfg_items), default=4)) * 9)
        opts = {"axes": {"x": xa, "y": _axis(ax.get("y"))},
                "pad": {"left": 64, "right": name_w},
                "pluginConfig": {"slopegraph": {"items": cfg_items, "xl": 0, "xr": 1}}}
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": series}, "options": opts}

    def structural_requires(self, payload):
        miss = []
        pos = payload.get("positions") or []
        if len(pos) < 2:
            miss.append({"field": "positions", "why": "두 위치(전/후 등) 라벨이 필요",
                         "ask": "두 축 위치 라벨을 주세요: positions:['전','후'] (2개)."})
        its = payload.get("items") or []
        if len(its) < 2 or any(i.get("left") is None or i.get("right") is None for i in its):
            miss.append({"field": "items", "why": "항목별 좌/우 값이 필요",
                         "ask": "items:[{name, left, right}, …] (2개 이상, 각 항목 좌·우 값 모두)."})
        ya = (payload.get("axes") or {}).get("y") or {}
        if not ya.get("label") or "unit" not in ya:
            miss.append({"field": "axes.y", "why": "값(y) 의미/단위 미상",
                         "ask": "값의 label과 unit을 주세요 (axes.y={label,unit}; 무차원이면 unit:'')."})
        return miss


class DumbbellRecipe(Recipe):
    type_name = "dumbbell-plot"

    def normalize(self, payload, resolved):
        cats = [str(c) for c in (payload.get("categories") or [])]
        sers = payload.get("series") or []
        a_ser = sers[0] if len(sers) > 0 else {}
        b_ser = sers[1] if len(sers) > 1 else {}
        av = [_num(v) for v in (a_ser.get("values") or [])]
        bv = [_num(v) for v in (b_ser.get("values") or [])]
        n = len(cats)
        rows, allv = [], []
        for i in range(n):
            a = av[i] if i < len(av) else None
            b = bv[i] if i < len(bv) else None
            rows.append({"y": n - 1 - i, "label": cats[i], "a": a, "b": b})
            allv += [v for v in (a, b) if v is not None]
        lo, hi = (min(allv), max(allv)) if allv else (0.0, 1.0)
        pad = (hi - lo) * 0.08 or 1.0
        ax = payload.get("axes") or {}
        xa = _axis(ax.get("x"))
        name_w = min(200, 28 + (max((len(c) for c in cats), default=4)) * 10)
        opts = {
            "hideAxes": True,
            "pad": {"left": name_w, "right": 56, "bottom": 30},
            "axes": {"x": xa, "y": {"label": "", "unit": ""}},
            "pluginConfig": {"dumbbell": {
                "rows": rows, "aName": str(a_ser.get("name", "A")), "bName": str(b_ser.get("name", "B")),
                "aColor": a_ser.get("color") or _PAL[0], "bColor": b_ser.get("color") or _PAL[1],
                "unit": xa["unit"], "xlabel": xa["label"]}},
        }
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine,
                "assets": {"series": [{"name": "_db", "x": [lo - pad, hi + pad], "y": [-0.5, n - 0.5], "style": "none"}]},
                "options": opts}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("categories") or []):
            miss.append({"field": "categories", "why": "범주(행) 라벨이 없음",
                         "ask": "범주 라벨들을 주세요: categories:[...]."})
        sers = payload.get("series") or []
        if len(sers) != 2:
            miss.append({"field": "series", "why": "두 값 계열(예: 전/후)이 필요",
                         "ask": "정확히 2개 계열을 주세요: series:[{name, values:[...]}, {name, values:[...]}]."})
        xa = (payload.get("axes") or {}).get("x") or {}
        if not xa.get("label") or "unit" not in xa:
            miss.append({"field": "axes.x", "why": "값(x) 의미/단위 미상",
                         "ask": "값 축의 label과 unit을 주세요 (axes.x={label,unit}; 무차원이면 unit:'')."})
        return miss


class DivergingLikertRecipe(Recipe):
    type_name = "diverging-likert-bar"

    def normalize(self, payload, resolved):
        questions = [str(q) for q in (payload.get("questions") or [])]
        responses = [str(r) for r in (payload.get("responses") or [])]
        data = payload.get("data") or []
        basis = str(payload.get("basis", "percent"))
        nr = len(responses)
        neutral = payload.get("neutral_index")
        if neutral is None and nr % 2 == 1:
            neutral = nr // 2
        left_idx = list(range(0, neutral)) if neutral is not None else list(range(0, nr // 2))
        right_start = (neutral + 1) if neutral is not None else (nr // 2)
        right_idx = list(range(right_start, nr))
        colors = _diverge_colors(nr)
        cats, max_left, max_right = [], 0.0, 0.0
        n = len(questions)
        for i in range(n):
            raw = [_num(v) or 0.0 for v in (data[i] if i < len(data) else [])]
            raw = (raw + [0.0] * nr)[:nr]
            tot = sum(raw) or 1.0
            vals = [v / tot * 100.0 for v in raw] if basis == "percent" else raw
            neutral_val = vals[neutral] if neutral is not None else 0.0
            left_sum = sum(vals[k] for k in left_idx)
            cursor = -left_sum - neutral_val / 2.0
            segs = []
            for k in left_idx:
                segs.append({"base": cursor, "top": cursor + vals[k], "ci": k}); cursor += vals[k]
            if neutral is not None:
                segs.append({"base": cursor, "top": cursor + neutral_val, "ci": neutral}); cursor += neutral_val
            for k in right_idx:
                segs.append({"base": cursor, "top": cursor + vals[k], "ci": k}); cursor += vals[k]
            right_sum = sum(vals[k] for k in right_idx)
            max_left = max(max_left, left_sum + neutral_val / 2.0)
            max_right = max(max_right, right_sum + neutral_val / 2.0)
            unit = "%" if basis == "percent" else ""
            summary = f"우호 {right_sum:.0f}{unit} / 비우호 {left_sum:.0f}{unit}"
            cats.append({"y": n - 1 - i, "label": questions[i], "segs": segs, "summary": summary})
        pad = (max_left + max_right) * 0.05 or 1.0
        unit = "%" if basis == "percent" else str(((payload.get("axes") or {}).get("x") or {}).get("unit", ""))
        name_w = min(240, 28 + (max((len(q) for q in questions), default=4)) * 10)
        opts = {
            "hideAxes": True,
            "pad": {"left": name_w, "right": 30, "bottom": 30},
            "axes": {"x": {"label": "응답 비율" if basis == "percent" else "응답 수", "unit": unit},
                     "y": {"label": "", "unit": ""}},
            "pluginConfig": {"diverging": {"cats": cats, "responses": responses, "colors": colors, "unit": unit}},
        }
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine,
                "assets": {"series": [{"name": "_lk", "x": [-max_left - pad, max_right + pad],
                                       "y": [-0.5, n - 0.5], "style": "none"}]},
                "options": opts}

    def structural_requires(self, payload):
        miss = []
        qs = payload.get("questions") or []
        rs = payload.get("responses") or []
        data = payload.get("data") or []
        if not qs:
            miss.append({"field": "questions", "why": "문항(행) 라벨이 없음",
                         "ask": "문항 라벨들을 주세요: questions:[...]."})
        if len(rs) < 2:
            miss.append({"field": "responses", "why": "순서형 응답 척도가 필요",
                         "ask": "순서대로 응답 척도를 주세요: responses:['매우 비동의', …, '매우 동의'] (낮음→높음)."})
        if not data or any(len(row) != len(rs) for row in data) or len(data) != len(qs):
            miss.append({"field": "data", "why": "문항×응답 카운트 행렬 형상 불일치",
                         "ask": "data:[[문항별 각 응답 카운트/비율], …] — 행=questions, 열=responses 길이와 일치."})
        if "basis" not in payload:
            miss.append({"field": "basis", "why": "비율(percent) vs 카운트(count) 기준 미상",
                         "ask": "data가 비율인지 카운트인지 알려주세요: basis:'percent' 또는 'count'."})
        return miss


class FunnelRecipe(Recipe):
    type_name = "funnel-conversion-chart"

    def normalize(self, payload, resolved):
        raw = payload.get("stages") or []
        n = len(raw)
        first = _num((raw[0] or {}).get("value")) if raw else None
        stages, max_v, prev = [], 0.0, None
        for idx, s in enumerate(raw):
            v = _num(s.get("value")) or 0.0
            max_v = max(max_v, v)
            pct_first = (v / first * 100.0) if first else 100.0
            pct_prev = (v / prev * 100.0) if (prev not in (None, 0)) else 100.0
            stages.append({"i": n - 1 - idx, "label": str(s.get("label", f"단계{idx+1}")),
                           "value": v, "pctFirst": pct_first, "pctPrev": pct_prev})
            prev = v
        ax = payload.get("axes") or {}
        xa = _axis(ax.get("x"))
        name_w = min(200, 28 + (max((len(s["label"]) for s in stages), default=6)) * 10)
        opts = {
            "hideAxes": True,
            "pad": {"left": name_w, "right": 96, "bottom": 16},
            "axes": {"x": xa, "y": {"label": "", "unit": ""}},
            "pluginConfig": {"funnel": {"stages": stages, "maxValue": max_v or 1.0,
                                        "unit": xa["unit"], "color": payload.get("color") or "#2563eb"}},
        }
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine,
                "assets": {"series": [{"name": "_fn", "x": [0, max_v or 1.0], "y": [-0.5, n - 0.5], "style": "none"}]},
                "options": opts}

    def structural_requires(self, payload):
        miss = []
        st = payload.get("stages") or []
        if len(st) < 2 or any(s.get("value") is None or not s.get("label") for s in st):
            miss.append({"field": "stages", "why": "단계 라벨/값이 부족",
                         "ask": "단계를 주세요: stages:[{label, value}, …] (2개 이상, 순서=위→아래)."})
        xa = (payload.get("axes") or {}).get("x") or {}
        if not xa.get("label") or "unit" not in xa:
            miss.append({"field": "axes.x", "why": "단계 값 의미/단위 미상",
                         "ask": "단계 값의 label과 unit을 주세요 (axes.x={label,unit}; 건수면 unit:'')."})
        return miss
