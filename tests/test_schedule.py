"""planning family — gantt-chart / milestone-timeline / calendar-heatmap / task-table /
work-plan (composite). Locks: registration+category, render/lint, date parsing/ticks,
deps resolution, hideAxes frame, work-plan multi-engine bundling, explicit as_of D-day,
gating (ISO dates), determinism."""
import json
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate
from graph_skill.recipes import REGISTRY
from graph_skill.recipes.schedule import _day, _date_ticks

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"
TYPES = {"gantt-chart": ("gantt", "xy-core"), "milestone-timeline": ("timeline", "xy-core"),
         "calendar-heatmap": ("calheat", "xy-core"), "task-table": ("tasktable", "review-matrix"),
         "work-plan": ("workplan", "review-matrix")}


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_registration_and_planning_category():
    cov = taxonomy.coverage(catalog.known_types())
    assert cov["ok"], cov["bad_category"]
    for t, (_, eng) in TYPES.items():
        assert t in REGISTRY and catalog.resolve_type(t).engine == eng
        assert taxonomy.meta(t)["category"] == "planning"


def test_render_lint():
    for t, (fx, _) in TYPES.items():
        p = _load(fx)
        assert validate.check(t, p)["ok"], t
        assert builder.render(t, p, out_path=str(OUT / f"{t}.html"))["lint"]["ok"], t


def test_date_parse_and_ticks():
    assert _day("2026-06-10") == 20614               # epoch days, deterministic
    assert _day("6월 10일") is None
    daily = _date_ticks(_day("2026-06-01"), _day("2026-06-10"))
    assert len(daily) == 10 and daily[0]["label"] == "6/1"
    weekly = _date_ticks(_day("2026-06-01"), _day("2026-08-20"))
    assert all((tk["t"] + 4) % 7 == 1 for tk in weekly)   # all Mondays


def test_gantt_rows_deps_hideaxes():
    out = REGISTRY["gantt-chart"].normalize(_load("gantt"), catalog.resolve_type("gantt-chart"))
    g = out["options"]["pluginConfig"]["gantt"]
    assert out["options"]["hideAxes"] is True
    assert len(g["rows"]) == 8 and g["ticks"]
    names = [r["name"] for r in g["rows"]]
    i_arch, i_back = names.index("아키텍처 설계"), names.index("백엔드 구현")
    assert [i_arch, i_back] in g["deps"]              # name refs resolved to index pairs
    ms = next(r for r in g["rows"] if r.get("milestone"))
    assert ms["start"] == ms["end"]


def test_task_table_dday_needs_explicit_as_of():
    rt = catalog.resolve_type("task-table")
    with_as_of = REGISTRY["task-table"].normalize(_load("tasktable"), rt)
    assert any(s["id"] == "dday" for s in with_as_of["assets"]["states"])
    p2 = dict(_load("tasktable")); p2.pop("as_of")
    without = REGISTRY["task-table"].normalize(p2, rt)
    assert not any(s["id"] == "dday" for s in without["assets"]["states"])  # no build-clock D-day
    cells = with_as_of["assets"]["items"][0]["cells"]
    assert cells["prog"]["kind"] == "bar" and cells["status"]["kind"] == "status"


def test_work_plan_composite_bundles_engines():
    html = Path(builder.render("work-plan", _load("workplan"),
                               out_path=str(OUT / "work-plan.html"))["html_path"]).read_text(encoding="utf-8")
    for needle in ('GraphEngines["review-matrix"]', 'GraphEngines["xy-core"]', 'GraphEngines["gauge-core"]',
                   '"gantt"', '"timeline"'):
        assert needle in html, needle
    out = REGISTRY["work-plan"].normalize(_load("workplan"), catalog.resolve_type("work-plan"))
    groups = {it["group"] for it in out["assets"]["items"]}
    assert {"개요", "핵심 지표", "일정", "마일스톤", "업무분장", "리스크 (영향×가능성)"} <= groups
    gantt_item = next(it for it in out["assets"]["items"] if it["id"] == "gantt")
    assert gantt_item["overlay"] == "gantt" and gantt_item["h"] >= 220


def test_gating_iso_dates():
    assert not validate.check("gantt-chart", {})["ok"]
    assert not validate.check("gantt-chart", {"tasks": [{"name": "a", "start": "6월1일", "end": "2026-06-05"}]})["ok"]
    assert not validate.check("gantt-chart", {"tasks": [{"name": "a", "start": "2026-06-09", "end": "2026-06-01"}]})["ok"]
    assert not validate.check("milestone-timeline", {})["ok"]
    assert not validate.check("calendar-heatmap", {"entries": ["어제"]})["ok"]
    assert not validate.check("work-plan", {"tasks": [{"name": "a", "start": "2026-06-01", "end": "2026-06-02"}]})["ok"]


def test_determinism():
    for t, (fx, _) in TYPES.items():
        p = _load(fx)
        a = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}A.html"))["html_path"]).read_bytes()
        b = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}B.html"))["html_path"]).read_bytes()
        assert a == b, t
        (OUT / f"_{fx}A.html").unlink(missing_ok=True)
        (OUT / f"_{fx}B.html").unlink(missing_ok=True)
