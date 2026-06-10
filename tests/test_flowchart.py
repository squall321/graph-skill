"""flow-core flowchart — rich nodes (text/value/kv/list/image/table/graph) + edges.
Locks: registration, render/lint, embedded node-graph bundles its engine, image/table
passthrough, steps[] shorthand, auto-layout vs explicit coords, determinism, gating."""
import hashlib
import json
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate
from graph_skill.recipes import REGISTRY

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"


def _fx():
    return json.loads((FIX / "flowchart.json").read_text(encoding="utf-8"))


def test_registration_and_taxonomy():
    assert "flowchart" in REGISTRY
    assert catalog.resolve_type("flowchart").engine == "flow-core"
    assert taxonomy.coverage(catalog.known_types())["ok"]


def test_render_lint_and_bundles_inner_engine():
    fx = _fx()
    assert validate.check("flowchart", fx)["ok"]
    r = builder.render("flowchart", fx, out_path=str(OUT / "flowchart.html"))
    assert r["lint"]["ok"]
    html = Path(r["html_path"]).read_text(encoding="utf-8")
    assert 'GraphEngines["flow-core"]' in html          # primary engine
    assert 'GraphEngines["xy-core"]' in html            # the node-embedded graph's engine
    assert '"graph_payloads"' in html and "::graph" in html


def test_rich_content_passthrough():
    html = Path(builder.render("flowchart", _fx(), out_path=str(OUT / "flowchart.html"))["html_path"]).read_text(encoding="utf-8")
    img = next(n for n in _fx()["nodes"] if (n.get("content") or {}).get("kind") == "image")
    assert "image/png" in html and img["content"]["image"]["data"][:32] in html   # image inline base64
    assert '"kind":"table"' in html and "균열" in html                              # table rows
    assert '"kind":"kv"' in html and '"kind":"value"' in html                       # kv + big-number


def test_edges_filtered_to_known_nodes():
    out = REGISTRY["flowchart"].normalize(_fx(), catalog.resolve_type("flowchart"))
    ids = {n["id"] for n in out["assets"]["nodes"]}
    assert all(e["from"] in ids and e["to"] in ids for e in out["assets"]["edges"])
    assert out["assets"]["direction"] == "TB"


def test_steps_shorthand_builds_linear_chain():
    p = {"steps": ["수집", "전처리", "분석", "보고"]}
    assert validate.check("flowchart", p)["ok"]
    out = REGISTRY["flowchart"].normalize(p, catalog.resolve_type("flowchart"))
    assert len(out["assets"]["nodes"]) == 4 and len(out["assets"]["edges"]) == 3
    assert out["assets"]["nodes"][0]["type"] == "terminal"   # first/last are terminals
    assert out["assets"]["nodes"][-1]["type"] == "terminal"
    assert out["assets"]["nodes"][1]["type"] == "process"
    assert builder.render("flowchart", p, out_path=str(OUT / "_fcsteps.html"))["lint"]["ok"]
    (OUT / "_fcsteps.html").unlink(missing_ok=True)


def test_explicit_coords_preserved():
    p = {"nodes": [{"id": "a", "label": "A", "x": 10, "y": 20},
                   {"id": "b", "label": "B", "x": 200, "y": 140}],
         "edges": [{"from": "a", "to": "b"}]}
    out = REGISTRY["flowchart"].normalize(p, catalog.resolve_type("flowchart"))
    na = next(n for n in out["assets"]["nodes"] if n["id"] == "a")
    assert na["x"] == 10 and na["y"] == 20


def test_determinism():
    fx = _fx()
    a = Path(builder.render("flowchart", fx, out_path=str(OUT / "_fcA.html"))["html_path"]).read_bytes()
    b = Path(builder.render("flowchart", fx, out_path=str(OUT / "_fcB.html"))["html_path"]).read_bytes()
    assert hashlib.sha256(a).hexdigest() == hashlib.sha256(b).hexdigest()
    (OUT / "_fcA.html").unlink(missing_ok=True)
    (OUT / "_fcB.html").unlink(missing_ok=True)


def test_gating():
    assert not validate.check("flowchart", {})["ok"]                                    # no nodes
    assert not validate.check("flowchart", {"nodes": [{"id": "a"}],
                                            "edges": [{"from": "a", "to": "ghost"}]})["ok"]  # dangling edge
