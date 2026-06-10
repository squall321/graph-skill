"""cad3d-core (batch J) data-pipeline regression — field_to_color (pure) + mesh_ingest +
decimate (trimesh). The WebGL engine/vendor + browser tiers land in a later step; this locks
the deterministic, dependency-light foundation."""
import base64
import importlib.util

import pytest

from graph_skill.postprocess import field_to_color

trimesh = pytest.importorskip("trimesh")  # cad3d deps are optional (extras: cad3d)

from graph_skill.postprocess import decimate, mesh_ingest  # noqa: E402

_HAVE_QEM = importlib.util.find_spec("fast_simplification") is not None


# ---- field_to_color (no deps) ----
def test_lut_shape_and_endpoints():
    t = field_to_color.lut("viridis", 256)
    assert len(t) == 256
    assert t[0] == [68, 1, 84] and t[-1] == [253, 231, 37]
    assert all(0 <= c <= 255 for rgb in t for c in rgb)


def test_lut_unknown_falls_back_to_viridis():
    assert field_to_color.lut("nope", 8) == field_to_color.lut("viridis", 8)


def test_scalar_to_rgb_range_and_clamp():
    cw = field_to_color.lut("coolwarm", 256)
    rgb, rng = field_to_color.scalar_to_rgb([-100, 125, 9999], vmin=0, vmax=250, cmap="coolwarm")
    assert rng == (0, 250)
    assert rgb[0] == cw[0] and rgb[-1] == cw[-1]            # clamped to endpoints


def test_scalar_to_rgb_auto_range():
    rgb, (vmin, vmax) = field_to_color.scalar_to_rgb([0, 5, 10], cmap="turbo")
    assert (vmin, vmax) == (0, 10) and rgb[0] != rgb[-1]


# ---- mesh_ingest (trimesh) ----
def test_box_surface_schema():
    box = trimesh.creation.box(extents=[2.0, 1.0, 0.5])
    s = mesh_ingest.to_surface(box)
    assert s["n_vertices"] == 8 and s["n_faces"] == 12
    assert s["bbox"] == [[-1.0, -0.5, -0.25], [1.0, 0.5, 0.25]]
    assert len(s["vertices"]) == 24 and len(s["indices"]) == 36


def test_glb_export_deterministic_and_roundtrip():
    box = trimesh.creation.box(extents=[1.0, 1.0, 1.0])
    mesh_ingest.color_mesh(box, list(range(8)), cmap="viridis")
    a, b = mesh_ingest.to_glb_b64(box), mesh_ingest.to_glb_b64(box)
    assert a == b and len(a) > 100                          # deterministic inline payload
    reloaded = mesh_ingest.load_mesh(base64.b64decode(a), file_type="glb")
    assert len(reloaded.vertices) >= 8


def test_color_mesh_sets_vertex_colors():
    box = trimesh.creation.box(extents=[1, 1, 1])
    rng = mesh_ingest.color_mesh(box, list(range(8)), cmap="turbo", vmin=0, vmax=7)
    assert rng == (0, 7)
    assert box.visual.vertex_colors.shape[0] == 8


# ---- decimate ----
def test_decimate_reduces_or_noops():
    sph = trimesh.creation.icosphere(subdivisions=4)
    n0 = len(sph.faces)
    dec = decimate.decimate_to(sph, 500)
    assert len(dec.faces) <= n0
    if _HAVE_QEM:
        assert len(dec.faces) < n0 and len(dec.faces) <= 600   # real QEM reduction


def test_decimate_noop_when_already_small():
    box = trimesh.creation.box()
    assert len(decimate.decimate_to(box, 10_000).faces) == len(box.faces)


def test_lod_target():
    assert decimate.lod_target(80_000, "mobile") == 10_000
    assert decimate.lod_target(3_000, "desktop") == 3_000
    assert decimate.lod_target(80_000, "desktop") == 50_000
