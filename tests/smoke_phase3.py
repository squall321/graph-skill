"""Phase (3) smoke: field-core (contour/heatmap/stress-contour) + z-meta gate. PYTHONPATH=src."""
import json
from pathlib import Path

from graph_skill import builder, catalog, validate

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "graph-out"
payload = json.loads((ROOT / "fixtures" / "field.json").read_text(encoding="utf-8"))

print("types:", catalog.known_types())
assert {"contour-plot", "heatmap-grid", "scalar-field-2d", "mcae-stress-contour"} <= set(catalog.known_types())

rt = catalog.resolve_type("mcae-stress-contour")
assert rt.engine == "field-core" and rt.require_series is False and rt.require_axes is True

v = validate.check("mcae-stress-contour", payload)
print("validate ok:", v["ok"], "missing:", [m["field"] for m in v["missing"]])
assert v["ok"]

r = builder.render("mcae-stress-contour", payload, out_path=str(OUT / "field.html"))
html = Path(r["html_path"]).read_text(encoding="utf-8")
print("bytes:", r["bytes"], "engine:", r["engine"], r["engine_version"], "lint:", r["lint"]["ok"])
assert r["lint"]["ok"] and "://" not in html
assert 'GraphEngines["field-core"]' in html
assert '"field"' in html and '"colormap":"turbo"' in html
assert "von Mises" in html

# heatmap-grid turns contours off by default
hm = dict(payload); hm["graph_type"] = "heatmap-grid"
rh = builder.render("heatmap-grid", hm, out_path=str(OUT / "heatmap.html"))
hhtml = Path(rh["html_path"]).read_text(encoding="utf-8")
assert rh["lint"]["ok"] and '"contours":false' in hhtml.replace(" ", "")

# --- z-meta gate: drop z label -> blocks ---
bad = dict(payload); bad.pop("z")
vb = validate.check("mcae-stress-contour", bad)
print("no z-meta ok:", vb["ok"], "missing:", [m["field"] for m in vb["missing"]])
assert not vb["ok"] and any(m["field"] == "z" for m in vb["missing"])

# --- dimension mismatch gate ---
bad2 = json.loads(json.dumps(payload)); bad2["field"]["z"][3] = bad2["field"]["z"][3][:-1]
vd = validate.check("mcae-stress-contour", bad2)
print("dim mismatch ok:", vd["ok"], "missing:", [m["field"] for m in vd["missing"]])
assert not vd["ok"] and any(m["field"] == "field.z" for m in vd["missing"])

# determinism
a = builder.render("mcae-stress-contour", payload)["html"]
b = builder.render("mcae-stress-contour", payload)["html"]
assert a == b

print("PHASE3 SMOKE OK")
