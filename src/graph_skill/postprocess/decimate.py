"""decimate — reduce triangle count (QEM) to keep the inline GLB within the size budget.

trimesh's quadric decimation; tolerant to API differences across versions. Coloring must be
applied AFTER decimation (vertex count changes) to avoid doubled interpolation error.
"""

from __future__ import annotations


def decimate_to(mesh, target_faces: int):
    """Quadric-decimate to ~target_faces. Returns mesh unchanged if already smaller or if
    the backend is unavailable."""
    if target_faces <= 0 or len(mesh.faces) <= target_faces:
        return mesh
    try:
        return mesh.simplify_quadric_decimation(face_count=target_faces)
    except TypeError:
        try:
            return mesh.simplify_quadric_decimation(target_faces)
        except Exception:  # noqa: BLE001
            return mesh
    except Exception:  # noqa: BLE001  (backend missing → graceful no-op)
        return mesh


def lod_target(n_faces: int, profile: str = "desktop") -> int:
    """Face-count target per LOD profile (desktop 50k / mobile 10k), capped at input."""
    cap = {"desktop": 50_000, "mobile": 10_000}.get(profile, 50_000)
    return min(n_faces, cap)
