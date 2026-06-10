"""Phase (G) smoke: engineering 2D quick-wins (xy-core reuse, no new engine/plugin).
main-effects / interaction / transient / convergence / cfd-line-compare / nonlinear-ld / s-n."""
import json
from pathlib import Path

from graph_skill import builder, catalog, validate

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "graph-out"
TYPES = {
    "main-effects-plot": "main_effects",
    "interaction-plot": "interaction",
    "transient-time-history": "transient",
    "convergence-residual-plot": "convergence",
    "cfd-line-extract-compare": "cfd_line",
    "nonlinear-load-displacement": "nonlinear_ld",
    "s-n-fatigue-curve": "sn_curve",
}


def load(n):
    return json.loads((ROOT / "fixtures" / f"{n}.json").read_text(encoding="utf-8"))


# all registered on xy-core
assert set(TYPES) <= set(catalog.known_types())
for t in TYPES:
    assert catalog.resolve_type(t).engine == "xy-core", t

# validate + render + lint each
for t, fix in TYPES.items():
    v = validate.check(t, load(fix))
    assert v["ok"], (t, v.get("missing"))
    r = builder.render(t, load(fix), out_path=str(OUT / f"{fix}.html"))
    assert r["lint"]["ok"], t
    print(f"{t:<28} {r['bytes']:>6} bytes  lint {r['lint']['ok']}")

# --- type-specific structural assertions in the rendered output ---
me = Path(OUT / "main_effects.html").read_text(encoding="utf-8")
assert "threshold-lines" in me and "전체평균" in me            # grand-mean line

tr = Path(OUT / "transient.html").read_text(encoding="utf-8")
assert "named-markers" in tr and "peak" in tr and "허용 50g" in tr   # peaks + limit line

cv = Path(OUT / "convergence.html").read_text(encoding="utf-8")
assert "수렴기준" in cv and '"label":"Residual","log":true' in cv               # tol line + log-y

sn = Path(OUT / "sn_curve.html").read_text(encoding="utf-8")
assert "피로한도" in sn and "설계점" in sn and "threshold-lines" in sn and "named-markers" in sn

nl = Path(OUT / "nonlinear_ld.html").read_text(encoding="utf-8")
assert "live-tangent" in nl and "named-markers" in nl and "극한" in nl

cf = Path(OUT / "cfd_line.html").read_text(encoding="utf-8")
assert "error-bars" in cf                                       # experiment uncertainty

# --- gating: never invent units / missing factors ---
assert not validate.check("main-effects-plot", {"factors": [{"name": "T", "levels": ["a"], "means": [1]}]})["ok"]
assert not validate.check("s-n-fatigue-curve", {"series": [{"name": "x", "data": [[1, 2]]}]})["ok"]  # no axes.y unit
assert not validate.check("interaction-plot", {"axes": {"y": {"label": "y", "unit": ""}}})["ok"]     # no data

# --- determinism ---
a = builder.render("main-effects-plot", load("main_effects"), out_path=str(OUT / "_gdet_a.html"))
b = builder.render("main-effects-plot", load("main_effects"), out_path=str(OUT / "_gdet_b.html"))
assert Path(a["html_path"]).read_bytes() == Path(b["html_path"]).read_bytes()
print("determinism OK")

print("PHASEG SMOKE OK")
