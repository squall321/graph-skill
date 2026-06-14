"""Discovery taxonomy — intent-based classification so an LLM narrows
'goal → category → type' fast. Loads data/catalog/taxonomy.json (SSOT for classification),
provides grouping + keyword search, and a coverage check gated by tests.
"""

from __future__ import annotations

import json
from functools import lru_cache

from . import assets


@lru_cache(maxsize=1)
def _tax() -> dict:
    return json.loads((assets.data_dir() / "catalog" / "taxonomy.json").read_text(encoding="utf-8"))


def categories() -> list:
    return list(_tax().get("categories", []))


def _cat_index() -> dict:
    return {c["id"]: c for c in categories()}


def meta(type_name: str) -> dict:
    return dict(_tax().get("types", {}).get(type_name, {}))


def category_of(type_name: str) -> str:
    return meta(type_name).get("category", "")


def grouped() -> list:
    """Categories in declared order, each with its member types (name + meta). Empty
    categories are dropped. Types with an unknown/missing category fall under '_uncategorized'."""
    types = _tax().get("types", {})
    by_cat: dict = {}
    for name, m in types.items():
        by_cat.setdefault(m.get("category", "_uncategorized"), []).append(dict(m, name=name))
    out = []
    for c in categories():
        members = sorted(by_cat.get(c["id"], []), key=lambda t: t["name"])
        if members:
            out.append(dict(c, types=members))
    extra = sorted(by_cat.get("_uncategorized", []), key=lambda t: t["name"])
    if extra:
        out.append({"id": "_uncategorized", "title": "(미분류)", "desc": "", "when": "", "types": extra})
    return out


def find(query: str, limit: int = 8) -> list:
    """Rank types by a free-text goal. Scores keyword/use_when/name/category-title overlap."""
    q = (query or "").lower().strip()
    terms = [t for t in q.replace(",", " ").replace("/", " ").split() if t]
    cats = _cat_index()
    scored = []
    for name, m in _tax().get("types", {}).items():
        kws = [k.lower() for k in (m.get("keywords", []) + m.get("synonyms", []))]
        hay = " ".join([
            name, m.get("use_when", ""), m.get("data", ""), " ".join(kws),
            (cats.get(m.get("category", ""), {}) or {}).get("title", ""),
        ]).lower()
        score = 0
        if q and q in hay:
            score += 5
        for t in terms:
            if t in hay:
                score += 2
            for k in kws:
                if t == k:
                    score += 2                      # exact keyword hit — strong signal
                elif len(t) >= 2 and (t in k or k in t):
                    score += 1                      # bidirectional substring (막대그래프~막대)
        if score:
            scored.append((score, name, m))
    scored.sort(key=lambda x: (-x[0], x[1]))         # deterministic: score desc, then name asc
    return [{"name": n, "category": m.get("category", ""), "dims": m.get("dims", ""),
             "use_when": m.get("use_when", ""), "data": m.get("data", "")}
            for _s, n, m in scored[:limit]]


def coverage(known_types: list) -> dict:
    """Consistency: every known type classified, every category id valid, no dangling types."""
    valid_cats = set(_cat_index())
    tax_types = _tax().get("types", {})
    known = set(known_types)
    missing = sorted(known - set(tax_types))                       # in catalog, not classified
    dangling = sorted(set(tax_types) - known)                       # classified, not in catalog
    bad_category = sorted(t for t, m in tax_types.items() if m.get("category") not in valid_cats)
    return {"missing": missing, "dangling": dangling, "bad_category": bad_category,
            "ok": not (missing or dangling or bad_category)}
