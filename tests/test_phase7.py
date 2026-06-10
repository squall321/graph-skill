"""Phase (B) regression tests — dual-axis + bode (secondary y-axis)."""
import json
from pathlib import Path

from graph_skill import builder, catalog, validate

FIX = Path(__file__).parent / "fixtures"


def load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_dual_bode_registered():
    assert {"dual-axis", "bode"} <= set(catalog.known_types())


def test_dual_render(tmp_path):
    r = builder.render("dual-axis", load("dual"), out_path=str(tmp_path / "d.html"))
    html = (tmp_path / "d.html").read_text(encoding="utf-8")
    assert r["lint"]["ok"] and '"y2"' in html and '"axis":"right"' in html.replace(" ", "")


def test_bode_render(tmp_path):
    r = builder.render("bode", load("bode"), out_path=str(tmp_path / "b.html"))
    html = (tmp_path / "b.html").read_text(encoding="utf-8")
    assert r["lint"]["ok"] and '"Magnitude"' in html and '"Phase"' in html
    assert '"log":true' in html.replace(" ", "")


def test_dual_y2_gate():
    p = {"series": [{"name": "a", "data": [[0, 1]]}], "axes": {"x": {"label": "t", "unit": "s"}, "y": {"label": "p", "unit": "W"}}}
    assert not validate.check("dual-axis", p)["ok"]


def test_bode_data_gate():
    assert not validate.check("bode", {"freqs": [1, 2, 3]})["ok"]


def test_single_axis_unaffected():
    assert builder.render("base-xy", load("base_xy"))["lint"]["ok"]


def test_bode_deterministic():
    p = load("bode")
    assert builder.render("bode", p)["html"] == builder.render("bode", p)["html"]
