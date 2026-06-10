"""Phase (H) regression — process-capability / paris / campbell / kaplan-meier / mac-matrix."""
import json
from pathlib import Path

import pytest

from graph_skill import builder, catalog, validate
from graph_skill.postprocess import reliability, stats

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"
TYPES = {
    "process-capability-hist": ("capability", "xy-core"),
    "paris-crack-growth": ("paris", "xy-core"),
    "campbell-diagram": ("campbell", "xy-core"),
    "kaplan-meier-survival": ("km", "xy-core"),
    "mac-matrix-heatmap": ("mac", "field-core"),
    "weibull-prob-paper": ("weibull", "xy-core"),
    "vector-quiver-2d": ("vquiver", "field-core"),
}


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("t,fix,eng", [(t, v[0], v[1]) for t, v in TYPES.items()])
def test_registered(t, fix, eng):
    assert t in catalog.known_types() and catalog.resolve_type(t).engine == eng


@pytest.mark.parametrize("t,fix", [(t, v[0]) for t, v in TYPES.items()])
def test_validates_and_renders(t, fix):
    assert validate.check(t, _load(fix))["ok"], t
    assert builder.render(t, _load(fix), out_path=str(OUT / f"{fix}.html"))["lint"]["ok"]


# ---- postprocess numerics ----
def test_capability_cp_cpk():
    c = stats.capability([9.0, 10.0, 11.0], usl=13, lsl=7)
    assert abs(c["mean"] - 10.0) < 1e-9 and c["cp"] is not None and c["cpk"] is not None


def test_capability_one_sided():
    c = stats.capability([1, 2, 3], usl=5)
    assert c["cp"] is None and c["cpk"] is not None


def test_km_monotone_non_increasing():
    ts, surv, cens = reliability.kaplan_meier([10, 20, 20, 30, 40], [1, 0, 1, 1, 0])
    assert ts[0] == 0.0 and surv[0] == 1.0
    assert all(surv[i] >= surv[i + 1] - 1e-12 for i in range(len(surv) - 1))
    assert any(c[0] == 40 for c in cens)            # last (censored) recorded


def test_median_ranks():
    mr = reliability.median_ranks(3)
    assert len(mr) == 3 and 0 < mr[0] < mr[1] < mr[2] < 1


# ---- output wiring ----
def test_capability_specs_and_cpk_in_title():
    h = Path(builder.render("process-capability-hist", _load("capability"),
                            out_path=str(OUT / "capability.html"))["html_path"]).read_text(encoding="utf-8")
    assert "USL" in h and "LSL" in h and "Cp=" in h and "Cpk=" in h and "normal fit" in h


def test_paris_loglog_fit_and_lines():
    h = Path(builder.render("paris-crack-growth", _load("paris"),
                            out_path=str(OUT / "paris.html"))["html_path"]).read_text(encoding="utf-8")
    assert "Paris fit" in h and "ΔKth" in h and "KIC" in h and '"log":true' in h


def test_campbell_order_rays():
    h = Path(builder.render("campbell-diagram", _load("campbell"),
                            out_path=str(OUT / "campbell.html"))["html_path"]).read_text(encoding="utf-8")
    assert "1X" in h and "2X" in h and "4X" in h


def test_km_step_and_censoring():
    h = Path(builder.render("kaplan-meier-survival", _load("km"),
                            out_path=str(OUT / "km.html"))["html_path"]).read_text(encoding="utf-8")
    assert '"curve":"step"' in h and "named-markers" in h and "censored" in h


def test_mac_heatmap_fixed_range():
    h = Path(builder.render("mac-matrix-heatmap", _load("mac"),
                            out_path=str(OUT / "mac.html"))["html_path"]).read_text(encoding="utf-8")
    assert "field-core" in h and "MAC" in h and '"zdomain":[0,1]' in h


# ---- gating ----
def test_capability_needs_spec_limits():
    assert not validate.check("process-capability-hist",
                              {"values": [1, 2, 3], "axes": {"x": {"label": "x", "unit": "mm"}}})["ok"]


def test_km_needs_time_unit():
    assert not validate.check("kaplan-meier-survival",
                              {"groups": [{"label": "g", "durations": [1], "events": [1]}]})["ok"]


def test_mac_needs_matrix():
    assert not validate.check("mac-matrix-heatmap", {})["ok"]


def test_weibull_fit_numeric():
    fit = reliability.weibull_fit([100, 200, 300, 400, 500, 600, 700])
    assert fit["beta"] > 0 and fit["eta"] > 0 and 0 <= fit["r2"] <= 1
    assert len(fit["x"]) == 7 and len(fit["Y"]) == 7


def test_weibull_output_has_shape_and_logx():
    h = Path(builder.render("weibull-prob-paper", _load("weibull"),
                            out_path=str(OUT / "weibull.html"))["html_path"]).read_text(encoding="utf-8")
    assert "β=" in h and "η=" in h and '"log":true' in h and "fit (β=" in h


def test_weibull_gating():
    assert not validate.check("weibull-prob-paper", {"values": [100], "axes": {"x": {"label": "L", "unit": "h"}}})["ok"]
    assert not validate.check("weibull-prob-paper", {"values": [100, 200, 300]})["ok"]  # no axes.x unit


def test_quiver_arrows_only_and_vectors():
    h = Path(builder.render("vector-quiver-2d", _load("vquiver"),
                            out_path=str(OUT / "vquiver.html"))["html_path"]).read_text(encoding="utf-8")
    assert '"arrowsOnly":true' in h and "vectors" in h and "field-core" in h


def test_quiver_gating():
    assert not validate.check("vector-quiver-2d",
                              {"axes": {"x": {"label": "x", "unit": "m"}, "y": {"label": "y", "unit": "m"}}})["ok"]
    assert not validate.check("vector-quiver-2d", {"field": _load("vquiver")["field"]})["ok"]  # no axis units


def test_determinism():
    a = builder.render("mac-matrix-heatmap", _load("mac"), out_path=str(OUT / "_hdet_a.html"))
    b = builder.render("mac-matrix-heatmap", _load("mac"), out_path=str(OUT / "_hdet_b.html"))
    assert Path(a["html_path"]).read_bytes() == Path(b["html_path"]).read_bytes()
