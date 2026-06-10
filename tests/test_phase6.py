"""Phase (6) regression tests — histogram / bar-plot / box-plot / error-bar."""
import json
from pathlib import Path

from graph_skill import builder, catalog, validate
from graph_skill.postprocess import stats

FIX = Path(__file__).parent / "fixtures"


def load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_stat_types_registered():
    assert {"histogram", "bar-plot", "box-plot", "error-bar"} <= set(catalog.known_types())


def test_histogram_counts_preserved():
    _, counts, _ = stats.histogram([1, 2, 2, 3, 3, 3, 4], 4)
    assert sum(counts) == 7


def test_quartiles_outlier():
    q = stats.quartiles([1, 2, 3, 4, 5, 6, 7, 8, 100])
    assert q["med"] == 5 and 100 in q["outliers"]


def test_histogram_render_bars(tmp_path):
    h = builder.render("histogram", load("hist"), out_path=str(tmp_path / "h.html"))
    html = (tmp_path / "h.html").read_text(encoding="utf-8")
    assert h["lint"]["ok"] and '"style":"bar"' in html.replace(" ", "")


def test_bar_categorical(tmp_path):
    b = builder.render("bar-plot", load("bar"), out_path=str(tmp_path / "b.html"))
    html = (tmp_path / "b.html").read_text(encoding="utf-8")
    assert b["lint"]["ok"] and '"categories"' in html and '"Frame"' in html


def test_box_render(tmp_path):
    x = builder.render("box-plot", load("box"), out_path=str(tmp_path / "x.html"))
    html = (tmp_path / "x.html").read_text(encoding="utf-8")
    assert x["lint"]["ok"] and '["box-plot"]' in html and '"style":"none"' in html.replace(" ", "")


def test_errorbar_render(tmp_path):
    e = builder.render("error-bar", load("errbar"), out_path=str(tmp_path / "e.html"))
    html = (tmp_path / "e.html").read_text(encoding="utf-8")
    assert e["lint"]["ok"] and '["error-bars"]' in html and '"bars"' in html


def test_histogram_axis_gate():
    assert not validate.check("histogram", {"values": [1, 2, 3]})["ok"]


def test_bar_categories_gate():
    assert not validate.check("bar-plot", {"axes": {"y": {"label": "E", "unit": "J"}}})["ok"]


def test_box_groups_gate():
    assert not validate.check("box-plot", {"axes": {"y": {"label": "S", "unit": "N"}}})["ok"]


def test_stat_deterministic():
    p = load("box")
    assert builder.render("box-plot", p)["html"] == builder.render("box-plot", p)["html"]
