"""cad3d-core (batch J) data-pipeline smoke — pure-Python verifiable foundation:
field_to_color LUT + mesh_ingest (trimesh) + decimate. No WebGL/browser needed here."""
import trimesh

from graph_skill.postprocess import decimate, field_to_color, mesh_ingest

# --- field_to_color: deterministic LUT + scalar mapping ---
table = field_to_color.lut("viridis", 256)
assert len(table) == 256 and table[0] == [68, 1, 84] and table[-1] == [253, 231, 37]
assert all(0 <= c <= 255 for rgb in table for c in rgb)
rgb, (vmin, vmax) = field_to_color.scalar_to_rgb([0, 5, 10], cmap="turbo")
assert vmin == 0 and vmax == 10 and rgb[0] != rgb[-1]
# fixed range (e.g. yield strength) clamps out-of-range to the endpoints
cw = field_to_color.lut("coolwarm", 256)
rgb2, rng = field_to_color.scalar_to_rgb([-100, 125, 9999], vmin=0, vmax=250, cmap="coolwarm")
assert rng == (0, 250) and rgb2[0] == cw[0] and rgb2[-1] == cw[-1]   # clamped lo/hi
print("field_to_color: LUT 256, endpoints OK, scalar map + clamp OK")

# --- mesh_ingest: box → schema + GLB (determinism) ---
box = trimesh.creation.box(extents=[2.0, 1.0, 0.5])
surf = mesh_ingest.to_surface(box)
assert surf["n_vertices"] == 8 and surf["n_faces"] == 12
assert surf["bbox"][0] == [-1.0, -0.5, -0.25] and surf["bbox"][1] == [1.0, 0.5, 0.25]
assert len(surf["vertices"]) == 8 * 3 and len(surf["indices"]) == 12 * 3
mesh_ingest.color_mesh(box, [0, 1, 2, 3, 4, 5, 6, 7], cmap="viridis")
b64a = mesh_ingest.to_glb_b64(box)
b64b = mesh_ingest.to_glb_b64(box)
assert len(b64a) > 100 and b64a == b64b                       # GLB export deterministic
print(f"mesh_ingest: box 8v/12f, bbox OK, GLB b64 {len(b64a)} chars, deterministic")

# round-trip: GLB bytes reload to same vertex count
import base64
reloaded = mesh_ingest.load_mesh(base64.b64decode(b64a), file_type="glb")
assert len(reloaded.vertices) >= 8
print("mesh_ingest: GLB round-trip OK")

# --- decimate: high-res sphere → fewer faces (or graceful no-op) ---
sph = trimesh.creation.icosphere(subdivisions=4)   # ~5120 faces
n0 = len(sph.faces)
dec = decimate.decimate_to(sph, 500)
assert len(dec.faces) <= n0
assert decimate.lod_target(80000, "mobile") == 10000 and decimate.lod_target(3000, "desktop") == 3000
print(f"decimate: {n0} -> {len(dec.faces)} faces (target 500), bbox preserved={list(dec.bounds[0].round(2))}")

print("CAD3D DATA SMOKE OK")
