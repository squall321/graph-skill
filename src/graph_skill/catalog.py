"""Artifact-type catalog: load types.json, flatten ``extends`` chains, expose resolvers.

Engine-agnostic. A type names an engine family and a plugin bundle; the builder reads the
engine assets without knowing the family. ``extends`` accumulates plugins/requires/options
parent->child (deterministic order).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache

from .assets import data_dir, engine_version


@lru_cache(maxsize=1)
def _catalog() -> dict:
    p = data_dir() / "catalog" / "types.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _types() -> dict:
    return _catalog()["types"]


@dataclass(frozen=True)
class ResolvedType:
    name: str
    engine: str
    backend: str
    plugins: tuple
    requires: tuple  # tuple of {field, type, unit, why, ask}
    options: dict
    require_axes: bool
    require_series: bool
    height_px: int


def known_types() -> list[str]:
    return list(_types().keys())


def _chain(name: str) -> list:
    """Return [(name, node), ...] child-first along the extends chain."""
    chain, seen, cur = [], set(), name
    while cur:
        if cur in seen:
            raise ValueError(f"extends cycle detected at '{cur}'")
        if cur not in _types():
            raise KeyError(f"unknown graph_type: '{cur}'")
        seen.add(cur)
        node = _types()[cur]
        chain.append((cur, node))
        cur = node.get("extends")
    return chain


def _merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def resolve_type(name: str) -> ResolvedType:
    chain = _chain(name)
    plugins: list = []
    requires: list = []
    options: dict = {}
    engine = None
    backend = "canvas"
    require_axes = False
    require_series = True
    height = 520
    for _cur, node in reversed(chain):  # parent -> child accumulation (deterministic)
        engine = node.get("engine", engine)
        backend = node.get("backend", backend)
        for p in node.get("plugins", []):
            if p not in plugins:
                plugins.append(p)
        for r in node.get("requires", []):
            if r not in requires:
                requires.append(r)
        options = _merge(options, node.get("options_defaults", {}))
        if "require_axes" in node:
            require_axes = bool(node["require_axes"])
        if "require_series" in node:
            require_series = bool(node["require_series"])
        if "height_px" in node:
            height = int(node["height_px"])
    if engine is None:
        raise ValueError(f"type '{name}' resolved no engine family")
    return ResolvedType(
        name=name,
        engine=engine,
        backend=backend,
        plugins=tuple(plugins),
        requires=tuple(requires),
        options=options,
        require_axes=require_axes,
        require_series=require_series,
        height_px=height,
    )


def effective_requires(name: str) -> list:
    return [dict(r) for r in resolve_type(name).requires]


def list_types() -> list[dict]:
    out = []
    for n in known_types():
        rt = resolve_type(n)
        node = _types()[n]
        out.append(
            {
                "name": n,
                "title": node.get("title", n),
                "engine": rt.engine,
                "extends": node.get("extends"),
                "requires": [r["field"] for r in rt.requires],
                "plugins": list(rt.plugins),
                "hint": node.get("hint", ""),
            }
        )
    return out


def get_schema(name: str) -> dict:
    rt = resolve_type(name)
    node = _types()[name]
    return {
        "name": name,
        "title": node.get("title", name),
        "engine": rt.engine,
        "backend": rt.backend,
        "plugins": list(rt.plugins),
        "require_axes": rt.require_axes,
        "requires": [dict(r) for r in rt.requires],
        "height_px": rt.height_px,
        "hint": node.get("hint", ""),
        "engine_version": engine_version(rt.engine),
    }
