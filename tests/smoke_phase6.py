"""Phase (6) smoke: histogram / bar-plot / box-plot / error-bar (xy-core bars + stats)."""
import json
from pathlib import Path

from graph_skill import builder, catalog, validate
from graph_skill.postprocess import stats

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "graph-out"


def load(n):
    return json.loads((ROOT / "fixtures" / f"{n}.json").read_text(encoding="utf-8"))


print("types ok:", {"histogram", "bar-plot", "box-plot", "error-bar"} <= set(catalog.known_types()))
assert {"histogram", "bar-plot", "box-plot", "error-bar"} <= set(catalog.known_types())

# --- stats correctness ---
c, counts, w = stats.histogram([1, 2, 2, 3, 3, 3, 4], bins=4)
assert sum(counts) == 7
q = stats.quartiles([1, 2, 3, 4, 5, 6, 7, 8, 100])
assert q["med"] == 5 and 100 in q["outliers"]
print("histogram sum & quartile outlier OK")

# --- histogram render (bar style + categorical-free numeric x) ---
rh = builder.render("histogram", load("hist"), out_path=str(OUT / "histogram.html"))
hh = Path(rh["html_path"]).read_text(encoding="utf-8")
assert rh["lint"]["ok"] and '"style":"bar"' in hh.replace(" ", "") and "MPa" in hh
# total count preserved
cfg = json.loads(hh.split('id="graph-config" type="application/json">', 1)[1].split("</script>", 1)[0]
                 .replace("\\u003c", "<").replace("\\u003e", ">").replace("\\u0026", "&"))
assert sum(cfg["assets"]["series"][0]["y"]) == 400

# --- bar (categorical) ---
rb = builder.render("bar-plot", load("bar"), out_path=str(OUT / "bar.html"))
bh = Path(rb["html_path"]).read_text(encoding="utf-8")
assert rb["lint"]["ok"] and '"categories"' in bh and '"Frame"' in bh and '"style":"bar"' in bh.replace(" ", "")

# --- box-plot (groups -> quartiles + plugin) ---
rx = builder.render("box-plot", load("box"), out_path=str(OUT / "box.html"))
xh = Path(rx["html_path"]).read_text(encoding="utf-8")
assert rx["lint"]["ok"] and '["box-plot"]' in xh and '"groups"' in xh and '"style":"none"' in xh.replace(" ", "")

# --- error-bar ---
re_ = builder.render("error-bar", load("errbar"), out_path=str(OUT / "errbar.html"))
eh = Path(re_["html_path"]).read_text(encoding="utf-8")
assert re_["lint"]["ok"] and '["error-bars"]' in eh and '"bars"' in eh

# --- gates ---
assert not validate.check("histogram", {"values": [1, 2, 3]})["ok"]   # axes.x missing
assert not validate.check("bar-plot", {"axes": {"y": {"label": "E", "unit": "J"}}})["ok"]  # categories missing
assert not validate.check("box-plot", {"axes": {"y": {"label": "S", "unit": "N"}}})["ok"]   # groups missing
print("gates OK")

print("PHASE6 SMOKE OK")
