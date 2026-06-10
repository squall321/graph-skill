"""Wave-7 regression — correlation/confusion matrices (field-core) + kpi-scorecard/decision
(review-matrix rich cells: heat/bar/delta). Also locks the new cell-kind passthrough."""
import json
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate
from graph_skill.postprocess import stats

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"
TYPES = {"correlation-matrix": ("corrmat", "field-core"), "confusion-matrix": ("confmat", "field-core"),
         "kpi-scorecard": ("kpi", "review-matrix"), "decision-matrix": ("decision", "review-matrix")}


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_taxonomy_and_engines():
    assert taxonomy.coverage(catalog.known_types())["ok"]
    for t, (_, eng) in TYPES.items():
        assert catalog.resolve_type(t).engine == eng


def test_render_lint():
    for t, (fx, _) in TYPES.items():
        assert validate.check(t, _load(fx))["ok"], t
        assert builder.render(t, _load(fx), out_path=str(OUT / f"{t}.html"))["lint"]["ok"], t


def test_pearson_matrix_signs():
    names, r = stats.pearson_matrix({"a": [1, 2, 3, 4], "b": [2, 4, 6, 8], "c": [4, 3, 2, 1]})
    assert names == ["a", "b", "c"]
    assert abs(r[0][1] - 1.0) < 1e-9 and abs(r[0][2] + 1.0) < 1e-9 and abs(r[0][0] - 1.0) < 1e-9


def test_confusion_accuracy_in_title():
    h = Path(builder.render("confusion-matrix", _load("confmat"), out_path=str(OUT / "confusion-matrix.html"))["html_path"]).read_text(encoding="utf-8")
    assert "acc=" in h and '"zdomain"' not in h         # confusion uses count colormap (no fixed range)
    # accuracy computed from the matrix diagonal
    m = _load("confmat")["matrix"]
    acc = sum(m[i][i] for i in range(len(m))) / sum(sum(r) for r in m)
    assert f"{acc:.1%}" in h


def test_confusion_from_y_true_pred():
    p = {"y_true": ["a", "a", "b", "b", "a"], "y_pred": ["a", "b", "b", "b", "a"]}
    assert validate.check("confusion-matrix", p)["ok"]
    assert builder.render("confusion-matrix", p, out_path=str(OUT / "_cm.html"))["lint"]["ok"]


def test_kpi_rich_cells():
    h = Path(builder.render("kpi-scorecard", _load("kpi"), out_path=str(OUT / "kpi-scorecard.html"))["html_path"]).read_text(encoding="utf-8")
    assert '"kind":"delta"' in h and '"kind":"bar"' in h and '"kind":"status"' in h


def test_decision_heat_and_weighted_total():
    from graph_skill.recipes import REGISTRY
    out = REGISTRY["decision-matrix"].normalize(_load("decision"), catalog.resolve_type("decision-matrix"))
    items = out["assets"]["items"]
    total = next(it for it in items if it["id"] == "_total")
    # weighted totals: opt B = 3*3+2*5+2*4+1*3 = 30 ; one option flagged pass (winner)
    assert any(c.get("kind") == "status" and c.get("status") == "pass" for c in total["cells"].values())
    assert any(it["cells"] and list(it["cells"].values())[0].get("kind") == "heat" for it in items[:-1])


def test_gating():
    assert not validate.check("correlation-matrix", {"variables": {"a": [1, 2]}})["ok"]
    assert not validate.check("confusion-matrix", {})["ok"]
    assert not validate.check("kpi-scorecard", {})["ok"]
    assert not validate.check("decision-matrix", {"criteria": [{"name": "x", "weight": 1}]})["ok"]
