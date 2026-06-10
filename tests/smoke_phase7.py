"""Phase (B) smoke: dual-axis + bode (xy-core secondary-y)."""
import json
from pathlib import Path

from graph_skill import builder, catalog, validate

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "graph-out"


def load(n):
    return json.loads((ROOT / "fixtures" / f"{n}.json").read_text(encoding="utf-8"))


assert {"dual-axis", "bode"} <= set(catalog.known_types())

# dual-axis: two y axes
rd = builder.render("dual-axis", load("dual"), out_path=str(OUT / "dual.html"))
dh = Path(rd["html_path"]).read_text(encoding="utf-8")
print("dual-axis lint:", rd["lint"]["ok"], "bytes:", rd["bytes"])
assert rd["lint"]["ok"]
assert '"y2"' in dh and '"axis":"right"' in dh.replace(" ", "") and "Temp" in dh

# bode: log-x mag(left)/phase(right)
rb = builder.render("bode", load("bode"), out_path=str(OUT / "bode.html"))
bh = Path(rb["html_path"]).read_text(encoding="utf-8")
print("bode lint:", rb["lint"]["ok"], "bytes:", rb["bytes"])
assert rb["lint"]["ok"]
assert '"Magnitude"' in bh and '"Phase"' in bh
assert '"log":true' in bh.replace(" ", "")  # frequency axis log
assert '"axis":"right"' in bh.replace(" ", "")

# gates
assert not validate.check("dual-axis", {"series": [{"name": "a", "data": [[0, 1]]}],
                                        "axes": {"x": {"label": "t", "unit": "s"}, "y": {"label": "p", "unit": "W"}}})["ok"]  # y2 missing
assert not validate.check("bode", {"freqs": [1, 2, 3]})["ok"]  # mag/phase missing
print("gates OK")

# existing single-axis unaffected (base-xy still renders)
assert builder.render("base-xy", json.loads((ROOT / "fixtures" / "base_xy.json").read_text(encoding="utf-8")))["lint"]["ok"]

print("PHASE7 SMOKE OK")
