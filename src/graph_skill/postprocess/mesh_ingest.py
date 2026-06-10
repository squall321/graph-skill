"""mesh_ingest — cad3d-core geometry/result pipeline (STL/OBJ/GLB via trimesh).

trimesh is imported lazily: the core skill never needs it; only cad3d render paths do.
All inputs converge on one schema {vertices, indices, vertexColors?} and a GLB for the
viewer. Field coloring reuses ``field_to_color`` so 3D result maps match 2D contours.
"""

from __future__ import annotations

import base64

from . import field_to_color


def _trimesh():
    try:
        import trimesh  # noqa: PLC0415
        return trimesh
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "cad3d 메쉬 처리에는 trimesh가 필요합니다: `pip install trimesh` "
            "(코어 그래프 타입은 trimesh 없이 동작합니다)."
        ) from e


def load_mesh(source, file_type=None):
    """Load STL/OBJ/GLB (path or bytes) → a single trimesh.Trimesh (scenes concatenated)."""
    trimesh = _trimesh()
    if isinstance(source, (bytes, bytearray)):
        import io  # noqa: PLC0415
        m = trimesh.load(io.BytesIO(bytes(source)), file_type=file_type, process=False)
    else:
        m = trimesh.load(source, file_type=file_type, process=False)
    if isinstance(m, trimesh.Scene):
        geos = list(m.geometry.values())
        m = trimesh.util.concatenate(geos) if geos else trimesh.Trimesh()
    return m


def warp(mesh, disp, factor: float = 1.0):
    """Return new vertices = vertices + factor·disp (deformed shape). disp: [[dx,dy,dz],...]."""
    import numpy as np  # noqa: PLC0415
    d = np.asarray(disp, dtype=float)
    return mesh.vertices + factor * d


def color_mesh(mesh, scalar, cmap="viridis", vmin=None, vmax=None, clip_percentile=None):
    """Set per-vertex colors from a nodal scalar field. Returns (vmin, vmax) actually used."""
    import numpy as np  # noqa: PLC0415
    rgb, rng = field_to_color.scalar_to_rgb(list(scalar), vmin, vmax, cmap, clip_percentile)
    rgba = np.concatenate([np.asarray(rgb, dtype=np.uint8),
                           np.full((len(rgb), 1), 255, dtype=np.uint8)], axis=1)
    mesh.visual.vertex_colors = rgba
    return rng


def to_surface(mesh, decimals: int | None = 5) -> dict:
    """Engine-agnostic surface schema: flat vertices/indices + bbox + counts.
    decimals rounds coords (size + determinism); None keeps full precision."""
    v = mesh.vertices
    f = mesh.faces
    if decimals is not None:
        v = v.round(decimals)
    bb = mesh.bounds  # [[minx,miny,minz],[maxx,maxy,maxz]]
    return {
        "vertices": [float(x) for x in v.reshape(-1)],
        "indices": [int(i) for i in f.reshape(-1)],
        "bbox": [[float(x) for x in bb[0]], [float(x) for x in bb[1]]],
        "n_vertices": int(len(v)),
        "n_faces": int(len(f)),
    }


def to_glb_bytes(mesh) -> bytes:
    """Export mesh (incl. vertex colors) to a binary GLB."""
    return mesh.export(file_type="glb")


def to_glb_b64(mesh) -> str:
    """GLB as base64 (ready for inline data URI in the self-contained artifact)."""
    return base64.b64encode(to_glb_bytes(mesh)).decode("ascii")
