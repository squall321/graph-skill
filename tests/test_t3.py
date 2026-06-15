"""T2 표준 보고 그래프 배치 B (10종) — phase-noise/soa/uncertainty-budget/tolerance-stackup/
evm/burndown/dqdv/torque-angle/creep/equivalence-tost.
Locks: 등록·render·lint, 수치 self-check, 게이트(NEVER-invent), 결정성."""
import json
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate
from graph_skill.postprocess import domain_t3 as t3
from graph_skill.recipes import REGISTRY

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"
TYPES = {"phase-noise": "phasenoise", "soa-chart": "soa", "uncertainty-budget-chart": "uncertainty",
         "tolerance-stackup-chart": "tolstack", "evm-s-curve": "evm", "burndown-burnup": "burndown",
         "dqdv-curve": "dqdv", "torque-angle-curve": "torqueangle", "creep-curve": "creep",
         "equivalence-tost-plot": "tost"}


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


def test_phase_jitter():
    # L=0 dBc/Hz flat over [0,1] → power 1 → RMS = √(2·1)
    j = t3.phase_jitter([0, 1], [0, 0], 0, 1)
    assert abs(j["rms_rad"] - (2 ** 0.5)) < 1e-9


def test_uncertainty_budget():
    r = t3.uncertainty_budget([{"name": "a", "u": 3}, {"name": "b", "u": 4}], k=2)
    assert abs(r["uc"] - 5) < 1e-9 and abs(r["U"] - 10) < 1e-9
    assert abs(r["percent"][0] - 36) < 1e-9 and abs(r["percent"][1] - 64) < 1e-9


def test_tolerance_stackup():
    r = t3.tolerance_stackup([{"nominal": 10, "tol_plus": 0.05, "tol_minus": -0.05},
                              {"nominal": 5, "tol_plus": 0.03, "tol_minus": -0.03}])
    assert abs(r["nominal"] - 15) < 1e-9 and abs(r["wc"] - 0.08) < 1e-9
    assert abs(r["rss"] - (0.0034 ** 0.5)) < 1e-9


def test_evm_and_risk():
    m = t3.evm_metrics(100, 80, 90, 1000)
    assert abs(m["spi"] - 0.8) < 1e-9 and abs(m["cpi"] - 80 / 90) < 1e-9
    assert abs(m["eac"] - 1000 / (80 / 90)) < 1e-6
    assert t3.risk_zone(5, 5) == "extreme" and t3.risk_zone(1, 1) == "low"


def test_soa_membership():
    args = (0.05, 50, 300, 100)
    assert t3.point_in_soa(20, 10, *args) is True       # inside all 4 limits
    assert t3.point_in_soa(90, 40, *args) is False      # V·I=3600 > Pd 300


def test_creep_and_dqdv():
    c = t3.min_creep_rate([0, 1, 2, 3, 4, 5], [0, 1, 2, 2.1, 2.2, 5])
    assert abs(c["min_rate"] - 0.1) < 1e-9               # secondary stage slope
    d = t3.dqdv([3, 3.5, 4], [0, 2, 3], window=0)
    assert d["v"] == [3.25, 3.75] and abs(d["dqdv"][0] - 4) < 1e-9


def test_gating():
    assert not validate.check("phase-noise", {"offsets": [1], "lf": [-90]})["ok"]
    assert not validate.check("soa-chart", {"points": [{"vds": 1, "id": 1}]})["ok"]                # no device/limits
    assert not validate.check("uncertainty-budget-chart", {"components": [{"name": "a", "u": 1}]})["ok"]  # no unit
    assert not validate.check("tolerance-stackup-chart", {"links": [{"name": "a", "nominal": 1, "tol_plus": 0.1, "tol_minus": -0.1}]})["ok"]  # no unit
    assert not validate.check("evm-s-curve", {"dates": ["a"], "pv": [1], "ev": [1], "ac": [1]})["ok"]  # no bac
    assert not validate.check("equivalence-tost-plot", {"estimates": [{"name": "a", "point": 0, "ci_low": -1, "ci_high": 1}]})["ok"]  # no bounds


def test_determinism():
    for t, fx in TYPES.items():
        p = _load(fx)
        a = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}A.html"))["html_path"]).read_bytes()
        b = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}B.html"))["html_path"]).read_bytes()
        assert a == b, t
        (OUT / f"_{fx}A.html").unlink(missing_ok=True)
        (OUT / f"_{fx}B.html").unlink(missing_ok=True)
