"""Isosurface extraction via marching TETRAHEDRA (no large case tables, unambiguous).
Each grid cube is split into 6 tetrahedra; for every tet the level-set crossing forms a
triangle (1 vertex on one side) or a quad→2 triangles (2v/2v). Returns a flat triangle-soup
(every 3 consecutive vertices = one triangle), which the cad3d engine renders directly."""

from __future__ import annotations

# cube corner offsets (i,j,k), and a 6-tetrahedron split sharing the 0-6 diagonal
_CORNERS = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]
_TETS = [(0, 1, 2, 6), (0, 2, 3, 6), (0, 3, 7, 6), (0, 7, 4, 6), (0, 4, 5, 6), (0, 5, 1, 6)]


def marching_tetrahedra(field, level, spacing=(1.0, 1.0, 1.0), origin=(0.0, 0.0, 0.0)):
    """field: 3D array-like [nx][ny][nz] of scalars. Returns list of [x,y,z] vertices where
    every consecutive triple is a triangle (triangle soup)."""
    import numpy as np  # noqa: PLC0415

    f = np.asarray(field, dtype=float)
    nx, ny, nz = f.shape
    sx, sy, sz = spacing
    ox, oy, oz = origin
    verts = []

    def interp(pa, va, pb, vb):
        t = 0.5 if vb == va else (level - va) / (vb - va)
        t = 0.0 if t < 0 else (1.0 if t > 1 else t)
        return [pa[0] + (pb[0] - pa[0]) * t, pa[1] + (pb[1] - pa[1]) * t, pa[2] + (pb[2] - pa[2]) * t]

    for i in range(nx - 1):
        for j in range(ny - 1):
            for k in range(nz - 1):
                pos, val = [], []
                for (dx, dy, dz) in _CORNERS:
                    pos.append((ox + (i + dx) * sx, oy + (j + dy) * sy, oz + (k + dz) * sz))
                    val.append(f[i + dx, j + dy, k + dz])
                for tet in _TETS:
                    p = [pos[c] for c in tet]
                    v = [val[c] for c in tet]
                    inside = [a for a in range(4) if v[a] > level]
                    ni = len(inside)
                    if ni in (0, 4):
                        continue
                    if ni == 1 or ni == 3:
                        apex = inside[0] if ni == 1 else [a for a in range(4) if a not in inside][0]
                        others = [a for a in range(4) if a != apex]
                        for o in others:
                            verts.append(interp(p[apex], v[apex], p[o], v[o]))
                    else:  # 2 inside, 2 outside → quad → 2 triangles
                        a, b = inside
                        c, d = [x for x in range(4) if x not in inside]
                        pac = interp(p[a], v[a], p[c], v[c])
                        pad = interp(p[a], v[a], p[d], v[d])
                        pbd = interp(p[b], v[b], p[d], v[d])
                        pbc = interp(p[b], v[b], p[c], v[c])
                        verts += [pac, pad, pbd, pac, pbd, pbc]
    return verts


def metaballs(n=26, centers=None, extent=2.2):
    """Demo scalar field: sum of 1/r^2 metaballs on an n^3 grid over [-extent,extent]^3.
    Returns (field, spacing, origin, suggested_level)."""
    import numpy as np  # noqa: PLC0415

    if centers is None:
        centers = [(-0.8, 0.0, 0.0, 1.0), (0.9, 0.4, 0.0, 0.9), (0.1, -0.9, 0.6, 0.7)]
    xs = np.linspace(-extent, extent, n)
    f = np.zeros((n, n, n))
    for (cx, cy, cz, w) in centers:
        X, Y, Z = np.meshgrid(xs - cx, xs - cy, xs - cz, indexing="ij")
        f += w / (X * X + Y * Y + Z * Z + 0.08)
    spacing = (2 * extent / (n - 1),) * 3
    origin = (-extent, -extent, -extent)
    return f.tolist(), spacing, origin, 2.2
