"""Phase (3) regression tests — field-core (contour/heatmap/stress) + z-meta/grid gates."""
import json
from pathlib import Path

from graph_skill import builder, catalog, validate

FIX = Path(__file__).parent / "fixtures"


def load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_field_types_registered():
    assert {"contour-plot", "heatmap-grid", "scalar-field-2d", "mcae-stress-contour"} <= set(catalog.known_types())


def test_field_resolve():
    rt = catalog.resolve_type("mcae-stress-contour")
    assert rt.engine == "field-core" and rt.require_series is False and rt.require_axes is True


def test_field_render_self_contained(tmp_path):
    res = builder.render("mcae-stress-contour", load("field"), out_path=str(tmp_path / "f.html"))
    html = (tmp_path / "f.html").read_text(encoding="utf-8")
    assert res["lint"]["ok"] and "://" not in html
    assert 'GraphEngines["field-core"]' in html and '"field"' in html and "von Mises" in html


def test_heatmap_no_contours_by_default():
    p = load("field")
    p["graph_type"] = "heatmap-grid"
    html = builder.render("heatmap-grid", p)["html"]
    assert '"contours":false' in html.replace(" ", "")


def test_contour_plot_has_contours():
    p = load("field")
    html = builder.render("contour-plot", p)["html"]
    assert '"contours":true' in html.replace(" ", "")


def test_field_zmeta_gate():
    p = load("field")
    p.pop("z")
    v = validate.check("mcae-stress-contour", p)
    assert not v["ok"] and any(m["field"] == "z" for m in v["missing"])


def test_field_dimension_gate():
    p = load("field")
    p["field"]["z"][2] = p["field"]["z"][2][:-1]
    v = validate.check("mcae-stress-contour", p)
    assert not v["ok"] and any(m["field"] == "field.z" for m in v["missing"])


def test_field_axes_required():
    p = load("field")
    p.pop("axes")
    assert not validate.check("mcae-stress-contour", p)["ok"]


def test_field_deterministic():
    p = load("field")
    assert builder.render("mcae-stress-contour", p)["html"] == builder.render("mcae-stress-contour", p)["html"]
