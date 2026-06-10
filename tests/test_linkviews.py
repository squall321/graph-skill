"""B-axis interaction depth — treemap-drilldown, overview-detail (focus+context),
shared crosshair (xsync→multitrack), SPLOM linked brushing (brushlink→scatter-matrix).
Locks: registration, render/lint, per-cell plugin injection + bundling, gating, determinism."""
import hashlib
import json
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate
from graph_skill.recipes import REGISTRY

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_taxonomy_total():
    cov = taxonomy.coverage(catalog.known_types())
    assert cov["ok"], cov["bad_category"]


def test_treemap_drilldown():
    p = _load("treemapdrill")
    assert validate.check("treemap-drilldown", p)["ok"]
    r = builder.render("treemap-drilldown", p, out_path=str(OUT / "treemap-drilldown.html"))
    assert r["lint"]["ok"]
    assert 'GraphPlugins["xy-core"]["treemap-drill"]' in Path(r["html_path"]).read_text(encoding="utf-8")
    out = REGISTRY["treemap-drilldown"].normalize(p, catalog.resolve_type("treemap-drilldown"))
    tree = out["options"]["pluginConfig"]["treemap-drill"]["tree"]
    assert len(tree["children"]) == len(tree["rects"])          # each node pre-squarified
    assert "rects" in tree["children"][0]                        # nested layouts too
    assert not validate.check("treemap-drilldown", {})["ok"]
    assert not validate.check("treemap-drilldown", {"tree": {"name": "x", "value": 1}})["ok"]


def test_overview_detail_focus_context():
    p = _load("overviewdetail")
    assert validate.check("overview-detail", p)["ok"]
    r = builder.render("overview-detail", p, out_path=str(OUT / "overview-detail.html"))
    assert r["lint"]["ok"]
    html = Path(r["html_path"]).read_text(encoding="utf-8")
    assert 'GraphPlugins["xy-core"]["xbrush"]' in html and 'GraphPlugins["xy-core"]["xfollow"]' in html
    gps = REGISTRY["overview-detail"].normalize(p, catalog.resolve_type("overview-detail"))["assets"]["graph_payloads"]
    assert any(ref.startswith("detail") and "xfollow" in (gp.get("plugins") or []) for ref, gp in gps.items())
    assert any(ref.startswith("overview") and "xbrush" in (gp.get("plugins") or []) for ref, gp in gps.items())
    # never-invent-units + structure gates
    assert not validate.check("overview-detail", {"axes": {"x": {"label": "t", "unit": "s"}}})["ok"]
    assert not validate.check("overview-detail", {"series": [{"name": "a", "data": [[0, 1]]}]})["ok"]


def test_multitrack_shared_crosshair():
    p = _load("multitrack")
    out = REGISTRY["multitrack-stack"].normalize(p, catalog.resolve_type("multitrack-stack"))
    gps = out["assets"]["graph_payloads"]
    assert gps and all("xsync" in (gp.get("plugins") or []) for gp in gps.values())
    assert all(gp["options"]["pluginConfig"]["xsync"]["group"] == "mt" for gp in gps.values())
    html = Path(builder.render("multitrack-stack", p, out_path=str(OUT / "multitrack-stack.html"))["html_path"]).read_text(encoding="utf-8")
    assert 'GraphPlugins["xy-core"]["xsync"]' in html


def test_splom_linked_brushing():
    p = {"title": "SPLOM", "variables": {"a": [1, 2, 3, 4, 5, 6], "b": [2, 4, 5, 4, 5, 7], "c": [6, 5, 4, 3, 3, 2]}}
    out = REGISTRY["scatter-matrix"].normalize(p, catalog.resolve_type("scatter-matrix"))
    gps = out["assets"]["graph_payloads"]
    assert gps and all("brushlink" in (gp.get("plugins") or []) for gp in gps.values())
    html = Path(builder.render("scatter-matrix", p, out_path=str(OUT / "scatter-matrix.html"))["html_path"]).read_text(encoding="utf-8")
    assert 'GraphPlugins["xy-core"]["brushlink"]' in html


def test_determinism():
    for t, fx in [("treemap-drilldown", "treemapdrill"), ("overview-detail", "overviewdetail")]:
        p = _load(fx)
        a = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}A.html"))["html_path"]).read_bytes()
        b = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}B.html"))["html_path"]).read_bytes()
        assert hashlib.sha256(a).hexdigest() == hashlib.sha256(b).hexdigest(), t
        (OUT / f"_{fx}A.html").unlink(missing_ok=True)
        (OUT / f"_{fx}B.html").unlink(missing_ok=True)
