"""마지막 정형 그래프 2종 — milestone-trend(MTA) + reliability-demo-sprt(PRST).
Locks: 등록·render·lint, PRST 경계 수치 self-check, 게이트, 결정성."""
import json
import math
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate
from graph_skill.postprocess import domain_t6 as t6
from graph_skill.recipes import REGISTRY

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"
TYPES = {"milestone-trend": "milestonetrend", "reliability-demo-sprt": "sprt"}


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


def test_sprt_bounds():
    b = t6.sprt_bounds(0.1, 0.1, 1000, 500)
    assert abs(b["A"] - 9.0) < 1e-9 and abs(b["B"] - (0.1 / 0.9)) < 1e-9        # (1−β)/α, β/(1−α)
    assert abs(b["slope"] - ((1 / 500 - 1 / 1000) / math.log(2))) < 1e-12
    assert b["accept_intercept"] < 0 < b["reject_intercept"]                     # accept below, reject above
    # decision from a clearly-rejecting path (many failures early)
    assert t6.sprt_decision([[100, 20]], b) == "reject"
    assert t6.sprt_decision([[5000, 0]], b) == "accept"                          # long run, no failures


def test_milestone_trend_shape():
    out = REGISTRY["milestone-trend"].normalize(_load("milestonetrend"), catalog.resolve_type("milestone-trend"))
    ser = out["assets"]["series"]
    assert any(s["name"] == "완료선 (y=x)" for s in ser)                          # diagonal completion line
    assert sum(1 for s in ser if s.get("style") == "line+markers") == 3          # 3 milestones


def test_gating():
    assert not validate.check("milestone-trend", {"report_dates": ["2026-01-01"], "milestones": []})["ok"]
    assert not validate.check("milestone-trend", {"report_dates": ["2026-01-01", "2026-02-01"],
                                                  "milestones": [{"name": "a", "forecasts": ["2026-03-01"]}]})["ok"]  # length mismatch
    assert not validate.check("reliability-demo-sprt", {"alpha": 0.1, "beta": 0.1})["ok"]   # no theta/discrimination


def test_determinism():
    for t, fx in TYPES.items():
        p = _load(fx)
        a = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}A.html"))["html_path"]).read_bytes()
        b = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}B.html"))["html_path"]).read_bytes()
        assert a == b, t
        (OUT / f"_{fx}A.html").unlink(missing_ok=True)
        (OUT / f"_{fx}B.html").unlink(missing_ok=True)
