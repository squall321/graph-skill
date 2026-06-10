"""Wave-6 regression — eye-diagram (field-core fold) + gauge-r-r (AIAG range method)."""
import json
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate
from graph_skill.postprocess import eye, gaugerr

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_taxonomy_and_engines():
    assert taxonomy.coverage(catalog.known_types())["ok"]
    assert catalog.resolve_type("eye-diagram").engine == "field-core"
    assert catalog.resolve_type("gauge-r-r").engine == "xy-core"


def test_render_lint():
    for t, fx in [("eye-diagram", "eye"), ("gauge-r-r", "gaugerr")]:
        assert validate.check(t, _load(fx))["ok"], t
        assert builder.render(t, _load(fx), out_path=str(OUT / f"{t}.html"))["lint"]["ok"], t


def test_eye_histogram_dims_and_folding():
    ph, amp, z = eye.eye_histogram(list(range(200)) * 2, sps=20, ui=2, n_phase=40, n_amp=30)
    assert len(z) == 30 and all(len(r) == 40 for r in z)
    assert ph[0] >= 0 and ph[-1] <= 2.0                        # phase in [0, ui] UI
    assert sum(sum(r) for r in z) > 0


def test_gauge_rr_components_sum_consistent():
    # perfectly repeatable + reproducible data → tiny GRR, GRR <= TV
    m = [[[10.0, 10.0], [10.0, 10.0]], [[12.0, 12.0], [12.0, 12.0]], [[8.0, 8.0], [8.0, 8.0]]]
    r = gaugerr.gauge_rr(m)
    assert r["GRR"] < 1e-6 and r["pct"]["PV"] > 99            # all variation is part-to-part
    assert r["GRR"] <= r["TV"] + 1e-9


def test_gauge_output_has_components_and_limits():
    h = Path(builder.render("gauge-r-r", _load("gaugerr"), out_path=str(OUT / "gauge-r-r.html"))["html_path"]).read_text(encoding="utf-8")
    assert "GRR" in h and "threshold-lines" in h and "%GRR=" in h


def test_eye_output_is_field_heatmap():
    h = Path(builder.render("eye-diagram", _load("eye"), out_path=str(OUT / "eye-diagram.html"))["html_path"]).read_text(encoding="utf-8")
    assert "field-core" in h and "Hits" in h


def test_gating():
    assert not validate.check("eye-diagram", {"signal": [1, 0, 1, 0, 1, 0, 1, 0, 1, 0]})["ok"]   # no sps
    assert not validate.check("gauge-r-r", {})["ok"]


def test_determinism():
    a = builder.render("eye-diagram", _load("eye"), out_path=str(OUT / "_w6a.html"))
    b = builder.render("eye-diagram", _load("eye"), out_path=str(OUT / "_w6b.html"))
    assert Path(a["html_path"]).read_bytes() == Path(b["html_path"]).read_bytes()
