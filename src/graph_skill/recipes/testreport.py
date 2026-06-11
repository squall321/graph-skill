"""test-report — 시험성적서 컴포지트: 시험 개요(kv) + 판정요약(spec-margin 임베드) +
결과 그래프들(임의 타입 graph_ref) + 종합판정을 한 self-contained 파일로 결합.
work-plan과 같은 review-matrix 멀티엔진 그래프셀 메커니즘."""

from __future__ import annotations

from .base import Recipe
from .ecae import SpecMarginRecipe


class TestReportRecipe(Recipe):
    type_name = "test-report"
    _margin = SpecMarginRecipe()

    def normalize(self, payload, resolved):
        from .. import graphconfig  # lazy — recipes<->graphconfig cycle

        gp_store, items = {}, []

        def wide(rid, group, label, gtype, gpayload, h):
            gp = dict(graphconfig.graph_config(gtype, gpayload, validate_cell=False))
            o = dict(gp.get("options") or {})
            o.setdefault("exportButtons", [])
            gp["options"] = o
            gp_store[rid] = gp
            items.append({"id": rid, "group": group, "label": label, "type": "graph",
                          "overlay": rid, "h": h, "cells": {}})

        # ── 시험 개요 (자유 key-value) ──
        for i, (k, v) in enumerate((payload.get("info") or {}).items()):
            items.append({"id": f"i{i}", "group": "시험 개요", "label": str(k), "type": "meta",
                          "cells": {"v": {"kind": "text", "value": str(v)}}})

        # ── 판정 요약 (spec-margin 임베드) ──
        margins = payload.get("margins") or []
        if margins:
            wide("margin", "판정 요약", "규격 마진", "spec-margin-chart",
                 {"items": margins}, max(180, 40 + 64 * len(margins)))

        # ── 결과 그래프 (임의 타입) ──
        for i, r in enumerate(payload.get("results") or []):
            gr = r["graph_ref"]
            wide(f"g{i}", "시험 결과", str(r.get("label", f"결과 {i + 1}")),
                 gr["type"], gr.get("payload") or {}, int(r.get("h", 320)))

        # ── 종합 판정 ──
        v = payload.get("verdict") or {}
        st = str(v.get("status", "")).lower()
        st_map = {"pass": "pass", "합격": "pass", "fail": "fail", "불합격": "fail", "warn": "warn", "조건부": "warn"}
        cells = {"v": {"kind": "status", "status": st_map.get(st, "warn")}}
        label = "종합 판정" + (f" — {v['note']}" if v.get("note") else "")
        items.append({"id": "verdict", "group": "종합 판정", "label": label, "type": "verdict", "cells": cells})

        assets = {"states": [{"id": "v", "label": ""}], "items": items, "baseline": "v",
                  "spec": {}, "graph_payloads": gp_store, "meta": {}}
        options = {"title": str(payload.get("title") or "시험성적서"), "theme": "auto", "diff": False}
        return {"engine": resolved.engine, "assets": assets, "options": options}

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("info") or {}):
            miss.append({"field": "info", "why": "시험 개요가 없음",
                         "ask": "info:{시험명, 규격/조건, 시료, 장비, 일자, …} 자유 키-값으로 주세요."})
        if not (payload.get("results") or payload.get("margins")):
            miss.append({"field": "results", "why": "시험 결과(그래프/마진)가 없음",
                         "ask": "results:[{label, graph_ref:{type,payload}, h?}] 또는 margins:[{label,value,min/max,unit}] 중 하나 이상."})
        if margins := payload.get("margins"):
            miss.extend(self._margin.structural_requires({"items": margins}))
        v = payload.get("verdict") or {}
        if not v.get("status"):
            miss.append({"field": "verdict.status", "why": "종합 판정 미상",
                         "ask": "verdict:{status:'pass|fail|warn'(합격/불합격/조건부), note?}를 주세요."})
        return miss
