"""T2 표준 보고 그래프 배치 A (11종) — ewma/oc/roc-pr/bathtub/crow-amsaa/mohr/boiling/
gate-charge/immunity/resource-histogram/raci.
Locks: 등록·render·lint, 수치 self-check, 게이트(NEVER-invent), 결정성."""
import json
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate
from graph_skill.postprocess import domain_t2 as t2
from graph_skill.recipes import REGISTRY

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"
TYPES = {"ewma-chart": "ewma", "oc-curve": "oc", "roc-pr-curve": "rocpr",
         "bathtub-curve": "bathtub", "crow-amsaa-growth": "crowamsaa", "mohr-circle": "mohr",
         "boiling-curve": "boiling", "gate-charge-curve": "gatecharge",
         "immunity-level-profile": "immunity", "resource-histogram": "resource_hist",
         "raci-matrix": "raci"}


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


def test_ewma_recursion():
    r = t2.ewma([0, 10], lam=0.5, target=5, sigma=2)
    assert abs(r["z"][0] - 2.5) < 1e-9 and abs(r["z"][1] - 6.25) < 1e-9


def test_oc_curve_monotone():
    r = t2.oc_curve(80, 2)
    assert abs(r["pa"][0] - 1.0) < 1e-12                      # p=0 → always accept
    assert all(r["pa"][i] <= r["pa"][i - 1] + 1e-12 for i in range(1, len(r["pa"])))


def test_roc_auc_perfect():
    r = t2.roc_pr([1, 1, 0, 0], [0.9, 0.8, 0.2, 0.1], "roc")
    assert abs(r["auc"] - 1.0) < 1e-9                          # perfect separation
    bad = t2.roc_pr([1, 0, 1, 0], [0.5, 0.5, 0.5, 0.5], "roc")
    assert bad["auc"] <= r["auc"]


def test_mohr_and_chf_and_hazard():
    m = t2.mohr_circle(120, -40)
    assert abs(m["center"] - 40) < 1e-9 and abs(m["radius"] - 80) < 1e-9
    assert abs(t2.detect_chf([5, 10, 20, 30, 40], [2, 8, 40, 110, 95])["q"] - 110) < 1e-9
    assert abs(t2.weibull_hazard(1.0, 100, 50) - 0.01) < 1e-12  # β=1 → constant 1/η
    assert abs(t2.steady_state([0, 1, 2, 3, 4, 5], [1, 1, 1, 5, 5, 5])["mean"] - 5) < 1e-9


def test_crow_amsaa_growth_flag():
    r = t2.crow_amsaa([10, 30, 75, 140, 260, 430, 700, 1050])  # widening intervals → β<1
    assert r["beta"] > 0 and r["growing"] is True
    assert len(r["cum_mtbf"]) == r["n"] and len(r["inst_mtbf"]) == r["n"]


def test_miller_plateau():
    pl = t2.miller_plateau([0, 3, 6, 10, 16, 22, 28], [0, 1.8, 3.6, 4.4, 4.6, 4.7, 6.2])
    assert pl is not None and pl["qg_total"] == 28 and pl["qgd"] > 0


def test_gating():
    assert not validate.check("ewma-chart", {"values": [1, 2, 3]})["ok"]                  # no y unit
    assert not validate.check("oc-curve", {"n": 80})["ok"]                                 # no c
    assert not validate.check("mohr-circle", {"states": [{"s1": 1, "s3": 0}]})["ok"]       # no unit
    assert not validate.check("resource-histogram", {"periods": ["a"], "resources": [{"name": "x", "hours": [1]}]})["ok"]  # no capacity
    # RACI: a task without exactly one Accountable -> needs_input
    assert not validate.check("raci-matrix", {"tasks": ["t1"], "roles": ["r1"],
                                              "assignments": [{"task": "t1", "role": "r1", "code": "R"}]})["ok"]


def test_determinism():
    for t, fx in TYPES.items():
        p = _load(fx)
        a = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}A.html"))["html_path"]).read_bytes()
        b = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}B.html"))["html_path"]).read_bytes()
        assert a == b, t
        (OUT / f"_{fx}A.html").unlink(missing_ok=True)
        (OUT / f"_{fx}B.html").unlink(missing_ok=True)
