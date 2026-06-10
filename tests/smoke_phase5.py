"""Phase (5) smoke: filter-tuner — FFT filter correctness (lowpass removes high freq) + render."""
import json
from pathlib import Path

from graph_skill import builder, catalog, validate
from graph_skill.postprocess import spectral

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "graph-out"
payload = json.loads((ROOT / "fixtures" / "filter_signal.json").read_text(encoding="utf-8"))
y = [d[1] for d in payload["series"][0]["data"]]
fs = 1000.0


def amp_at(freqs, amp, f0):
    best, bd = 0.0, 1e9
    for f, a in zip(freqs, amp):
        if abs(f - f0) < bd:
            bd, best = abs(f - f0), a
    return best


print("types:", "filter-tuner" in catalog.known_types())
assert "filter-tuner" in catalog.known_types()

# --- lowpass fc=80 keeps 30 Hz, removes 180 Hz ---
fr, a_orig = spectral.amp_spectrum(y, fs)
filt = spectral.fft_filter(y, fs, "low", 80.0)
_, a_filt = spectral.amp_spectrum(filt, fs)
o30, f30 = amp_at(fr, a_orig, 30), amp_at(fr, a_filt, 30)
o180, f180 = amp_at(fr, a_orig, 180), amp_at(fr, a_filt, 180)
print(f"30Hz: {o30:.3f} -> {f30:.3f}   180Hz: {o180:.3f} -> {f180:.3f}")
assert f30 > 0.8 * o30, "lowpass should keep 30 Hz"
assert f180 < 0.1 * o180, "lowpass should remove 180 Hz"

# highpass fc=80 does the opposite
hp = spectral.fft_filter(y, fs, "high", 80.0)
_, a_hp = spectral.amp_spectrum(hp, fs)
assert amp_at(fr, a_hp, 30) < 0.1 * o30 and amp_at(fr, a_hp, 180) > 0.8 * o180

# --- render: filter-panel bundled, both series present, starts in freq ---
v = validate.check("filter-tuner", payload)
assert v["ok"], v["missing"]
r = builder.render("filter-tuner", payload, out_path=str(OUT / "filter.html"))
html = Path(r["html_path"]).read_text(encoding="utf-8")
print("bytes:", r["bytes"], "lint:", r["lint"]["ok"])
assert r["lint"]["ok"]
assert 'GraphPlugins["xy-core"]["filter-panel"]' in html
assert '"filter-panel"' in html and '"original"' in html and '"filtered"' in html
assert '"Frequency"' in html

# --- fs gate ---
bad = {"series": payload["series"], "axes": payload["axes"], "params": {"filter": "low"}}
vb = validate.check("filter-tuner", bad)
print("no fs ok:", vb["ok"], "missing:", [m["field"] for m in vb["missing"]])
assert not vb["ok"] and any(m["field"] == "params.fs" for m in vb["missing"])

# determinism
assert builder.render("filter-tuner", payload)["html"] == builder.render("filter-tuner", payload)["html"]

print("PHASE5 SMOKE OK")
