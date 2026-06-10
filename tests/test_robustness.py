"""Edge-case robustness — messy real-world inputs must degrade gracefully (no crash, valid
self-contained output), not just clean synthetic data. Complements the browser visual smoke."""
from pathlib import Path

import pytest

from graph_skill import builder, validate

OUT = Path(__file__).resolve().parent.parent / "graph-out"


def _render_ok(t, payload, name):
    r = builder.render(t, payload, out_path=str(OUT / f"_rob_{name}.html"))
    assert r["lint"]["ok"], (t, name, r["lint"])
    return Path(r["html_path"]).read_text(encoding="utf-8")


def test_null_gaps_become_breaks():
    p = {"axes": {"x": {"label": "t", "unit": "s"}, "y": {"label": "v", "unit": "m"}},
         "series": [{"name": "g", "data": [[0, 1], [1, None], [2, 3], [3, float("nan")], [4, 5]]}]}
    assert validate.check("base-xy", p)["ok"]
    h = _render_ok("base-xy", p, "gaps")
    assert "null" in h                      # NaN/None y serialized as null (gap), not a crash


def test_single_point_series():
    p = {"axes": {"x": {"label": "x", "unit": ""}, "y": {"label": "y", "unit": ""}},
         "series": [{"name": "one", "data": [[5, 5]]}]}
    _render_ok("base-xy", p, "single")


def test_unsorted_and_duplicate_x():
    p = {"axes": {"x": {"label": "x", "unit": ""}, "y": {"label": "y", "unit": ""}},
         "series": [{"name": "u", "data": [[3, 1], [1, 2], [3, 9], [2, 4], [1, 7]]}]}
    _render_ok("base-xy", p, "unsorted")


def test_log_scale_with_zero_and_negative():
    p = {"axes": {"x": {"label": "x", "unit": ""}, "y": {"label": "y", "unit": "", "scale": "log"}},
         "series": [{"name": "z", "data": [[1, 0], [2, -5], [3, 10], [4, 100]]}]}
    _render_ok("base-xy", p, "logzero")     # engine guards log(≤0); builder must not crash


def test_all_null_series_does_not_crash_validate():
    # a series whose y are all null still has finite x — should render (flat gaps) or gate cleanly
    p = {"axes": {"x": {"label": "x", "unit": ""}, "y": {"label": "y", "unit": ""}},
         "series": [{"name": "n", "data": [[0, None], [1, None]]}]}
    v = validate.check("base-xy", p)
    assert isinstance(v, dict) and "ok" in v   # no exception


def test_histogram_with_nan_values():
    p = {"axes": {"x": {"label": "x", "unit": "mm"}},
         "values": [1.0, 2.0, float("nan"), 3.0, None, 2.5, 2.1, 1.8, 2.2]}
    _render_ok("histogram", p, "histnan")


def test_contour_with_gap_cells():
    p = {"field": {"x": [0, 1, 2], "y": [0, 1], "z": [[1, None, 3], [4, 5, float("nan")]]},
         "z": {"label": "T", "unit": "C"}, "axes": {"x": {"label": "x", "unit": "m"}, "y": {"label": "y", "unit": "m"}}}
    _render_ok("contour-plot", p, "contourgap")


@pytest.mark.parametrize("n", [20000])
def test_large_series_renders(n):
    import math
    data = [[i * 0.01, math.sin(i * 0.01) + (i % 7) * 0.01] for i in range(n)]
    p = {"axes": {"x": {"label": "t", "unit": "s"}, "y": {"label": "a", "unit": "g"}},
         "series": [{"name": "big", "data": data}]}
    r = builder.render("base-xy", p, out_path=str(OUT / "_rob_big.html"))
    assert r["lint"]["ok"]                  # 20k points: builder stays deterministic + self-contained
    # NOTE: xy-core has no LTTB downsampling yet — large sets render fully (perf TODO).


def test_render_is_deterministic_under_gaps():
    p = {"axes": {"x": {"label": "x", "unit": ""}, "y": {"label": "y", "unit": ""}},
         "series": [{"name": "g", "data": [[0, 1], [1, None], [2, 3]]}]}
    a = builder.render("base-xy", p, out_path=str(OUT / "_rob_da.html"))
    b = builder.render("base-xy", p, out_path=str(OUT / "_rob_db.html"))
    assert Path(a["html_path"]).read_bytes() == Path(b["html_path"]).read_bytes()
