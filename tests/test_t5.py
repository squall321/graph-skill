"""엔진-오버레이 정형 그래프 5종 — eye-mask-compliance/efficiency-map/rpm-order-map/
psychrometric-chart/distribution-fit-compare.
Locks: 등록·render·lint, 수치 self-check, field-core 오버레이, 게이트, 결정성."""
import json
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate
from graph_skill.postprocess import domain_t5 as t5
from graph_skill.recipes import REGISTRY

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"
TYPES = {"eye-mask-compliance": "eyemask", "efficiency-map": "effmap", "rpm-order-map": "rpmorder",
         "psychrometric-chart": "psychro", "distribution-fit-compare": "distfit"}


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


def test_point_in_polygon_and_hits():
    sq = [[-1, -1], [1, -1], [1, 1], [-1, 1]]
    assert t5.point_in_polygon(0, 0, sq) is True
    assert t5.point_in_polygon(2, 2, sq) is False
    # one hit cell inside the square
    h = t5.eye_mask_hits([0, 5], [0, 5], [[3, 0], [0, 7]], [sq])
    assert h["hits"] == 3 and h["total"] == 10            # (0,0)=3 inside, (5,0)/(0,5)/(5,5) outside


def test_overlay_in_rendered_artifact():
    # field-core overlay assets actually reach the artifact's config
    out = REGISTRY["efficiency-map"].normalize(_load("effmap"), catalog.resolve_type("efficiency-map"))
    ov = out["assets"]["field"]["overlays"]
    assert ov["curves"] and ov["markers"]                 # envelope curve + operating points
    html = (OUT / "efficiency-map.html").read_text(encoding="utf-8") if (OUT / "efficiency-map.html").exists() else \
        Path(builder.render("efficiency-map", _load("effmap"), out_path=str(OUT / "efficiency-map.html"))["html_path"]).read_text(encoding="utf-8")
    assert "overlays" in html


def test_psychro_and_norm():
    assert abs(t5.p_ws(0) - 611.0) < 5                    # saturation pressure at 0°C ≈ 611 Pa
    assert abs(t5.norm_ppf(0.5)) < 1e-6 and abs(t5.norm_ppf(0.975) - 1.96) < 0.01
    w = t5.humidity_ratio(20, 0.5) * 1000.0               # ~7.2 g/kg at 20°C/50%RH
    assert 6 < w < 9


def test_prob_plot_ranks_normal():
    # symmetric ~normal data → normal/lognormal fit better than exponential
    vals = [10, 12, 11, 13, 9, 14, 10, 12, 11, 13, 8, 15]
    rn = t5.prob_plot(vals, "normal")["r2"]
    re = t5.prob_plot(vals, "exponential")["r2"]
    assert rn > 0.9 and rn >= re


def test_gating():
    assert not validate.check("eye-mask-compliance", {"signal": [1, 2, 3]})["ok"]              # no sps
    assert not validate.check("efficiency-map", {"envelope": [[0, 0]]})["ok"]                  # no field
    assert not validate.check("rpm-order-map", {"orders": [1, 2]})["ok"]                       # no field
    assert not validate.check("distribution-fit-compare", {"values": [1, 2]})["ok"]           # <3


def test_determinism():
    for t, fx in TYPES.items():
        p = _load(fx)
        a = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}A.html"))["html_path"]).read_bytes()
        b = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}B.html"))["html_path"]).read_bytes()
        assert a == b, t
        (OUT / f"_{fx}A.html").unlink(missing_ok=True)
        (OUT / f"_{fx}B.html").unlink(missing_ok=True)
