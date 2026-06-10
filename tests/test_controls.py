"""Controls regression — nyquist-plot / root-locus + equalAspect engine option."""
import json
from pathlib import Path

from graph_skill import builder, catalog, validate

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_registered():
    for t in ("nyquist-plot", "root-locus"):
        assert t in catalog.known_types() and catalog.resolve_type(t).engine == "xy-core"


def test_nyquist_renders_with_equal_aspect_and_unit_circle():
    h = Path(builder.render("nyquist-plot", _load("nyquist"),
                            out_path=str(OUT / "nyquist.html"))["html_path"]).read_text(encoding="utf-8")
    assert '"equalAspect":true' in h and "unit-circle" in h and "−1" in h


def test_root_locus_renders_with_pole_markers():
    h = Path(builder.render("root-locus", _load("rootlocus"),
                            out_path=str(OUT / "rootlocus.html"))["html_path"]).read_text(encoding="utf-8")
    assert '"equalAspect":true' in h and "unit-circle" in h and "pole" in h


def test_nyquist_accepts_real_imag_form():
    p = {"series": [{"name": "G", "real": [1, 0, -0.5], "imag": [0, -0.5, -0.2]}]}
    assert validate.check("nyquist-plot", p)["ok"]
    assert builder.render("nyquist-plot", p, out_path=str(OUT / "_ny2.html"))["lint"]["ok"]


def test_gating():
    assert not validate.check("nyquist-plot", {"series": [{"name": "g", "data": []}]})["ok"]
    assert not validate.check("root-locus", {})["ok"]


def test_determinism():
    a = builder.render("root-locus", _load("rootlocus"), out_path=str(OUT / "_rldet_a.html"))
    b = builder.render("root-locus", _load("rootlocus"), out_path=str(OUT / "_rldet_b.html"))
    assert Path(a["html_path"]).read_bytes() == Path(b["html_path"]).read_bytes()


def test_equal_aspect_opt_in_does_not_affect_base_xy():
    # base-xy config must not set equalAspect (engine code mentions the identifier; config must not enable it)
    h = Path(builder.render("base-xy", _load("base_xy"),
                            out_path=str(OUT / "_bxy.html"))["html_path"]).read_text(encoding="utf-8")
    assert '"equalAspect":true' not in h
