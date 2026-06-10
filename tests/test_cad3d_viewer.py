"""cad3d-core viewer regression — cad-3d-viewer / mesh-result-3d build a self-contained
three.js artifact with an inline GLB. (WebGL render itself is the browser/Playwright tier;
here we lock the build: engine resolves, three.js inlined, lint clean, GLB embedded.)"""
import json
from pathlib import Path

import pytest

from graph_skill import assets, builder, catalog, validate

pytest.importorskip("trimesh")  # cad3d is an optional extra

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_vendor_three_js_inlined():
    ejs = assets.read_engine_js("cad3d-core")
    assert "WebGLRenderer" in ejs and "OrbitControls" in ejs and "GLTFLoader" in ejs
    assert 'GraphEngines["cad3d-core"]' in ejs


def test_types_resolve_on_cad3d_core():
    for t in ("cad-3d-viewer", "mesh-result-3d"):
        assert catalog.resolve_type(t).engine == "cad3d-core"


def test_cad_viewer_renders_self_contained():
    r = builder.render("cad-3d-viewer", _load("cad_viewer"), out_path=str(OUT / "cad-3d-viewer.html"))
    h = Path(r["html_path"]).read_text(encoding="utf-8")
    assert r["lint"]["ok"] and r["lint"]["external_urls"] == 0 and r["lint"]["self_contained"]
    assert '"glb"' in h and 'GraphEngines["cad3d-core"]' in h


def test_mesh_result_colors_and_colorbar():
    r = builder.render("mesh-result-3d", _load("mesh_result"), out_path=str(OUT / "mesh-result-3d.html"))
    h = Path(r["html_path"]).read_text(encoding="utf-8")
    assert r["lint"]["ok"]
    # field-coloured → zrange + LUT embedded for the colorbar, z meta present
    assert '"zrange"' in h and '"lut"' in h and "von Mises" in h


def test_primitive_and_vertices_inputs():
    a = builder.render("cad-3d-viewer", {"mesh": {"primitive": "box", "extents": [2, 1, 1]}},
                       out_path=str(OUT / "_cadbox.html"))
    assert a["lint"]["ok"]
    b = builder.render("cad-3d-viewer", {"mesh": {
        "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], "faces": [[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]]}},
        out_path=str(OUT / "_cadtet.html"))
    assert b["lint"]["ok"]


def test_deformed_mesh_raw_geometry_and_warp():
    p = {"mesh": {"primitive": "box", "extents": [6, 1, 0.6]}, "displacement": "auto",
         "z": {"label": "|U|", "unit": "mm"}, "colormap": "turbo"}
    r = builder.render("mesh-deformed-3d", p, out_path=str(OUT / "mesh-deformed-3d.html"))
    h = Path(r["html_path"]).read_text(encoding="utf-8")
    assert r["lint"]["ok"]
    # raw BufferGeometry path (not GLB) with per-vertex displacement + colour
    assert '"vertices"' in h and '"displacement"' in h and '"colors"' in h and "_buildRaw" in h


def test_mode_shape_auto_modes():
    p = {"mesh": {"primitive": "box", "extents": [8, 1, 0.5]}, "modes": "auto", "freqs": [120, 340, 660]}
    out = builder.render("mode-shape-3d", p, out_path=str(OUT / "mode-shape-3d.html"))
    h = Path(out["html_path"]).read_text(encoding="utf-8")
    assert out["lint"]["ok"] and '"modes"' in h and '"vertices"' in h
    from graph_skill.recipes import REGISTRY
    norm = REGISTRY["mode-shape-3d"].normalize(p, catalog.resolve_type("mode-shape-3d"))
    assert len(norm["assets"]["model"]["modes"]) == 3         # 3 auto bending modes


def test_3d_determinism():
    p = {"mesh": {"primitive": "box", "extents": [6, 1, 0.6]}, "displacement": "auto", "z": {"label": "U", "unit": "mm"}}
    a = builder.render("mesh-deformed-3d", p, out_path=str(OUT / "_d3a.html"))
    b = builder.render("mesh-deformed-3d", p, out_path=str(OUT / "_d3b.html"))
    assert Path(a["html_path"]).read_bytes() == Path(b["html_path"]).read_bytes()


def test_gating():
    assert not validate.check("cad-3d-viewer", {})["ok"]                       # no mesh
    assert not validate.check("mesh-result-3d", {"mesh": {"primitive": "box"}})["ok"]  # no field/z


def test_determinism():
    a = builder.render("mesh-result-3d", _load("mesh_result"), out_path=str(OUT / "_md_a.html"))
    b = builder.render("mesh-result-3d", _load("mesh_result"), out_path=str(OUT / "_md_b.html"))
    assert Path(a["html_path"]).read_bytes() == Path(b["html_path"]).read_bytes()
