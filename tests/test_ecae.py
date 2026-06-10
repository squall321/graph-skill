"""E-CAE family — srs/emi/zth/pdn/temp-cycle/spec-margin/derating/battery.
Locks: registration, render/lint, SRS physics (half-sine peak ≈ pulse peak near knee,
low-freq rolloff), EMI margin/violations, PDN target exceedance, cycle profile shape,
margin kind routing, gating, determinism."""
import json
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate
from graph_skill.postprocess import srs as _srs
from graph_skill.recipes import REGISTRY

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"
TYPES = {"srs-spectrum": "srs", "emi-spectrum": "emi", "zth-transient": "zth",
         "pdn-impedance": "pdn", "temp-cycle-profile": "tempcycle",
         "spec-margin-chart": "specmargin", "derating-curve": "derating",
         "battery-discharge": "battery"}


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_registration_and_render():
    cov = taxonomy.coverage(catalog.known_types())
    assert cov["ok"], cov["bad_category"]
    for t, fxn in TYPES.items():
        assert t in REGISTRY
        p = _load(fxn)
        assert validate.check(t, p)["ok"], t
        assert builder.render(t, p, out_path=str(OUT / f"{t}.html"))["lint"]["ok"], t


def test_srs_physics():
    # half-sine 1500g/0.5ms: SRS plateaus near ~1500-2500g at high fn, rolls off at low fn
    _, pulse = _srs.half_sine(1500, 0.5, 50000)
    fns, vals = _srs.srs_maximax(pulse, 50000)
    assert vals[0] < 300                                  # 10 Hz: far below pulse content
    hi = [v for f, v in zip(fns, vals) if f > 2000]
    assert hi and 1200 < max(vals) < 3000                 # maximax amplification ~1-1.8x peak
    assert all(v > 0 for v in vals)


def test_emi_margin_and_violations():
    out = REGISTRY["emi-spectrum"].normalize(_load("emi"), catalog.resolve_type("emi-spectrum"))
    names = [s["name"] for s in out["assets"]["series"]]
    assert any("한계선" in n for n in names)
    assert "최소 마진" in out["options"]["title"]
    assert out["options"]["axes"]["x"]["log"] is True   # engine key is `log`, not `scale`


def test_pdn_target_exceedance():
    out = REGISTRY["pdn-impedance"].normalize(_load("pdn"), catalog.resolve_type("pdn-impedance"))
    assert any(s["name"] == "target impedance" for s in out["assets"]["series"])
    assert "초과" in out["options"]["title"]              # fixture intentionally violates 0.05Ω


def test_temp_cycle_profile_shape():
    out = REGISTRY["temp-cycle-profile"].normalize(_load("tempcycle"), catalog.resolve_type("temp-cycle-profile"))
    prof = out["assets"]["series"][0]
    assert min(prof["y"]) == -40 and max(prof["y"]) == 125
    assert len(prof["x"]) == 1 + 3 * 4                    # cycles=3, 4 segments each
    lines = out["options"]["pluginConfig"]["threshold-lines"]["lines"]
    assert {ln["value"] for ln in lines} == {-40, 125}


def test_spec_margin_kind_and_fail_detection():
    out = REGISTRY["spec-margin-chart"].normalize(_load("specmargin"), catalog.resolve_type("spec-margin-chart"))
    assert out["assets"]["kind"] == "margin"
    glass = next(i for i in out["assets"]["items"] if "글라스" in i["label"])
    assert glass["value"] > glass["max"]                  # the intentional FAIL row survives normalize


def test_derating_split_pass_fail():
    out = REGISTRY["derating-curve"].normalize(_load("derating"), catalog.resolve_type("derating-curve"))
    names = [s["name"] for s in out["assets"]["series"]]
    assert "동작점 (적합)" in names and "동작점 (위반)" in names   # 95°C/92% violates interpolated limit


def test_gating():
    assert not validate.check("srs-spectrum", {"accel": [0, 1, 0]})["ok"]
    assert not validate.check("emi-spectrum", {"spectrum": [[30, 40]]})["ok"]
    assert not validate.check("pdn-impedance", {"series": [{"name": "z", "data": [[1e3, 0.1]]}]})["ok"]
    assert not validate.check("temp-cycle-profile", {})["ok"]
    assert not validate.check("spec-margin-chart", {"items": [{"label": "a", "value": 1}]})["ok"]
    assert not validate.check("derating-curve", {"curve": [[25, 100], [125, 40]]})["ok"]


def test_determinism():
    for t, fxn in TYPES.items():
        p = _load(fxn)
        a = Path(builder.render(t, p, out_path=str(OUT / f"_{fxn}A.html"))["html_path"]).read_bytes()
        b = Path(builder.render(t, p, out_path=str(OUT / f"_{fxn}B.html"))["html_path"]).read_bytes()
        assert a == b, t
        (OUT / f"_{fxn}A.html").unlink(missing_ok=True)
        (OUT / f"_{fxn}B.html").unlink(missing_ok=True)
