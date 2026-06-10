"""flowchart — freeform node-link diagram (flow-core). Nodes carry rich content
(text/value/kv/list/image/table) or a REAL embedded graph (graph_ref → re-mounted
in-document via graph_payloads, same mechanism as review-matrix graph cells).
Highly structured input: nodes[] + edges[]. Layout = explicit x,y (irregular) OR
auto-layered when omitted. A `steps[]` shorthand builds a linear chain."""

from __future__ import annotations

from .base import Recipe

_NODE_KEYS = ("id", "type", "label", "x", "y", "w", "h", "color", "accent", "group")
_PASS_CONTENT = ("text", "value", "unit", "sub", "items", "image", "table")


class FlowchartRecipe(Recipe):
    type_name = "flowchart"

    def normalize(self, payload: dict, resolved) -> dict:
        from .. import graphconfig  # lazy — avoid recipes<->graphconfig cycle

        nodes_in, edges_in = self._materialize(payload)
        graph_payloads: dict = {}
        out_nodes = []
        for n in nodes_in:
            nn = {k: n[k] for k in _NODE_KEYS if k in n}
            nn.setdefault("id", str(nn.get("label", "n")))
            c = n.get("content")
            if isinstance(c, dict) and c.get("kind"):
                nn["content"] = self._content(nn["id"], c, graph_payloads, graphconfig)
            out_nodes.append(nn)

        ids = {n["id"] for n in out_nodes}
        out_edges = [
            {k: e[k] for k in ("from", "to", "label", "kind", "color", "from_side", "to_side") if k in e}
            for e in edges_in if e.get("from") in ids and e.get("to") in ids
        ]

        opts = payload.get("options") or {}
        options = {
            "title": payload.get("title") or "",
            "theme": opts.get("theme", "auto"),
            "direction": opts.get("direction") or payload.get("direction") or "TB",
        }
        for k in ("node_w", "rank_gap", "node_gap"):
            if opts.get(k) is not None:
                options[k] = opts[k]

        assets = {
            "nodes": out_nodes, "edges": out_edges,
            "direction": options["direction"], "graph_payloads": graph_payloads,
        }
        return {"engine": resolved.engine, "assets": assets, "options": options}

    def _content(self, node_id, c, graph_payloads, graphconfig):
        kind = c.get("kind")
        if kind == "graph" and c.get("graph_ref"):
            gr = c["graph_ref"]
            gp = self._mini(graphconfig.graph_config(gr["type"], gr.get("payload") or {}, validate_cell=False))
            ref = f"{node_id}::graph"
            graph_payloads[ref] = gp
            return {"kind": "graph", "ref": ref}
        out = {"kind": kind}
        for k in _PASS_CONTENT:
            if k in c:
                out[k] = c[k]
        return out

    @staticmethod
    def _mini(gp):
        gp = dict(gp)
        o = dict(gp.get("options") or {})
        o["legend"] = {"show": False}
        o["exportButtons"] = []
        gp["options"] = o
        return gp

    @staticmethod
    def _materialize(payload):
        """Return (nodes, edges). Supports a `steps[]` shorthand → linear chain."""
        nodes = payload.get("nodes")
        edges = payload.get("edges")
        if nodes:
            return list(nodes), list(edges or [])
        steps = payload.get("steps")
        if steps:
            ns, es, n = [], [], len(steps)
            for i, s in enumerate(steps):
                sid = f"s{i}"
                if isinstance(s, dict):
                    node = dict(s)
                    node.setdefault("id", sid)
                else:
                    node = {"id": sid, "label": str(s)}
                node.setdefault("type", "terminal" if i in (0, n - 1) else "process")
                ns.append(node)
                if i:
                    es.append({"from": ns[i - 1]["id"], "to": node["id"]})
            return ns, es
        return [], list(edges or [])

    def structural_requires(self, payload: dict) -> list:
        miss = []
        nodes, edges = self._materialize(payload)
        if not nodes:
            miss.append({
                "field": "nodes",
                "why": "순서도 노드가 없음",
                "ask": "순서도 노드들을 알려주세요. 각 노드의 id/label/type(terminal|process|decision|io|subprocess)과, "
                       "원하면 content(text/value/kv/list/image/table/graph)를. 또는 간단히 steps:[\"단계1\",\"단계2\",…] 로.",
            })
            return miss
        ids = {n.get("id") if isinstance(n, dict) else None for n in nodes}
        ids |= {str((n or {}).get("label")) for n in nodes if isinstance(n, dict) and "id" not in n}
        bad = [e for e in (edges or []) if e.get("from") not in ids or e.get("to") not in ids]
        if bad:
            miss.append({
                "field": "edges",
                "why": f"{len(bad)}개 엣지가 존재하지 않는 노드 id를 참조",
                "ask": "엣지의 from/to가 모두 nodes의 id와 일치해야 합니다. 어떤 노드를 연결하려는 건가요? "
                       f"(문제 엣지 예: {bad[0].get('from')}→{bad[0].get('to')})",
            })
        return miss
