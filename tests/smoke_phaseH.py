"""Phase (H) smoke: reliability/SPC/fatigue/controls/modal — no new plugin/engine.
process-capability-hist / paris-crack-growth / campbell-diagram / kaplan-meier-survival / mac-matrix-heatmap."""
import json
from pathlib import Path

from graph_skill import builder, catalog, validate
from graph_skill.postprocess import reliability, stats

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "graph-out"
TYPES = {
    "process-capability-hist": ("capability", "xy-core"),
    "paris-crack-growth": ("paris", "xy-core"),
    "campbell-diagram": ("campbell", "xy-core"),
    "kaplan-meier-survival": ("km", "xy-core"),
    "mac-matrix-heatmap": ("mac", "field-core"),
}


def load(n):
    return json.loads((ROOT / "fixtures" / f"{n}.json").read_text(encoding="utf-8"))


# --- postprocess numerics ---
cap = stats.capability([9.5, 10.0, 10.5], usl=11, lsl=9)
assert cap["cp"] is not None and abs(cap["mean"] - 10.0) < 1e-9
ts, surv, cens = reliability.kaplan_meier([10, 20, 20, 30], [1, 0, 1, 1])
assert ts[0] == 0.0 and surv[0] == 1.0 and surv[-1] < surv[0]      # monotone non-increasing
assert all(surv[i] >= surv[i + 1] - 1e-12 for i in range(len(surv) - 1))
assert len(reliability.median_ranks(5)) == 5

# --- registered on the right engine ---
for t, (_, eng) in TYPES.items():
    assert t in catalog.known_types() and catalog.resolve_type(t).engine == eng, t

# --- validate + render + lint each ---
for t, (fix, _) in TYPES.items():
    v = validate.check(t, load(fix))
    assert v["ok"], (t, v.get("missing"))
    r = builder.render(t, load(fix), out_path=str(OUT / f"{fix}.html"))
    assert r["lint"]["ok"], t
    print(f"{t:<26} {r['bytes']:>6} bytes  lint {r['lint']['ok']}")

# --- type-specific output checks ---
ch = Path(OUT / "capability.html").read_text(encoding="utf-8")
assert "USL" in ch and "LSL" in ch and "Cp=" in ch and "Cpk=" in ch and "normal fit" in ch

ph = Path(OUT / "paris.html").read_text(encoding="utf-8")
assert "Paris fit" in ph and "ΔKth" in ph and "KIC" in ph and '"log":true' in ph

cb = Path(OUT / "campbell.html").read_text(encoding="utf-8")
assert "1X" in cb and "2X" in cb and "4X" in cb            # engine-order rays

kh = Path(OUT / "km.html").read_text(encoding="utf-8")
assert '"curve":"step"' in kh and "named-markers" in kh and "censored" in kh

mh = Path(OUT / "mac.html").read_text(encoding="utf-8")
assert "field-core" in mh and "MAC" in mh and '"zdomain":[0,1]' in mh

# --- gating ---
assert not validate.check("process-capability-hist", {"values": [1, 2, 3], "axes": {"x": {"label": "x", "unit": "mm"}}})["ok"]  # no USL/LSL
assert not validate.check("kaplan-meier-survival", {"groups": [{"label": "g", "durations": [1], "events": [1]}]})["ok"]          # no axes.x unit
assert not validate.check("mac-matrix-heatmap", {})["ok"]

# --- determinism ---
a = builder.render("mac-matrix-heatmap", load("mac"), out_path=str(OUT / "_hdet_a.html"))
b = builder.render("mac-matrix-heatmap", load("mac"), out_path=str(OUT / "_hdet_b.html"))
assert Path(a["html_path"]).read_bytes() == Path(b["html_path"]).read_bytes()
print("determinism OK")

print("PHASEH SMOKE OK")
