"""cad3d-core recipes — cad-3d-viewer (geometry) / mesh-result-3d (field-colored).

Builds an inline GLB from mesh input (primitive / vertices+faces / STL·OBJ·GLB path or base64)
via trimesh; optionally colors per-vertex by a nodal scalar (field_to_color) and decimates
geometry to the inline size budget. trimesh is imported lazily — only cad3d render needs it.
"""

from __future__ import annotations

from .base import Recipe


class Cad3dViewerRecipe(Recipe):
    type_name = "cad-3d-viewer"

    def normalize(self, payload, resolved):
        import trimesh  # noqa: PLC0415  (optional [cad3d] dep, lazy)

        from ..postprocess import decimate, field_to_color, mesh_ingest

        mesh = self._build_mesh(payload.get("mesh") or {}, trimesh, mesh_ingest)
        model = {}
        field = payload.get("field")
        if field == "auto":
            field = [float(v) for v in mesh.vertices[:, 1]]   # demo: colour by height (y)
        cmap = payload.get("colormap", "viridis")
        zdom = payload.get("zdomain") or [None, None]
        if isinstance(field, list) and len(field) == len(mesh.vertices):
            rng = mesh_ingest.color_mesh(mesh, field, cmap=cmap, vmin=zdom[0], vmax=zdom[1])
            model["zrange"] = [rng[0], rng[1]]
            model["lut"] = field_to_color.lut(cmap, 32)
        else:
            prof = (payload.get("options") or {}).get("lod", "desktop")
            mesh = decimate.decimate_to(mesh, decimate.lod_target(len(mesh.faces), prof))

        model["glb"] = mesh_ingest.to_glb_b64(mesh)
        options = {"theme": (payload.get("options") or {}).get("theme", "auto")}
        if payload.get("title"):
            options["title"] = str(payload["title"])
        assets = {"model": model}
        zmeta = payload.get("z") or {}
        if zmeta:
            assets["z"] = {"label": str(zmeta.get("label", "")), "unit": str(zmeta.get("unit", ""))}
        return {"engine": resolved.engine, "assets": assets, "options": options}

    @staticmethod
    def _build_mesh(spec, trimesh, mesh_ingest):
        if spec.get("glb_b64"):
            import base64  # noqa: PLC0415
            return mesh_ingest.load_mesh(base64.b64decode(spec["glb_b64"]), file_type="glb")
        if spec.get("path"):
            return mesh_ingest.load_mesh(spec["path"])
        if spec.get("vertices") and spec.get("faces"):
            return trimesh.Trimesh(vertices=spec["vertices"], faces=spec["faces"], process=False)
        prim = spec.get("primitive", "box")
        if prim == "sphere":
            return trimesh.creation.icosphere(subdivisions=int(spec.get("subdivisions", 3)),
                                              radius=float(spec.get("radius", 1.0)))
        if prim == "cylinder":
            return trimesh.creation.cylinder(radius=float(spec.get("radius", 1.0)),
                                             height=float(spec.get("height", 2.0)))
        if prim == "torus":
            return trimesh.creation.torus(float(spec.get("major", 1.0)), float(spec.get("minor", 0.35)))
        return trimesh.creation.box(extents=spec.get("extents", [1.0, 1.0, 1.0]))

    def structural_requires(self, payload):
        spec = payload.get("mesh") or {}
        if not (spec.get("glb_b64") or spec.get("path")
                or (spec.get("vertices") and spec.get("faces")) or spec.get("primitive")):
            return [{"field": "mesh", "why": "3D 메시 입력이 없음",
                     "ask": "메시를 주세요: mesh={path:'model.stl'} 또는 {glb_b64} 또는 {vertices,faces} "
                            "또는 {primitive:'box|sphere|cylinder|torus'}."}]
        return []


class MeshResult3dRecipe(Cad3dViewerRecipe):
    """Field-colored FE/CAE result on a 3D mesh (von Mises, temperature, FoS …)."""

    type_name = "mesh-result-3d"

    def structural_requires(self, payload):
        miss = super().structural_requires(payload)
        field = payload.get("field")
        if not (field == "auto" or (isinstance(field, list) and field)):
            miss.append({"field": "field", "why": "결과 컨투어용 노달 스칼라장이 없음",
                         "ask": "메시 정점별 결과값을 주세요 (field:[노드별 값...] 또는 데모는 'auto')."})
        zmeta = payload.get("z") or {}
        if not zmeta.get("label") or "unit" not in zmeta:
            miss.append({"field": "z", "why": "결과량(z) 의미/단위 미상",
                         "ask": "결과량과 단위는? (z={label:'von Mises σ', unit:'MPa'})"})
        return miss


