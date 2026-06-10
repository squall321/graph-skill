"""residual-diagnostic-panel regression — 4 diagnostics embedded as review-matrix graph cells."""
import json
from pathlib import Path

from graph_skill import builder, catalog, validate

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"


def _load():
    return json.loads((FIX / "residual.json").read_text(encoding="utf-8"))


def test_registered_on_review_matrix():
    assert catalog.resolve_type("residual-diagnostic-panel").engine == "review-matrix"


def test_validates_renders_and_bundles_xy_core():
    p = _load()
    assert validate.check("residual-diagnostic-panel", p)["ok"]
    r = builder.render("residual-diagnostic-panel", p, out_path=str(OUT / "residual.html"))
    h = Path(r["html_path"]).read_text(encoding="utf-8")
    assert r["lint"]["ok"]
    # review-matrix carrier + xy-core engine bundled for the embedded graph cells
    assert "review-matrix" in h and "xy-core" in h
    for lbl in ("Normal Q-Q", "Residual vs Fitted", "Scale-Location", "Residual vs Leverage"):
        assert lbl in h


def test_gating_few_points():
    assert not validate.check("residual-diagnostic-panel", {"x": [1, 2], "y": [1, 2]})["ok"]


def test_gating_constant_x():
    assert not validate.check("residual-diagnostic-panel", {"x": [5, 5, 5], "y": [1, 2, 3]})["ok"]


def test_accepts_series_form():
    p = {"series": [{"data": [[1, 2], [2, 4.1], [3, 5.9], [4, 8.2], [5, 9.8]]}]}
    assert validate.check("residual-diagnostic-panel", p)["ok"]
    assert builder.render("residual-diagnostic-panel", p, out_path=str(OUT / "_resid2.html"))["lint"]["ok"]


def test_determinism():
    a = builder.render("residual-diagnostic-panel", _load(), out_path=str(OUT / "_rdet_a.html"))
    b = builder.render("residual-diagnostic-panel", _load(), out_path=str(OUT / "_rdet_b.html"))
    assert Path(a["html_path"]).read_bytes() == Path(b["html_path"]).read_bytes()
