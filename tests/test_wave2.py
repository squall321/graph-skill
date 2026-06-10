"""Wave-2 regression — area-plot / stacked-area / waterfall-chart / violin-plot
(area-fill / waterfall / violin plugins, no engine change)."""
import json
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"
TYPES = {"area-plot": "area", "stacked-area": "stackedarea",
         "waterfall-chart": "waterfall", "violin-plot": "violin"}


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_taxonomy_complete():
    assert taxonomy.coverage(catalog.known_types())["ok"]


def test_all_xy_core():
    for t in TYPES:
        assert catalog.resolve_type(t).engine == "xy-core"


def test_validate_render_lint():
    for t, fx in TYPES.items():
        assert validate.check(t, _load(fx))["ok"], t
        assert builder.render(t, _load(fx), out_path=str(OUT / f"{t}.html"))["lint"]["ok"], t


def test_stacked_area_accumulates():
    # last series y must be the running cumulative (5+3+2=10 at x=1)
    norm = catalog.resolve_type("stacked-area")
    from graph_skill.recipes import REGISTRY
    out = REGISTRY["stacked-area"].normalize(_load("stackedarea"), norm)
    ser = out["assets"]["series"]
    assert ser[-1]["y"][0] == 10 and out["options"]["pluginConfig"]["area-fill"]["stacked"] is True


def test_waterfall_running_totals():
    from graph_skill.recipes import REGISTRY
    out = REGISTRY["waterfall-chart"].normalize(_load("waterfall"), catalog.resolve_type("waterfall-chart"))
    bars = out["options"]["pluginConfig"]["waterfall"]["bars"]
    assert bars[0]["top"] == 1000 and bars[1]["kind"] == "inc" and bars[2]["kind"] == "dec"
    assert abs(bars[-1]["top"] - 1130) < 1e-9          # closing total = running sum


def test_violin_has_densities():
    h = Path(builder.render("violin-plot", _load("violin"), out_path=str(OUT / "violin-plot.html"))["html_path"]).read_text(encoding="utf-8")
    assert "violin" in h and "dens" in h


def test_area_fill_in_output():
    h = Path(builder.render("area-plot", _load("area"), out_path=str(OUT / "area-plot.html"))["html_path"]).read_text(encoding="utf-8")
    assert "area-fill" in h


def test_gating():
    assert not validate.check("area-plot", {"axes": {"x": {"label": "x", "unit": ""}, "y": {"label": "y", "unit": ""}}})["ok"]
    assert not validate.check("violin-plot", {"groups": [{"label": "a", "values": [1, 2, 3]}]})["ok"]      # no axes.y unit
    assert not validate.check("waterfall-chart", {"categories": ["a"], "values": [1]})["ok"]                # no axes.y unit


def test_determinism():
    a = builder.render("waterfall-chart", _load("waterfall"), out_path=str(OUT / "_w2a.html"))
    b = builder.render("waterfall-chart", _load("waterfall"), out_path=str(OUT / "_w2b.html"))
    assert Path(a["html_path"]).read_bytes() == Path(b["html_path"]).read_bytes()
