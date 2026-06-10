"""UX P0 regressions (2026-06 audit) — python-side locks.
Browser-side interaction checks live in tests/verify_ux_p0.py (Playwright)."""
import json
import re
from pathlib import Path

from graph_skill import builder, catalog, tools
from graph_skill.recipes import REGISTRY

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"
ENGINES_DIR = Path(__file__).resolve().parent.parent / "src" / "graph_skill" / "data" / "engines"


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_carriers_are_xy_arrays():
    # engine setData reads s.x/s.y — every autoscale carrier must be in that shape
    for t, fx in [("bubble-timeline", "bubble"), ("animated-trajectory", "trajectory"),
                  ("bar-chart-race", "race"), ("stream-graph", "stream")]:
        s = REGISTRY[t].normalize(_load(fx), catalog.resolve_type(t))["assets"]["series"][0]
        assert "x" in s and "y" in s and len(s["x"]) > 0, t
        assert "data" not in s, t


def test_embed_block_uses_artifact_height():
    h = builder.render("gauge", _load("gauge"), out_path=str(OUT / "_ux_gauge.html"))
    blk = builder.embed_block(h["html_path"])
    assert blk["input"]["height_px"] == 320          # gauge catalog height, not the 520 fallback
    assert builder.embed_block(h["html_path"], height_px=700)["input"]["height_px"] == 700
    (OUT / "_ux_gauge.html").unlink(missing_ok=True)


def test_tool_schemas_allow_family_keys():
    # additionalProperties:false used to reject nodes/links/tree/... payload keys
    assert "additionalProperties" not in tools.VALIDATE_SCHEMA
    assert "additionalProperties" not in tools.RENDER_SCHEMA
    assert "type" not in tools._PAYLOAD_PROPS["field"]   # field accepts object | 3D array | "metaballs"


def test_validate_hint_falls_back_to_catalog():
    res = tools.validate_inputs("sankey-diagram", {})    # not in prompt._INPUT_HINTS
    assert not res["ok"] and res["hint"]                 # catalog hint, not empty


def test_skill_md_documents_every_engine_family():
    md = (Path(__file__).resolve().parent.parent / ".claude" / "skills" / "graph-skill" / "SKILL.md").read_text(encoding="utf-8")
    fams = [p.name for p in ENGINES_DIR.iterdir() if p.is_dir()]
    missing = [f for f in fams if f not in md]
    assert not missing, f"SKILL.md missing engine families: {missing}"
    assert "xy-core 하나" not in md                       # the stale phrasing must never return


def test_wheel_gates_in_engines():
    # every zooming engine requires Ctrl/Meta before preventDefault (no embed scroll-trap)
    for fam, pat in [("xy-core", r"ctrlKey \|\| e\.metaKey"), ("field-core", r"ctrlKey \|\| e\.metaKey"),
                     ("flow-core", r"ctrlKey \|\| ev\.metaKey"), ("cad3d-core", r"ctrlKey \|\| e\.metaKey")]:
        js = (ENGINES_DIR / fam / "engine.js").read_text(encoding="utf-8")
        assert re.search(pat, js), fam


def test_modal_escape_and_aria():
    for fam in ("flow-core", "review-matrix"):
        js = (ENGINES_DIR / fam / "engine.js").read_text(encoding="utf-8")
        assert 'e.key === "Escape"' in js, fam
        assert 'setAttribute("role", "dialog")' in js, fam


def test_artifact_versions_and_determinism():
    p = _load("flowchart")
    r1 = builder.render("flowchart", p, out_path=str(OUT / "_ux_f1.html"))
    r2 = builder.render("flowchart", p, out_path=str(OUT / "_ux_f2.html"))
    a = Path(r1["html_path"]).read_bytes()
    assert a == Path(r2["html_path"]).read_bytes()       # determinism preserved
    assert r1["engine_version"] >= "0.4.0"
    for q in ("_ux_f1.html", "_ux_f2.html"):
        (OUT / q).unlink(missing_ok=True)
