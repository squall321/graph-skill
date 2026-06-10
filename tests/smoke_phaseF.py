"""Phase (F) smoke: pareto / qq-plot / ecdf-plot / spc-control-chart.

All xy-core, reusing bar + secondary axis + threshold-lines(y2) + regression-fit +
named-markers + curve:"step". Verifies stats numerics, validate gate, render+lint,
correct plugin bundling, and determinism.
"""
import json
from pathlib import Path

from graph_skill import builder, catalog, validate
from graph_skill.postprocess import stats

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "graph-out"


def load(n):
    return json.loads((ROOT / "fixtures" / f"{n}.json").read_text(encoding="utf-8"))


# --- types registered on the right engine ---
assert {"pareto", "qq-plot", "ecdf-plot", "spc-control-chart"} <= set(catalog.known_types())
for t in ("pareto", "qq-plot", "ecdf-plot", "spc-control-chart"):
    assert catalog.resolve_type(t).engine == "xy-core", t

# --- stats numerics ---------------------------------------------------------
cats, vals, cum = stats.pareto(["a", "b", "c"], [10, 30, 20])
assert vals == [30, 20, 10]                      # sorted desc
assert cats == ["b", "c", "a"]
assert abs(cum[-1] - 100.0) < 1e-9               # cumulative ends at 100%
assert all(cum[i] <= cum[i + 1] + 1e-9 for i in range(len(cum) - 1))   # monotone

q = stats.normal_quantiles(30)
assert all(q[i] <= q[i + 1] for i in range(len(q) - 1))                 # sorted
assert abs(q[0] + q[-1]) < 1e-6                   # symmetric about 0
assert abs(stats.inv_norm(0.5)) < 1e-6            # median quantile = 0

xs, F = stats.ecdf([3, 1, 2, 2])
assert xs == [1, 2, 2, 3]
assert abs(F[-1] - 1.0) < 1e-9 and all(F[i] <= F[i + 1] for i in range(len(F) - 1))

cl = stats.control_limits([0.5, 0.5, 0.5, 0.6, 0.4])
assert cl["lcl"] < cl["mean"] < cl["ucl"]

# --- validate gate: complete fixtures pass; missing axes asks ---------------
for name, t in [("pareto", "pareto"), ("qq", "qq-plot"), ("ecdf", "ecdf-plot"), ("spc", "spc-control-chart")]:
    v = validate.check(t, load(name))
    assert v["ok"], (t, v.get("missing"))

# pareto without axes.y must be gated (NEVER invent units)
gated = validate.check("pareto", {"categories": ["a", "b"], "values": [1, 2]})
assert not gated["ok"] and any(m["field"] == "axes.y" for m in gated["missing"])
# qq with <3 samples gated
assert not validate.check("qq-plot", {"values": [1, 2]})["ok"]

# --- render + lint + correct plugin bundling --------------------------------
rp = builder.render("pareto", load("pareto"), out_path=str(OUT / "pareto.html"))
ph = Path(rp["html_path"]).read_text(encoding="utf-8")
assert rp["lint"]["ok"]
assert "threshold-lines" in ph and "Cumulative" in ph and "cumulative" in ph
assert '"y2"' in ph or "y2" in ph                # secondary axis present
print("pareto:", rp["bytes"], "bytes lint", rp["lint"]["ok"])

rq = builder.render("qq-plot", load("qq"), out_path=str(OUT / "qq.html"))
qh = Path(rq["html_path"]).read_text(encoding="utf-8")
assert rq["lint"]["ok"]
assert "regression-fit" in qh and "Theoretical quantiles" in qh
print("qq-plot:", rq["bytes"], "bytes lint", rq["lint"]["ok"])

re_ = builder.render("ecdf-plot", load("ecdf"), out_path=str(OUT / "ecdf.html"))
eh = Path(re_["html_path"]).read_text(encoding="utf-8")
assert re_["lint"]["ok"]
assert "F(x)" in eh and "step" in eh
assert "regression-fit" not in eh and "threshold-lines" not in eh   # no plugins for ecdf
print("ecdf-plot:", re_["bytes"], "bytes lint", re_["lint"]["ok"])

rs = builder.render("spc-control-chart", load("spc"), out_path=str(OUT / "spc.html"))
sh = Path(rs["html_path"]).read_text(encoding="utf-8")
assert rs["lint"]["ok"]
assert "threshold-lines" in sh and "named-markers" in sh
assert "UCL" in sh and "LCL" in sh and "CL" in sh and "OOC" in sh
# both engineered outliers (samples 13=0.555, 20=0.448) flagged out-of-control
cl_spc = stats.control_limits([pt[1] for pt in load("spc")["series"][0]["data"]])
assert cl_spc["violations"] == [12, 19], cl_spc["violations"]
print("spc:", rs["bytes"], "bytes lint", rs["lint"]["ok"], "OOC idx", cl_spc["violations"])

# --- determinism: same input -> identical bytes -----------------------------
a = builder.render("pareto", load("pareto"), out_path=str(OUT / "_det_a.html"))
b = builder.render("pareto", load("pareto"), out_path=str(OUT / "_det_b.html"))
assert Path(a["html_path"]).read_bytes() == Path(b["html_path"]).read_bytes()
print("determinism: identical bytes OK")

print("PHASEF SMOKE OK")
