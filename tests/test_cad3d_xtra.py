"""cad3d-core 3D data viz — point-cloud-3d (Points) / surface-3d (grid mesh).
Locks: registration, render/lint, three.js bundled, scalar→colors+LUT, grid
triangulation, gating (scalar/z meta, jagged grid), determinism."""
import hashlib
import json
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate
from graph_skill.recipes import REGISTRY

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_registration_and_taxonomy():
    cov = taxonomy.coverage(catalog.known_types())
    assert cov["ok"], cov["bad_category"]
    for t in ("point-cloud-3d", "surface-3d", "isosurface-3d"):
        assert t in REGISTRY and catalog.resolve_type(t).engine == "cad3d-core"


def test_isosurface_marching_tetrahedra():
    p = _load("isosurface")
    assert validate.check("isosurface-3d", p)["ok"]
    r = builder.render("isosurface-3d", p, out_path=str(OUT / "isosurface-3d.html"))
    assert r["lint"]["ok"]
    out = REGISTRY["isosurface-3d"].normalize(p, catalog.resolve_type("isosurface-3d"))["assets"]
    m = out["model"]
    assert len(m["indices"]) >= 300 and len(m["indices"]) % 3 == 0      # a real triangle soup
    assert len(m["vertices"]) == len(m["indices"]) * 3 and "lut" in m
    # explicit small sphere field also yields a surface
    n = 12
    fld = [[[(1.0 if (i - 5.5) ** 2 + (j - 5.5) ** 2 + (k - 5.5) ** 2 < 16 else 0.0)
             for k in range(n)] for j in range(n)] for i in range(n)]
    assert builder.render("isosurface-3d", {"field": fld, "level": 0.5}, out_path=str(OUT / "_iso.html"))["lint"]["ok"]
    (OUT / "_iso.html").unlink(missing_ok=True)


def test_isosurface_gating():
    assert not validate.check("isosurface-3d", {})["ok"]
    assert not validate.check("isosurface-3d", {"field": "nope"})["ok"]
    assert not validate.check("isosurface-3d", {"field": [[1, 2], [3, 4]]})["ok"]


def test_point_cloud_render_and_colors():
    p = _load("pointcloud")
    assert validate.check("point-cloud-3d", p)["ok"]
    r = builder.render("point-cloud-3d", p, out_path=str(OUT / "point-cloud-3d.html"))
    assert r["lint"]["ok"]
    html = Path(r["html_path"]).read_text(encoding="utf-8")
    assert 'GraphEngines["cad3d-core"]' in html and "THREE" in html
    m = REGISTRY["point-cloud-3d"].normalize(p, catalog.resolve_type("point-cloud-3d"))["assets"]["model"]
    assert len(m["points"]) == len(p["points"]) * 3
    assert len(m["colors"]) == len(p["points"]) * 3 and "lut" in m and m["size"] > 0


def test_surface_triangulation_and_colors():
    p = _load("surface")
    assert validate.check("surface-3d", p)["ok"]
    r = builder.render("surface-3d", p, out_path=str(OUT / "surface-3d.html"))
    assert r["lint"]["ok"]
    out = REGISTRY["surface-3d"].normalize(p, catalog.resolve_type("surface-3d"))["assets"]
    ny, nx = len(p["z_grid"]), len(p["z_grid"][0])
    assert len(out["model"]["vertices"]) == nx * ny * 3
    assert len(out["model"]["indices"]) == (nx - 1) * (ny - 1) * 6      # 2 triangles/cell
    assert "lut" in out["model"] and out["z"]["label"] == "f(x,y)"


def test_gating():
    assert not validate.check("point-cloud-3d", {})["ok"]
    # scalar present but no z meta -> ask
    assert not validate.check("point-cloud-3d", {"points": [[0, 0, 0], [1, 1, 1]], "scalar": [0.1, 0.5]})["ok"]
    assert not validate.check("surface-3d", {})["ok"]
    assert not validate.check("surface-3d", {"z_grid": [[1, 2], [3, 4]]})["ok"]                    # no z_meta
    assert not validate.check("surface-3d", {"z_grid": [[1, 2], [3]], "z_meta": {"label": "a", "unit": ""}})["ok"]  # jagged


def test_determinism():
    for t, fx in [("point-cloud-3d", "pointcloud"), ("surface-3d", "surface")]:
        p = _load(fx)
        a = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}A.html"))["html_path"]).read_bytes()
        b = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}B.html"))["html_path"]).read_bytes()
        assert hashlib.sha256(a).hexdigest() == hashlib.sha256(b).hexdigest(), t
        (OUT / f"_{fx}A.html").unlink(missing_ok=True)
        (OUT / f"_{fx}B.html").unlink(missing_ok=True)
