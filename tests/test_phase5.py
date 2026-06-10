"""Phase (5) regression tests — filter-tuner (FFT filter correctness + render + fs gate)."""
import json
from pathlib import Path

from graph_skill import builder, catalog, validate
from graph_skill.postprocess import spectral

FIX = Path(__file__).parent / "fixtures"


def load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def _amp_at(fr, a, f0):
    best, bd = 0.0, 1e9
    for f, v in zip(fr, a):
        if abs(f - f0) < bd:
            bd, best = abs(f - f0), v
    return best


def test_filter_type_registered():
    assert "filter-tuner" in catalog.known_types()


def test_lowpass_keeps_low_removes_high():
    y = [d[1] for d in load("filter_signal")["series"][0]["data"]]
    fr, ao = spectral.amp_spectrum(y, 1000.0)
    _, af = spectral.amp_spectrum(spectral.fft_filter(y, 1000.0, "low", 80.0), 1000.0)
    assert _amp_at(fr, af, 30) > 0.8 * _amp_at(fr, ao, 30)
    assert _amp_at(fr, af, 180) < 0.1 * _amp_at(fr, ao, 180)


def test_highpass_keeps_high_removes_low():
    y = [d[1] for d in load("filter_signal")["series"][0]["data"]]
    fr, ao = spectral.amp_spectrum(y, 1000.0)
    _, ah = spectral.amp_spectrum(spectral.fft_filter(y, 1000.0, "high", 80.0), 1000.0)
    assert _amp_at(fr, ah, 30) < 0.1 * _amp_at(fr, ao, 30)
    assert _amp_at(fr, ah, 180) > 0.8 * _amp_at(fr, ao, 180)


def test_fft_filter_preserves_length():
    assert len(spectral.fft_filter([1, 2, 3, 4, 5, 6, 7], 100.0, "low", 10.0)) == 7


def test_filter_render_self_contained(tmp_path):
    res = builder.render("filter-tuner", load("filter_signal"), out_path=str(tmp_path / "f.html"))
    html = (tmp_path / "f.html").read_text(encoding="utf-8")
    assert res["lint"]["ok"] and '["filter-panel"]' in html
    assert '"original"' in html and '"filtered"' in html and '"Frequency"' in html


def test_filter_fs_gate():
    p = load("filter_signal")
    p.pop("params")
    v = validate.check("filter-tuner", p)
    assert not v["ok"] and any(m["field"] == "params.fs" for m in v["missing"])


def test_filter_deterministic():
    p = load("filter_signal")
    assert builder.render("filter-tuner", p)["html"] == builder.render("filter-tuner", p)["html"]
