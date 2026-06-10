"""Quick end-to-end smoke: validate -> render -> lint -> determinism. Run with PYTHONPATH=src."""
import hashlib
import json
from pathlib import Path

from graph_skill import builder, catalog, validate

ROOT = Path(__file__).resolve().parent
payload = json.loads((ROOT / "fixtures" / "base_xy.json").read_text(encoding="utf-8"))

print("known types:", catalog.known_types())

v = validate.check("base-xy", payload)
print("validate ok:", v["ok"], "| missing:", [m["field"] for m in v["missing"]])
assert v["ok"], v["missing"]

out = ROOT.parent / "graph-out" / "base_xy.html"
res = builder.render("base-xy", payload, out_path=str(out))
print("engine:", res["engine"], res["engine_version"], "| bytes:", res["bytes"])
print("lint:", res["lint"])
print("path:", res["html_path"])
assert res["lint"]["ok"], "self-contained lint failed"

# determinism: same input -> identical html string (two in-memory renders)
a = builder.render("base-xy", payload)["html"]
b = builder.render("base-xy", payload)["html"]
h1 = hashlib.sha256(a.encode("utf-8")).hexdigest()
h2 = hashlib.sha256(b.encode("utf-8")).hexdigest()
print("deterministic:", h1 == h2)
assert h1 == h2
# and the written file matches the in-memory render byte-for-byte (LF, no CRLF translation)
assert out.read_bytes() == a.encode("utf-8"), "written file differs from in-memory html"

# missing-info gate: drop axes -> must report missing, not render
bad = {"series": payload["series"]}
vb = validate.check("base-xy", bad)
print("gate (no axes) ok:", vb["ok"], "| missing:", [m["field"] for m in vb["missing"]])
assert not vb["ok"] and any(m["field"] == "axes.x" for m in vb["missing"])

try:
    builder.render("base-xy", bad)
    print("ERROR: render should have raised")
except builder.MissingFieldsError as e:
    print("MissingFieldsError raised as expected:", [m["field"] for m in e.missing])

print("SMOKE OK")
