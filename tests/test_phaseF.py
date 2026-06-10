"""Phase (F) regression tests — pareto / qq-plot / ecdf-plot / spc-control-chart + stats."""
import json
from pathlib import Path

from graph_skill import builder, catalog, validate
from graph_skill.postprocess import stats

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


# ---- catalog registration --------------------------------------------------
def test_types_registered_on_xy_core():
    for t in ("pareto", "qq-plot", "ecdf-plot", "spc-control-chart"):
        assert t in catalog.known_types()
        assert catalog.resolve_type(t).engine == "xy-core"


# ---- stats numerics --------------------------------------------------------
def test_pareto_sorts_and_accumulates():
    cats, vals, cum = stats.pareto(["a", "b", "c"], [10, 30, 20])
    assert cats == ["b", "c", "a"] and vals == [30, 20, 10]
    assert abs(cum[-1] - 100.0) < 1e-9
    assert all(cum[i] <= cum[i + 1] + 1e-9 for i in range(len(cum) - 1))


def test_inv_norm_and_quantiles():
    assert abs(stats.inv_norm(0.5)) < 1e-6
    assert stats.inv_norm(0.84) > 0 and stats.inv_norm(0.16) < 0
    q = stats.normal_quantiles(20)
    assert all(q[i] <= q[i + 1] for i in range(len(q) - 1))
    assert abs(q[0] + q[-1]) < 1e-6                       # symmetric


def test_ecdf_monotone_to_one():
    xs, F = stats.ecdf([3, 1, 2, 2])
    assert xs == [1, 2, 2, 3]
    assert abs(F[-1] - 1.0) < 1e-9
    assert all(F[i] <= F[i + 1] for i in range(len(F) - 1))


def test_control_limits_3sigma_and_violations():
    cl = stats.control_limits([0.5, 0.5, 0.5, 0.5, 0.7, 0.3])
    assert cl["lcl"] < cl["mean"] < cl["ucl"]
    assert abs((cl["ucl"] - cl["mean"]) - 3 * cl["sd"]) < 1e-9


def test_spc_fixture_flags_two_outliers():
    ys = [pt[1] for pt in _load("spc")["series"][0]["data"]]
    assert stats.control_limits(ys)["violations"] == [12, 19]


# ---- validate gate ---------------------------------------------------------
def test_fixtures_validate_ok():
    for name, t in [("pareto", "pareto"), ("qq", "qq-plot"),
                    ("ecdf", "ecdf-plot"), ("spc", "spc-control-chart")]:
        assert validate.check(t, _load(name))["ok"], t


def test_pareto_missing_axis_unit_is_gated():
    v = validate.check("pareto", {"categories": ["a", "b"], "values": [1, 2]})
    assert not v["ok"] and any(m["field"] == "axes.y" for m in v["missing"])


def test_qq_too_few_samples_gated():
    assert not validate.check("qq-plot", {"values": [1, 2]})["ok"]


# ---- render + lint + plugin bundling ---------------------------------------
def test_pareto_renders_with_secondary_axis():
    r = builder.render("pareto", _load("pareto"), out_path=str(OUT / "pareto.html"))
    h = Path(r["html_path"]).read_text(encoding="utf-8")
    assert r["lint"]["ok"]
    assert "threshold-lines" in h and "Cumulative" in h


def test_qq_renders_with_regression_fit():
    r = builder.render("qq-plot", _load("qq"), out_path=str(OUT / "qq.html"))
    h = Path(r["html_path"]).read_text(encoding="utf-8")
    assert r["lint"]["ok"] and "regression-fit" in h


def test_ecdf_renders_step_no_plugins():
    r = builder.render("ecdf-plot", _load("ecdf"), out_path=str(OUT / "ecdf.html"))
    h = Path(r["html_path"]).read_text(encoding="utf-8")
    assert r["lint"]["ok"] and "step" in h
    assert "regression-fit" not in h and "threshold-lines" not in h


def test_spc_renders_with_limits_and_markers():
    r = builder.render("spc-control-chart", _load("spc"), out_path=str(OUT / "spc.html"))
    h = Path(r["html_path"]).read_text(encoding="utf-8")
    assert r["lint"]["ok"]
    assert "threshold-lines" in h and "named-markers" in h and "OOC" in h


def test_pareto_determinism():
    a = builder.render("pareto", _load("pareto"), out_path=str(OUT / "_det_a.html"))
    b = builder.render("pareto", _load("pareto"), out_path=str(OUT / "_det_b.html"))
    assert Path(a["html_path"]).read_bytes() == Path(b["html_path"]).read_bytes()
