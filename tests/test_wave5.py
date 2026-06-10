"""Wave-5 regression — multitrack-stack (review-matrix stack) + response-surface-2d (RSM)."""
import json
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate
from graph_skill.recipes.wave5 import _solve

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_taxonomy_and_engines():
    assert taxonomy.coverage(catalog.known_types())["ok"]
    assert catalog.resolve_type("multitrack-stack").engine == "review-matrix"
    assert catalog.resolve_type("response-surface-2d").engine == "field-core"


def test_render_lint():
    for t, fx in [("multitrack-stack", "multitrack"), ("response-surface-2d", "rsm")]:
        assert validate.check(t, _load(fx))["ok"], t
        assert builder.render(t, _load(fx), out_path=str(OUT / f"{t}.html"))["lint"]["ok"], t


def test_multitrack_stacks_channels_as_graph_cells():
    from graph_skill.recipes import REGISTRY
    out = REGISTRY["multitrack-stack"].normalize(_load("multitrack"), catalog.resolve_type("multitrack-stack"))
    assert len(out["assets"]["items"]) == 3                     # 3 channels → 3 stacked panels
    h = Path(builder.render("multitrack-stack", _load("multitrack"), out_path=str(OUT / "multitrack-stack.html"))["html_path"]).read_text(encoding="utf-8")
    assert "review-matrix" in h and "xy-core" in h and "Accel X" in h


def test_solve_linear_system():
    x = _solve([[2.0, 1.0], [1.0, 3.0]], [5.0, 10.0])
    assert abs(x[0] - 1.0) < 1e-9 and abs(x[1] - 3.0) < 1e-9


def test_rsm_recovers_quadratic_peak():
    # exact quadratic y = 100 - (x1-5)^2 - (x2-3)^2 sampled on a grid → fitted peak ≈ (5,3)
    x1, x2, y = [], [], []
    for a in (3, 4, 5, 6, 7):
        for b in (1, 2, 3, 4, 5):
            x1.append(a); x2.append(b); y.append(100 - (a - 5) ** 2 - (b - 3) ** 2)
    p = {"x1": x1, "x2": x2, "y": y, "factors": {"x1": {"label": "A", "unit": ""}, "x2": {"label": "B", "unit": ""}},
         "z": {"label": "y", "unit": ""}}
    out = builder.render("response-surface-2d", p, out_path=str(OUT / "_rsm.html"))
    assert out["lint"]["ok"]
    # peak of the fitted z-grid should sit near the true optimum (5,3)
    cfg = json.loads(Path(out["html_path"]).read_text(encoding="utf-8").split('id="graph-config" type="application/json">')[1].split("</script>")[0])
    z = cfg["assets"]["field"]["z"]
    gx, gy = cfg["assets"]["field"]["x"], cfg["assets"]["field"]["y"]
    best = max(((i, j) for j in range(len(z)) for i in range(len(z[0]))), key=lambda ij: z[ij[1]][ij[0]])
    assert abs(gx[best[0]] - 5) < 0.6 and abs(gy[best[1]] - 3) < 0.6


def test_treemap_squarify_areas_match_values():
    from graph_skill.postprocess import treemap
    rects = treemap.squarify([50, 30, 20], 1.0, 1.0)
    areas = [r["w"] * r["h"] for r in rects]
    tot = sum(areas)
    assert abs(tot - 1.0) < 1e-6                                # tiles the unit square
    assert abs(areas[0] / tot - 0.5) < 0.02 and abs(areas[2] / tot - 0.2) < 0.02   # area ∝ value


def test_treemap_renders():
    p = {"items": [{"label": "A", "value": 40}, {"label": "B", "value": 30}, {"label": "C", "value": 30}]}
    h = Path(builder.render("treemap", p, out_path=str(OUT / "treemap.html"))["html_path"]).read_text(encoding="utf-8")
    assert "treemap" in h and '"rects"' in h


def test_gating():
    assert not validate.check("multitrack-stack", {"channels": [{"name": "a", "data": [[0, 1]]}]})["ok"]
    assert not validate.check("response-surface-2d",
                              {"x1": [1, 2], "x2": [1, 2], "y": [1, 2], "z": {"label": "y", "unit": "%"}})["ok"]
    assert not validate.check("treemap", {})["ok"]


def test_determinism():
    a = builder.render("response-surface-2d", _load("rsm"), out_path=str(OUT / "_w5a.html"))
    b = builder.render("response-surface-2d", _load("rsm"), out_path=str(OUT / "_w5b.html"))
    assert Path(a["html_path"]).read_bytes() == Path(b["html_path"]).read_bytes()
