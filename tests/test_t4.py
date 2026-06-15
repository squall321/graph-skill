"""T2 표준 보고 그래프 배치 C (9종) — risk-matrix/friction-wear/fan-pump/tq-pinch/jr-curve/
load-transient/mott-schottky/compressor-map/harmonic-spur.
Locks: 등록·render·lint, 수치 self-check, 게이트(NEVER-invent), 결정성."""
import json
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate
from graph_skill.postprocess import domain_t4 as t4
from graph_skill.recipes import REGISTRY

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"
TYPES = {"risk-matrix": "riskmatrix", "friction-wear-curve": "frictionwear",
         "fan-pump-operating-point": "fanpump", "tq-pinch-diagram": "tqpinch", "jr-curve": "jrcurve",
         "load-transient-response": "loadtransient", "mott-schottky-cv": "mottschottky",
         "compressor-map": "compmap", "harmonic-spur-table": "harmonspur"}


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_registration_render():
    cov = taxonomy.coverage(catalog.known_types())
    assert cov["ok"], cov["bad_category"]
    for t, fx in TYPES.items():
        assert t in REGISTRY, t
        p = _load(fx)
        assert validate.check(t, p)["ok"], t
        assert builder.render(t, p, out_path=str(OUT / f"{t}.html"))["lint"]["ok"], t


def test_curve_intersection():
    p = t4.curve_intersection([(0, 0), (2, 2)], [(0, 2), (2, 0)])   # y=x ∩ y=2−x → (1,1)
    assert p is not None and abs(p[0] - 1) < 1e-9 and abs(p[1] - 1) < 1e-9
    assert t4.curve_intersection([(0, 0), (1, 1)], [(0, 5), (1, 6)]) is None  # parallel-ish, no cross


def test_jr_fit_and_composite():
    r = t4.jr_curve_fit([1, 2, 4], [2, 8, 32], 350)    # J = 2·Δa²
    assert abs(r["m"] - 2) < 1e-9 and abs(r["C"] - 2) < 1e-9 and r["blunting_slope"] == 700
    cc = t4.composite_curve([{"side": "hot", "T_in": 100, "T_out": 50, "mcp": 2}], "hot")
    assert cc[-1][0] == 100 and cc[0][1] == 50   # H = 2·(100−50)=100, base T 50


def test_transient_and_mott():
    m = t4.transient_metrics([0, 1, 2], [3.3, 3.5, 3.3], 3.3, 3)
    assert abs(m["overshoot_pct"] - (0.2 / 3.3 * 100)) < 1e-9 and m["recovery_t"] == 1
    ms = t4.mott_schottky([0, 1], [1.0, 1 / (2 ** 0.5)], 0.01, 11.9)   # 1/C² = [1,2] → slope 1, V_fb −1
    assert abs(ms["v_fb"] + 1) < 1e-9 and ms["n_d"] is not None


def test_harmonic_peaks():
    pk = t4.harmonic_peaks([100, 200, 300], [-10, -40, -30], 100, 3)
    assert len(pk) == 3 and pk[0]["n"] == 1
    assert abs(pk[1]["dbc"] - (-30)) < 1e-9      # 2f0: −40 − (−10)


def test_gating():
    assert not validate.check("risk-matrix", {})["ok"]
    assert not validate.check("fan-pump-operating-point", {"curves": [{"name": "a", "data": [[0, 1], [1, 2]]}]})["ok"]  # no y unit
    assert not validate.check("jr-curve", {"data": [[0.1, 80], [0.3, 180], [0.6, 290]]})["ok"]                 # no sigma_y
    assert not validate.check("mott-schottky-cv", {"data": [[0, 1e-9], [1, 1e-9], [2, 1e-9]]})["ok"]           # no params
    assert not validate.check("harmonic-spur-table", {"spectrum": [[1, -10], [2, -40]]})["ok"]                 # no f0


def test_determinism():
    for t, fx in TYPES.items():
        p = _load(fx)
        a = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}A.html"))["html_path"]).read_bytes()
        b = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}B.html"))["html_path"]).read_bytes()
        assert a == b, t
        (OUT / f"_{fx}A.html").unlink(missing_ok=True)
        (OUT / f"_{fx}B.html").unlink(missing_ok=True)
