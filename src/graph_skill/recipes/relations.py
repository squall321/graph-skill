"""relational / flow diagrams on the flow-core engine (kind = sankey|network|chord).
Sankey = layered flow ribbons (width∝value); network = force-directed draggable graph;
chord = circular relation ribbons from a square matrix. Structure-only gates (these are
dimensionless relations — no physical units to invent)."""

from __future__ import annotations

from .base import Recipe


def _nodes_from_links(nodes, links, key_pairs=("source", "target")):
    """Return node dicts, synthesizing any referenced-but-undeclared ids."""
    have = {n.get("id") for n in (nodes or []) if isinstance(n, dict) and n.get("id") is not None}
    out = [dict(n) for n in (nodes or []) if isinstance(n, dict) and n.get("id") is not None]
    seen = set(have)
    for l in links or []:
        for k in key_pairs:
            v = l.get(k)
            if v is not None and v not in seen:
                out.append({"id": v, "label": str(v)})
                seen.add(v)
    return out


class SankeyRecipe(Recipe):
    type_name = "sankey-diagram"

    def normalize(self, payload: dict, resolved) -> dict:
        links = [{"source": l["source"], "target": l["target"], "value": float(l.get("value", 0)),
                  **({"color": l["color"]} if l.get("color") else {})}
                 for l in (payload.get("links") or []) if l.get("value", 0)]
        nodes = _nodes_from_links(payload.get("nodes"), links)
        options = {"title": payload.get("title") or "", "theme": (payload.get("options") or {}).get("theme", "auto")}
        return {"engine": resolved.engine,
                "assets": {"kind": "sankey", "nodes": nodes, "links": links}, "options": options}

    def structural_requires(self, payload: dict) -> list:
        miss = []
        links = [l for l in (payload.get("links") or []) if isinstance(l, dict)]
        if not links:
            miss.append({"field": "links", "why": "흐름(링크)이 없음",
                         "ask": "흐름을 알려주세요: links:[{source, target, value}, …] (value=흐름량)."})
            return miss
        bad = [l for l in links if l.get("source") is None or l.get("target") is None or not l.get("value")]
        if bad:
            miss.append({"field": "links", "why": "source/target/value 누락 링크 존재",
                         "ask": "각 링크에 source·target·value(>0)가 필요합니다. 누락 링크를 채워주세요."})
        return miss


class NetworkRecipe(Recipe):
    type_name = "network-graph"

    def normalize(self, payload: dict, resolved) -> dict:
        links = [{"source": l["source"], "target": l["target"],
                  **({"value": float(l["value"])} if l.get("value") is not None else {})}
                 for l in (payload.get("links") or []) if l.get("source") is not None and l.get("target") is not None]
        nodes = _nodes_from_links(payload.get("nodes"), links)
        # re-merge declared attrs (group/value/color/label) onto synthesized node list
        decl = {n["id"]: n for n in (payload.get("nodes") or []) if isinstance(n, dict) and n.get("id") is not None}
        for n in nodes:
            d = decl.get(n["id"])
            if d:
                for k in ("group", "value", "color", "label"):
                    if d.get(k) is not None:
                        n[k] = d[k]
        options = {"title": payload.get("title") or "", "theme": (payload.get("options") or {}).get("theme", "auto")}
        return {"engine": resolved.engine,
                "assets": {"kind": "network", "nodes": nodes, "links": links}, "options": options}

    def structural_requires(self, payload: dict) -> list:
        miss = []
        links = [l for l in (payload.get("links") or []) if isinstance(l, dict)]
        nodes = [n for n in (payload.get("nodes") or []) if isinstance(n, dict)]
        if not links and not nodes:
            miss.append({"field": "nodes/links", "why": "노드/링크가 없음",
                         "ask": "네트워크를 알려주세요: nodes:[{id,label,group?,value?}], links:[{source,target,value?}]."})
        elif links:
            bad = [l for l in links if l.get("source") is None or l.get("target") is None]
            if bad:
                miss.append({"field": "links", "why": "source/target 누락 링크 존재",
                             "ask": "각 링크에 source·target node id가 필요합니다."})
        return miss


class ChordRecipe(Recipe):
    type_name = "chord-diagram"

    def normalize(self, payload: dict, resolved) -> dict:
        labels, matrix = self._matrix(payload)
        options = {"title": payload.get("title") or "", "theme": (payload.get("options") or {}).get("theme", "auto")}
        return {"engine": resolved.engine,
                "assets": {"kind": "chord", "labels": labels, "matrix": matrix}, "options": options}

    @staticmethod
    def _matrix(payload):
        if payload.get("matrix"):
            mat = [[float(v) for v in row] for row in payload["matrix"]]
            n = len(mat)
            labels = payload.get("labels") or [f"G{i}" for i in range(n)]
            return list(labels), mat
        # build from links {source,target,value} over the union of node ids (or labels)
        labels = []
        for l in payload.get("links") or []:
            for k in ("source", "target"):
                if l.get(k) is not None and l[k] not in labels:
                    labels.append(l[k])
        idx = {lab: i for i, lab in enumerate(labels)}
        n = len(labels)
        mat = [[0.0] * n for _ in range(n)]
        for l in payload.get("links") or []:
            s, t = l.get("source"), l.get("target")
            if s in idx and t in idx:
                mat[idx[s]][idx[t]] += float(l.get("value", 0))
        return labels, mat

    def structural_requires(self, payload: dict) -> list:
        miss = []
        has_matrix = bool(payload.get("matrix"))
        has_links = bool(payload.get("links"))
        if not has_matrix and not has_links:
            miss.append({"field": "matrix", "why": "관계 행렬/링크가 없음",
                         "ask": "정사각 관계행렬 matrix:[[…]](+labels) 또는 links:[{source,target,value}]를 주세요."})
            return miss
        if has_matrix:
            m = payload["matrix"]
            if any(len(row) != len(m) for row in m):
                miss.append({"field": "matrix", "why": "정사각 행렬이 아님",
                             "ask": "matrix는 N×N 정사각이어야 합니다(행=열=그룹 수). 행 길이를 맞춰주세요."})
        return miss
