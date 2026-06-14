"""graph-skill — self-contained interactive HTML visualization generator.

The skill turns *normalized config* (data assets + axis meta + graph-type + background
params) into a *single self-contained .html* rendered by a fixed, version-controlled JS
engine. It is engine-family based: `xy-core` (Canvas 2D) is the first family; future
families (e.g. `cad-viewer` for 3D CAD) sit on the same builder/catalog/validate machinery.

See docs/SKILL-PLAN.md for the full architecture.
"""

from importlib.metadata import PackageNotFoundError, version

try:  # single source of truth — never hardcode __version__
    __version__ = version("graph-skill")
except PackageNotFoundError:  # running from source without install
    __version__ = "0.1.0+src"

# Top-level re-export of the tool functions so callers can do
# ``from graph_skill import types_find, render_payload`` instead of digging into
# ``graph_skill.tools.X``. Lazy (PEP 562 __getattr__) to avoid an import cycle at load time.
_TOOL_FNS = (
    "types_list", "types_find", "schema_get", "validate_inputs", "render", "render_payload",
    "lint_output", "embed_block", "ingest_csv", "ingest_s2p", "resample", "smooth",
)

__all__ = ["__version__", *_TOOL_FNS]


def __getattr__(name: str):
    if name in _TOOL_FNS:
        from . import tools
        return getattr(tools, name)
    raise AttributeError(f"module 'graph_skill' has no attribute '{name}'")
