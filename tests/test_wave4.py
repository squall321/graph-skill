"""Wave-4 regression — pole-zero-map / cusum-chart / goodman-haigh / psd-welch (xy-core reuse)."""
import json
import math
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate
from graph_skill.postprocess import spectral

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"
TYPES = {"pole-zero-map": "polezero", "cusum-chart": "cusum",
         "goodman-haigh": "goodman", "psd-welch": "psd"}


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_taxonomy_complete_and_count():
    assert taxonomy.coverage(catalog.known_types())["ok"]
    assert len(catalog.known_types()) >= 62


def test_validate_render_lint():
    for t, fx in TYPES.items():
        assert validate.check(t, _load(fx))["ok"], t
        assert builder.render(t, _load(fx), out_path=str(OUT / f"{t}.html"))["lint"]["ok"], t


def test_pole_zero_equal_aspect_and_markers():
    h = Path(builder.render("pole-zero-map", _load("polezero"), out_path=str(OUT / "pole-zero-map.html"))["html_path"]).read_text(encoding="utf-8")
    assert '"equalAspect":true' in h and "unit-circle" in h and "pole" in h and "zero" in h


def test_cusum_decision_lines():
    h = Path(builder.render("cusum-chart", _load("cusum"), out_path=str(OUT / "cusum-chart.html"))["html_path"]).read_text(encoding="utf-8")
    assert "threshold-lines" in h and "+H" in h


def test_goodman_line_and_points():
    from graph_skill.recipes import REGISTRY
    out = REGISTRY["goodman-haigh"].normalize(_load("goodman"), catalog.resolve_type("goodman-haigh"))
    ser = out["assets"]["series"]
    line = next(s for s in ser if "Goodman" in s["name"])
    assert line["x"] == [0, 500] and line["y"] == [200, 0]      # (0,Se)→(Su,0)


def test_welch_psd_peaks_at_tone():
    fs, n = 400, 512
    sig = [math.sin(2 * math.pi * 30 * i / fs) for i in range(n)]
    f, psd = spectral.welch(sig, fs, 128)
    pk = max(range(len(psd)), key=lambda k: psd[k])
    assert abs(f[pk] - 30) <= fs / 128                          # dominant bin ≈ 30 Hz
    assert len(f) == len(psd) and min(psd) >= 0


def test_psd_is_log_log():
    h = Path(builder.render("psd-welch", _load("psd"), out_path=str(OUT / "psd-welch.html"))["html_path"]).read_text(encoding="utf-8")
    assert h.count('"log":true') >= 2


def test_gating():
    assert not validate.check("pole-zero-map", {})["ok"]
    assert not validate.check("goodman-haigh", {"points": [{"mean": 1, "alt": 2}]})["ok"]    # no Su/Se
    assert not validate.check("psd-welch", {"signal": [1, 2, 3, 4, 5, 6]})["ok"]             # no fs
    assert not validate.check("cusum-chart", {})["ok"]                                        # no values


def test_determinism():
    a = builder.render("psd-welch", _load("psd"), out_path=str(OUT / "_w4a.html"))
    b = builder.render("psd-welch", _load("psd"), out_path=str(OUT / "_w4b.html"))
    assert Path(a["html_path"]).read_bytes() == Path(b["html_path"]).read_bytes()
