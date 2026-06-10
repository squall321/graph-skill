"""Wave-7 — diverse table types. correlation-matrix / confusion-matrix (field-core computed
heatmaps) + kpi-scorecard / decision-matrix (review-matrix with rich cells: heat/bar/delta)."""

from __future__ import annotations

from ..postprocess import stats
from .base import Recipe
from .base_xy import _num
from .matrix_compare import MatrixRecipe


class CorrelationMatrixRecipe(Recipe):
    """Pearson correlation heatmap of N variables (−1..1, diverging)."""

    type_name = "correlation-matrix"

    def normalize(self, payload, resolved):
        names, r = stats.pearson_matrix(payload.get("variables") or {})
        n = len(names)
        opts = {"axes": {"x": {"label": "변수 (index)", "unit": ""}, "y": {"label": "변수 (index)", "unit": ""}},
                "z": {"label": "r", "unit": ""}, "colormap": "coolwarm", "zdomain": [-1, 1], "contours": False}
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"field": {"x": list(range(n)), "y": list(range(n)), "z": r}}, "options": opts}

    def structural_requires(self, payload):
        v = payload.get("variables") or {}
        if len(v) < 2:
            return [{"field": "variables", "why": "상관행렬은 변수 2개 이상",
                     "ask": "변수별 값을 주세요 (variables:{이름:[값...], ...}, 같은 길이)."}]
        return []


class ConfusionMatrixRecipe(Recipe):
    """Classification confusion matrix heatmap (+ accuracy in the title)."""

    type_name = "confusion-matrix"

    def normalize(self, payload, resolved):
        labels = payload.get("labels") or []
        m = payload.get("matrix")
        if m is None and payload.get("y_true") and payload.get("y_pred"):
            yt, yp = payload["y_true"], payload["y_pred"]
            labs = labels or sorted(set(yt) | set(yp))
            idx = {lab: i for i, lab in enumerate(labs)}
            m = [[0] * len(labs) for _ in labs]
            for a, b in zip(yt, yp):
                m[idx[a]][idx[b]] += 1
            labels = labs
        m = [[_num(c) or 0 for c in row] for row in (m or [])]
        n = len(m)
        tot = sum(sum(r) for r in m) or 1
        acc = sum(m[i][i] for i in range(n)) / tot
        title = str(payload.get("title") or "Confusion matrix") + f"  (acc={acc:.1%})"
        opts = {"axes": {"x": {"label": "Predicted", "unit": ""}, "y": {"label": "Actual", "unit": ""}},
                "z": {"label": "count", "unit": ""}, "colormap": "viridis", "contours": False, "title": title}
        return {"engine": resolved.engine, "assets": {"field": {"x": list(range(n)), "y": list(range(n)), "z": m}}, "options": opts}

    def structural_requires(self, payload):
        if not payload.get("matrix") and not (payload.get("y_true") and payload.get("y_pred")):
            return [{"field": "matrix", "why": "혼동행렬 데이터가 없음",
                     "ask": "matrix:[[...], ...] (실제×예측 카운트) 또는 y_true:[...], y_pred:[...] 를 주세요."}]
        return []


class KpiScorecardRecipe(Recipe):
    """KPI scorecard — metrics × (value/target/status/achievement bar), rich cells."""

    type_name = "kpi-scorecard"
    _matrix = MatrixRecipe()

    def normalize(self, payload, resolved):
        metrics = payload.get("metrics") or []
        states = [{"id": "val", "label": "값"}, {"id": "tgt", "label": "목표"},
                  {"id": "st", "label": "상태"}, {"id": "ach", "label": "달성도"}]
        items = []
        for i, m in enumerate(metrics):
            val, tgt = _num(m.get("value")), _num(m.get("target"))
            unit, goal = str(m.get("unit", "")), m.get("goal", "max")
            status = m.get("status")
            if not status and tgt is not None and val is not None:
                status = "pass" if ((val >= tgt) if goal == "max" else (val <= tgt)) else "warn"
            bmax = _num(m.get("max")) or (tgt if (goal == "max" and tgt) else None) or (max(filter(None, [val, tgt])) if (val or tgt) else 1)
            cells = {
                "val": {"kind": "delta", "value": val, "unit": unit,
                        "delta": (val - tgt) if (val is not None and tgt is not None) else None, "goal": goal},
                "tgt": {"kind": "number", "value": tgt, "unit": unit},
                "st": {"kind": "status", "status": status or "pass"},
                "ach": {"kind": "bar", "value": val, "max": bmax},
            }
            items.append({"id": f"m{i}", "label": str(m.get("name", f"KPI{i+1}")), "unit": unit, "cells": cells})
        mp = {"title": str(payload.get("title") or "KPI Scorecard"), "states": states, "items": items, "options": {"diff": False}}
        return self._matrix.normalize(mp, resolved)

    def structural_requires(self, payload):
        if not (payload.get("metrics") or []):
            return [{"field": "metrics", "why": "KPI 지표가 없음",
                     "ask": "지표들을 주세요 (metrics:[{name, value, target, unit, goal:'max'|'min'}, ...])."}]
        return []


class DecisionMatrixRecipe(Recipe):
    """Weighted decision (Pugh) matrix — criteria × options scored (heat) + weighted total/winner."""

    type_name = "decision-matrix"
    _matrix = MatrixRecipe()

    def normalize(self, payload, resolved):
        criteria = payload.get("criteria") or []
        options = payload.get("options") or []
        scores = payload.get("scores") or []                 # scores[criterion][option]
        states = [{"id": f"o{j}", "label": str(o)} for j, o in enumerate(options)]
        flat = [s for row in scores for s in (row or []) if _num(s) is not None]
        smin, smax = (min(flat), max(flat)) if flat else (0, 1)
        items = []
        for ci, cr in enumerate(criteria):
            w = _num(cr.get("weight")) or 1.0
            cells = {}
            for j in range(len(options)):
                sv = _num(scores[ci][j]) if (ci < len(scores) and j < len(scores[ci])) else None
                cells[f"o{j}"] = {"kind": "heat", "value": sv, "min": smin, "max": smax, "scale": "highgood"}
            items.append({"id": f"c{ci}", "label": f"{cr.get('name', '')} (w{w:g})", "cells": cells})
        totals = []
        for j in range(len(options)):
            tot = sum((_num(criteria[ci].get("weight")) or 1.0) * (_num(scores[ci][j]) or 0.0)
                      for ci in range(len(criteria)) if (ci < len(scores) and j < len(scores[ci])))
            totals.append(tot)
        best = max(range(len(totals)), key=lambda j: totals[j]) if totals else -1
        tcells = {}
        for j in range(len(options)):
            tcells[f"o{j}"] = ({"kind": "status", "status": "pass", "value": totals[j]} if j == best
                               else {"kind": "number", "value": totals[j]})
        items.append({"id": "_total", "label": "가중 합계", "cells": tcells})
        mp = {"title": str(payload.get("title") or "Decision matrix"), "states": states, "items": items, "options": {"diff": False}}
        return self._matrix.normalize(mp, resolved)

    def structural_requires(self, payload):
        if not (payload.get("criteria") and payload.get("options") and payload.get("scores")):
            return [{"field": "criteria/options/scores", "why": "의사결정표 데이터 부족",
                     "ask": "criteria:[{name,weight}], options:[이름...], scores:[[기준×옵션 점수]] 를 주세요."}]
        return []
