"""Phase (2) smoke: review-matrix (design-state-compare) — multi-engine bundling, graph cells,
images, structural gate. Run with PYTHONPATH=src."""
import json
from pathlib import Path

from graph_skill import builder, catalog, validate

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "graph-out"
payload = json.loads((ROOT / "fixtures" / "design_state.json").read_text(encoding="utf-8"))

print("types:", catalog.known_types())
assert {"review-matrix", "design-state-compare", "single-state-checklist"} <= set(catalog.known_types())

# review-matrix needs no series/axes
rt = catalog.resolve_type("design-state-compare")
assert rt.engine == "review-matrix" and rt.require_series is False and rt.require_axes is False

v = validate.check("design-state-compare", payload)
print("validate ok:", v["ok"], "missing:", [m["field"] for m in v["missing"]])
assert v["ok"]

r = builder.render("design-state-compare", payload, out_path=str(OUT / "design_state.html"))
html = Path(r["html_path"]).read_text(encoding="utf-8")
print("bytes:", r["bytes"], "engine:", r["engine"], r["engine_version"], "lint:", r["lint"]["ok"])
assert r["lint"]["ok"] and "://" not in html.replace("mention://", "")  # only the data link uses ://

# multi-engine bundle: BOTH review-matrix engine AND xy-core engine (graph cells) inlined
assert 'GraphEngines["review-matrix"]' in html, "matrix engine not bundled"
assert 'GraphEngines["xy-core"]' in html, "xy-core engine (for graph cells) not bundled"
# graph cell payloads present
assert '"graph_payloads"' in html and '"drop_curve::v1"' in html
# image inlined as base64 data
assert "data:image/png;base64," not in html  # builder doesn't add the prefix; the engine does at runtime
assert "iVBORw0KGgo" in html, "image base64 not inlined"
# states/items in config
assert '"states"' in html and '"AS-IS (v1)"' in html

# --- structural gate: baseline not in states ---
bad = json.loads(json.dumps(payload))
bad["meta"]["baseline"] = "v9"
vb = validate.check("design-state-compare", bad)
print("bad baseline ok:", vb["ok"], "missing:", [m["field"] for m in vb["missing"]])
assert not vb["ok"] and any(m["field"] == "meta.baseline" for m in vb["missing"])

# --- structural gate: design-state-compare with <2 states ---
one = json.loads(json.dumps(payload))
one["states"] = [payload["states"][0]]
one["meta"]["baseline"] = "v1"
v1 = validate.check("design-state-compare", one)
print("single-state-as-compare ok:", v1["ok"], "missing:", [m["field"] for m in v1["missing"]])
assert not v1["ok"] and any(m["field"] == "states" for m in v1["missing"])

# but single-state-checklist accepts 1 state
v2 = validate.check("single-state-checklist", one)
print("single-state-checklist ok:", v2["ok"])
assert v2["ok"]

# determinism
a = builder.render("design-state-compare", payload)["html"]
b = builder.render("design-state-compare", payload)["html"]
assert a == b, "matrix not deterministic"

print("PHASE2 SMOKE OK")
