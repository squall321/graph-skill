"""cad3d-core 3D data viz — point-cloud-3d (THREE.Points, scalar-colored) and
surface-3d (z=f(x,y) grid mesh, height/color). Both orbit/clip/wireframe via the
existing engine; surface reuses the raw-mesh path (vertices+indices+colors), point
cloud uses the new _buildPoints path. z label/unit required only for the displayed
colorbar quantity (3D axes carry no displayed ticks → no invented units there)."""

from __future__ import annotations

import math

from .base import Recipe


def _xyz(points):
    flat = []
    for p in points:
        if isinstance(p, dict):
            flat += [float(p["x"]), float(p["y"]), float(p["z"])]
        else:
            flat += [float(p[0]), float(p[1]), float(p[2])]
    return flat


class PointCloud3dRecipe(Recipe):
    type_name = "point-cloud-3d"

    def normalize(self, payload, resolved):
        from ..postprocess import field_to_color

        pts = payload.get("points") or []
        flat = _xyz(pts)
        n = len(flat) // 3
        # bbox → default point size
        xs = flat[0::3] or [0]; ys = flat[1::3] or [0]; zs = flat[2::3] or [0]
        diag = math.sqrt((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2 + (max(zs) - min(zs)) ** 2) or 1.0
        model = {"points": [round(v, 6) for v in flat],
                 "size": float(payload.get("point_size") or diag / 220.0)}
        assets = {"model": model}
        scalar = payload.get("scalar")
        if isinstance(scalar, list) and len(scalar) == n and n:
            cmap = payload.get("colormap", "viridis")
            rgb, rng = field_to_color.scalar_to_rgb([float(s) for s in scalar], cmap=cmap)
            model["colors"] = [int(c) for row in rgb for c in row]
            model["zrange"] = [rng[0], rng[1]]
            model["lut"] = field_to_color.lut(cmap, 32)
            zmeta = payload.get("scalar_meta") or payload.get("z") or {}
            assets["z"] = {"label": str(zmeta.get("label", "")), "unit": str(zmeta.get("unit", ""))}
        options = {"theme": (payload.get("options") or {}).get("theme", "auto")}
        if payload.get("title"):
            options["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": assets, "options": options}

    def structural_requires(self, payload):
        miss = []
        pts = payload.get("points") or []
        if len(pts) < 1:
            miss.append({"field": "points", "why": "3D 점 데이터가 없음",
                         "ask": "점 좌표를 주세요: points:[[x,y,z], …] 또는 [{x,y,z}, …]."})
        scalar = payload.get("scalar")
        if isinstance(scalar, list) and scalar:
            if len(scalar) != len(pts):
                miss.append({"field": "scalar", "why": "scalar 길이가 점 개수와 다름",
                             "ask": f"scalar(점별 색상값)는 점 개수({len(pts)})와 같아야 합니다."})
            zmeta = payload.get("scalar_meta") or payload.get("z") or {}
            if not zmeta.get("label") or "unit" not in zmeta:
                miss.append({"field": "z", "why": "색상 스칼라(z) 의미/단위 미상",
                             "ask": "색으로 표현할 양과 단위는? (z={label:'온도', unit:'°C'})"})
        return miss


class Isosurface3dRecipe(Recipe):
    """Isosurface of a 3D scalar field at a level (marching tetrahedra) → orbitable mesh,
    colored by height. field = 3D list [nx][ny][nz] or the preset "metaballs"/"auto"."""

    type_name = "isosurface-3d"

    def normalize(self, payload, resolved):
        import numpy as np  # noqa: PLC0415

        from ..postprocess import field_to_color, isosurface

        field = payload.get("field")
        if field in (None, "auto", "metaballs"):
            f, spacing, origin, lvl = isosurface.metaballs(n=int(payload.get("n", 26)))
            level = float(payload.get("level", lvl))
        else:
            f = field
            spacing = tuple(payload.get("spacing", (1.0, 1.0, 1.0)))
            origin = tuple(payload.get("origin", (0.0, 0.0, 0.0)))
            arr = np.asarray(f, dtype=float)
            level = float(payload.get("level", float((arr.min() + arr.max()) / 2)))

        verts = isosurface.marching_tetrahedra(f, level, spacing, origin)
        v = np.asarray(verts, dtype=float) if verts else np.zeros((0, 3))
        if len(v):
            v = v - (v.max(0) + v.min(0)) / 2          # center for orbit
        ys = v[:, 1].tolist() if len(v) else []
        cmap = payload.get("colormap", "viridis")
        if ys:
            rgb, rng = field_to_color.scalar_to_rgb(ys, cmap=cmap)
            colors = [int(c) for row in rgb for c in row]
        else:
            colors, rng = [], [0, 1]
        model = {"vertices": [round(x, 6) for x in v.reshape(-1).tolist()],
                 "indices": list(range(len(verts))),
                 "colors": colors, "zrange": [rng[0], rng[1]], "lut": field_to_color.lut(cmap, 32)}
        zmeta = payload.get("scalar_meta") or payload.get("z") or {}
        options = {"theme": (payload.get("options") or {}).get("theme", "auto")}
        if payload.get("title"):
            options["title"] = str(payload["title"])
        assets = {"model": model, "z": {"label": str(zmeta.get("label", "높이")), "unit": str(zmeta.get("unit", ""))}}
        return {"engine": resolved.engine, "assets": assets, "options": options}

    def structural_requires(self, payload):
        field = payload.get("field")
        if field is None:
            return [{"field": "field", "why": "3D 스칼라장이 없음",
                     "ask": "3D 스칼라장을 주세요: field:[[[…]]] (nx×ny×nz) + level(등위값). "
                            "데모는 field:'metaballs'."}]
        if isinstance(field, str):
            if field not in ("auto", "metaballs"):
                return [{"field": "field", "why": "알 수 없는 프리셋",
                         "ask": "field는 3D 리스트이거나 'metaballs'(데모)여야 합니다."}]
            return []
        if not (isinstance(field, list) and field and isinstance(field[0], list) and field[0] and isinstance(field[0][0], list)):
            return [{"field": "field", "why": "field가 3D 배열이 아님",
                     "ask": "field는 3차원 배열 [nx][ny][nz] 이어야 합니다."}]
        return []


class Surface3dRecipe(Recipe):
    type_name = "surface-3d"

    def normalize(self, payload, resolved):
        from ..postprocess import field_to_color

        z = payload.get("z_grid") or payload.get("zz") or payload.get("surface")
        ny = len(z); nx = len(z[0]) if ny else 0
        xs = payload.get("x") or list(range(nx))
        ys = payload.get("y") or list(range(ny))
        # 3D mapping: X=x, Y=height(z), Z=y. Center XZ so orbit pivots nicely.
        x0 = (min(xs) + max(xs)) / 2 if xs else 0
        y0 = (min(ys) + max(ys)) / 2 if ys else 0
        verts, scal = [], []
        for i in range(ny):
            for j in range(nx):
                verts += [float(xs[j]) - x0, float(z[i][j]), float(ys[i]) - y0]
                scal.append(float(z[i][j]))
        idx = []
        for i in range(ny - 1):
            for j in range(nx - 1):
                a = i * nx + j; b = a + 1; c = a + nx; d = c + 1
                idx += [a, c, b, b, c, d]
        cmap = payload.get("colormap", "viridis")
        rgb, rng = field_to_color.scalar_to_rgb(scal, cmap=cmap)
        model = {"vertices": [round(v, 6) for v in verts], "indices": idx,
                 "colors": [int(c) for row in rgb for c in row],
                 "zrange": [rng[0], rng[1]], "lut": field_to_color.lut(cmap, 32)}
        zmeta = payload.get("z_meta") or payload.get("zaxis") or {}
        options = {"theme": (payload.get("options") or {}).get("theme", "auto")}
        if payload.get("title"):
            options["title"] = str(payload["title"])
        assets = {"model": model, "z": {"label": str(zmeta.get("label", "z")), "unit": str(zmeta.get("unit", ""))}}
        return {"engine": resolved.engine, "assets": assets, "options": options}

    def structural_requires(self, payload):
        miss = []
        z = payload.get("z_grid") or payload.get("zz") or payload.get("surface")
        if not z or not isinstance(z, list) or not z[0]:
            miss.append({"field": "z_grid", "why": "격자 높이값 z가 없음",
                         "ask": "격자 높이를 주세요: z_grid:[[…행=y…], …] (z_grid[i][j]=점 (x[j],y[i])의 높이). x/y 좌표는 선택."})
            return miss
        nx = len(z[0])
        if any(len(row) != nx for row in z):
            miss.append({"field": "z_grid", "why": "격자 행 길이가 불균일",
                         "ask": "z_grid의 모든 행 길이를 동일하게 맞춰주세요(정규 격자)."})
        zmeta = payload.get("z_meta") or payload.get("zaxis") or {}
        if not zmeta.get("label") or "unit" not in zmeta:
            miss.append({"field": "z_meta", "why": "높이/색 양(z) 의미·단위 미상",
                         "ask": "높이(z)가 나타내는 양과 단위는? (z_meta={label:'변위', unit:'mm'})"})
        return miss
