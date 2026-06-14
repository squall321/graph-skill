"""grouped-bar / stacked-bar (+ 막대+선 콤보). Locks: 등록, render/lint, barMode 옵션,
grouped 다계열, stacked, 콤보(우측축 선), 게이트, 결정성."""
import json
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate
from graph_skill.recipes import REGISTRY

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_registration_render():
    cov = taxonomy.coverage(catalog.known_types())
    assert cov["ok"], cov["bad_category"]
    for t, fx in (("grouped-bar", "grouped_bar"), ("stacked-bar", "stacked_bar")):
        assert t in REGISTRY
        p = _load(fx)
        assert validate.check(t, p)["ok"], t
        assert builder.render(t, p, out_path=str(OUT / f"{t}.html"))["lint"]["ok"], t


def test_grouped_barmode_and_combo():
    out = REGISTRY["grouped-bar"].normalize(_load("grouped_bar"), catalog.resolve_type("grouped-bar"))
    assert out["options"]["barMode"] == "grouped"
    assert len([s for s in out["assets"]["series"] if s["style"] == "bar"]) == 2   # 매출, 비용
    line = next(s for s in out["assets"]["series"] if s["style"] == "line+markers")  # 이익률 콤보
    assert line["axis"] == "right" and out["options"]["axes"]["y2"]["unit"] == "%"
    assert out["options"]["axes"]["x"]["categories"][0] == "1월"


def test_stacked_barmode():
    out = REGISTRY["stacked-bar"].normalize(_load("stacked_bar"), catalog.resolve_type("stacked-bar"))
    assert out["options"]["barMode"] == "stacked"
    assert len([s for s in out["assets"]["series"] if s["style"] == "bar"]) == 3


def test_gating():
    yok = {"y": {"label": "v", "unit": "x"}}
    assert not validate.check("grouped-bar", {"series": [{"name": "a", "values": [1]}], "axes": yok})["ok"]  # no cats
    assert not validate.check("grouped-bar", {"categories": ["a"], "axes": yok})["ok"]                       # no series
    assert not validate.check("grouped-bar", {"categories": ["a"], "series": [{"name": "s", "values": [1]}]})["ok"]  # no y unit
    assert not validate.check("grouped-bar", {"categories": ["a"], "axes": yok,
                                              "series": [{"name": "s", "values": [1], "axis": "right"}]})["ok"]  # combo no y2


def test_determinism():
    for t, fx in (("grouped-bar", "grouped_bar"), ("stacked-bar", "stacked_bar")):
        p = _load(fx)
        a = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}A.html"))["html_path"]).read_bytes()
        b = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}B.html"))["html_path"]).read_bytes()
        assert a == b, t
        (OUT / f"_{fx}A.html").unlink(missing_ok=True)
        (OUT / f"_{fx}B.html").unlink(missing_ok=True)
