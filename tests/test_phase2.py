"""Phase (2) regression tests — review-matrix family, multi-engine bundling, structural gate."""
import json
from pathlib import Path

from graph_skill import builder, catalog, validate

FIX = Path(__file__).parent / "fixtures"


def load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_matrix_types_registered():
    assert {"review-matrix", "design-state-compare", "single-state-checklist"} <= set(catalog.known_types())


def test_matrix_needs_no_series_axes():
    rt = catalog.resolve_type("design-state-compare")
    assert rt.engine == "review-matrix" and rt.require_series is False and rt.require_axes is False


def test_matrix_render_bundles_both_engines(tmp_path):
    res = builder.render("design-state-compare", load("design_state"), out_path=str(tmp_path / "m.html"))
    html = (tmp_path / "m.html").read_text(encoding="utf-8")
    assert res["lint"]["ok"] and res["engine"] == "review-matrix"
    assert 'GraphEngines["review-matrix"]' in html, "matrix engine missing"
    assert 'GraphEngines["xy-core"]' in html, "cell-graph engine (xy-core) missing"
    assert '"graph_payloads"' in html and "iVBORw0KGgo" in html  # graph cells + inline image


def test_matrix_baseline_referential_integrity():
    p = load("design_state")
    p["meta"]["baseline"] = "v9"
    v = validate.check("design-state-compare", p)
    assert not v["ok"] and any(m["field"] == "meta.baseline" for m in v["missing"])


def test_compare_requires_two_states_but_checklist_allows_one():
    p = load("design_state")
    p["states"] = [p["states"][0]]
    p["meta"]["baseline"] = "v1"
    assert not validate.check("design-state-compare", p)["ok"]
    assert validate.check("single-state-checklist", p)["ok"]


def test_missing_items_blocks():
    v = validate.check("review-matrix", {"states": [{"id": "a", "label": "A"}]})
    assert not v["ok"] and any(m["field"] == "items" for m in v["missing"])


def test_overlay_states_merges_into_one_graph(tmp_path):
    p = load("design_state")
    for it in p["items"]:
        if it["id"] == "drop_curve":
            it["overlay_states"] = True
    res = builder.render("design-state-compare", p, out_path=str(tmp_path / "o.html"))
    html = (tmp_path / "o.html").read_text(encoding="utf-8")
    assert res["lint"]["ok"] and "drop_curve::__overlay" in html


def test_matrix_deterministic():
    p = load("design_state")
    a = builder.render("design-state-compare", p)["html"]
    b = builder.render("design-state-compare", p)["html"]
    assert a == b
