"""stream-graph (themeriver) on xy-core + sunburst (radial hierarchy, drill-down) on
flow-core. Stream bands are pre-stacked on a centered baseline so the JS plugin only
fills paths; sunburst passes a nested tree the engine partitions + re-roots on click."""

from __future__ import annotations

from .base import Recipe
from .matrix_compare import MatrixRecipe
from .playback import _carrier_series


def _axis(ax, key, dflt_label, dflt_unit):
    a = (ax or {}).get(key) or {}
    return {"label": str(a.get("label", dflt_label)), "unit": str(a.get("unit", dflt_unit)),
            "scale": a.get("scale", "linear")}


class StreamGraphRecipe(Recipe):
    type_name = "stream-graph"

    def normalize(self, payload, resolved):
        series = payload.get("series") or []
        # union x grid across series
        xset = set()
        smaps = []
        for s in series:
            m = {}
            for p in s.get("data") or []:
                x, y = (p[0], p[1]) if isinstance(p, (list, tuple)) else (p["x"], p["y"])
                m[float(x)] = float(y)
            smaps.append(m)
            xset.update(m.keys())
        xs = sorted(xset)
        # centered (silhouette) baseline: g0[i] = -0.5 * total[i]
        totals = [sum(m.get(x, 0.0) for m in smaps) for x in xs]
        base = [-0.5 * t for t in totals]
        bands, acc = [], list(base)
        for si, s in enumerate(series):
            lo = list(acc)
            hi = [acc[i] + smaps[si].get(xs[i], 0.0) for i in range(len(xs))]
            acc = hi
            band = {"name": s.get("name", f"s{si}"), "lo": [round(v, 6) for v in lo], "hi": [round(v, 6) for v in hi]}
            if s.get("color"):
                band["color"] = s["color"]
            bands.append(band)
        ymin = min(base) if base else 0
        ymax = max(acc) if acc else 1
        carrier = [[xs[0] if xs else 0, ymin], [xs[-1] if xs else 1, ymax]]
        options = {
            "axes": {"x": _axis(payload.get("axes"), "x", "X", ""), "y": _axis(payload.get("axes"), "y", "", "")},
            "pluginConfig": {"streamgraph": {"x": [round(x, 6) for x in xs], "bands": bands}},
        }
        if payload.get("title"):
            options["title"] = str(payload["title"])
        return {"engine": resolved.engine,
                "assets": {"series": _carrier_series(carrier)},
                "options": options}

    def structural_requires(self, payload):
        miss = []
        series = payload.get("series") or []
        if len(series) < 2:
            miss.append({"field": "series", "why": "누적할 계열이 2개 미만",
                         "ask": "구성 계열을 주세요: series:[{name,data:[[x,y],…]}, …] (공유 x축, 값≥0)."})
        ax = (payload.get("axes") or {}).get("x") or {}
        if not ax.get("label") or ax.get("unit") is None:
            miss.append({"field": "axes.x", "why": "x축 의미/단위 미상",
                         "ask": "x축(보통 시간)의 label과 unit을 알려주세요(무차원이면 unit=\"\")."})
        return miss


class OverviewDetailRecipe(Recipe):
    """focus+context — a detail panel that zooms to a draggable window in a context overview
    below it. Two base-xy panels of the same series, linked via xbrush→xfollow on the bus."""

    type_name = "overview-detail"
    _matrix = MatrixRecipe()

    def normalize(self, payload, resolved):
        axes = {"x": _axis(payload.get("axes"), "x", "X", ""), "y": _axis(payload.get("axes"), "y", "Y", "")}
        series = payload.get("series") or []

        def cell():
            return {"kind": "graph", "graph_ref": {"type": "base-xy",
                    "payload": {"axes": axes, "series": [dict(s) for s in series]}}}

        items = [{"id": "detail", "label": "상세", "type": "graph", "cells": {"t": cell()}},
                 {"id": "overview", "label": "개요 (창을 드래그)", "type": "graph", "cells": {"t": cell()}}]
        mp = {"title": str(payload.get("title") or "Overview + detail"),
              "states": [{"id": "t", "label": ""}], "items": items, "options": {"diff": False}}
        out = self._matrix.normalize(mp, resolved)
        for ref, gp in (out["assets"].get("graph_payloads") or {}).items():
            plug = "xbrush" if ref.startswith("overview") else "xfollow"
            gp["plugins"] = (gp.get("plugins") or []) + [plug]
            gp.setdefault("options", {}).setdefault("pluginConfig", {})[plug] = {"group": "od"}
        return out

    def structural_requires(self, payload):
        miss = []
        if not (payload.get("series") or []):
            miss.append({"field": "series", "why": "표시할 시계열이 없음",
                         "ask": "시계열을 주세요: series:[{name, data:[[x,y],…]}]."})
        ax = (payload.get("axes") or {}).get("x") or {}
        if not ax.get("label") or ax.get("unit") is None:
            miss.append({"field": "axes.x", "why": "x축 의미/단위 미상",
                         "ask": "x축의 label과 unit을 알려주세요(무차원이면 unit=\"\")."})
        return miss


