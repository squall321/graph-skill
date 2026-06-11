"""확장 7종 + s2p — cie/octave/tornado/motor-tn/vswr/dma/test-report + ingest_s2p.
Locks: CIE 궤적 공식 앵커값, 옥타브 에너지합, 토네이도 정렬, VSWR 변환(-9.54dB→2.0),
DMA Tg 마커, test-report 멀티엔진 번들, s2p 파서(MA/DB/RI), 게이트, 결정성."""
import json
import math
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, tools, validate
from graph_skill.postprocess import photometry as ph
from graph_skill.postprocess import touchstone as ts
from graph_skill.recipes import REGISTRY

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"
TYPES = {"cie-chromaticity": "cie", "octave-band": "octave", "tornado-chart": "tornado",
         "motor-tn-curve": "motortn", "vswr-curve": "vswr", "dma-curve": "dma",
         "test-report": "testreport"}


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_registration_render():
    cov = taxonomy.coverage(catalog.known_types())
    assert cov["ok"], cov["bad_category"]
    for t, fxn in TYPES.items():
        assert t in REGISTRY
        p = _load(fxn)
        assert validate.check(t, p)["ok"], t
        assert builder.render(t, p, out_path=str(OUT / f"{t}.html"))["lint"]["ok"], t


def test_cie_locus_official_anchors():
    # 공식 CIE 018:2019 Table 6 앵커 — 절대 흔들리면 안 됨
    loc = dict(zip(range(380, 701, 5), ph.spectral_locus()))
    assert abs(loc[520][0] - 0.0743) < 1e-4 and abs(loc[520][1] - 0.8338) < 1e-4
    assert abs(loc[700][0] - 0.7347) < 1e-4 and abs(loc[700][1] - 0.2653) < 1e-4
    assert abs(loc[480][0] - 0.0913) < 1e-4
    out = REGISTRY["cie-chromaticity"].normalize(_load("cie"), catalog.resolve_type("cie-chromaticity"))
    assert out["options"]["equalAspect"] is True
    assert "면적비" in out["options"]["title"]


def test_octave_energy_sum():
    # 동일 레벨 2개 빈이 같은 밴드 → +3dB
    bands = ph.spectrum_to_third_octave([995, 1005], [70, 70])
    assert len(bands) == 1 and abs(bands[0][1] - 73.0103) < 0.01


def test_tornado_sorted_by_span():
    out = REGISTRY["tornado-chart"].normalize(_load("tornado"), catalog.resolve_type("tornado-chart"))
    rows = out["options"]["pluginConfig"]["tornado"]["rows"]
    spans = [abs(r["high"] - r["low"]) for r in rows]
    assert spans == sorted(spans, reverse=True)
    assert out["options"]["hideAxes"] is True


def test_vswr_conversion():
    out = REGISTRY["vswr-curve"].normalize(
        {"s11_db": [[1000, -9.542425094393249]], "f_unit": "MHz"}, catalog.resolve_type("vswr-curve"))
    assert abs(out["assets"]["series"][0]["y"][0] - 2.0) < 1e-6


def test_dma_tg_marker():
    out = REGISTRY["dma-curve"].normalize(_load("dma"), catalog.resolve_type("dma-curve"))
    assert "Tg" in out["options"]["title"]
    tg = next(s for s in out["assets"]["series"] if "Tg" in s["name"])
    assert 90 <= tg["x"][0] <= 105                       # fixture peak at ~98°C
    assert out["options"]["axes"]["y"]["log"] is True


def test_test_report_composite():
    html = Path(builder.render("test-report", _load("testreport"),
                               out_path=str(OUT / "test-report.html"))["html_path"]).read_text(encoding="utf-8")
    for needle in ('GraphEngines["review-matrix"]', 'GraphEngines["xy-core"]', 'GraphEngines["gauge-core"]'):
        assert needle in html
    out = REGISTRY["test-report"].normalize(_load("testreport"), catalog.resolve_type("test-report"))
    groups = {it["group"] for it in out["assets"]["items"]}
    assert {"시험 개요", "판정 요약", "시험 결과", "종합 판정"} <= groups


def test_s2p_parser_formats():
    db_text = "# MHz S DB R 50\n1000 -9.542425094393249 45 -1 10 -30 5 -12 20\n"
    p = ts.parse_s2p(db_text)
    assert abs(p["s11_vswr"][0] - 2.0) < 1e-6 and p["z0"] == 50
    ri_text = "# GHz S RI R 75\n1 0.2 0.1 0.5 -0.5 0.01 0 0.1 0.1\n"
    q = ts.parse_s2p(ri_text)
    assert q["z0"] == 75 and abs(q["freq_hz"][0] - 1e9) < 1
    assert abs(abs(complex(0.2, 0.1)) - abs(q["s11"][0])) < 1e-12
    ma_text = "# Hz S MA R 50\n100 0.3333333 0 1 0 0 0 0 0\n"
    m = ts.parse_s2p(ma_text)
    assert abs(m["s11_vswr"][0] - 2.0) < 1e-4
    tool = tools.ingest_s2p(db_text)
    assert tool["n_points"] == 1 and "usage" in tool


def test_gating():
    assert not validate.check("octave-band", {"bands": [[100, 60]]})["ok"]
    assert not validate.check("tornado-chart", {"factors": [{"name": "a", "low": 1, "high": 2},
                                                            {"name": "b", "low": 0, "high": 3}], "unit": ""})["ok"]
    assert not validate.check("dma-curve", {"temp": [0, 10], "e_storage": [100, 90]})["ok"]
    assert not validate.check("motor-tn-curve", {"curves": [{"name": "a", "data": [[0, 1]]}]})["ok"]
    assert not validate.check("test-report", {"info": {"a": "b"},
                                              "margins": [{"label": "x", "value": 1, "max": 2}]})["ok"]
    assert not validate.check("cie-chromaticity", {"gamuts": ["adobe-rgb-unknown"]})["ok"]


def test_determinism():
    for t, fxn in TYPES.items():
        p = _load(fxn)
        a = Path(builder.render(t, p, out_path=str(OUT / f"_{fxn}A.html"))["html_path"]).read_bytes()
        b = Path(builder.render(t, p, out_path=str(OUT / f"_{fxn}B.html"))["html_path"]).read_bytes()
        assert a == b, t
        (OUT / f"_{fxn}A.html").unlink(missing_ok=True)
        (OUT / f"_{fxn}B.html").unlink(missing_ok=True)
