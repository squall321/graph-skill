"""smith-chart regression — new smith-core engine family (RF reflection coefficient)."""
import json
from pathlib import Path

from graph_skill import assets, builder, catalog, taxonomy, validate

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"


def _load():
    return json.loads((FIX / "smith.json").read_text(encoding="utf-8"))


def test_new_engine_family_resolves():
    assert catalog.resolve_type("smith-chart").engine == "smith-core"
    assert assets.engine_version("smith-core") != "0.0.0"
    assert taxonomy.coverage(catalog.known_types())["ok"]


def test_renders_self_contained():
    r = builder.render("smith-chart", _load(), out_path=str(OUT / "smith-chart.html"))
    h = Path(r["html_path"]).read_text(encoding="utf-8")
    assert r["lint"]["ok"] and r["lint"]["external_urls"] == 0
    assert 'GraphEngines["smith-core"]' in h and "gamma" in h


def test_accepts_mag_phase_and_reim():
    a = {"series": [{"name": "a", "mag": [0.2, 0.5, 0.8], "phase": [0, 90, 180]}]}
    b = {"series": [{"name": "b", "re": [0.1, -0.2], "im": [0.0, 0.3]}]}
    for p in (a, b):
        assert validate.check("smith-chart", p)["ok"]
        assert builder.render("smith-chart", p, out_path=str(OUT / "_sm.html"))["lint"]["ok"]


def test_gamma_conversion_mag_phase():
    from graph_skill.recipes import REGISTRY
    out = REGISTRY["smith-chart"].normalize(
        {"series": [{"name": "x", "mag": [0.5], "phase": [0]}]}, catalog.resolve_type("smith-chart"))
    g = out["assets"]["series"][0]["gamma"][0]
    assert abs(g[0] - 0.5) < 1e-9 and abs(g[1]) < 1e-9     # mag 0.5 ∠0° → Γ = 0.5 + j0


def test_gating():
    assert not validate.check("smith-chart", {})["ok"]
    assert not validate.check("smith-chart", {"series": [{"name": "x"}]})["ok"]


def test_determinism():
    a = builder.render("smith-chart", _load(), out_path=str(OUT / "_sma.html"))
    b = builder.render("smith-chart", _load(), out_path=str(OUT / "_smb.html"))
    assert Path(a["html_path"]).read_bytes() == Path(b["html_path"]).read_bytes()
