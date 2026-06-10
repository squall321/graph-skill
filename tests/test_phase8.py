"""Phase (C) regression tests — polar-core (polar-plot / radar / rf-radiation-pattern)."""
import json
from pathlib import Path

from graph_skill import builder, catalog, validate

FIX = Path(__file__).parent / "fixtures"


def load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_polar_types_registered():
    assert {"polar-plot", "radar-chart", "rf-radiation-pattern"} <= set(catalog.known_types())


def test_polar_engine():
    assert catalog.resolve_type("radar-chart").engine == "polar-core"
    assert catalog.resolve_type("rf-radiation-pattern").engine == "polar-core"


def test_pattern_render(tmp_path):
    r = builder.render("rf-radiation-pattern", load("pattern"), out_path=str(tmp_path / "p.html"))
    html = (tmp_path / "p.html").read_text(encoding="utf-8")
    assert r["lint"]["ok"] and 'GraphEngines["polar-core"]' in html
    assert '"closed":true' in html.replace(" ", "") and "dBi" in html


def test_radar_render(tmp_path):
    r = builder.render("radar-chart", load("radar"), out_path=str(tmp_path / "r.html"))
    html = (tmp_path / "r.html").read_text(encoding="utf-8")
    assert r["lint"]["ok"] and '"angleLabels"' in html and '"Drop"' in html


def test_polar_radius_gate():
    assert not validate.check("polar-plot", {"series": [{"theta": [0], "r": [1]}]})["ok"]


def test_radar_labels_gate():
    assert not validate.check("radar-chart", {"series": [{"name": "a", "values": [1, 2]}]})["ok"]


def test_polar_deterministic():
    p = load("radar")
    assert builder.render("radar-chart", p)["html"] == builder.render("radar-chart", p)["html"]
