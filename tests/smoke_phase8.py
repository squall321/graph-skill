"""Phase (C) smoke: polar-core (rf-radiation-pattern / radar-chart / polar-plot)."""
import json
from pathlib import Path

from graph_skill import builder, catalog, validate

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "graph-out"


def load(n):
    return json.loads((ROOT / "fixtures" / f"{n}.json").read_text(encoding="utf-8"))


assert {"polar-plot", "radar-chart", "rf-radiation-pattern"} <= set(catalog.known_types())
assert catalog.resolve_type("rf-radiation-pattern").engine == "polar-core"

# rf-radiation-pattern (radius defaulted to Gain/dBi, closed)
rp = builder.render("rf-radiation-pattern", load("pattern"), out_path=str(OUT / "pattern.html"))
ph = Path(rp["html_path"]).read_text(encoding="utf-8")
print("pattern lint:", rp["lint"]["ok"], "bytes:", rp["bytes"])
assert rp["lint"]["ok"] and 'GraphEngines["polar-core"]' in ph
assert '"theta"' in ph and '"closed":true' in ph.replace(" ", "") and "dBi" in ph

# radar-chart (categories -> angle labels, closed polygons)
rr = builder.render("radar-chart", load("radar"), out_path=str(OUT / "radar.html"))
rh = Path(rr["html_path"]).read_text(encoding="utf-8")
print("radar lint:", rr["lint"]["ok"])
assert rr["lint"]["ok"] and '"angleLabels"' in rh and '"Drop"' in rh and '"closed":true' in rh.replace(" ", "")

# polar-plot (generic, needs radius meta)
pp = {"graph_type": "polar-plot", "radius": {"label": "Gain", "unit": "dBi"},
      "series": [{"name": "x", "theta": [0, 90, 180, 270], "r": [0, -3, -10, -3]}]}
rpp = builder.render("polar-plot", pp, out_path=str(OUT / "polar.html"))
assert rpp["lint"]["ok"]

# gates
assert not validate.check("polar-plot", {"series": [{"theta": [0], "r": [1]}]})["ok"]  # radius missing
assert not validate.check("radar-chart", {"series": [{"name": "a", "values": [1, 2]}]})["ok"]  # axes_labels missing
assert not validate.check("rf-radiation-pattern", {})["ok"]  # series missing
print("gates OK")

a = builder.render("radar-chart", load("radar"))["html"]
b = builder.render("radar-chart", load("radar"))["html"]
assert a == b
print("PHASE8 SMOKE OK")
