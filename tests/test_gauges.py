"""gauge-core KPI indicators — gauge / radial-progress / bullet-chart.
Locks: registration, render/lint, kind routing, single+items forms, default dial,
bands passthrough, gating, determinism."""
import hashlib
import json
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate
from graph_skill.recipes import REGISTRY

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"
TYPES = {"gauge": ("gauge", "gauge"), "radial-progress": ("ring", "radial-progress"),
         "bullet-chart": ("bullet", "bullet")}


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_registration_and_taxonomy():
    cov = taxonomy.coverage(catalog.known_types())
    assert cov["ok"], cov["bad_category"]
    for t in TYPES:
        assert t in REGISTRY and catalog.resolve_type(t).engine == "gauge-core"


def test_render_lint_and_kind():
    for t, (fx, kind) in TYPES.items():
        p = _load(fx)
        assert validate.check(t, p)["ok"], t
        r = builder.render(t, p, out_path=str(OUT / f"{t}.html"))
        assert r["lint"]["ok"], t
        html = Path(r["html_path"]).read_text(encoding="utf-8")
        assert 'GraphEngines["gauge-core"]' in html
        out = REGISTRY[t].normalize(p, catalog.resolve_type(t))
        assert out["assets"]["kind"] == kind and len(out["assets"]["items"]) >= 1


def test_single_flat_form_and_default_dial():
    out = REGISTRY["gauge"].normalize({"label": "score", "value": 72}, catalog.resolve_type("gauge"))
    it = out["assets"]["items"][0]
    assert len(out["assets"]["items"]) == 1 and it["value"] == 72
    assert it["min"] == 0.0 and it["max"] == 100.0          # conventional default dial


def test_bands_and_target_passthrough():
    out = REGISTRY["gauge"].normalize(_load("gauge"), catalog.resolve_type("gauge"))
    rpm = next(i for i in out["assets"]["items"] if i["label"] == "회전수")
    assert rpm["bands"] and rpm["target"] == 3000


def test_gating():
    assert not validate.check("gauge", {})["ok"]
    assert not validate.check("radial-progress", {})["ok"]
    assert not validate.check("bullet-chart", {"items": [{"label": "x"}]})["ok"]   # item without value


def test_determinism():
    for t, (fx, _) in TYPES.items():
        p = _load(fx)
        a = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}A.html"))["html_path"]).read_bytes()
        b = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}B.html"))["html_path"]).read_bytes()
        assert hashlib.sha256(a).hexdigest() == hashlib.sha256(b).hexdigest(), t
        (OUT / f"_{fx}A.html").unlink(missing_ok=True)
        (OUT / f"_{fx}B.html").unlink(missing_ok=True)
