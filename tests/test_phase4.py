"""Phase (4) regression tests — fft-spectrum (pure-Python FFT + time/freq toggle + fs gate)."""
import json
from pathlib import Path

import pytest

from graph_skill import builder, catalog, validate
from graph_skill.postprocess import spectral

FIX = Path(__file__).parent / "fixtures"


def load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_fft_type_registered():
    assert "fft-spectrum" in catalog.known_types()


def test_fft_peaks_correct():
    p = load("signal")
    y = [d[1] for d in p["series"][0]["data"]]
    f, a = spectral.fft_onesided(y, 1000.0)
    pk = [round(ff, 1) for ff, _ in spectral.peaks(f, a, 3)]
    assert any(abs(x - 50) < 3 for x in pk), pk
    assert any(abs(x - 120) < 3 for x in pk), pk


def test_fft_length_and_dc():
    f, a = spectral.fft_onesided([0, 1, 0, -1, 0, 1, 0, -1], 8.0)
    assert len(f) == len(a) and f[0] == 0.0


def test_fft_guards():
    with pytest.raises(ValueError):
        spectral.fft_onesided([1.0], 1000.0)
    with pytest.raises(ValueError):
        spectral.fft_onesided([1, 2, 3, 4], 0)


def test_fft_render_carries_both_domains(tmp_path):
    res = builder.render("fft-spectrum", load("signal"), out_path=str(tmp_path / "f.html"))
    html = (tmp_path / "f.html").read_text(encoding="utf-8")
    assert res["lint"]["ok"]
    assert '["domain-toggle"]' in html and '"Frequency"' in html and "Time" in html
    assert '"start":"freq"' in html.replace(" ", "")


def test_fft_fs_gate():
    p = load("signal")
    p.pop("params")
    v = validate.check("fft-spectrum", p)
    assert not v["ok"] and any(m["field"] == "params.fs" for m in v["missing"])


def test_fft_deterministic():
    p = load("signal")
    assert builder.render("fft-spectrum", p)["html"] == builder.render("fft-spectrum", p)["html"]
