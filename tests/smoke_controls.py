"""Controls smoke — nyquist-plot / root-locus (equalAspect + unit-circle plugin)."""
import json
from pathlib import Path

from graph_skill import builder, catalog, validate

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "graph-out"


def load(n):
    return json.loads((ROOT / "fixtures" / f"{n}.json").read_text(encoding="utf-8"))


for t in ("nyquist-plot", "root-locus"):
    assert t in catalog.known_types() and catalog.resolve_type(t).engine == "xy-core"

rn = builder.render("nyquist-plot", load("nyquist"), out_path=str(OUT / "nyquist.html"))
nh = Path(rn["html_path"]).read_text(encoding="utf-8")
assert rn["lint"]["ok"]
assert "unit-circle" in nh and '"equalAspect":true' in nh and "−1" in nh and "named-markers" in nh
print("nyquist-plot:", rn["bytes"], "bytes lint", rn["lint"]["ok"])

rl = builder.render("root-locus", load("rootlocus"), out_path=str(OUT / "rootlocus.html"))
lh = Path(rl["html_path"]).read_text(encoding="utf-8")
assert rl["lint"]["ok"]
assert "unit-circle" in lh and '"equalAspect":true' in lh and "pole" in lh
print("root-locus:", rl["bytes"], "bytes lint", rl["lint"]["ok"])

# gating
assert not validate.check("nyquist-plot", {"series": [{"name": "g", "data": []}]})["ok"]
assert not validate.check("root-locus", {})["ok"]

# determinism
a = builder.render("nyquist-plot", load("nyquist"), out_path=str(OUT / "_ndet_a.html"))
b = builder.render("nyquist-plot", load("nyquist"), out_path=str(OUT / "_ndet_b.html"))
assert Path(a["html_path"]).read_bytes() == Path(b["html_path"]).read_bytes()
print("determinism OK")

print("CONTROLS SMOKE OK")
