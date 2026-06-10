"""review-matrix recipes — normalize states/items/cells. Graph cells are embedded by
re-using the cell type's own recipe (via graphconfig) so they re-mount a real engine
in-document. One recipe instance serves review-matrix / design-state-compare /
single-state-checklist (behaviour differs only in the structural gate)."""

from __future__ import annotations

from .base import Recipe

_CELL_KEYS = ("value", "unit", "status", "reason", "text", "ref", "link", "image",
              "min", "max", "scale", "delta", "goal", "tags", "color")


def inject_plugin(norm: dict, plugin: str, config: dict) -> dict:
    """Append a plugin + its pluginConfig to every embedded graph payload — used to LINK
    sibling cells (shared crosshair / linked brushing) without touching the cell recipes.
    The builder bundles the plugin because it scans graph_payloads[].plugins."""
    gps = (norm.get("assets") or {}).get("graph_payloads") or {}
    for gp in gps.values():
        plugs = gp.get("plugins") or []
        if plugin not in plugs:
            gp["plugins"] = plugs + [plugin]
        gp.setdefault("options", {}).setdefault("pluginConfig", {})[plugin] = dict(config)
    return norm


class MatrixRecipe(Recipe):
    type_name = "review-matrix"

    def normalize(self, payload: dict, resolved) -> dict:
        from .. import graphconfig  # lazy — avoids recipes<->graphconfig import cycle

        states = [s for s in (payload.get("states") or []) if isinstance(s, dict) and s.get("id")]
        baseline = (payload.get("meta") or {}).get("baseline") or (states[0]["id"] if states else None)
        graph_payloads: dict = {}
        out_items = []

        for it in payload.get("items") or []:
            nit = {k: it[k] for k in ("id", "group", "label", "unit", "type", "spec", "tags") if k in it}
            nit.setdefault("group", "")
            nit.setdefault("id", str(nit.get("label", "item")))
            if it.get("overlay_states"):
                ref = self._overlay(nit, it, states, graph_payloads, graphconfig)
                if ref:
                    nit["overlay"] = ref
                else:
                    nit["cells"] = {}
            else:
                cells = {}
                for s in states:
                    c = (it.get("cells") or {}).get(s["id"])
                    if c is not None:
                        cells[s["id"]] = self._cell(nit, s, c, graph_payloads, graphconfig)
                nit["cells"] = cells
            out_items.append(nit)

        options = {"title": payload.get("title") or "", "theme": (payload.get("options") or {}).get("theme", "auto")}
        for k in ("freeze_baseline", "diff", "heat", "collapsed_groups", "print_mode"):
            v = (payload.get("options") or {}).get(k)
            if v is not None:
                options[k] = v
        options.setdefault("diff", True)

        assets = {
            "states": states, "items": out_items, "baseline": baseline,
            "spec": payload.get("spec") or {}, "graph_payloads": graph_payloads,
            "meta": payload.get("meta") or {},
        }
        return {"engine": resolved.engine, "assets": assets, "options": options}

    def _cell(self, item, state, c, graph_payloads, graphconfig):
        if not isinstance(c, dict):
            return {"kind": "text", "value": str(c)}
        if c.get("kind") == "graph" and c.get("graph_ref"):
            gr = c["graph_ref"]
            gp = self._mini(graphconfig.graph_config(gr["type"], gr.get("payload") or {}, validate_cell=False))
            ref = f'{item["id"]}::{state["id"]}'
            graph_payloads[ref] = gp
            return {"kind": "graph", "ref": ref}
        out = {"kind": c.get("kind", "text")}
        for k in _CELL_KEYS:
            if k in c:
                out[k] = c[k]
        return out

    def _overlay(self, nit, it, states, graph_payloads, graphconfig):
        series, axes = [], None
        for s in states:
            c = (it.get("cells") or {}).get(s["id"])
            if c and c.get("kind") == "graph" and c.get("graph_ref"):
                pl = c["graph_ref"].get("payload") or {}
                axes = axes or pl.get("axes")
                for ser in pl.get("series") or []:
                    s2 = dict(ser)
                    s2["name"] = s.get("label", s["id"])
                    series.append(s2)
        if not series:
            return None
        gp = self._mini(graphconfig.graph_config("base-xy", {"axes": axes or {}, "series": series}, validate_cell=False))
        ref = f'{nit["id"]}::__overlay'
        graph_payloads[ref] = gp
        return ref

    @staticmethod
    def _mini(gp):
        gp = dict(gp)
        opts = dict(gp.get("options") or {})
        opts["legend"] = {"show": False}
        opts["exportButtons"] = []
        opts["controlbar"] = False           # mini cell: chrome lives in the modal only
        gp["options"] = opts
        return gp

    def structural_requires(self, payload: dict) -> list:
        miss = []
        states = payload.get("states") or []
        items = payload.get("items") or []
        gt = payload.get("graph_type")
        if not items:
            miss.append({"field": "items", "why": "점검 항목(행)이 없음",
                         "ask": "점검 항목(행)들을 알려주세요 (각 group/label/type)."})
        if not states:
            miss.append({"field": "states", "why": "비교할 열(설계 state)이 없음",
                         "ask": "비교할 설계 state(열)들을 알려주세요. 각 라벨/버전은? (단일 점검표면 1개)"})
        if gt == "design-state-compare" and len(states) < 2:
            miss.append({"field": "states", "why": "비교표는 state ≥2 필요",
                         "ask": "비교표는 설계 state가 2개 이상 필요합니다. 추가 state를 주시거나 single-state-checklist로 전환할까요?"})
        for it in items:
            for c in (it.get("cells") or {}).values():
                if isinstance(c, dict) and c.get("kind") == "graph":
                    gr = c.get("graph_ref")
                    if not (isinstance(gr, dict) and gr.get("type")):
                        miss.append({"field": "items[].cells.graph_ref", "why": "graph 셀에 graph_ref.type 누락",
                                     "ask": "graph 셀은 graph_ref:{type, payload}가 필요합니다. 어떤 그래프 타입인가요?"})
        base = (payload.get("meta") or {}).get("baseline")
        ids = {s.get("id") for s in states if isinstance(s, dict)}
        if base and base not in ids:
            miss.append({"field": "meta.baseline", "why": "baseline이 states에 없음",
                         "ask": "diff 기준(baseline) state id가 states 중 하나여야 합니다. 어느 것인가요?"})
        return miss
