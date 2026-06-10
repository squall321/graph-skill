"""Phase (4) smoke: fft-spectrum — pure-Python FFT correctness + both-domain bundling + fs gate."""
import json
from pathlib import Path

from graph_skill import builder, catalog, validate
from graph_skill.postprocess import spectral

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "graph-out"
payload = json.loads((ROOT / "fixtures" / "signal.json").read_text(encoding="utf-8"))

print("types:", catalog.known_types())
assert "fft-spectrum" in catalog.known_types()

# --- numeric correctness: peaks near 50 and 120 Hz ---
y = [p[1] for p in payload["series"][0]["data"]]
freqs, amp = spectral.fft_onesided(y, 1000.0)
pk = [round(f, 1) for f, a in spectral.peaks(freqs, amp, 3)]
print("detected peaks (Hz):", pk)
assert any(abs(f - 50) < 3 for f in pk), f"50 Hz peak not found: {pk}"
assert any(abs(f - 120) < 3 for f in pk), f"120 Hz peak not found: {pk}"

# --- render: starts in freq domain, carries both domains + peaks ---
v = validate.check("fft-spectrum", payload)
print("validate ok:", v["ok"])
assert v["ok"]
r = builder.render("fft-spectrum", payload, out_path=str(OUT / "fft.html"))
html = Path(r["html_path"]).read_text(encoding="utf-8")
print("bytes:", r["bytes"], "lint:", r["lint"]["ok"])
assert r["lint"]["ok"]
assert 'GraphPlugins["xy-core"]["domain-toggle"]' in html
assert '"domain-toggle"' in html and '"Frequency"' in html and '"start":"freq"' in html.replace(" ", "")
assert "Hz" in html  # peak labels

# --- fs gate: drop fs -> blocked ---
bad = {"series": payload["series"], "axes": payload["axes"]}
vb = validate.check("fft-spectrum", bad)
print("no fs ok:", vb["ok"], "missing:", [m["field"] for m in vb["missing"]])
assert not vb["ok"] and any(m["field"] == "params.fs" for m in vb["missing"])

# determinism
a = builder.render("fft-spectrum", payload)["html"]
b = builder.render("fft-spectrum", payload)["html"]
assert a == b

print("PHASE4 SMOKE OK")
