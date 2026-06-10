"""Phase (D) smoke: equipment raw ingest + resample + smoothing (numeric correctness + e2e)."""
import math
from pathlib import Path

from graph_skill import builder, tools
from graph_skill.postprocess import ingest, resample, smoothing

OUT = Path(__file__).resolve().parent.parent / "graph-out"

# --- ingest CSV ---
csv = "time,force\n# comment\n0,0\n0.5,12\n1.0,oops\n1.5,9\n"
got = ingest.parse_csv(csv)
print("ingest names:", got["names"], "rows:", got["rows"])
assert got["names"] == ["time", "force"] and got["rows"] == 4
assert got["columns"]["force"][2] is None  # 'oops' -> None

# --- resample non-uniform -> uniform ---
x = [0, 1, 3, 4, 7]
y = list(x)  # linear so interpolation is exact
assert not resample.is_uniform(x)
gx, gy = resample.resample_uniform(x, y, n=8)
assert resample.is_uniform(gx)
assert max(abs(gy[i] - gx[i]) for i in range(len(gx))) < 1e-9   # y=x preserved
print("resample uniform:", resample.is_uniform(gx), "n:", len(gx))

# --- savgol reduces noise, preserves shape ---
clean = [math.sin(2 * math.pi * i / 50) for i in range(200)]
noisy = [clean[i] + (0.3 if i % 2 else -0.3) for i in range(200)]  # alternating noise
sm = smoothing.savgol(noisy, 11, 2)
rmse = lambda a, b: (sum((a[i] - b[i]) ** 2 for i in range(len(a))) / len(a)) ** 0.5
print("rmse raw:", round(rmse(noisy, clean), 3), "-> savgol:", round(rmse(sm, clean), 3))
assert rmse(sm, clean) < 0.5 * rmse(noisy, clean)
# moving average also smooths
assert rmse(smoothing.moving_average(noisy, 9), clean) < rmse(noisy, clean)

# --- tools layer + end-to-end (ingest -> resample -> smooth -> render) ---
cols = tools.ingest_csv("t,a\n" + "\n".join(f"{i*0.5},{math.sin(i*0.3)+ (0.2 if i%2 else -0.2):.4f}" for i in range(60)))
series = [{"name": "accel", "data": [[cols["columns"]["t"][i], cols["columns"]["a"][i]] for i in range(len(cols["columns"]["t"]))]}]
rs = tools.resample(series, n=120)
print("uniform_input:", rs["uniform_input"])
sm2 = tools.smooth(rs["series"], method="savgol", window=9, polyorder=2)
payload = {"axes": {"x": {"label": "Time", "unit": "s"}, "y": {"label": "Accel", "unit": "g"}},
           "series": [{"name": "raw", "data": series[0]["data"]}, {"name": "smoothed", "data": sm2["series"][0]["data"]}],
           "title": "Raw vs resampled+smoothed"}
res = builder.render("base-xy", payload, out_path=str(OUT / "ingest_demo.html"))
assert res["lint"]["ok"]
print("e2e render lint:", res["lint"]["ok"], "bytes:", res["bytes"])

# tools registered
assert {"ingest_csv", "resample", "smooth"} <= {t["name"] for t in tools.TOOLS}
assert {"ingest_csv", "resample", "smooth"} <= set(tools.DISPATCH)

print("PHASE9 SMOKE OK")
