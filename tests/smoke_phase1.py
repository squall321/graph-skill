"""Phase (1) smoke: stress-strain / force-displacement / correlation-scatter + plugin bundling
+ missing-A0 gate. Run with PYTHONPATH=src."""
import json
from pathlib import Path

from graph_skill import builder, catalog, tools, validate

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "graph-out"


def load(name):
    return json.loads((ROOT / "fixtures" / f"{name}.json").read_text(encoding="utf-8"))


print("types:", catalog.known_types())
assert {"stress-strain", "force-displacement", "correlation-scatter"} <= set(catalog.known_types())

# --- stress-strain: requires A0/L0, derives axes, bundles 3 plugins ---
ss = load("stress_strain")
v = validate.check("stress-strain", ss)
print("stress-strain validate ok:", v["ok"], "preview:", v.get("normalized_preview"))
assert v["ok"]
r = builder.render("stress-strain", ss, out_path=str(OUT / "stress_strain.html"))
html = Path(r["html_path"]).read_text(encoding="utf-8")
print("stress-strain bytes:", r["bytes"], "lint:", r["lint"]["ok"])
assert r["lint"]["ok"]
for token in ('GraphPlugins["xy-core"]["region-shading"]',
              'GraphPlugins["xy-core"]["named-markers"]',
              'GraphPlugins["xy-core"]["live-tangent"]'):
    assert token in html, f"plugin not bundled: {token}"
assert '"named-markers"' in html and "UTS" in html, "marker config not inlined"
assert '"live-tangent"' in html and "Et" in html
# axes derived
assert "Strain" in html and "Stress" in html

# --- missing A0 -> gate blocks ---
ss_bad = {"params": {"L0": 50}, "series": ss["series"]}
vb = validate.check("stress-strain", ss_bad)
print("stress-strain (no A0) ok:", vb["ok"], "missing:", [m["field"] for m in vb["missing"]])
assert not vb["ok"] and any(m["field"] == "params.A0" for m in vb["missing"])
ni = tools.render("stress-strain", ss["series"], {}, params={"L0": 50}, out_path=str(OUT / "x.html"))
assert ni["status"] == "needs_input" and any(m["field"] == "params.A0" for m in ni["missing"])

# --- force-displacement: live-tangent(stiffness) ---
fd = load("force_displacement")
r2 = builder.render("force-displacement", fd, out_path=str(OUT / "force_displacement.html"))
h2 = Path(r2["html_path"]).read_text(encoding="utf-8")
print("force-displacement lint:", r2["lint"]["ok"])
assert r2["lint"]["ok"] and 'GraphPlugins["xy-core"]["live-tangent"]' in h2 and "N/mm" in h2

# --- correlation-scatter: regression-fit + identity ---
co = load("correlation")
r3 = builder.render("correlation-scatter", co, out_path=str(OUT / "correlation.html"))
h3 = Path(r3["html_path"]).read_text(encoding="utf-8")
print("correlation lint:", r3["lint"]["ok"])
assert r3["lint"]["ok"] and 'GraphPlugins["xy-core"]["regression-fit"]' in h3
assert '"identityLine":true' in h3 or '"identityLine": true' in h3

# --- determinism for stress-strain ---
a = builder.render("stress-strain", ss)["html"]
b = builder.render("stress-strain", ss)["html"]
assert a == b, "stress-strain not deterministic"

print("PHASE1 SMOKE OK")
