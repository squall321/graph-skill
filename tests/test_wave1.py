"""Wave-1 regression — pdf-kde / ridgeline / spectrogram / scatter-matrix + kde/STFT postprocess."""
import json
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate
from graph_skill.postprocess import spectral, stats

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"
TYPES = {"pdf-kde": ("kde", "xy-core"), "ridgeline": ("ridge", "xy-core"),
         "spectrogram": ("spectro", "field-core"), "scatter-matrix": ("splom", "review-matrix")}


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_taxonomy_still_complete():
    assert taxonomy.coverage(catalog.known_types())["ok"]


def test_registered():
    for t, (_, eng) in TYPES.items():
        assert catalog.resolve_type(t).engine == eng


def test_validate_render_lint():
    for t, (fx, _) in TYPES.items():
        assert validate.check(t, _load(fx))["ok"], t
        assert builder.render(t, _load(fx), out_path=str(OUT / f"{t}.html"))["lint"]["ok"], t


# ---- postprocess numerics ----
def test_kde_integrates_to_one():
    xs, dens = stats.kde([1, 2, 2, 3, 3, 3, 4, 4, 5], n=200)
    area = sum((xs[i + 1] - xs[i]) * (dens[i] + dens[i + 1]) / 2 for i in range(len(xs) - 1))
    assert 0.9 < area < 1.1 and min(dens) >= 0     # density ≈ integrates to 1, non-negative


def test_spectrogram_dims_and_peak_tracks_chirp():
    import math
    fs, n = 200, 256
    sig = [math.sin(2 * math.pi * (10 + 50 * (i / n)) * (i / fs)) for i in range(n)]
    times, freqs, z = spectral.spectrogram(sig, fs, nperseg=64, overlap=0.5)
    assert len(z) == len(freqs) and all(len(row) == len(times) for row in z)
    # dominant freq should rise from first column to last (chirp 10→60 Hz)
    pk0 = max(range(len(freqs)), key=lambda k: z[k][0])
    pk1 = max(range(len(freqs)), key=lambda k: z[k][-1])
    assert freqs[pk1] > freqs[pk0]


# ---- output wiring ----
def test_ridgeline_offsets_groups():
    h = Path(builder.render("ridgeline", _load("ridge"), out_path=str(OUT / "ridgeline.html"))["html_path"]).read_text(encoding="utf-8")
    assert "Lot A" in h and "Lot C" in h


def test_splom_embeds_correlation_scatter():
    h = Path(builder.render("scatter-matrix", _load("splom"), out_path=str(OUT / "scatter-matrix.html"))["html_path"]).read_text(encoding="utf-8")
    assert "review-matrix" in h and "xy-core" in h and "regression-fit" in h   # off-diagonal cells


# ---- gating ----
def test_gating():
    assert not validate.check("spectrogram", {"signal": [1, 2, 3, 4, 5, 6]})["ok"]          # no fs
    assert not validate.check("scatter-matrix", {"variables": {"A": [1, 2, 3]}})["ok"]       # <2 vars
    assert not validate.check("pdf-kde", {"values": [1, 2, 3]})["ok"]                        # no axes.x unit
    assert not validate.check("ridgeline", {"groups": [{"label": "a", "values": [1, 2]}], "axes": {"x": {"label": "x", "unit": ""}}})["ok"]  # 1 group


def test_determinism():
    a = builder.render("spectrogram", _load("spectro"), out_path=str(OUT / "_w1a.html"))
    b = builder.render("spectrogram", _load("spectro"), out_path=str(OUT / "_w1b.html"))
    assert Path(a["html_path"]).read_bytes() == Path(b["html_path"]).read_bytes()