class Cad3dDeformRecipe(Cad3dViewerRecipe):
    """Deformed-shape view — base mesh + nodal displacement warp (scale slider, undeformed overlay)."""

    type_name = "mesh-deformed-3d"

    def normalize(self, payload, resolved):
        import numpy as np  # noqa: PLC0415
        import trimesh  # noqa: PLC0415

        from ..postprocess import field_to_color, mesh_ingest

        mesh = self._build_mesh(payload.get("mesh") or {"primitive": "box", "extents": [4, 1, 1]}, trimesh, mesh_ingest)
        v = mesh.vertices
        n = len(v)
        size = float(max(v.max(0) - v.min(0))) or 1.0
        disp_in = payload.get("displacement")
        if isinstance(disp_in, list) and len(disp_in) == n:
            disp = np.asarray(disp_in, dtype=float)
        else:                                              # auto cantilever bending in z
            xmin = float(v[:, 0].min())
            length = float(v[:, 0].max() - xmin) or 1.0
            t = (v[:, 0] - xmin) / length
            disp = np.zeros((n, 3))
            disp[:, 2] = t ** 2
            disp *= 0.25 * size / (float(np.abs(disp).max()) or 1.0)
        cmap = payload.get("colormap", "turbo")
        fld = payload.get("field")
        if isinstance(fld, list) and len(fld) == n:
            scal = [float(x) for x in fld]
        else:                                              # default colour = displacement magnitude
            scal = np.linalg.norm(disp, axis=1).tolist()
        rgb, rng = field_to_color.scalar_to_rgb(scal, cmap=cmap)
        surf = mesh_ingest.to_surface(mesh, decimals=5)
        model = {"vertices": surf["vertices"], "indices": surf["indices"],
                 "displacement": [round(x, 6) for x in disp.reshape(-1).tolist()],
                 "colors": np.asarray(rgb, dtype="uint8").reshape(-1).tolist(),
                 "zrange": [rng[0], rng[1]], "lut": field_to_color.lut(cmap, 32),
                 "scale": float(payload.get("scale", 1.0))}
        zmeta = payload.get("z") or {}
        options = {"theme": (payload.get("options") or {}).get("theme", "auto")}
        if payload.get("title"):
            options["title"] = str(payload["title"])
        assets = {"model": model, "z": {"label": str(zmeta.get("label", "|U|")), "unit": str(zmeta.get("unit", "mm"))}}
        return {"engine": resolved.engine, "assets": assets, "options": options}


class Cad3dModeRecipe(Cad3dViewerRecipe):
    """Mode-shape view — base mesh + eigenvector modes (dropdown + play/pause animation)."""

    type_name = "mode-shape-3d"

    def normalize(self, payload, resolved):
        import numpy as np  # noqa: PLC0415
        import trimesh  # noqa: PLC0415

        from ..postprocess import mesh_ingest

        mesh = self._build_mesh(payload.get("mesh") or {"primitive": "box", "extents": [6, 1, 0.5]}, trimesh, mesh_ingest)
        v = mesh.vertices
        n = len(v)
        size = float(max(v.max(0) - v.min(0))) or 1.0
        modes_in = payload.get("modes")
        modes = []
        if isinstance(modes_in, list) and modes_in and isinstance(modes_in[0], dict) and modes_in[0].get("disp"):
            for md in modes_in:
                d = np.asarray(md["disp"], dtype=float)
                modes.append({"name": md.get("name"), "freq": md.get("freq"),
                              "disp": [round(x, 6) for x in d.reshape(-1).tolist()]})
        else:                                              # auto bending modes
            xmin = float(v[:, 0].min())
            length = float(v[:, 0].max() - xmin) or 1.0
            t = (v[:, 0] - xmin) / length
            freqs = payload.get("freqs") or [120, 340, 660]
            for mi in range(3):
                d = np.zeros((n, 3))
                d[:, 2] = np.sin((mi + 1) * np.pi * t)
                d *= 0.2 * size / (float(np.abs(d).max()) or 1.0)
                modes.append({"name": f"Mode {mi + 1}", "freq": (freqs[mi] if mi < len(freqs) else None),
                              "disp": [round(x, 6) for x in d.reshape(-1).tolist()]})
        surf = mesh_ingest.to_surface(mesh, decimals=5)
        model = {"vertices": surf["vertices"], "indices": surf["indices"], "modes": modes,
                 "scale": float(payload.get("scale", 1.0))}
        options = {"theme": (payload.get("options") or {}).get("theme", "auto")}
        if payload.get("title"):
            options["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"model": model}, "options": options}