class TreemapDrilldownRecipe(Recipe):
    """Hierarchical treemap — each node's children pre-squarified; JS plugin drills on click."""

    type_name = "treemap-drilldown"
    _pal = ["#2563eb", "#0891b2", "#059669", "#ca8a04", "#dc2626", "#9333ea", "#0ea5e9", "#65a30d",
            "#e11d48", "#7c3aed", "#0d9488", "#b45309"]

    def normalize(self, payload, resolved):
        from ..postprocess import treemap as _tm

        tree = payload.get("tree") or payload.get("hierarchy")
        clean = self._annotate(tree, _tm, 0, None)
        opts = {"axes": {"x": {"label": "", "unit": "", "log": False}, "y": {"label": "", "unit": "", "log": False}},
                "hideAxes": True, "pad": {"left": 12, "right": 12, "bottom": 12},
                "pluginConfig": {"treemap-drill": {"tree": clean}}}
        if payload.get("title"):
            opts["title"] = str(payload["title"])
        return {"engine": resolved.engine,
                "assets": {"series": [{"name": "_tm", "x": [0, 1], "y": [0, 1], "style": "none"}]}, "options": opts}

    def _annotate(self, n, _tm, depth, branch):
        out = {"name": str(n.get("name", ""))}
        kids = n.get("children") if isinstance(n, dict) else None
        if isinstance(kids, list) and kids:
            children = []
            for i, c in enumerate(kids):
                bcol = (c.get("color") if isinstance(c, dict) else None) or (self._pal[i % len(self._pal)] if depth == 0 else branch)
                children.append(self._annotate(c, _tm, depth + 1, bcol))
            vals = [ch["value"] for ch in children]
            rects = _tm.squarify(vals, 1.0, 1.0)
            out["children"] = children
            out["rects"] = [({"x": r["x"], "y": r["y"], "w": r["w"], "h": r["h"]} if r else None) for r in rects]
            out["value"] = float(sum(vals))
            if branch:
                out["color"] = branch
        else:
            out["value"] = float((n.get("value", 0) if isinstance(n, dict) else 0) or 0)
            out["color"] = (n.get("color") if isinstance(n, dict) else None) or branch or self._pal[0]
        return out

    def structural_requires(self, payload):
        tree = payload.get("tree") or payload.get("hierarchy")
        if not isinstance(tree, dict) or not tree.get("children"):
            return [{"field": "tree", "why": "계층 트리가 없음",
                     "ask": "계층을 주세요: tree:{name, children:[{name, value} 또는 {name, children:[…]}]} (잎에 value)."}]
        return []


class SunburstRecipe(Recipe):
    type_name = "sunburst"

    def normalize(self, payload, resolved):
        tree = payload.get("tree") or payload.get("hierarchy")
        options = {"title": payload.get("title") or "", "theme": (payload.get("options") or {}).get("theme", "auto")}
        return {"engine": resolved.engine,
                "assets": {"kind": "sunburst", "tree": self._clean(tree)}, "options": options}

    def _clean(self, n):
        if not isinstance(n, dict):
            return {"name": str(n), "value": 1}
        out = {"name": str(n.get("name", ""))}
        if n.get("color"):
            out["color"] = n["color"]
        kids = n.get("children")
        if isinstance(kids, list) and kids:
            out["children"] = [self._clean(c) for c in kids]
        elif n.get("value") is not None:
            out["value"] = float(n["value"])
        else:
            out["value"] = 1.0
        return out

    def structural_requires(self, payload):
        tree = payload.get("tree") or payload.get("hierarchy")
        if not isinstance(tree, dict) or not (tree.get("children")):
            return [{"field": "tree", "why": "계층 트리가 없음",
                     "ask": "계층을 주세요: tree:{name, children:[{name, value} 또는 {name, children:[…]}]} "
                            "(잎 노드에 value)."}]
        return []
