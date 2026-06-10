"""Taxonomy / discovery regression — classification SSOT must cover every type, group
cleanly, and power keyword search + the enhanced graph_types_list / graph_find tools."""
from graph_skill import catalog, taxonomy, tools


def test_coverage_complete():
    """Every catalog type is classified; no dangling/invalid categories (gates new types)."""
    cov = taxonomy.coverage(catalog.known_types())
    assert cov["ok"], cov


def test_every_type_has_meta_fields():
    for t in catalog.known_types():
        m = taxonomy.meta(t)
        assert m.get("category") and m.get("use_when") and m.get("dims"), t
        assert isinstance(m.get("keywords"), list) and m["keywords"], t


def test_categories_nonempty_and_ordered():
    g = taxonomy.grouped()
    assert len(g) == len(taxonomy.categories())          # all categories used, none empty
    assert all(grp["types"] for grp in g)
    total = sum(len(grp["types"]) for grp in g)
    assert total == len(catalog.known_types())           # partition (each type once)


def test_find_ranks_relevant():
    names = [m["name"] for m in taxonomy.find("피로 수명")]
    assert "s-n-fatigue-curve" in names and "weibull-prob-paper" in names
    assert taxonomy.find("3d 응력")[0]["name"] in ("cad-3d-viewer", "mesh-result-3d", "mcae-stress-contour")
    assert taxonomy.find("공정 능력 cpk")[0]["name"] == "process-capability-hist"
    assert taxonomy.find("nyquist 안정도")[0]["name"] == "nyquist-plot"


def test_find_empty_query():
    assert taxonomy.find("") == []


def test_types_list_tool_shape():
    tl = tools.types_list()
    assert set(("categories", "types", "count", "rule")) <= set(tl)
    assert tl["count"] == len(catalog.known_types())
    assert len(tl["categories"]) == len(taxonomy.categories())
    # flat list enriched with classification
    sample = tl["types"][0]
    assert "category" in sample and "use_when" in sample and "data_shape" in sample


def test_find_tool_registered_and_dispatches():
    assert "graph_find" in tools.DISPATCH
    assert any(t["name"] == "graph_find" for t in tools.TOOLS)
    r = tools.DISPATCH["graph_find"]({"query": "벡터장 유동"})
    assert r["matches"] and r["matches"][0]["name"] == "vector-quiver-2d"
