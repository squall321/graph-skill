"""Locate and read the bundled, version-controlled engine assets.

Engine-family aware: assets live under ``data/engines/<engine>/`` so that future families
(e.g. ``cad-viewer``) sit beside ``xy-core`` without touching the builder. The shell
(template + boot glue) is family-agnostic and lives under ``data/shell/``.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

_DATA = Path(__file__).resolve().parent / "data"


def data_dir() -> Path:
    return _DATA


@lru_cache(maxsize=None)
def _read(rel: str) -> str:
    p = _DATA / rel
    if not p.is_file():
        raise FileNotFoundError(f"bundled asset missing: {rel} ({p})")
    return p.read_text(encoding="utf-8")


def read_shell(name: str) -> str:
    """template.html / boot.js — family-agnostic bootstrap."""
    return _read(f"shell/{name}")


def engine_dir(engine: str) -> Path:
    return _DATA / "engines" / engine


def read_engine_js(engine: str) -> str:
    """Engine JS, with any vendored libraries (data/vendor/<name>) prepended.

    An engine that needs a third-party runtime (e.g. cad3d-core → three.js) lists the vendor
    files, one per line, in ``engines/<engine>/vendor.txt``. They are sha256-pinned via
    ``data/vendor/manifest.json`` (determinism) and inlined ahead of engine.js so the artifact
    stays self-contained."""
    parts = []
    manifest = engine_dir(engine) / "vendor.txt"
    if manifest.is_file():
        for name in manifest.read_text(encoding="utf-8").split("\n"):
            name = name.strip()
            if name and not name.startswith("#"):
                parts.append(_read(f"vendor/{name}"))
    parts.append(_read(f"engines/{engine}/engine.js"))
    return "\n".join(parts)


def read_engine_css(engine: str) -> str:
    return _read(f"engines/{engine}/engine.css")


def read_plugin(engine: str, plugin_id: str) -> str:
    """Plugins are family-scoped (a Canvas overlay != a three.js plugin)."""
    return _read(f"engines/{engine}/plugins/{plugin_id}.js")


def engine_version(engine: str) -> str:
    p = _DATA / "engines" / engine / "ENGINE_VERSION"
    if not p.is_file():
        return "0.0.0"
    return p.read_text(encoding="utf-8").strip()


def engine_code_hash(engine: str) -> str:
    """sha256 over the engine's own source (engine.js + engine.css + plugins/*.js).
    Vendored libs are excluded — they're separately sha256-pinned. The freshness gate binds
    this to ENGINE_VERSION: change code -> hash changes -> the gate fails until you bump the
    version + regenerate the manifest (structurally catches 'edited engine, forgot to bump')."""
    d = engine_dir(engine)
    files = [d / "engine.js", d / "engine.css"]
    plug = d / "plugins"
    if plug.is_dir():
        files += sorted(plug.glob("*.js"))
    h = hashlib.sha256()
    for f in sorted((p for p in files if p.is_file()), key=lambda p: p.relative_to(d).as_posix()):
        h.update(f.relative_to(d).as_posix().encode("utf-8"))
        h.update(b"\0")
        h.update(f.read_bytes())
    return h.hexdigest()
