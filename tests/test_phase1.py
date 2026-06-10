"""Phase (1) regression tests — plugin-bearing types + units + gate."""
import json
from pathlib import Path

import pytest

from graph_skill import builder, catalog, validate
from graph_skill.postprocess import units

FIX = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIX / f"{name}.json").read_text(encoding="utf-8"))


def test_new_types_registered():
    assert {"stress-strain", "force-displacement", "correlation-scatter"} <= set(catalog.known_types())


def test_units_eng_stress_strain():
    strain, stress = units.eng_stress_strain([2830.0, None], [0.5, 1.0], 28.3, 50.0)
    assert stress[0] == pytest.approx(100.0)   # 2830 N / 28.3 mm² = 100 MPa
    assert strain[0] == pytest.approx(0.01)     # 0.5 mm / 50 mm
    assert stress[1] is None                     # gap passthrough


def test_units_guards():
    with pytest.raises(ValueError):
        units.eng_stress_strain([1.0], [1.0], 0, 50)
    with pytest.raises(ValueError):
        units.eng_stress_strain([1.0], [1.0], 28.3, 0)


def test_units_eng_to_true():
    te, ts = units.eng_to_true([0.0, 0.1], [100.0, 200.0])
    assert te[0] == pytest.approx(0.0) and ts[0] == pytest.approx(100.0)
    assert ts[1] == pytest.approx(220.0)         # 200*(1+0.1)


def test_stress_strain_extends_and_plugins():
    rt = catalog.resolve_type("stress-strain")
    assert rt.engine == "xy-core" and rt.require_axes is False
    assert set(rt.plugins) == {"region-shading", "named-markers", "live-tangent"}
    assert [r["field"] for r in rt.requires] == ["params.A0", "params.L0"]


def test_stress_strain_render_self_contained():
    res = builder.render("stress-strain", load("stress_strain"))
    html = res["html"]
    assert res["lint"]["ok"] and "://" not in html
    for tok in ('["region-shading"]', '["named-markers"]', '["live-tangent"]'):
        assert tok in html
    assert "UTS" in html and "Strain" in html and "Stress" in html


def test_stress_strain_missing_A0_blocks():
    bad = {"params": {"L0": 50}, "series": load("stress_strain")["series"]}
    v = validate.check("stress-strain", bad)
    assert not v["ok"] and any(m["field"] == "params.A0" for m in v["missing"])
    with pytest.raises(builder.MissingFieldsError):
        builder.render("stress-strain", bad)


def test_force_displacement_tangent_config():
    html = builder.render("force-displacement", load("force_displacement"))["html"]
    assert '["live-tangent"]' in html and "N/mm" in html


def test_correlation_regression_config():
    html = builder.render("correlation-scatter", load("correlation"))["html"]
    assert '["regression-fit"]' in html
    assert "identityLine" in html


def test_stress_strain_deterministic():
    a = builder.render("stress-strain", load("stress_strain"))["html"]
    b = builder.render("stress-strain", load("stress_strain"))["html"]
    assert a == b
