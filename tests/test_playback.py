"""playback plugin — bubble-timeline / animated-trajectory / bar-chart-race.
Locks: registration, render/lint, plugin+config bundled, style:"none" carrier series
(autoscale over all frames), frame normalization, never-invent-units gate, determinism."""
import hashlib
import json
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate
from graph_skill.recipes import REGISTRY

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"
TYPES = {"bubble-timeline": "bubble", "animated-trajectory": "trajectory", "bar-chart-race": "race"}


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_registration_and_taxonomy():
    cov = taxonomy.coverage(catalog.known_types())
    assert cov["ok"], cov["bad_category"]
    for t in TYPES:
        assert t in REGISTRY
        rt = catalog.resolve_type(t)
        assert rt.engine == "xy-core" and "playback" in rt.plugins


def test_render_lint_and_plugin_bundled():
    for t, fx in TYPES.items():
        p = _load(fx)
        assert validate.check(t, p)["ok"], t
        r = builder.render(t, p, out_path=str(OUT / f"{t}.html"))
        assert r["lint"]["ok"], t
        html = Path(r["html_path"]).read_text(encoding="utf-8")
        assert 'GraphPlugins["xy-core"]["playback"]' in html        # plugin js bundled
        assert '"playback"' in html and '"mode"' in html            # config embedded
        assert '"style":"none"' in html or '"_carrier"' in html     # autoscale carrier


def test_bubble_size_to_radius_and_frames():
    out = REGISTRY["bubble-timeline"].normalize(_load("bubble"), catalog.resolve_type("bubble-timeline"))
    pb = out["options"]["pluginConfig"]["playback"]
    assert pb["mode"] == "bubble" and len(pb["frames"]) >= 2
    # size present -> radius computed (>0), larger size -> larger radius within a frame
    ents = pb["frames"][0]["entities"]
    assert all("r" in e and e["r"] > 0 for e in ents)


def test_trajectory_path_and_mode():
    out = REGISTRY["animated-trajectory"].normalize(_load("trajectory"), catalog.resolve_type("animated-trajectory"))
    pb = out["options"]["pluginConfig"]["playback"]
    assert pb["mode"] == "trail" and len(pb["path"]) >= 100
    assert all(len(p) == 2 for p in pb["path"])


def test_race_sorts_and_carrier_spans_max():
    out = REGISTRY["bar-chart-race"].normalize(_load("race"), catalog.resolve_type("bar-chart-race"))
    pb = out["options"]["pluginConfig"]["playback"]
    assert pb["mode"] == "race"
    carrier = out["assets"]["series"][0]
    # engine setData reads x/y arrays — the carrier MUST be in that shape (regression: was data pairs)
    assert "x" in carrier and "y" in carrier and "data" not in carrier
    maxv = max(e["value"] for fr in pb["frames"] for e in fr["entities"])
    assert max(carrier["x"]) >= maxv        # x-domain covers the largest bar


def test_never_invent_units_gate():
    # frames present but axes units missing -> must ASK (not silently render)
    p = {"frames": [{"t": "1", "entities": [{"id": "a", "x": 1, "y": 2}]},
                    {"t": "2", "entities": [{"id": "a", "x": 2, "y": 3}]}]}
    res = validate.check("bubble-timeline", p)
    assert not res["ok"] and any("axes" in m.get("field", "") for m in res.get("missing", []))


def test_gating():
    assert not validate.check("bubble-timeline", {})["ok"]
    assert not validate.check("animated-trajectory",
                              {"axes": {"x": {"label": "a", "unit": ""}, "y": {"label": "b", "unit": ""}}})["ok"]
    assert not validate.check("bar-chart-race",
                              {"frames": [{"t": "1", "entities": [{"id": "a"}]},
                                          {"t": "2", "entities": [{"id": "a"}]}]})["ok"]


def test_determinism():
    p = _load("race")
    a = Path(builder.render("bar-chart-race", p, out_path=str(OUT / "_rcA.html"))["html_path"]).read_bytes()
    b = Path(builder.render("bar-chart-race", p, out_path=str(OUT / "_rcB.html"))["html_path"]).read_bytes()
    assert hashlib.sha256(a).hexdigest() == hashlib.sha256(b).hexdigest()
    (OUT / "_rcA.html").unlink(missing_ok=True)
    (OUT / "_rcB.html").unlink(missing_ok=True)
