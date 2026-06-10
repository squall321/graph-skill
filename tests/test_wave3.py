"""Wave-3 regression — nichols-chart / parallel-coordinates (xy-core) · wind-rose (polar-core)."""
import json
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"
TYPES = {"nichols-chart": ("nichols", "xy-core"),
         "parallel-coordinates": ("parcoord", "xy-core"),
         "wind-rose": ("windrose", "polar-core")}


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_taxonomy_complete():
    assert taxonomy.coverage(catalog.known_types())["ok"]


def test_registered():
    for t, (_, eng) in TYPES.items():
        assert catalog.resolve_type(t).engine == eng


def test_validate_render_lint():
    for t, (fx, _) in TYPES.items():
        assert validate.check(t, _load(fx))["ok"], t
        assert builder.render(t, _load(fx), out_path=str(OUT / f"{t}.html"))["lint"]["ok"], t


def test_nichols_refs_and_critical():
    h = Path(builder.render("nichols-chart", _load("nichols"), out_path=str(OUT / "nichols-chart.html"))["html_path"]).read_text(encoding="utf-8")
    assert "threshold-lines" in h and "crit" in h and "0 dB" in h


def test_parcoord_normalizes_and_keeps_real_ranges():
    from graph_skill.recipes import REGISTRY
    out = REGISTRY["parallel-coordinates"].normalize(_load("parcoord"), catalog.resolve_type("parallel-coordinates"))
    pc = out["options"]["pluginConfig"]["parcoord"]
    assert len(pc["dims"]) == 4 and all("min" in d and "max" in d for d in pc["dims"])
    assert pc["rows"] and all(0.0 <= v <= 1.0 for row in pc["rows"] for v in row)   # normalized


def test_windrose_stacks_and_bins():
    h = Path(builder.render("wind-rose", _load("windrose"), out_path=str(OUT / "wind-rose.html"))["html_path"]).read_text(encoding="utf-8")
    assert "rose" in h and "0–3 m/s" in h and "6–9 m/s" in h        # '>' is HTML-escaped (>), so check safe labels


def test_gating():
    assert not validate.check("nichols-chart", {})["ok"]
    assert not validate.check("parallel-coordinates", {"variables": {"A": [1, 2]}})["ok"]      # <2 vars
    assert not validate.check("wind-rose", {"dir_labels": ["N", "S"]})["ok"]                    # no bins


def test_determinism():
    a = builder.render("wind-rose", _load("windrose"), out_path=str(OUT / "_w3a.html"))
    b = builder.render("wind-rose", _load("windrose"), out_path=str(OUT / "_w3b.html"))
    assert Path(a["html_path"]).read_bytes() == Path(b["html_path"]).read_bytes()
