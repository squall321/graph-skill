"""Phase (G) regression — engineering 2D quick-wins (xy-core reuse, no new engine)."""
import json
from pathlib import Path

import pytest

from graph_skill import builder, catalog, validate

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"

TYPES = {
    "main-effects-plot": "main_effects",
    "interaction-plot": "interaction",
    "transient-time-history": "transient",
    "convergence-residual-plot": "convergence",
    "cfd-line-extract-compare": "cfd_line",
    "nonlinear-load-displacement": "nonlinear_ld",
    "s-n-fatigue-curve": "sn_curve",
}


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("t", list(TYPES))
def test_registered_on_xy_core(t):
    assert t in catalog.known_types()
    assert catalog.resolve_type(t).engine == "xy-core"


@pytest.mark.parametrize("t,fix", list(TYPES.items()))
def test_fixture_validates_and_renders(t, fix):
    assert validate.check(t, _load(fix))["ok"], t
    r = builder.render(t, _load(fix), out_path=str(OUT / f"{fix}.html"))
    assert r["lint"]["ok"]


def test_main_effects_grand_mean_line():
    h = Path(builder.render("main-effects-plot", _load("main_effects"),
                            out_path=str(OUT / "main_effects.html"))["html_path"]).read_text(encoding="utf-8")
    assert "threshold-lines" in h and "전체평균" in h


def test_transient_peaks_and_limit():
    h = Path(builder.render("transient-time-history", _load("transient"),
                            out_path=str(OUT / "transient.html"))["html_path"]).read_text(encoding="utf-8")
    assert "named-markers" in h and "peak" in h and "허용 50g" in h


def test_convergence_log_y_and_tolerance():
    h = Path(builder.render("convergence-residual-plot", _load("convergence"),
                            out_path=str(OUT / "convergence.html"))["html_path"]).read_text(encoding="utf-8")
    assert '"label":"Residual","log":true' in h and "수렴기준" in h


def test_sn_curve_limit_and_design_point():
    h = Path(builder.render("s-n-fatigue-curve", _load("sn_curve"),
                            out_path=str(OUT / "sn_curve.html"))["html_path"]).read_text(encoding="utf-8")
    assert "피로한도" in h and "설계점" in h


def test_nonlinear_markers_and_tangent():
    h = Path(builder.render("nonlinear-load-displacement", _load("nonlinear_ld"),
                            out_path=str(OUT / "nonlinear_ld.html"))["html_path"]).read_text(encoding="utf-8")
    assert "live-tangent" in h and "named-markers" in h and "극한" in h


def test_cfd_line_error_bars():
    h = Path(builder.render("cfd-line-extract-compare", _load("cfd_line"),
                            out_path=str(OUT / "cfd_line.html"))["html_path"]).read_text(encoding="utf-8")
    assert "error-bars" in h


# --- gating: never invent ---
def test_main_effects_missing_unit_gated():
    v = validate.check("main-effects-plot", {"factors": [{"name": "T", "levels": ["a"], "means": [1]}]})
    assert not v["ok"] and any(m["field"] == "axes.y" for m in v["missing"])


def test_sn_missing_unit_gated():
    assert not validate.check("s-n-fatigue-curve", {"series": [{"name": "x", "data": [[1, 2]]}]})["ok"]


def test_interaction_missing_data_gated():
    assert not validate.check("interaction-plot", {"axes": {"y": {"label": "y", "unit": ""}}})["ok"]


def test_determinism():
    a = builder.render("main-effects-plot", _load("main_effects"), out_path=str(OUT / "_gdet_a.html"))
    b = builder.render("main-effects-plot", _load("main_effects"), out_path=str(OUT / "_gdet_b.html"))
    assert Path(a["html_path"]).read_bytes() == Path(b["html_path"]).read_bytes()
