"""relational flow diagrams on flow-core (kind sankey/network/chord).
Locks: registration, render/lint, kind routing, node synthesis from links,
chord matrix-from-links + square gate, determinism, structure gates."""
import hashlib
import json
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate
from graph_skill.recipes import REGISTRY

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"
TYPES = {"sankey-diagram": ("sankey", "sankey"), "network-graph": ("network", "network"),
         "chord-diagram": ("chord", "chord")}


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_registration_and_taxonomy():
    cov = taxonomy.coverage(catalog.known_types())
    assert cov["ok"], cov["bad_category"]
    for t in TYPES:
        assert t in REGISTRY and catalog.resolve_type(t).engine == "flow-core"


def test_render_lint_and_kind():
    for t, (fx, kind) in TYPES.items():
        p = _load(fx)
        assert validate.check(t, p)["ok"], t
        r = builder.render(t, p, out_path=str(OUT / f"{t}.html"))
        assert r["lint"]["ok"], t
        html = Path(r["html_path"]).read_text(encoding="utf-8")
        assert 'GraphEngines["flow-core"]' in html
        assert REGISTRY[t].normalize(p, catalog.resolve_type(t))["assets"]["kind"] == kind


def test_sankey_synthesizes_nodes_and_drops_zero_links():
    out = REGISTRY["sankey-diagram"].normalize(_load("sankey"), catalog.resolve_type("sankey-diagram"))
    ids = {n["id"] for n in out["assets"]["nodes"]}
    for l in out["assets"]["links"]:
        assert l["source"] in ids and l["target"] in ids and l["value"] > 0


def test_network_merges_declared_attrs():
    out = REGISTRY["network-graph"].normalize(_load("network"), catalog.resolve_type("network-graph"))
    gw = next(n for n in out["assets"]["nodes"] if n["id"] == "gw")
    assert gw.get("group") == "edge" and gw.get("value") == 30


def test_chord_matrix_from_links_and_square():
    out = REGISTRY["chord-diagram"].normalize(
        {"links": [{"source": "a", "target": "b", "value": 3}, {"source": "b", "target": "a", "value": 1}]},
        catalog.resolve_type("chord-diagram"))
    assert out["assets"]["labels"] == ["a", "b"]
    assert out["assets"]["matrix"] == [[0.0, 3.0], [1.0, 0.0]]


def test_gating():
    assert not validate.check("sankey-diagram", {})["ok"]
    assert not validate.check("sankey-diagram", {"links": [{"source": "a", "target": "b"}]})["ok"]   # no value
    assert not validate.check("network-graph", {})["ok"]
    assert not validate.check("chord-diagram", {})["ok"]
    assert not validate.check("chord-diagram", {"matrix": [[0, 1], [1]]})["ok"]                       # non-square


def test_determinism():
    for t, (fx, _) in TYPES.items():
        p = _load(fx)
        a = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}A.html"))["html_path"]).read_bytes()
        b = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}B.html"))["html_path"]).read_bytes()
        assert hashlib.sha256(a).hexdigest() == hashlib.sha256(b).hexdigest(), t
        (OUT / f"_{fx}A.html").unlink(missing_ok=True)
        (OUT / f"_{fx}B.html").unlink(missing_ok=True)
