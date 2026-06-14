"""UX P2 regressions — keyboard map, export common set, label halo, Korean graph_find
synonyms, validate dedupe, gallery freshness gate (engine bump without rebuild fails CI)."""
import json
import re
from pathlib import Path

from graph_skill import assets, catalog, taxonomy, validate

ROOT = Path(__file__).resolve().parent.parent
ENGINES = ROOT / "src" / "graph_skill" / "data" / "engines"
GAL = ROOT / "graph-out" / "gallery"


def test_validate_missing_dedup():
    # bubble-timeline: require_axes + structural hook both flag axes.x — must appear once
    res = validate.check("bubble-timeline", {"frames": [
        {"t": "1", "entities": [{"id": "a", "x": 1, "y": 2}]},
        {"t": "2", "entities": [{"id": "a", "x": 2, "y": 3}]}]})
    fields = [m["field"] for m in res["missing"]]
    assert len(fields) == len(set(fields)), fields


def test_korean_find_synonyms():
    expect = {"샌키": "sankey-diagram", "계기판": "gauge", "네트워크": "network-graph",
              "조직도": "network-graph", "상자그림": "box-plot", "폭포차트": "waterfall-chart",
              "간트": "gantt-chart", "업무계획": "work-plan", "등위면": "isosurface-3d"}
    for q, want in expect.items():
        names = [m["name"] for m in taxonomy.find(q, 5)]
        assert want in names, f"{q!r} -> {names}"


def test_keyboard_map_and_focusable():
    js = (ENGINES / "xy-core" / "engine.js").read_text(encoding="utf-8")
    assert '_onKey' in js and '"ArrowLeft"' in js and '"Home"' in js
    assert 'setAttribute("tabindex", "0")' in js                     # canvas focusable
    fjs = (ENGINES / "flow-core" / "engine.js").read_text(encoding="utf-8")
    assert 'setAttribute("role", "button")' in fjs                   # cards keyboard-activatable


def test_export_common_set_everywhere():
    # every family ships at least theme(◐) + source/PNG export
    smith = (ENGINES / "smith-core" / "engine.js").read_text(encoding="utf-8")
    assert "_buildBar" in smith and "toDataURL" in smith
    matrix = (ENGINES / "review-matrix" / "engine.js").read_text(encoding="utf-8")
    assert "_exportCSV" in matrix and "_exportSource" in matrix
    flow = (ENGINES / "flow-core" / "engine.js").read_text(encoding="utf-8")
    assert "_exportPNG" in flow and "XMLSerializer" in flow


def test_label_halo_and_dense_mode():
    css = (ENGINES / "flow-core" / "engine.css").read_text(encoding="utf-8")
    assert "paint-order: stroke" in css
    assert ".gs-fl-dense .gs-fl-nlabel" in css


def test_gallery_freshness_gate():
    """Bumping an ENGINE_VERSION without rebuilding the gallery must fail CI.
    Every gallery artifact embeds <meta name="graph-engine" content="<fam>@<ver>">."""
    if not GAL.exists():
        import pytest
        pytest.skip("gallery not built")
    stale = []
    for f in GAL.glob("*.html"):
        if f.name == "index.html":
            continue
        head = f.read_text(encoding="utf-8")[:2000]
        m = re.search(r'<meta name="graph-engine" content="([\w-]+)@([\w.]+)"', head)
        if not m:
            continue
        fam, ver = m.group(1), m.group(2)
        cur = assets.engine_version(fam)
        if ver != cur:
            stale.append(f"{f.name}: {fam}@{ver} != {cur}")
    assert not stale, "STALE gallery artifacts (run build_gallery.py): " + "; ".join(stale[:8])


def test_engine_code_version_binding():
    """Structural freshness gate: each engine's source hash + version must match the committed
    manifest. Editing an engine's code without bumping ENGINE_VERSION fails here — closing the
    gap the gallery gate misses (it only compares baked meta, not whether code actually changed).
    After a legit bump, regenerate via: python tests/update_engine_manifest.py."""
    manifest = json.loads((Path(__file__).resolve().parent / "engine_manifest.json").read_text(encoding="utf-8"))
    engines = sorted({catalog.resolve_type(t).engine for t in catalog.known_types()})
    bad = []
    for e in engines:
        m = manifest.get(e)
        if not m or m["version"] != assets.engine_version(e) or m["code_hash"] != assets.engine_code_hash(e):
            bad.append(e)
    assert not bad, ("engine manifest stale — code changed without a version bump, or manifest not "
                     f"regenerated (run tests/update_engine_manifest.py): {bad}")


def test_needs_input_answer_template():
    """needs_input must carry a machine-fillable skeleton (not just prose 'ask') so an
    automation/REST client can fill the missing values programmatically and re-call."""
    from graph_skill import tools
    r = tools.render_payload("stress-linearization", {"path": [[0, 100], [1, 50], [2, 0]]})
    assert r["status"] == "needs_input"
    assert r["answer_template"]["axes"]["y"]["unit"] == "<채울 값>"
