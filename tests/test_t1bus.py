"""T1 business/report-genre charts — candlestick-ohlc / slopegraph / dumbbell-plot /
diverging-likert-bar / funnel-conversion-chart. Locks: registration, render/lint, glyph
pluginConfig geometry, NEVER-invent gates, determinism."""
import json
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate
from graph_skill.recipes import REGISTRY

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"

CASES = [
    ("candlestick-ohlc", "candlestick"),
    ("slopegraph", "slopegraph"),
    ("dumbbell-plot", "dumbbell"),
    ("diverging-likert-bar", "diverging_likert"),
    ("funnel-conversion-chart", "funnel"),
]


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def _norm(t, fx):
    return REGISTRY[t].normalize(_load(fx), catalog.resolve_type(t))


def test_registration_render():
    cov = taxonomy.coverage(catalog.known_types())
    assert cov["ok"], cov.get("bad_category")
    for t, fx in CASES:
        assert t in REGISTRY, t
        p = _load(fx)
        assert validate.check(t, p)["ok"], t
        r = builder.render(t, p, out_path=str(OUT / f"{t}.html"))
        assert r["lint"]["ok"], t
        # declared plugin actually bundled into the self-contained HTML
        for pl in catalog.resolve_type(t).plugins:
            html = Path(r["html_path"]).read_text(encoding="utf-8")
            assert f'"xy-core"]["{pl}"]' in html or f'"xy-core"].{pl} ' in html, (t, pl)


def test_candlestick_glyphs():
    out = _norm("candlestick-ohlc", "candlestick")
    bars = out["options"]["pluginConfig"]["ohlc"]["bars"]
    assert len(bars) == 8
    assert bars[0]["c"] >= bars[0]["o"]          # W1 rising (100 -> 103.1)
    assert bars[2]["c"] < bars[2]["o"]           # W3 falling (102 -> 97.2)
    assert all(b["l"] <= min(b["o"], b["c"]) and b["h"] >= max(b["o"], b["c"]) for b in bars)
    assert out["assets"]["series"][0]["style"] == "none"   # autoscale carrier only
    assert out["options"]["axes"]["x"]["categories"][0] == "W1"


def test_slopegraph_visible_series():
    out = _norm("slopegraph", "slopegraph")
    sers = out["assets"]["series"]
    assert len(sers) == 5 and all(s["style"] == "line+markers" for s in sers)   # real visible lines
    assert all(s["x"] == [0, 1] for s in sers)
    items = out["options"]["pluginConfig"]["slopegraph"]["items"]
    assert len(items) == 5 and items[0]["color"] == sers[0]["color"]            # label color == line color


def test_dumbbell_rows():
    out = _norm("dumbbell-plot", "dumbbell")
    cfg = out["options"]["pluginConfig"]["dumbbell"]
    assert out["options"]["hideAxes"] is True
    assert len(cfg["rows"]) == 6
    assert cfg["rows"][0]["y"] == 5 and cfg["rows"][0]["label"] == "로그인"     # first category at top
    assert cfg["aName"] == "현행" and cfg["bName"] == "목표"
    assert cfg["aColor"] != cfg["bColor"]
    assert out["assets"]["series"][0]["style"] == "none"


def test_diverging_straddles_zero():
    out = _norm("diverging-likert-bar", "diverging_likert")
    cfg = out["options"]["pluginConfig"]["diverging"]
    assert out["options"]["hideAxes"] is True
    assert len(cfg["responses"]) == 5 and len(cfg["colors"]) == 5
    for cat in cfg["cats"]:
        segs = cat["segs"]
        assert min(s["base"] for s in segs) < 0 < max(s["top"] for s in segs)   # bar spans the zero baseline
        neutral = next(s for s in segs if s["ci"] == 2)                          # middle response straddles 0
        assert neutral["base"] < 0 < neutral["top"]


def test_funnel_conversion():
    out = _norm("funnel-conversion-chart", "funnel")
    cfg = out["options"]["pluginConfig"]["funnel"]
    assert out["options"]["hideAxes"] is True
    st = cfg["stages"]
    assert len(st) == 5 and cfg["maxValue"] == 12000
    assert st[0]["i"] == 4 and st[0]["label"] == "방문"                          # first stage at top
    assert abs(st[0]["pctFirst"] - 100.0) < 1e-9 and abs(st[0]["pctPrev"] - 100.0) < 1e-9
    assert abs(st[1]["pctFirst"] - 5200 / 12000 * 100) < 1e-6                    # vs first
    assert abs(st[2]["pctPrev"] - 3900 / 5200 * 100) < 1e-6                      # vs previous


def test_gates_never_invent():
    # candlestick: needs value unit
    assert not validate.check("candlestick-ohlc",
                              {"periods": ["a"], "ohlc": [[1, 2, 0, 1.5]]})["ok"]
    # slopegraph: needs two positions + y unit
    assert not validate.check("slopegraph",
                              {"items": [{"name": "a", "left": 1, "right": 2},
                                         {"name": "b", "left": 2, "right": 1}],
                               "axes": {"y": {"label": "v", "unit": "%"}}})["ok"]   # no positions
    # dumbbell: needs exactly 2 series + x unit
    yx = {"x": {"label": "v", "unit": "ms"}}
    assert not validate.check("dumbbell-plot",
                              {"categories": ["a"], "axes": yx,
                               "series": [{"name": "s", "values": [1]}]})["ok"]     # only 1 series
    assert not validate.check("dumbbell-plot",
                              {"categories": ["a"],
                               "series": [{"name": "s", "values": [1]}, {"name": "t", "values": [2]}]})["ok"]  # no x unit
    # diverging: needs basis declared
    assert not validate.check("diverging-likert-bar",
                              {"questions": ["q"], "responses": ["lo", "mid", "hi"],
                               "data": [[1, 2, 3]]})["ok"]                          # no basis
    # funnel: needs value label/unit
    assert not validate.check("funnel-conversion-chart",
                              {"stages": [{"label": "a", "value": 10}, {"label": "b", "value": 5}]})["ok"]


def test_determinism():
    for t, fx in CASES:
        p = _load(fx)
        a = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}A.html"))["html_path"]).read_bytes()
        b = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}B.html"))["html_path"]).read_bytes()
        assert a == b, t
        (OUT / f"_{fx}A.html").unlink(missing_ok=True)
        (OUT / f"_{fx}B.html").unlink(missing_ok=True)
