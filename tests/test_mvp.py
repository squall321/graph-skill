"""base-xy MVP regression tests. Run: pytest (conftest puts src on the path)."""
import hashlib
import json
from pathlib import Path

import pytest

from graph_skill import builder, catalog, tools, validate

FIX = Path(__file__).parent / "fixtures" / "base_xy.json"


@pytest.fixture
def payload():
    return json.loads(FIX.read_text(encoding="utf-8"))


def test_known_types():
    assert "base-xy" in catalog.known_types()


def test_validate_ok(payload):
    assert validate.check("base-xy", payload)["ok"]


def test_validate_missing_axes(payload):
    r = validate.check("base-xy", {"series": payload["series"], "axes": {}})
    assert not r["ok"]
    fields = {m["field"] for m in r["missing"]}
    assert {"axes.x", "axes.y"} <= fields
    assert all(m["ask"] for m in r["missing"])  # every gap has a question


def test_axis_unit_may_be_empty():
    p = {
        "axes": {"x": {"label": "strain", "unit": ""}, "y": {"label": "stress", "unit": "MPa"}},
        "series": [{"name": "s", "data": [[0, 0], [1, 1]]}],
    }
    assert validate.check("base-xy", p)["ok"]


def test_render_self_contained(payload, tmp_path):
    out = tmp_path / "p.html"
    res = builder.render("base-xy", payload, out_path=str(out))
    assert res["lint"]["ok"] and res["lint"]["external_urls"] == 0
    html = out.read_text(encoding="utf-8")
    assert "<script src" not in html
    assert "://" not in html  # no external protocol anywhere
    assert html.count("<html") == 1
    assert "graph-engine" in html  # version baked


def test_determinism(payload):
    a = builder.render("base-xy", payload)["html"]
    b = builder.render("base-xy", payload)["html"]
    assert hashlib.sha256(a.encode()).hexdigest() == hashlib.sha256(b.encode()).hexdigest()


def test_written_file_is_lf(payload, tmp_path):
    out = tmp_path / "p.html"
    a = builder.render("base-xy", payload, out_path=str(out))
    assert out.read_bytes() == a["html"].encode("utf-8") if "html" in a else True
    # explicit: no CRLF in artifact
    assert b"\r\n" not in out.read_bytes()


def test_missing_raises(payload):
    with pytest.raises(builder.MissingFieldsError):
        builder.render("base-xy", {"series": payload["series"]})


def test_gap_and_parallel_arrays():
    p = {
        "axes": {"x": {"label": "a", "unit": ""}, "y": {"label": "b", "unit": ""}},
        "series": [{"name": "s", "x": [0, 1, 2], "y": [0, None, 2]}],
    }
    res = builder.render("base-xy", p)
    assert res["lint"]["ok"]


def test_tools_render_needs_input(payload, tmp_path):
    r = tools.render("base-xy", payload["series"], {}, out_path=str(tmp_path / "x.html"))
    assert r["status"] == "needs_input"
    assert r["questions"]


def test_tools_render_ok(payload, tmp_path):
    r = tools.render(
        "base-xy", payload["series"], payload["axes"],
        title=payload.get("title"), out_path=str(tmp_path / "ok.html"),
    )
    assert r["status"] == "ok" and r["lint"]["ok"]


def test_embed_block_clamps(payload, tmp_path):
    out = tmp_path / "p.html"
    builder.render("base-xy", payload, out_path=str(out))
    b = builder.embed_block(str(out), height_px=99999)
    assert b["type"] == "html_embed" and b["input"]["height_px"] == 4000


def test_extends_flatten_is_stable():
    # base-xy has no parent, but resolve must be deterministic and engine-bound
    rt = catalog.resolve_type("base-xy")
    assert rt.engine == "xy-core" and rt.require_axes is True
