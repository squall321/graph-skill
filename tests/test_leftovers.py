"""stat-card (gauge-core card) / stream-graph (xy-core themeriver) / sunburst (flow-core
drill-down). Locks: registration, render/lint, engine routing, stream centered baseline,
stat delta/spark passthrough, sunburst tree, gating, determinism."""
import hashlib
import json
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate
from graph_skill.recipes import REGISTRY

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"
TYPES = {"stat-card": ("statcard", "gauge-core"), "stream-graph": ("stream", "xy-core"),
         "sunburst": ("sunburst", "flow-core")}


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_registration_and_taxonomy():
    cov = taxonomy.coverage(catalog.known_types())
    assert cov["ok"], cov["bad_category"]
    for t, (_, eng) in TYPES.items():
        assert t in REGISTRY and catalog.resolve_type(t).engine == eng


def test_render_lint():
    for t, (fx, eng) in TYPES.items():
        p = _load(fx)
        assert validate.check(t, p)["ok"], t
        r = builder.render(t, p, out_path=str(OUT / f"{t}.html"))
        assert r["lint"]["ok"], t
        assert f'GraphEngines["{eng}"]' in Path(r["html_path"]).read_text(encoding="utf-8")


def test_stream_centered_baseline_and_bands():
    out = REGISTRY["stream-graph"].normalize(_load("stream"), catalog.resolve_type("stream-graph"))
    sg = out["options"]["pluginConfig"]["streamgraph"]
    assert len(sg["bands"]) == 4 and len(sg["x"]) == 12
    # centered (silhouette): first band lower edge starts below zero
    assert sg["bands"][0]["lo"][0] < 0
    # bands stack: each band's hi equals next band's lo
    for k in range(len(sg["bands"]) - 1):
        assert sg["bands"][k]["hi"] == sg["bands"][k + 1]["lo"]


def test_statcard_delta_spark():
    out = REGISTRY["stat-card"].normalize(_load("statcard"), catalog.resolve_type("stat-card"))
    assert out["assets"]["kind"] == "card"
    it0 = out["assets"]["items"][0]
    assert "delta" in it0 and isinstance(it0["spark"], list) and len(it0["spark"]) > 1


def test_sunburst_tree_passthrough():
    out = REGISTRY["sunburst"].normalize(_load("sunburst"), catalog.resolve_type("sunburst"))
    assert out["assets"]["kind"] == "sunburst"
    tree = out["assets"]["tree"]
    assert tree["name"] == "전체" and len(tree["children"]) == 3
    # nested leaves keep value
    media = next(c for c in tree["children"][1]["children"] if c["name"] == "미디어")
    assert any(leaf.get("value") for leaf in media["children"])


def test_log_axis_key_reaches_engine():
    # 회귀: _axis 가 죽은 `scale` 키 대신 엔진이 읽는 `log` 불리언을 방출해야 한다.
    # (엔진은 axes.x.log 만 읽음 — scale:"log" 는 과거 묵묵히 무시됐다.)
    from graph_skill.recipes.leftovers import _axis as ax_lo
    from graph_skill.recipes.playback import _axis as ax_pb
    for ax in (ax_lo, ax_pb):
        log_ax = ax({"x": {"label": "f", "unit": "Hz", "scale": "log"}}, "x", "X", "")
        assert log_ax["log"] is True and "scale" not in log_ax
        lin_ax = ax({"x": {"label": "t", "unit": "s"}}, "x", "X", "")
        assert lin_ax["log"] is False and "scale" not in lin_ax
    # 엔드투엔드: stream-graph normalize → options.axes.x.log 까지 전달
    p = {"axes": {"x": {"label": "f", "unit": "Hz", "scale": "log"}, "y": {"label": "p", "unit": ""}},
         "series": [{"name": "a", "data": [[1, 1], [2, 2]]}, {"name": "b", "data": [[1, 1], [2, 2]]}]}
    out = REGISTRY["stream-graph"].normalize(p, catalog.resolve_type("stream-graph"))
    assert out["options"]["axes"]["x"]["log"] is True and "scale" not in out["options"]["axes"]["x"]


def test_gating():
    assert not validate.check("stat-card", {"items": [{"label": "x"}]})["ok"]
    assert not validate.check("stream-graph",
                              {"axes": {"x": {"label": "m", "unit": ""}},
                               "series": [{"name": "a", "data": [[0, 1]]}]})["ok"]
    assert not validate.check("stream-graph",
                              {"series": [{"name": "a", "data": [[0, 1]]}, {"name": "b", "data": [[0, 1]]}]})["ok"]  # no x unit
    assert not validate.check("sunburst", {})["ok"]
    assert not validate.check("sunburst", {"tree": {"name": "x", "value": 1}})["ok"]    # no children


def test_determinism():
    for t, (fx, _) in TYPES.items():
        p = _load(fx)
        a = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}A.html"))["html_path"]).read_bytes()
        b = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}B.html"))["html_path"]).read_bytes()
        assert hashlib.sha256(a).hexdigest() == hashlib.sha256(b).hexdigest(), t
        (OUT / f"_{fx}A.html").unlink(missing_ok=True)
        (OUT / f"_{fx}B.html").unlink(missing_ok=True)
